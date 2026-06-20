# Dishify API Contract (v1)

> **Frozen** for the MVP sprint. Change only if backend teammates agree.
>
> **v1.1 (June 2026):** Added auth + user sections. Microservice gateway at `:8000`.
>
> **v1.2 (June 2026):** Single hard-filter field `exclusion_restrictions` for allergies and diets. Removed `dietary_preferences` and `cuisine_preferences`. Soft preferences belong in the NL `query` only.
>
> **v1.3 (June 2026):** User preferences stored in Postgres (`user_preferences` table, keyed by JWT `sub`). Keycloak is auth-only. Authenticated `/recommend` calls default to stored prefs when `exclusion_restrictions` is omitted.

- **Base URL (local):** `http://localhost:8000`
- **OpenAPI docs:** `http://localhost:8000/docs`
- **Keycloak (local):** `http://localhost:9001` — realm `dishify`
- **Auth header:** `Authorization: Bearer <access_token>` (Keycloak JWT)

Day 1: backend may run with auth disabled (`DISABLE_AUTH=true`) on **`POST /recommend` only**. Clients should still send the token when available. **`/me/*` always requires a valid Bearer token.**

Pipeline matches `notebooks/end_to_end_pipeline.ipynb`: Qdrant retrieval → inventory re-ranking → optional LLM reasoning.

Hard-filter tags must be top-level keys from [`data/restriction_rules.json`](../data/restriction_rules.json) (e.g. `nut_allergy`, `vegetarian`, `halal`).

---

## Authentication (two supported flows)

### Flow A — OIDC PKCE

Clients authenticate **directly with Keycloak** using the public clients provisioned in [`keycloak/create-realm.sh`](../keycloak/create-realm.sh):

| Client | Use | Redirect URI (local) |
|--------|-----|------------------------|
| `dishify-web` | Web / SPA clients | `http://localhost:5173/*` |
| `dishify-ios` | Mobile clients | `dishify://callback` |

1. Discover OIDC endpoints via Keycloak (`/realms/dishify/.well-known/openid-configuration`) or `GET /auth/config`.
2. Run authorization code + PKCE flow against Keycloak.
3. Send the resulting `access_token` on API calls: `Authorization: Bearer <token>`.

### Flow B — Backend auth APIs (register / login)

For programmatic clients, tests, or apps that prefer a single backend entrypoint:

1. `POST /auth/register` — create account (Keycloak admin API).
2. `POST /auth/login` — username/password → JWT (`access_token`).
3. Use the token on `/me/*` and `/recommend`.

**Identity** (username, email, password) lives in Keycloak. **Preferences** (`exclusion_restrictions`) are stored in Postgres via `PUT /me/preferences` (or optionally at registration). Clients should set preferences once and omit them from routine `/recommend` calls.

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

## Auth

### `GET /auth/config`

No auth required. Returns OIDC discovery URLs and client IDs for app configuration.

**Response `200`:**
```json
{
  "issuer": "http://localhost:9001/realms/dishify",
  "authorization_endpoint": "http://localhost:9001/realms/dishify/protocol/openid-connect/auth",
  "token_endpoint": "http://localhost:9001/realms/dishify/protocol/openid-connect/token",
  "logout_endpoint": "http://localhost:9001/realms/dishify/protocol/openid-connect/logout",
  "userinfo_endpoint": "http://localhost:9001/realms/dishify/protocol/openid-connect/userinfo",
  "jwks_uri": "http://localhost:9001/realms/dishify/protocol/openid-connect/certs",
  "realm": "dishify",
  "clients": {
    "ios": "dishify-ios",
    "web": "dishify-web",
    "backend": "dishify-backend",
    "api": "dishify-web"
  }
}
```

| Field | Notes |
|-------|-------|
| `clients.ios` | Public PKCE client for mobile |
| `clients.web` | Public PKCE client for web |
| `clients.backend` | Confidential service-account client (backend only; not for app login) |
| `clients.api` | Client used by `POST /auth/login` (password grant) |

**Note:** When the gateway runs inside Docker, URLs may use the internal hostname `keycloak:9001`. Clients on the host should use `http://localhost:9001` (or configure `KEYCLOAK_URL` accordingly).

**Errors:**
- `503` — Keycloak unavailable

---

### `POST /auth/register`

No auth required.

**Request:**
```json
{
  "username": "demo_user",
  "email": "demo@example.com",
  "password": "demo-secret-1",
  "exclusion_restrictions": ["shellfish_allergy", "nut_allergy"]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `username` | `string` | yes | 3–64 characters |
| `email` | `string` | yes | Valid email |
| `password` | `string` | yes | 8–128 characters |
| `exclusion_restrictions` | `string[]` | no | Optional initial hard-filter tags; persisted to Postgres after account creation |

**Response `201`:**
```json
{
  "id": "4267aa58-4ec7-4f83-a8eb-ada7b8743d88",
  "username": "demo_user",
  "email": "demo@example.com",
  "message": "Registration successful"
}
```

**Errors:**
- `409` — username or email already exists
- `422` — validation error (unknown restriction tags)
- `502` / `503` — Keycloak or preferences storage error

---

### `POST /auth/login`

No auth required.

**Request:**
```json
{
  "username": "demo_user",
  "password": "demo-secret-1"
}
```

| Field | Type | Required |
|-------|------|----------|
| `username` | `string` | yes |
| `password` | `string` | yes |

**Response `200`:**
```json
{
  "access_token": "<jwt>",
  "expires_in": 300,
  "refresh_token": "<refresh_token>",
  "token_type": "Bearer",
  "scope": "openid profile email"
}
```

Use `access_token` as the Bearer token for `/me/*` and `/recommend`.

**Errors:**
- `401` — invalid username or password
- `422` — validation error
- `502` / `503` — Keycloak error

---

## User

All `/me/*` endpoints require `Authorization: Bearer <access_token>`. JWT is validated against Keycloak JWKS (issuer `http://localhost:9001/realms/dishify`).

Profile fields (`GET /me`) are read from Keycloak. Preferences (`GET` / `PUT /me/preferences`) are read and written in Postgres, keyed by the JWT `sub` claim.

### `GET /me`

**Response `200`:**
```json
{
  "id": "4267aa58-4ec7-4f83-a8eb-ada7b8743d88",
  "username": "demo_user",
  "email": "demo@example.com",
  "email_verified": true,
  "first_name": "demo_user",
  "last_name": "User"
}
```

**Errors:**
- `401` — missing or invalid token

---

### `GET /me/preferences`

**Response `200`:**
```json
{
  "exclusion_restrictions": ["shellfish_allergy", "nut_allergy", "vegetarian"]
}
```

| Field | Notes |
|-------|-------|
| `exclusion_restrictions` | Allergies, diets, and other hard-filter tags (same vocabulary as `/recommend`); stored in Postgres |

**Errors:**
- `401` — missing or invalid token
- `503` — Postgres unavailable

---

### `PUT /me/preferences`

Replaces `exclusion_restrictions` in Postgres when provided. Omitted fields are left unchanged.

**Request:**
```json
{
  "exclusion_restrictions": ["shellfish_allergy", "nut_allergy", "vegetarian"]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `exclusion_restrictions` | `string[]` | no | Set to update; omit to keep existing |

**Response `200`:**
```json
{
  "exclusion_restrictions": ["shellfish_allergy", "nut_allergy", "vegetarian"]
}
```

**Errors:**
- `401` — missing or invalid token
- `422` — unknown restriction tags
- `503` — Postgres update failed

---

## `POST /recommend`

Auth required in production. Optional when `DISABLE_AUTH=true`.

When a Bearer token is present, the gateway loads stored preferences from `GET /me/preferences` and applies them if the request omits `exclusion_restrictions` or sends an empty list. Explicit non-empty values in the request body override stored prefs for that call only.

**Request (authenticated — stored prefs applied automatically):**
```json
{
  "query": "creamy tomato pasta with spinach",
  "top_k": 5,
  "available_ingredients": [
    {
      "name": "penne",
      "quantity": 12,
      "unit": "oz",
      "raw_text": "12 oz penne"
    },
    {
      "name": "tomato",
      "quantity": null,
      "unit": null,
      "raw_text": "tomato"
    }
  ]
}
```

**Request (one-off override — explicit restrictions win for this call):**
```json
{
  "query": "creamy tomato pasta with spinach",
  "top_k": 5,
  "exclusion_restrictions": ["shellfish_allergy", "nut_allergy", "vegetarian"]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `query` | `string` | yes | Natural-language recipe search (include soft preferences here) |
| `top_k` | `integer` | no | Default `5`, max `100` |
| `available_ingredients` | `ParsedIngredient[]` | no | Structured pantry inventory |
| `exclusion_restrictions` | `string[]` | no | Hard-filter tags for Qdrant retrieval. When authenticated, defaults to stored prefs if omitted or empty; non-empty body values override for this request |

**ParsedIngredient:**
| Field | Type | Notes |
|-------|------|-------|
| `name` | `string` | Normalized ingredient name |
| `quantity` | `number \| null` | Optional amount on hand |
| `unit` | `string \| null` | Optional unit (e.g. `oz`, `cup`) |
| `raw_text` | `string` | Original user text |

**Response `200`:**
```json
{
  "results": [
    {
      "rank": 1,
      "id": 3136,
      "title": "Pasta With Spinach Sauce",
      "summary": null,
      "time_minutes": null,
      "score": 0.59,
      "reasoning": {
        "positive": ["Uses penne and spinach from your pantry."],
        "negative": ["Requires bacon and whipping cream."]
      },
      "directions": ["Cook pasta as directed.", "..."],
      "inventory_matched": ["penne", "spinach"],
      "inventory_missing": ["bacon", "whipping cream"]
    }
  ],
  "stages": [
    {"name": "retrieve", "status": "ok", "latency_ms": 120},
    {"name": "rank", "status": "ok", "latency_ms": 2},
    {"name": "explain", "status": "skipped", "latency_ms": 0}
  ]
}
```

**Pipeline stages:**

| Stage | Description |
|-------|-------------|
| `retrieve` | Semantic search in Qdrant (+ hard filter on `exclusion_restrictions`) |
| `rank` | Inventory re-ranking |
| `explain` | LLM reasoning (`ok`, `skipped`, or `error`) |

**Errors:**
- `401` — missing or invalid token (when auth enabled)
- `422` — validation error (unknown restriction tags)
- `503` — Qdrant collection not indexed, user service unavailable, or preferences load failed

---

## Indexing (backend setup)

One-time offline step. **Not** part of the request pipeline — `/recommend` queries vectors already stored in Qdrant.

```bash
# Qdrant must be running (docker compose up qdrant)
docker compose run --rm indexing-worker --recreate
```

Uses `data/dataset_10000_annotated.csv` by default (~10k recipes). Set `QDRANT_COLLECTION=recipes_10000` to match the notebook.

Optional LLM reasoning: set `ENABLE_LLM_REASONING=true` and `OPENROUTER_API_KEY` in `.env`.

---

## Deferred (post-MVP)

- `POST /auth/logout` — client-side Keycloak logout for now
- `POST /auth/refresh` — refresh-token exchange
- `POST /auth/forgot-password` — password reset via Keycloak
