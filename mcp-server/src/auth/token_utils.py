"""Token utilities for hashing and lookup."""

import hashlib


def hash_token(token: str) -> str:
    """Return a SHA-256 hex digest for the token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
