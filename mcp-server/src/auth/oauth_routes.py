"""OAuth 2.0 endpoints for ChatGPT Apps integration."""

from fastapi import APIRouter, HTTPException, status, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import secrets
import jwt
from urllib.parse import urlparse

from ..database import get_db
from ..config import settings
from ..models.database import (
    User,
    OAuthClient,
    OAuthAuthorizationCode,
    OAuthToken,
)
from ..models.oauth import (
    OAuthProtectedResourceMetadataResponse,
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


def _normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def _validate_resource(resource: Optional[str]) -> Optional[JSONResponse]:
    if not resource:
        return None
    expected = _normalize_base_url(settings.public_base_url)
    if not expected:
        logger.warning("Resource validation skipped because PUBLIC_BASE_URL is empty")
        return None
    if _normalize_base_url(resource) != expected:
        logger.warning(f"Invalid resource requested: {resource} (expected {expected})")
        return oauth_error_response("invalid_target", "Unknown resource")
    return None


def _demo_login_enabled() -> bool:
    return bool(settings.demo_username and settings.demo_password)


def _create_demo_session_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.demo_session_ttl_minutes)
    payload = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "demo_session",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _get_demo_username_from_cookie(request: Request) -> Optional[str]:
    token = request.cookies.get("demo_session")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except Exception:
        return None
    if payload.get("type") != "demo_session":
        return None
    return payload.get("sub")


def _safe_return_path(return_url: str | None) -> str:
    if not return_url:
        return "/authorize"
    parsed = urlparse(return_url)
    if parsed.scheme or parsed.netloc:
        return "/authorize"
    if not return_url.startswith("/authorize"):
        return "/authorize"
    return return_url


def _login_page(return_url: str, error: Optional[str] = None) -> str:
    error_html = f"<p style='color:#b91c1c;'>{error}</p>" if error else ""
    return f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Sign in</title>
    <style>
      body {{ font-family: system-ui, -apple-system, sans-serif; margin: 40px; }}
      .card {{ max-width: 420px; margin: 0 auto; padding: 24px; border: 1px solid #e5e7eb; border-radius: 12px; }}
      label {{ display: block; margin: 12px 0 6px; font-weight: 600; }}
      input {{ width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; }}
      button {{ margin-top: 16px; width: 100%; padding: 10px; border: 0; border-radius: 8px; background: #111827; color: #fff; font-weight: 600; }}
      .hint {{ color: #6b7280; font-size: 14px; }}
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Sign in</h1>
      <p class="hint">Use the demo credentials provided for App review.</p>
      {error_html}
      <form method="post" action="/login">
        <input type="hidden" name="return_url" value="{return_url}" />
        <label for="username">Username</label>
        <input id="username" name="username" type="text" required />
        <label for="password">Password</label>
        <input id="password" name="password" type="password" required />
        <button type="submit">Continue</button>
      </form>
    </div>
  </body>
</html>
""".strip()


# OAuth 2.0 Protected Resource Metadata Endpoint
@router.get(
    "/.well-known/oauth-protected-resource",
    response_model=OAuthProtectedResourceMetadataResponse,
)
async def oauth_protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata (RFC 9728).

    This is discovered by ChatGPT to locate the authorization server.
    """
    resource = _normalize_base_url(settings.public_base_url)
    issuer = _normalize_base_url(settings.oauth_issuer or settings.public_base_url)

    metadata = OAuthProtectedResourceMetadataResponse(
        resource=resource,
        authorization_servers=[issuer],
        scopes_supported=["tasks.read", "tasks.write", "offline_access"],
    )

    logger.info("OAuth protected-resource metadata requested")
    return metadata


# OAuth 2.0 Authorization Server Metadata Endpoint
@router.get("/.well-known/oauth-authorization-server", response_model=OAuthMetadataResponse)
@router.get("/.well-known/openid-configuration", response_model=OAuthMetadataResponse)
async def oauth_authorization_server_metadata():
    """
    OAuth 2.0 Authorization Server Metadata endpoint (RFC 8414).
    """
    issuer = _normalize_base_url(settings.oauth_issuer or settings.public_base_url)

    metadata = OAuthMetadataResponse(
        issuer=issuer,
        authorization_endpoint=f"{issuer}/authorize",
        token_endpoint=f"{issuer}/token",
        registration_endpoint=f"{issuer}/register",
        revocation_endpoint=f"{issuer}/revoke",
        jwks_uri=f"{issuer}/.well-known/jwks.json" if settings.jwt_algorithm.startswith("RS") else None,
        response_types_supported=["code"],
        grant_types_supported=["authorization_code", "refresh_token"],
        token_endpoint_auth_methods_supported=["none"],  # PKCE public clients
        code_challenge_methods_supported=["S256", "plain"],
        scopes_supported=["tasks.read", "tasks.write", "offline_access"],
    )

    logger.info("OAuth authorization-server metadata requested")
    return metadata


# Authorization Endpoint
@router.get("/authorize")
async def authorize(
    request: Request,
    response_type: str = Query(..., description="Must be 'code'"),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(default="tasks.read tasks.write offline_access"),
    state: Optional[str] = Query(None),
    code_challenge: str = Query(..., description="PKCE code challenge"),
    code_challenge_method: str = Query(default="S256", description="S256 or plain"),
    resource: Optional[str] = Query(default=None, description="Resource indicator (RFC 8707)"),
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

    resource_error = _validate_resource(resource)
    if resource_error:
        return resource_error

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

    demo_username = None
    if _demo_login_enabled():
        demo_username = _get_demo_username_from_cookie(request)
        if not demo_username:
            return_url = request.url.path
            if request.url.query:
                return_url += f"?{request.url.query}"
            return HTMLResponse(content=_login_page(return_url), status_code=200)

    # TODO: In production, render consent screen and get user approval
    # For now, we auto-create or get the mock/demo user
    oauth_sub = f"demo:{demo_username}" if demo_username else "chatgpt_user_mock"
    result = await db.execute(select(User).where(User.oauth_sub == oauth_sub))
    user = result.scalar_one_or_none()

    if not user:
        # Create mock/demo user
        user = User(
            oauth_sub=oauth_sub,
            email=f"{demo_username}@example.com" if demo_username else "chatgpt@example.com",
            name=demo_username or "ChatGPT User",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Created user: {user.id}")

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


@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    return_url: Optional[str] = Form(None),
):
    if not _demo_login_enabled():
        return oauth_error_response("access_denied", "Demo login is not configured", status_code=403)

    safe_return_url = _safe_return_path(return_url)
    if username != settings.demo_username or password != settings.demo_password:
        return HTMLResponse(content=_login_page(safe_return_url, error="Invalid username or password."), status_code=401)

    token = _create_demo_session_token(username)
    response = RedirectResponse(url=safe_return_url, status_code=302)
    secure_cookie = settings.public_base_url.startswith("https://")
    response.set_cookie(
        "demo_session",
        token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=settings.demo_session_ttl_minutes * 60,
    )
    return response


# Token Endpoint
@router.post("/token", response_model=TokenResponse)
async def token(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    client_id: str = Form(...),
    resource: Optional[str] = Form(None),
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

    resource_error = _validate_resource(resource)
    if resource_error:
        return resource_error

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
