from __future__ import annotations

import threading
import time
from typing import Any

import httpx

from app.config import settings

_lock = threading.Lock()
_service_token: str | None = None
_service_token_expires_at: float = 0.0


class KeycloakError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class KeycloakClient:
    def __init__(self) -> None:
        self.realm_base = settings.keycloak_internal_realm_url
        self.admin_base = f"{settings.keycloak_internal_base_url}/admin/realms/{settings.keycloak_realm}"
        self.timeout = settings.request_timeout_seconds

    def _token_url(self) -> str:
        return f"{self.realm_base}/protocol/openid-connect/token"

    def get_openid_config(self) -> dict[str, Any]:
        url = f"{self.realm_base}/.well-known/openid-configuration"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def get_service_account_token(self) -> str:
        global _service_token, _service_token_expires_at

        now = time.time()
        if _service_token and now < _service_token_expires_at - 30:
            return _service_token

        with _lock:
            now = time.time()
            if _service_token and now < _service_token_expires_at - 30:
                return _service_token

            data = {
                "grant_type": "client_credentials",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
            }
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self._token_url(), data=data)
                if not response.is_success:
                    raise KeycloakError(
                        f"Service account auth failed: {response.text}",
                        status_code=response.status_code,
                    )
                payload = response.json()
                _service_token = payload["access_token"]
                _service_token_expires_at = now + int(payload.get("expires_in", 60))
                return _service_token

    def login(self, username: str, password: str) -> dict[str, Any]:
        data = {
            "grant_type": "password",
            "client_id": settings.keycloak_login_client_id,
            "username": username,
            "password": password,
            "scope": "openid profile email",
        }
        if settings.keycloak_login_client_secret is not None:
            if settings.keycloak_login_client_secret:
                data["client_secret"] = settings.keycloak_login_client_secret
        else:
            data["client_secret"] = settings.keycloak_client_secret
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self._token_url(), data=data)
            if response.status_code == 401:
                raise KeycloakError("Invalid username or password", status_code=401)
            if not response.is_success:
                raise KeycloakError(
                    f"Login failed: {response.text}",
                    status_code=response.status_code,
                )
            return response.json()

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        data = {
            "grant_type": "refresh_token",
            "client_id": settings.keycloak_login_client_id,
            "refresh_token": refresh_token,
        }
        if settings.keycloak_login_client_secret:
            data["client_secret"] = settings.keycloak_login_client_secret
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self._token_url(), data=data)
            if not response.is_success:
                raise KeycloakError(
                    "Refresh token invalid or expired",
                    status_code=response.status_code,
                )
            return response.json()

    def logout(self, refresh_token: str) -> None:
        data = {
            "client_id": settings.keycloak_login_client_id,
            "refresh_token": refresh_token,
        }
        if settings.keycloak_login_client_secret:
            data["client_secret"] = settings.keycloak_login_client_secret
        url = f"{self.realm_base}/protocol/openid-connect/logout"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, data=data)
            if not response.is_success:
                raise KeycloakError(
                    "Logout failed",
                    status_code=response.status_code,
                )

    def register_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
    ) -> str:
        body: dict[str, Any] = {
            "username": username,
            "email": email,
            "firstName": username,
            "lastName": "User",
            "enabled": True,
            "emailVerified": True,
            "requiredActions": [],
            "credentials": [
                {"type": "password", "value": password, "temporary": False}
            ],
        }

        token = self.get_service_account_token()
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.admin_base}/users",
                json=body,
                headers=headers,
            )
            if response.status_code == 409:
                raise KeycloakError("Username or email already exists", status_code=409)
            if not response.is_success:
                raise KeycloakError(
                    f"Registration failed: {response.text}",
                    status_code=response.status_code,
                )

            location = response.headers.get("Location", "")
            user_id = location.rstrip("/").split("/")[-1]
            if not user_id:
                users = self.find_users(username=username)
                if not users:
                    raise KeycloakError(
                        "User created but id not returned", status_code=500
                    )
                user_id = users[0]["id"]

            self._set_password(user_id, password)
            self._finalize_user(user_id)
            return user_id

    def _set_password(self, user_id: str, password: str) -> None:
        token = self.get_service_account_token()
        headers = {"Authorization": f"Bearer {token}"}
        body = {"type": "password", "value": password, "temporary": False}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.put(
                f"{self.admin_base}/users/{user_id}/reset-password",
                json=body,
                headers=headers,
            )
            if not response.is_success:
                raise KeycloakError(
                    f"Failed to set password: {response.text}",
                    status_code=response.status_code,
                )

    def _finalize_user(self, user_id: str) -> None:
        user = self.get_user(user_id)
        body = {
            "username": user.get("username"),
            "email": user.get("email"),
            "firstName": user.get("firstName") or user.get("username"),
            "lastName": user.get("lastName") or "User",
            "enabled": True,
            "emailVerified": True,
            "requiredActions": [],
            "attributes": user.get("attributes") or {},
        }
        token = self.get_service_account_token()
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.put(
                f"{self.admin_base}/users/{user_id}",
                json=body,
                headers=headers,
            )
            if not response.is_success:
                raise KeycloakError(
                    f"Failed to finalize user: {response.text}",
                    status_code=response.status_code,
                )

    def find_users(
        self, *, username: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if username:
            params["username"] = username
        if email:
            params["email"] = email

        token = self.get_service_account_token()
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.admin_base}/users",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    def get_user(self, user_id: str) -> dict[str, Any]:
        token = self.get_service_account_token()
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.admin_base}/users/{user_id}",
                headers=headers,
            )
            if response.status_code == 404:
                raise KeycloakError("User not found", status_code=404)
            response.raise_for_status()
            return response.json()

    def update_user_attributes(
        self,
        user_id: str,
        *,
        attributes: dict[str, list[str]],
    ) -> None:
        user = self.get_user(user_id)
        body = {
            "username": user.get("username"),
            "email": user.get("email"),
            "firstName": user.get("firstName") or user.get("username"),
            "lastName": user.get("lastName") or "User",
            "enabled": user.get("enabled", True),
            "emailVerified": True,
            "requiredActions": [],
            "attributes": attributes,
        }

        token = self.get_service_account_token()
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.put(
                f"{self.admin_base}/users/{user_id}",
                json=body,
                headers=headers,
            )
            if not response.is_success:
                raise KeycloakError(
                    f"Failed to update user: {response.text}",
                    status_code=response.status_code,
                )


def clear_preference_attributes(user_id: str, client: KeycloakClient) -> None:
    user = client.get_user(user_id)
    attributes = dict(user.get("attributes") or {})
    if (
        "exclusion_restrictions" not in attributes
        and "cuisine_preferences" not in attributes
    ):
        return
    attributes.pop("exclusion_restrictions", None)
    attributes.pop("cuisine_preferences", None)
    client.update_user_attributes(user_id, attributes=attributes)


def attribute_list(raw: dict[str, Any], key: str) -> list[str]:
    values = raw.get(key)
    if not values:
        return []
    if isinstance(values, list):
        return [str(item) for item in values if item]
    return [str(values)]


def user_to_profile(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user.get("username"),
        "email": user.get("email"),
        "email_verified": user.get("emailVerified"),
        "first_name": user.get("firstName"),
        "last_name": user.get("lastName"),
    }


def _merge_dedupe(*lists: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for values in lists:
        for item in values:
            normalized = str(item).strip()
            key = normalized.lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(normalized)
    return merged


def user_to_preferences(user: dict[str, Any]) -> dict[str, list[str]]:
    attributes = user.get("attributes") or {}
    exclusions = attribute_list(attributes, "exclusion_restrictions")
    legacy_cuisine = attribute_list(attributes, "cuisine_preferences")
    if legacy_cuisine:
        exclusions = _merge_dedupe(exclusions, legacy_cuisine)
    return {"exclusion_restrictions": exclusions}


def migrate_legacy_preferences(user_id: str, client: KeycloakClient) -> None:
    user = client.get_user(user_id)
    attributes = dict(user.get("attributes") or {})
    legacy_cuisine = attribute_list(attributes, "cuisine_preferences")
    if not legacy_cuisine:
        return

    exclusions = attribute_list(attributes, "exclusion_restrictions")
    merged = _merge_dedupe(exclusions, legacy_cuisine)
    attributes["exclusion_restrictions"] = merged
    attributes.pop("cuisine_preferences", None)
    client.update_user_attributes(user_id, attributes=attributes)
