"""Keycloak auth helpers for FastAPI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt


@dataclass(frozen=True)
class KeycloakConfig:
    issuer: str
    audience: str | None
    jwks_url: str


@lru_cache(maxsize=1)
def _load_keycloak_config() -> KeycloakConfig:
    base_url = (os.getenv("KEYCLOAK_URL") or "").rstrip("/")
    realm = (os.getenv("KEYCLOAK_REALM") or "").strip()
    if not base_url or not realm:
        raise RuntimeError("KEYCLOAK_URL and KEYCLOAK_REALM must be set")

    issuer = f"{base_url}/realms/{realm}"
    jwks_url = f"{issuer}/protocol/openid-connect/certs"
    audience = (os.getenv("KEYCLOAK_AUDIENCE") or "").strip() or None
    return KeycloakConfig(issuer=issuer, audience=audience, jwks_url=jwks_url)


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    config = _load_keycloak_config()
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(config.jwks_url)
        resp.raise_for_status()
        return resp.json()


_security = HTTPBearer(auto_error=False)


def _get_key_for_token(token: str) -> dict:
    jwks = _get_jwks()
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unknown token key id",
    )


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = credentials.credentials
    try:
        config = _load_keycloak_config()
        key = _get_key_for_token(token)
        options = {"verify_aud": config.audience is not None}
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=config.audience,
            issuer=config.issuer,
            options=options,
        )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject",
            )
        return str(sub)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc
