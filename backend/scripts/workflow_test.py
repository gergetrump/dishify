#!/usr/bin/env python3
"""End-to-end user workflow test via gateway."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from uuid import uuid4

BASE = "http://localhost:8000"


def req(
    method: str, path: str, body: dict | None = None, token: str | None = None
) -> tuple[int, dict | str]:
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def step(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("=== Dishify full user workflow ===\n")

    # 1. Health
    code, health = req("GET", "/health")
    step("GET /health", code == 200 and health.get("status") == "ok", str(health))
    if code != 200:
        return 1

    # 2. Auth config (new user opens app)
    code, config = req("GET", "/auth/config")
    step(
        "GET /auth/config",
        code == 200 and config.get("realm") == "dishify",
        f"clients={list(config.get('clients', {}).keys())}",
    )
    if code != 200:
        return 1

    # 3. Register new user (signup), then login
    suffix = uuid4().hex[:8]
    new_user = {
        "username": f"demo_{suffix}",
        "email": f"demo_{suffix}@example.com",
        "password": "demo-secret-1",
        "exclusion_restrictions": ["vegetarian"],
    }
    code, reg = req("POST", "/auth/register", new_user)
    step(
        "POST /auth/register",
        code == 201,
        f"username={reg.get('username') if isinstance(reg, dict) else reg}",
    )
    if code != 201:
        return 1

    code, tokens = req(
        "POST",
        "/auth/login",
        {"username": new_user["username"], "password": new_user["password"]},
    )
    token = tokens.get("access_token") if isinstance(tokens, dict) else None
    login_detail = tokens.get("expires_in") if isinstance(tokens, dict) else tokens
    step(
        "POST /auth/login",
        code == 200 and bool(token),
        f"expires_in={login_detail}" if token else str(tokens),
    )
    if not token:
        return 1

    # 4. Profile
    code, profile = req("GET", "/me", token=token)
    step(
        "GET /me",
        code == 200 and profile.get("username") == new_user["username"],
        f"email={profile.get('email')}",
    )

    # 5. Read preferences
    code, prefs = req("GET", "/me/preferences", token=token)
    step(
        "GET /me/preferences",
        code == 200,
        f"restrictions={prefs.get('exclusion_restrictions')}",
    )

    # 6. Update preferences
    code, updated = req(
        "PUT",
        "/me/preferences",
        {
            "exclusion_restrictions": [
                "shellfish_allergy",
                "nut_allergy",
                "vegetarian",
            ],
        },
        token=token,
    )
    step(
        "PUT /me/preferences",
        code == 200 and "vegetarian" in (updated.get("exclusion_restrictions") or []),
        str(updated),
    )

    # 7. Recommend with logged-in user + pantry (stored prefs applied by gateway)
    code, rec = req(
        "POST",
        "/recommend",
        {
            "query": "creamy tomato pasta with spinach",
            "top_k": 3,
            "available_ingredients": [
                {
                    "name": "penne",
                    "quantity": 12,
                    "unit": "oz",
                    "raw_text": "12 oz penne",
                },
                {
                    "name": "tomato",
                    "quantity": None,
                    "unit": None,
                    "raw_text": "tomato",
                },
                {
                    "name": "spinach",
                    "quantity": 4,
                    "unit": "cup",
                    "raw_text": "4 cups spinach",
                },
            ],
        },
        token=token,
    )
    results = rec.get("results", []) if isinstance(rec, dict) else []
    stages = rec.get("stages", []) if isinstance(rec, dict) else []
    top = results[0] if results else {}
    step(
        "POST /recommend",
        code == 200 and len(results) > 0,
        f"top='{top.get('title')}' score={top.get('score')} stages={[s.get('name') for s in stages]}",
    )

    if code != 200:
        return 1

    if results:
        print("\n--- Top recipe ---")
        print(json.dumps(results[0], indent=2))

    # 8. Refresh token
    refresh_token = tokens.get("refresh_token") if isinstance(tokens, dict) else None
    if refresh_token:
        code, refreshed = req("POST", "/auth/refresh", {"refresh_token": refresh_token})
        new_token = (
            refreshed.get("access_token") if isinstance(refreshed, dict) else None
        )
        new_refresh = (
            refreshed.get("refresh_token") if isinstance(refreshed, dict) else None
        )
        step(
            "POST /auth/refresh",
            code == 200 and bool(new_token),
            (
                f"new_expires_in={refreshed.get('expires_in')}"
                if new_token
                else str(refreshed)
            ),
        )
        if new_token:
            token = new_token
        if new_refresh:
            refresh_token = new_refresh

        # Verify refreshed token works
        code, profile2 = req("GET", "/me", token=token)
        step(
            "GET /me (refreshed token)",
            code == 200 and profile2.get("username") == new_user["username"],
            f"username={profile2.get('username')}",
        )
    else:
        step("POST /auth/refresh", False, "no refresh_token in login response")

    # 9. Logout
    if refresh_token:
        code, _ = req("POST", "/auth/logout", {"refresh_token": refresh_token})
        step("POST /auth/logout", code == 204, f"status={code}")
    else:
        step("POST /auth/logout", False, "no refresh_token available")

    print("\n=== Workflow complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
