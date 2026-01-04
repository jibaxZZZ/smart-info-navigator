"""OAuth middleware for protecting MCP endpoints."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from typing import Optional, Callable
import jwt

from ..database import AsyncSessionLocal
from ..config import settings
from ..models.database import OAuthToken
from ..auth import verify_token
from .token_utils import hash_token
from ..utils.logging import get_logger

logger = get_logger(__name__)


class OAuthMiddleware:
    """
    Middleware to protect endpoints with OAuth Bearer token authentication.

    Usage:
        app.middleware("http")(OAuthMiddleware(protected_paths=["/mcp"]))
    """

    def __init__(self, protected_paths: list[str] = None):
        """
        Initialize OAuth middleware.

        Args:
            protected_paths: List of path prefixes to protect (e.g., ["/mcp", "/api"])
                            If None or empty, all paths except OAuth endpoints are protected.
        """
        self.protected_paths = protected_paths or []

    async def __call__(self, request: Request, call_next: Callable):
        """Process the request and verify OAuth token if needed."""
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path

        # Skip authentication for OAuth endpoints and health/manifest
        if self._is_public_path(path):
            return await call_next(request)

        # Check if path should be protected
        if not self._should_protect(path):
            return await call_next(request)

        # Extract and verify token
        token = self._extract_bearer_token(request)
        if not token:
            logger.warning(f"Missing Authorization header for protected path: {path}")
            return self._unauthorized_response("Missing Authorization header")

        # Verify JWT token
        try:
            payload = verify_token(token, expected_token_type="access_token")
        except jwt.ExpiredSignatureError:
            logger.info(f"Expired token for path: {path}")
            return self._unauthorized_response("Token has expired", error="invalid_token")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token for path {path}: {e}")
            return self._unauthorized_response("Invalid token", error="invalid_token")
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return self._unauthorized_response("Token verification failed")

        if not payload:
            return self._unauthorized_response("Invalid token")

        # Check if token is revoked in database
        async with AsyncSessionLocal() as db:
            token_hash = hash_token(token)
            result = await db.execute(
                select(OAuthToken).where(OAuthToken.access_token_hash == token_hash)
            )
            token_record = result.scalar_one_or_none()

            if not token_record:
                logger.warning("Token not found in database")
                return self._unauthorized_response("Token not found", error="invalid_token")

            if token_record.revoked == "true":
                logger.warning(f"Revoked token used for path: {path}")
                return self._unauthorized_response("Token has been revoked", error="invalid_token")

            if token_record.is_access_token_expired:
                logger.info(f"Expired token in database for path: {path}")
                return self._unauthorized_response("Token has expired", error="invalid_token")

        # Attach user info to request state for downstream use
        request.state.user_id = payload.get("sub")
        request.state.client_id = payload.get("client_id")
        request.state.scope = payload.get("scope")

        logger.debug(f"Authenticated user {request.state.user_id} for path: {path}")

        # Proceed with request
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is a public endpoint that doesn't require authentication."""
        public_paths = [
            "/health",
            "/manifest.json",
            "/.well-known/",
            "/authorize",
            "/login",
            "/token",
            "/revoke",
            "/register",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        return any(path.startswith(prefix) for prefix in public_paths)

    def _should_protect(self, path: str) -> bool:
        """Determine if the path should be protected."""
        if not self.protected_paths:
            # If no specific paths defined, protect everything except public paths
            return True

        # Check if path matches any protected path prefix
        return any(path.startswith(prefix) for prefix in self.protected_paths)

    def _extract_bearer_token(self, request: Request) -> Optional[str]:
        """
        Extract Bearer token from Authorization header.

        Expected format: "Authorization: Bearer <token>"

        Returns:
            Token string if found, None otherwise
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning(f"Invalid Authorization header format: {auth_header[:20]}...")
            return None

        return parts[1]

    def _unauthorized_response(
        self, description: str, error: str = "invalid_request"
    ) -> JSONResponse:
        """
        Create a 401 Unauthorized response with WWW-Authenticate header.

        Follows RFC 6750 (The OAuth 2.0 Authorization Framework: Bearer Token Usage).
        """
        resource_metadata = None
        if settings.public_base_url:
            base_url = settings.public_base_url.rstrip("/")
            resource_metadata = f'{base_url}/.well-known/oauth-protected-resource'

        auth_params = [
            'realm="MCP"',
            f'error="{error}"',
            f'error_description="{description}"',
        ]
        if resource_metadata:
            auth_params.append(f'resource_metadata="{resource_metadata}"')
        auth_params.append('scope="tasks.read tasks.write offline_access"')

        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": error, "error_description": description},
            headers={
                "WWW-Authenticate": "Bearer " + ", ".join(auth_params)
            },
        )
