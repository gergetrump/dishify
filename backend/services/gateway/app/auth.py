from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from app.config import settings

_jwk_client: PyJWKClient | None = None
_jwk_client_url: str | None = None


def _jwks_url() -> str:
	base = settings.keycloak_url.rstrip("/")
	return f"{base}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"


def _get_jwk_client() -> PyJWKClient:
	global _jwk_client, _jwk_client_url
	url = _jwks_url()
	if _jwk_client is None or _jwk_client_url != url:
		_jwk_client = PyJWKClient(url, cache_keys=True, lifespan=300)
		_jwk_client_url = url
	return _jwk_client


def validate_token(token: str) -> dict[str, Any]:
	client = _get_jwk_client()
	signing_key = client.get_signing_key_from_jwt(token)
	issuer = f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"
	return jwt.decode(
		token,
		signing_key.key,
		algorithms=["RS256"],
		issuer=issuer,
		options={"verify_aud": False},
	)
