"""OAuth 2.0 endpoints for ChatGPT Apps integration."""

from fastapi import APIRouter, HTTPException, status, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import secrets

from ..database import get_db
from ..config import settings
from ..models.database import (
    User,
    OAuthClient,
    OAuthAuthorizationCode,
    OAuthToken,
)
from ..models.oauth import (
    OAuthMetadataResponse,
    TokenRequest,
    TokenResponse,
    TokenErrorResponse,
    RevokeRequest,
    ClientRegistrationRequest,
    ClientRegistrationResponse,
    JWKSet,
)
from ..auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_pkce_challenge,
    generate_random_string,
)
from .token_utils import hash_token
from ..utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Helper functions
def oauth_error_response(error: str, description: Optional[str] = None, status_code: int = 400):
    """Create OAuth error response."""
    return JSONResponse(
        status_code=status_code,
        content=TokenErrorResponse(
            error=error,
            error_description=description,
        ).model_dump(exclude_none=True),
    )


async def get_client_by_client_id(db: AsyncSession, client_id: str) -> Optional[OAuthClient]:
    """Get OAuth client by client_id."""
    result = await db.execute(select(OAuthClient).where(OAuthClient.client_id == client_id))
    return result.scalar_one_or_none()


# OAuth 2.0 Metadata Endpoint
@router.get("/.well-known/oauth-protected-resource", response_model=OAuthMetadataResponse)
async def oauth_metadata():
    """
    OAuth 2.0 Authorization Server Metadata endpoint (RFC 8414).

    This is discovered by ChatGPT to understand available endpoints and capabilities.
    """
    base_url = settings.public_base_url

    metadata = OAuthMetadataResponse(
        issuer=settings.oauth_issuer or base_url,
        authorization_endpoint=f"{base_url}/authorize",
        token_endpoint=f"{base_url}/token",
        registration_endpoint=f"{base_url}/register",
        revocation_endpoint=f"{base_url}/revoke",
        jwks_uri=f"{base_url}/.well-known/jwks.json" if settings.jwt_algorithm.startswith("RS") else None,
        response_types_supported=["code"],
        grant_types_supported=["authorization_code", "refresh_token"],
        token_endpoint_auth_methods_supported=["none"],  # PKCE public clients
        code_challenge_methods_supported=["S256", "plain"],
        scopes_supported=["tasks.read", "tasks.write", "offline_access"],
    )

    logger.info("OAuth metadata requested")
    return metadata


# Authorization Endpoint
@router.get("/authorize")
async def authorize(
    response_type: str = Query(..., description="Must be 'code'"),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(default="tasks.read tasks.write offline_access"),
    state: Optional[str] = Query(None),
    code_challenge: str = Query(..., description="PKCE code challenge"),
    code_challenge_method: str = Query(default="S256", description="S256 or plain"),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth 2.0 authorization endpoint with PKCE.

    In production, this would render a consent screen. For now, it auto-approves.
    """
    # Validate response_type
    if response_type != "code":
        return oauth_error_response("unsupported_response_type", "Only 'code' is supported")

    # Validate code_challenge_method
    if code_challenge_method not in ["S256", "plain"]:
        return oauth_error_response("invalid_request", "code_challenge_method must be S256 or plain")

    # Get OAuth client
    client = await get_client_by_client_id(db, client_id)
    if not client:
        logger.warning(f"Unknown client_id: {client_id}")
        return oauth_error_response("invalid_client", "Unknown client_id", status_code=401)

    # Validate redirect_uri
    allowed_uris = json.loads(client.redirect_uris)
    if redirect_uri not in allowed_uris:
        logger.warning(f"Invalid redirect_uri: {redirect_uri} not in {allowed_uris}")
        return oauth_error_response("invalid_request", "Invalid redirect_uri")

    # TODO: In production, render consent screen and get user approval
    # For now, we auto-create or get the mock user
    result = await db.execute(select(User).where(User.oauth_sub == "chatgpt_user_mock"))
    user = result.scalar_one_or_none()

    if not user:
        # Create mock user
        user = User(
            oauth_sub="chatgpt_user_mock",
            email="chatgpt@example.com",
            name="ChatGPT User",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Created mock user: {user.id}")

    # Generate authorization code
    auth_code = generate_random_string(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.authorization_code_expire_minutes
    )

    code_record = OAuthAuthorizationCode(
        code=auth_code,
        client_id=client.id,
        user_id=user.id,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=expires_at,
        used="false",
    )
    db.add(code_record)
    await db.commit()

    logger.info(f"Issued authorization code for user {user.id}, client {client_id}")

    # Redirect back to client with code and state
    redirect_url = f"{redirect_uri}?code={auth_code}"
    if state:
        redirect_url += f"&state={state}"

    return RedirectResponse(url=redirect_url, status_code=302)


# Token Endpoint
@router.post("/token", response_model=TokenResponse)
async def token(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    client_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth 2.0 token endpoint.

    Handles both authorization_code and refresh_token grants.
    """
    # Validate grant_type
    if grant_type not in ["authorization_code", "refresh_token"]:
        return oauth_error_response(
            "unsupported_grant_type",
            "Only 'authorization_code' and 'refresh_token' are supported",
        )

    # Get client
    client = await get_client_by_client_id(db, client_id)
    if not client:
        return oauth_error_response("invalid_client", "Unknown client_id", status_code=401)

    # Handle authorization_code grant
    if grant_type == "authorization_code":
        if not code or not redirect_uri or not code_verifier:
            return oauth_error_response(
                "invalid_request",
                "code, redirect_uri, and code_verifier are required for authorization_code grant",
            )

        # Get authorization code
        result = await db.execute(
            select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code)
        )
        code_record = result.scalar_one_or_none()

        if not code_record:
            return oauth_error_response("invalid_grant", "Invalid authorization code")

        # Validate code
        if code_record.used == "true":
            logger.warning(f"Authorization code already used: {code}")
            return oauth_error_response("invalid_grant", "Authorization code already used")

        if code_record.is_expired:
            logger.warning(f"Authorization code expired: {code}")
            return oauth_error_response("invalid_grant", "Authorization code expired")

        if code_record.redirect_uri != redirect_uri:
            logger.warning(f"redirect_uri mismatch: {redirect_uri} != {code_record.redirect_uri}")
            return oauth_error_response("invalid_grant", "redirect_uri mismatch")

        # Verify PKCE
        if not verify_pkce_challenge(
            code_verifier, code_record.code_challenge, code_record.code_challenge_method
        ):
            logger.warning("PKCE verification failed")
            return oauth_error_response("invalid_grant", "Invalid code_verifier")

        # Mark code as used
        code_record.used = "true"

        # Create tokens
        user_id = code_record.user_id
        scope = code_record.scope
        access_token_str, access_token_expires = create_access_token(
            user_id, client.client_id, scope
        )
        refresh_token_str, refresh_token_expires = create_refresh_token(
            user_id, client.client_id, scope
        )

        access_token_hash = hash_token(access_token_str)
        refresh_token_hash = hash_token(refresh_token_str)

        # Store tokens in database
        token_record = OAuthToken(
            access_token=access_token_str,
            refresh_token=refresh_token_str,
            access_token_hash=access_token_hash,
            refresh_token_hash=refresh_token_hash,
            token_type="Bearer",
            client_id=client.id,
            user_id=user_id,
            scope=scope,
            access_token_expires_at=access_token_expires,
            refresh_token_expires_at=refresh_token_expires,
            revoked="false",
        )
        db.add(token_record)
        await db.commit()

        logger.info(f"Issued tokens for user {user_id}, client {client_id}")

        return TokenResponse(
            access_token=access_token_str,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            refresh_token=refresh_token_str,
            scope=scope,
        )

    # Handle refresh_token grant
    elif grant_type == "refresh_token":
        if not refresh_token:
            return oauth_error_response("invalid_request", "refresh_token is required")

        # Verify refresh token
        try:
            payload = verify_token(refresh_token, expected_token_type="refresh_token")
        except Exception as e:
            logger.warning(f"Invalid refresh token: {e}")
            return oauth_error_response("invalid_grant", "Invalid refresh token")

        if not payload:
            return oauth_error_response("invalid_grant", "Invalid refresh token")

        # Get token from database
        refresh_token_hash = hash_token(refresh_token)
        result = await db.execute(
            select(OAuthToken).where(OAuthToken.refresh_token_hash == refresh_token_hash)
        )
        token_record = result.scalar_one_or_none()

        if not token_record or token_record.revoked == "true":
            return oauth_error_response("invalid_grant", "Token revoked or not found")

        if token_record.is_refresh_token_expired:
            return oauth_error_response("invalid_grant", "Refresh token expired")

        # Create new access token
        user_id = token_record.user_id
        scope = token_record.scope
        new_access_token, new_access_expires = create_access_token(
            user_id, client.client_id, scope
        )

        # Update token record
        token_record.access_token = new_access_token
        token_record.access_token_hash = hash_token(new_access_token)
        token_record.access_token_expires_at = new_access_expires
        await db.commit()

        logger.info(f"Refreshed access token for user {user_id}")

        return TokenResponse(
            access_token=new_access_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            refresh_token=refresh_token,  # Return same refresh token
            scope=scope,
        )


# Token Revocation Endpoint
@router.post("/revoke")
async def revoke(
    token: str = Form(...),
    token_type_hint: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth 2.0 token revocation endpoint (RFC 7009).
    """
    # Find token in database (check both access_token and refresh_token)
    token_hash = hash_token(token)
    result = await db.execute(
        select(OAuthToken).where(
            (OAuthToken.access_token_hash == token_hash)
            | (OAuthToken.refresh_token_hash == token_hash)
        )
    )
    token_record = result.scalar_one_or_none()

    if token_record:
        token_record.revoked = "true"
        await db.commit()
        logger.info(f"Revoked token for user {token_record.user_id}")

    # Per RFC 7009, return 200 OK even if token doesn't exist
    return JSONResponse(content={}, status_code=200)


# Client Registration Endpoint (Dynamic Client Registration)
@router.post("/register", response_model=ClientRegistrationResponse)
async def register_client(
    request: ClientRegistrationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Dynamic client registration endpoint (RFC 7591).

    Allows ChatGPT to register as an OAuth client.
    """
    # Generate client_id
    client_id = f"chatgpt_{generate_random_string(16)}"

    # Create OAuth client
    client = OAuthClient(
        client_id=client_id,
        client_name=request.client_name,
        client_uri=request.client_uri,
        redirect_uris=json.dumps(request.redirect_uris),
        grant_types=json.dumps(request.grant_types),
        response_types=json.dumps(request.response_types),
        scope=request.scope,
        token_endpoint_auth_method=request.token_endpoint_auth_method,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)

    logger.info(f"Registered new OAuth client: {client_id}")

    return ClientRegistrationResponse(
        client_id=client.client_id,
        client_name=client.client_name,
        client_uri=client.client_uri,
        redirect_uris=json.loads(client.redirect_uris),
        grant_types=json.loads(client.grant_types),
        response_types=json.loads(client.response_types),
        scope=client.scope,
        token_endpoint_auth_method=client.token_endpoint_auth_method,
        client_id_issued_at=int(client.created_at.timestamp()),
    )


# JWKS Endpoint (for RS256)
@router.get("/.well-known/jwks.json", response_model=JWKSet)
async def jwks():
    """
    JSON Web Key Set endpoint (for RS256 signature verification).

    Only needed if using RS256. For HS256, ChatGPT won't call this.
    """
    if not settings.jwt_algorithm.startswith("RS"):
        raise HTTPException(
            status_code=404,
            detail="JWKS endpoint only available when using RS256/RS384/RS512",
        )

    # TODO: Implement JWKS key extraction from RSA public key
    # For now, return empty key set
    logger.warning("JWKS endpoint not fully implemented - returning empty key set")
    return JWKSet(keys=[])
