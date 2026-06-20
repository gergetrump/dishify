from __future__ import annotations

import time
from typing import Any

import jwt
from jwt import PyJWKClient

from app.config import settings

_jwk_client: PyJWKClient | None = None
_jwk_client_url: str | None = None


def _realm_base() -> str:
	return settings.keycloak_public_realm_url


def _jwks_url() -> str:
	return f"{settings.keycloak_internal_realm_url}/protocol/openid-connect/certs"


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
	return jwt.decode(
		token,
		signing_key.key,
		algorithms=["RS256"],
		issuer=_realm_base(),
		options={"verify_aud": False},
	)


def user_id_from_claims(claims: dict[str, Any]) -> str:
	user_id = claims.get("sub")
	if not user_id:
		raise ValueError("Token missing subject claim")
	return str(user_id)
