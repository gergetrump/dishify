from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(title="User Service", version="0.1.0")

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:9001")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "dishify")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "dishify-user-service")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")


class User(BaseModel):
    id: str
    name: str = Field(..., min_length=1)
    email: EmailStr


class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr


@app.get("/health")
def health() -> dict:
    try:
        _get_admin_token()
    except HTTPException as exc:
        return {"status": "error", "service": "user-service", "detail": exc.detail}
    return {"status": "ok", "service": "user-service"}


@app.get("/users", response_model=list[User])
def list_users() -> list[User]:
    token = _get_admin_token()
    url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users"
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url, headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Keycloak unavailable: {exc}") from exc

    users: list[User] = []
    for raw in response.json():
        name = raw.get("firstName") or raw.get("username") or raw.get("email") or ""
        email = raw.get("email") or "unknown@example.com"
        users.append(User(id=str(raw.get("id", "")), name=name, email=email))
    return users


@app.post("/users", response_model=User)
def create_user(payload: CreateUserRequest) -> User:
    token = _get_admin_token()
    url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users"
    body = {
        "username": payload.email,
        "firstName": payload.name,
        "email": payload.email,
        "enabled": True,
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            location = response.headers.get("Location", "")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Keycloak unavailable: {exc}") from exc

    user_id = location.rsplit("/", 1)[-1] if location else ""
    return User(id=user_id, name=payload.name, email=payload.email)


def _get_admin_token() -> str:
    if not KEYCLOAK_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="KEYCLOAK_CLIENT_SECRET is not set")

    token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET,
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(token_url, data=data)
            response.raise_for_status()
            return response.json()["access_token"]
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Keycloak unavailable: {exc}") from exc
