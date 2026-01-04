"""Pydantic models for OAuth 2.0 requests and responses."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class OAuthMetadataResponse(BaseModel):
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: Optional[str] = None
    revocation_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    response_types_supported: List[str] = ["code"]
    grant_types_supported: List[str] = ["authorization_code", "refresh_token"]
    token_endpoint_auth_methods_supported: List[str] = ["none"]  # PKCE public clients
    code_challenge_methods_supported: List[str] = ["S256", "plain"]
    scopes_supported: List[str] = ["tasks.read", "tasks.write", "offline_access"]


class AuthorizeRequest(BaseModel):
    """OAuth 2.0 authorization request parameters."""

    response_type: str = Field(..., description="Must be 'code'")
    client_id: str
    redirect_uri: str
    scope: Optional[str] = None
    state: Optional[str] = None
    code_challenge: str = Field(..., description="PKCE code challenge")
    code_challenge_method: str = Field(default="S256", description="PKCE method (S256 or plain)")

    @field_validator("response_type")
    @classmethod
    def validate_response_type(cls, v: str) -> str:
        if v != "code":
            raise ValueError("response_type must be 'code'")
        return v

    @field_validator("code_challenge_method")
    @classmethod
    def validate_code_challenge_method(cls, v: str) -> str:
        if v not in ["S256", "plain"]:
            raise ValueError("code_challenge_method must be 'S256' or 'plain'")
        return v


class TokenRequest(BaseModel):
    """OAuth 2.0 token request parameters."""

    grant_type: str
    code: Optional[str] = None  # Required for authorization_code grant
    redirect_uri: Optional[str] = None  # Required for authorization_code grant
    code_verifier: Optional[str] = None  # Required for PKCE
    refresh_token: Optional[str] = None  # Required for refresh_token grant
    client_id: str

    @field_validator("grant_type")
    @classmethod
    def validate_grant_type(cls, v: str) -> str:
        if v not in ["authorization_code", "refresh_token"]:
            raise ValueError("grant_type must be 'authorization_code' or 'refresh_token'")
        return v


class TokenResponse(BaseModel):
    """OAuth 2.0 token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # Seconds until expiration
    refresh_token: Optional[str] = None
    scope: str


class TokenErrorResponse(BaseModel):
    """OAuth 2.0 error response (RFC 6749 Section 5.2)."""

    error: str  # Error code (invalid_request, invalid_client, etc.)
    error_description: Optional[str] = None
    error_uri: Optional[str] = None


class RevokeRequest(BaseModel):
    """OAuth 2.0 token revocation request (RFC 7009)."""

    token: str
    token_type_hint: Optional[str] = None  # "access_token" or "refresh_token"


class ClientRegistrationRequest(BaseModel):
    """Dynamic client registration request (RFC 7591)."""

    client_name: str
    client_uri: Optional[str] = None
    redirect_uris: List[str]
    grant_types: List[str] = ["authorization_code", "refresh_token"]
    response_types: List[str] = ["code"]
    scope: str = "tasks.read tasks.write offline_access"
    token_endpoint_auth_method: str = "none"  # Public client


class ClientRegistrationResponse(BaseModel):
    """Dynamic client registration response (RFC 7591)."""

    client_id: str
    client_name: str
    client_uri: Optional[str] = None
    redirect_uris: List[str]
    grant_types: List[str]
    response_types: List[str]
    scope: str
    token_endpoint_auth_method: str
    client_id_issued_at: int  # Unix timestamp


class JWK(BaseModel):
    """JSON Web Key (for JWKS endpoint)."""

    kty: str = Field(..., description="Key Type (e.g., 'RSA')")
    use: str = Field(default="sig", description="Public Key Use (e.g., 'sig' for signature)")
    kid: str = Field(..., description="Key ID")
    alg: str = Field(..., description="Algorithm (e.g., 'RS256')")
    n: Optional[str] = Field(None, description="RSA modulus (base64url)")
    e: Optional[str] = Field(None, description="RSA exponent (base64url)")


class JWKSet(BaseModel):
    """JSON Web Key Set (JWKS)."""

    keys: List[JWK]
