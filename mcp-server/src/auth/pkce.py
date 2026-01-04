"""PKCE (Proof Key for Code Exchange) validation utilities."""

import hashlib
import base64
import secrets
from ..utils.logging import get_logger

logger = get_logger(__name__)


def generate_random_string(length: int = 32) -> str:
    """
    Generate a cryptographically secure random string.

    Args:
        length: Length of the random string (default: 32 characters)

    Returns:
        URL-safe random string
    """
    return secrets.token_urlsafe(length)


def _base64_url_encode(data: bytes) -> str:
    """
    Base64 URL-safe encoding without padding.

    Args:
        data: Bytes to encode

    Returns:
        Base64 URL-safe string without '=' padding
    """
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def compute_code_challenge(code_verifier: str, method: str = "S256") -> str:
    """
    Compute PKCE code challenge from code verifier.

    Args:
        code_verifier: The code verifier string (43-128 characters)
        method: Challenge method - "S256" (SHA-256) or "plain"

    Returns:
        Code challenge string

    Raises:
        ValueError: If code_verifier length is invalid or method is unsupported
    """
    if not (43 <= len(code_verifier) <= 128):
        raise ValueError(f"code_verifier must be 43-128 characters, got {len(code_verifier)}")

    if method == "S256":
        # SHA-256 hash of code_verifier, then base64url encode
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        return _base64_url_encode(digest)
    elif method == "plain":
        # Plain method: challenge = verifier
        return code_verifier
    else:
        raise ValueError(f"Unsupported code_challenge_method: {method}")


def verify_pkce_challenge(
    code_verifier: str,
    code_challenge: str,
    code_challenge_method: str = "S256",
) -> bool:
    """
    Verify PKCE code_verifier matches the stored code_challenge.

    This is called during the token exchange step to validate that the client
    presenting the authorization code is the same client that initiated the
    authorization request.

    Args:
        code_verifier: The code_verifier sent by client during token request
        code_challenge: The code_challenge stored during authorization request
        code_challenge_method: The method used ("S256" or "plain")

    Returns:
        True if verification succeeds, False otherwise
    """
    try:
        # Validate code_verifier length (RFC 7636)
        if not (43 <= len(code_verifier) <= 128):
            logger.warning(f"Invalid code_verifier length: {len(code_verifier)} (must be 43-128)")
            return False

        # Compute expected challenge from verifier
        computed_challenge = compute_code_challenge(code_verifier, code_challenge_method)

        # Constant-time comparison to prevent timing attacks
        is_valid = secrets.compare_digest(computed_challenge, code_challenge)

        if is_valid:
            logger.info("PKCE verification successful")
        else:
            logger.warning("PKCE verification failed: challenge mismatch")

        return is_valid

    except ValueError as e:
        logger.error(f"PKCE verification error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during PKCE verification: {e}")
        return False
