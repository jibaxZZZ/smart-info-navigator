"""Unit tests for OAuth 2.0 endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta, timezone
import json

from src.http_app import create_app
from src.config import settings
from sqlalchemy import text

from src.database import engine, AsyncSessionLocal
from src.models.database import User, OAuthClient
from src.auth import create_access_token, generate_random_string


@pytest_asyncio.fixture(scope="function")
async def test_db(setup_database):
    """Ensure database is initialized and cleanup OAuth tables per test."""
    yield
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE oauth_tokens, oauth_authorization_codes, oauth_clients "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture
async def async_client(test_db):
    """Create async test client with database setup."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def test_oauth_client(test_db):
    """Create a test OAuth client in the database."""
    async with AsyncSessionLocal() as db:
        oauth_client = OAuthClient(
            client_id="test_client_id",
            client_name="Test ChatGPT App",
            client_uri="https://chatgpt.com",
            redirect_uris=json.dumps(["https://chatgpt.com/aip/g-test/oauth/callback"]),
            grant_types=json.dumps(["authorization_code", "refresh_token"]),
            response_types=json.dumps(["code"]),
            scope="tasks.read tasks.write offline_access",
            token_endpoint_auth_method="none",
        )
        db.add(oauth_client)
        await db.commit()
        await db.refresh(oauth_client)
        return oauth_client


class TestOAuthMetadata:
    """Test OAuth metadata endpoint."""

    @pytest.mark.asyncio
    async def test_oauth_metadata(self, async_client):
        """Test /.well-known/oauth-protected-resource returns correct metadata."""
        response = await async_client.get("/.well-known/oauth-protected-resource")
        assert response.status_code == 200

        data = response.json()
        assert data["issuer"] == settings.oauth_issuer or settings.public_base_url
        assert data["authorization_endpoint"] == f"{settings.public_base_url}/authorize"
        assert data["token_endpoint"] == f"{settings.public_base_url}/token"
        assert data["revocation_endpoint"] == f"{settings.public_base_url}/revoke"
        assert data["registration_endpoint"] == f"{settings.public_base_url}/register"
        assert "authorization_code" in data["grant_types_supported"]
        assert "refresh_token" in data["grant_types_supported"]
        assert "S256" in data["code_challenge_methods_supported"]
        assert "none" in data["token_endpoint_auth_methods_supported"]


class TestClientRegistration:
    """Test dynamic client registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_client(self, async_client):
        """Test POST /register creates a new OAuth client."""
        response = await async_client.post(
            "/register",
            json={
                "client_name": "Test ChatGPT",
                "redirect_uris": ["https://chatgpt.com/aip/g-test/oauth/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": "tasks.read tasks.write offline_access",
                "token_endpoint_auth_method": "none",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["client_name"] == "Test ChatGPT"
        assert "client_id" in data
        assert data["client_id"].startswith("chatgpt_")
        assert data["token_endpoint_auth_method"] == "none"
        assert "client_id_issued_at" in data


class TestAuthorizeEndpoint:
    """Test /authorize endpoint."""

    @pytest.mark.asyncio
    async def test_authorize_with_valid_params(self, async_client, test_oauth_client):
        """Test GET /authorize with valid parameters returns authorization code."""
        response = await async_client.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": test_oauth_client.client_id,
                "redirect_uri": "https://chatgpt.com/aip/g-test/oauth/callback",
                "scope": "tasks.read tasks.write",
                "state": "random_state_string",
                "code_challenge": "test_code_challenge",
                "code_challenge_method": "S256",
            },
            follow_redirects=False,
        )

        # Should redirect to callback with code
        assert response.status_code == 302
        location = response.headers["location"]
        assert location.startswith("https://chatgpt.com/aip/g-test/oauth/callback?code=")
        assert "state=random_state_string" in location

    @pytest.mark.asyncio
    async def test_authorize_with_invalid_client_id(self, async_client):
        """Test /authorize with unknown client_id returns error."""
        response = await async_client.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": "invalid_client_id",
                "redirect_uri": "https://chatgpt.com/callback",
                "code_challenge": "test_challenge",
                "code_challenge_method": "S256",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "invalid_client"

    @pytest.mark.asyncio
    async def test_authorize_with_invalid_redirect_uri(self, async_client, test_oauth_client):
        """Test /authorize with unregistered redirect_uri returns error."""
        response = await async_client.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": test_oauth_client.client_id,
                "redirect_uri": "https://evil.com/callback",  # Not registered
                "code_challenge": "test_challenge",
                "code_challenge_method": "S256",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_request"
        assert "redirect_uri" in data["error_description"]


class TestTokenEndpoint:
    """Test /token endpoint."""

    @pytest.mark.asyncio
    async def test_token_with_unsupported_grant_type(self, async_client):
        """Test POST /token with unsupported grant_type returns error."""
        response = await async_client.post(
            "/token",
            data={
                "grant_type": "client_credentials",  # Not supported
                "client_id": "test_client",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "unsupported_grant_type"

    @pytest.mark.asyncio
    async def test_token_with_missing_parameters(self, async_client, test_oauth_client):
        """Test POST /token with missing required parameters returns error."""
        response = await async_client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "client_id": test_oauth_client.client_id,
                # Missing: code, redirect_uri, code_verifier
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_request"


class TestRevokeEndpoint:
    """Test /revoke endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_returns_200_even_for_unknown_token(self, async_client):
        """Test POST /revoke returns 200 OK even if token doesn't exist (per RFC 7009)."""
        response = await async_client.post(
            "/revoke",
            data={
                "token": "nonexistent_token",
            },
        )

        assert response.status_code == 200


class TestJWTTokens:
    """Test JWT token generation and verification."""

    @pytest.mark.asyncio
    async def test_create_access_token(self):
        """Test access token creation."""
        from uuid import uuid4

        user_id = uuid4()
        client_id = "test_client"
        scope = "tasks.read tasks.write"

        token, expires_at = create_access_token(user_id, client_id, scope)

        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_pkce_verification(self):
        """Test PKCE code_verifier validation."""
        from src.auth import verify_pkce_challenge, compute_code_challenge

        code_verifier = generate_random_string(43)
        code_challenge = compute_code_challenge(code_verifier, "S256")

        # Valid verifier should pass
        assert verify_pkce_challenge(code_verifier, code_challenge, "S256") is True

        # Invalid verifier should fail
        wrong_verifier = generate_random_string(43)
        assert verify_pkce_challenge(wrong_verifier, code_challenge, "S256") is False

    @pytest.mark.asyncio
    async def test_pkce_plain_method(self):
        """Test PKCE with plain method."""
        from src.auth import verify_pkce_challenge, compute_code_challenge

        code_verifier = generate_random_string(43)
        code_challenge = compute_code_challenge(code_verifier, "plain")

        # For plain method, challenge == verifier
        assert code_challenge == code_verifier
        assert verify_pkce_challenge(code_verifier, code_challenge, "plain") is True
