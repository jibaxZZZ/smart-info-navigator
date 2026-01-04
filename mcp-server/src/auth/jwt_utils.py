"""JWT token generation and validation utilities."""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from uuid import UUID
from pathlib import Path
from ..config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _load_rsa_key(key_path: Optional[str], key_type: str = "private") -> Optional[str]:
    """Load RSA key from file path."""
    if not key_path:
        return None

    try:
        key_file = Path(key_path)
        if not key_file.exists():
            logger.warning(f"RSA {key_type} key file not found: {key_path}")
            return None

        with open(key_file, "r") as f:
            key_content = f.read()

        logger.info(f"Successfully loaded RSA {key_type} key from {key_path}")
        return key_content
    except Exception as e:
        logger.error(f"Failed to load RSA {key_type} key: {e}")
        return None


def _get_signing_key() -> str:
    """Get the signing key for JWT (RSA private key or HS256 secret)."""
    if settings.jwt_algorithm.startswith("RS"):
        # RS256/RS384/RS512 - use RSA private key
        private_key = _load_rsa_key(settings.jwt_private_key_path, "private")
        if not private_key:
            logger.warning("RSA private key not available, falling back to HS256 with jwt_secret")
            return settings.jwt_secret
        return private_key
    else:
        # HS256/HS384/HS512 - use shared secret
        return settings.jwt_secret


def _get_verification_key() -> str:
    """Get the verification key for JWT (RSA public key or HS256 secret)."""
    if settings.jwt_algorithm.startswith("RS"):
        # RS256/RS384/RS512 - use RSA public key
        public_key = _load_rsa_key(settings.jwt_public_key_path, "public")
        if not public_key:
            logger.warning("RSA public key not available, falling back to HS256 with jwt_secret")
            return settings.jwt_secret
        return public_key
    else:
        # HS256/HS384/HS512 - use shared secret
        return settings.jwt_secret


def create_access_token(
    user_id: UUID,
    client_id: str,
    scope: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    """
    Create a JWT access token.

    Args:
        user_id: User UUID
        client_id: OAuth client ID
        scope: Space-separated scope string
        expires_delta: Custom expiration time (defaults to settings.access_token_expire_minutes)

    Returns:
        Tuple of (token_string, expiration_datetime)
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    now = datetime.now(timezone.utc)
    expires_at = now + expires_delta

    payload = {
        "sub": str(user_id),  # Subject: user ID
        "client_id": client_id,  # OAuth client
        "scope": scope,  # Granted scopes
        "iss": settings.oauth_issuer or settings.public_base_url,  # Issuer
        "aud": settings.public_base_url,  # Audience
        "iat": int(now.timestamp()),  # Issued at
        "exp": int(expires_at.timestamp()),  # Expiration
        "token_type": "access_token",
    }

    signing_key = _get_signing_key()
    token = jwt.encode(payload, signing_key, algorithm=settings.jwt_algorithm)

    logger.info(f"Created access token for user {user_id} with scope '{scope}', expires at {expires_at}")
    return token, expires_at


def create_refresh_token(
    user_id: UUID,
    client_id: str,
    scope: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    """
    Create a JWT refresh token.

    Args:
        user_id: User UUID
        client_id: OAuth client ID
        scope: Space-separated scope string
        expires_delta: Custom expiration time (defaults to settings.refresh_token_expire_days)

    Returns:
        Tuple of (token_string, expiration_datetime)
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    now = datetime.now(timezone.utc)
    expires_at = now + expires_delta

    payload = {
        "sub": str(user_id),
        "client_id": client_id,
        "scope": scope,
        "iss": settings.oauth_issuer or settings.public_base_url,
        "aud": settings.public_base_url,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "token_type": "refresh_token",
    }

    signing_key = _get_signing_key()
    token = jwt.encode(payload, signing_key, algorithm=settings.jwt_algorithm)

    logger.info(f"Created refresh token for user {user_id}, expires at {expires_at}")
    return token, expires_at


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token without verification (for debugging/inspection).

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except jwt.DecodeError as e:
        logger.error(f"Failed to decode token: {e}")
        return None


def verify_token(token: str, expected_token_type: str = "access_token") -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string
        expected_token_type: Expected token type ("access_token" or "refresh_token")

    Returns:
        Decoded and verified payload, or None if invalid/expired

    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        verification_key = _get_verification_key()

        payload = jwt.decode(
            token,
            verification_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.public_base_url,
            issuer=settings.oauth_issuer or settings.public_base_url,
        )

        # Verify token type matches expectation
        if payload.get("token_type") != expected_token_type:
            logger.warning(
                f"Token type mismatch: expected '{expected_token_type}', got '{payload.get('token_type')}'"
            )
            return None

        logger.debug(f"Successfully verified {expected_token_type} for user {payload.get('sub')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.info(f"Token expired: {expected_token_type}")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None
