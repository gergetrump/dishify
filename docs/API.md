# Dishify API Contract (v1)

> **Frozen** for the 2-day MVP sprint. Change only if both backend and iOS teammates agree.

- **Base URL (local):** `http://localhost:8000`
- **OpenAPI docs:** `http://localhost:8000/docs`
- **Auth header:** `Authorization: Bearer <access_token>` (Keycloak JWT)

Day 1: backend may run with auth disabled (`DISABLE_AUTH=true`). iOS should still send the token when available.

---

## `GET /health`

No auth required.

**Response `200`:**
```json
{
  "status": "ok",
  "service": "dishify-backend"
}
```

---

## `POST /recommend`

Auth required in production. Optional when `DISABLE_AUTH=true`.

**Request:**
```json
{
  "ingredients": ["tomato", "pasta", "mozzarella"],
  "limit": 5
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `ingredients` | `string[]` | yes | Raw ingredient names from user |
| `limit` | `integer` | no | Default `5`, max `20` |

**Response `200`:**
```json
{
  "recommendations": [
    {
      "recipe_id": "123",
      "title": "Caprese Pasta",
      "score": 0.87,
      "matched_ingredients": ["tomato", "pasta"],
      "missing_ingredients": ["basil"],
      "reason": "Uses most of what you have."
    }
  ],
  "stages": [
    {"name": "normalize", "status": "ok", "latency_ms": 120},
    {"name": "filter", "status": "ok", "latency_ms": 8}
  ]
}
```

**Errors:**
- `401` — missing or invalid token (when auth enabled)
- `422` — validation error

---

## Deferred (post-MVP)

- `GET /me/preferences`
- `PUT /me/preferences`
