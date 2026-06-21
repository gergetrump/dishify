# Dishify Backend (Microservices)

FastAPI microservice stack aligned with `notebooks/end_to_end_pipeline.ipynb`.

## Architecture

| Service | Port | Role |
|---------|------|------|
| `gateway` | 8000 | Public API, JWT auth, CORS |
| `recommendation` | 8001 | Pipeline orchestrator (retrieve → rank → explain) |
| `retrieval` | 8002 | Embeddings + Qdrant search |
| `reasoning` | 8003 | Optional LLM reasoning (OpenRouter) |
| `user` | 8004 | Registration, login, profile & preferences (Keycloak) |
| `indexing-worker` | — | Offline batch indexing into Qdrant |

Shared libraries: `shared/dishify-contracts`, `shared/dishify-ranking`, `shared/dishify-vector-store`.

## Run with Docker Compose (from repo root)

```bash
docker compose up -d
docker compose run --rm indexing-worker --recreate
curl http://localhost:8000/health
```

## Run locally (without Docker)

Start Qdrant first, index recipes, then run each service in separate terminals:

```bash
# Terminal 1 — retrieval
cd backend/services/retrieval
pip install -r requirements.txt ../../shared/dishify-contracts ../../shared/dishify-vector-store
PYTHONPATH=. uvicorn app.main:app --reload --port 8002

# Terminal 2 — reasoning
cd backend/services/reasoning
pip install -r requirements.txt ../../shared/dishify-contracts
PYTHONPATH=. uvicorn app.main:app --reload --port 8003

# Terminal 3 — recommendation
cd backend/services/recommendation
pip install -r requirements.txt ../../shared/dishify-contracts ../../shared/dishify-ranking
PYTHONPATH=. uvicorn app.main:app --reload --port 8001

# Terminal 4 — user
cd backend/services/user
pip install -r requirements.txt ../../shared/dishify-contracts
PYTHONPATH=. uvicorn app.main:app --reload --port 8004

# Terminal 5 — gateway
cd backend/services/gateway
pip install -r requirements.txt ../../shared/dishify-contracts
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Index recipes (see [`services/indexing/README.md`](services/indexing/README.md) for CSV format and options):

```bash
cd backend/services/indexing
pip install -r requirements.txt ../../shared/dishify-contracts ../../shared/dishify-vector-store
PYTHONPATH=. python -m app.main --recreate
```

## Endpoints (public)

- `GET /health` — on gateway (`:8000`)
- `POST /recommend` — on gateway (`:8000`)
- `GET /auth/config` — OIDC discovery + client IDs
- `POST /auth/register` — create account (Keycloak admin API via `dishify-backend` service account)
- `POST /auth/login` — username/password token (password grant on `dishify-backend`)
- `GET /me` — current user profile (Bearer token required)
- `GET /me/preferences` — `exclusion_restrictions`
- `PUT /me/preferences` — update preference attributes in Keycloak

See [`docs/API.md`](../docs/API.md) for recommend request/response shapes.

## User service & Keycloak

The user service uses the `dishify-backend` confidential client from [`keycloak/create-realm.sh`](../keycloak/create-realm.sh):

- **Service account** (`manage-users`, `view-users`) — registration and preference updates
- **Direct access grants** — `POST /auth/login` password flow
- **User attributes** — `exclusion_restrictions` (hard-filter tags from `restriction_rules.json`)

API clients can use OIDC PKCE directly; use `GET /auth/config` for issuer and client IDs.

Env vars (see `.env.example`): `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`.

## Auth

Set `DISABLE_AUTH=true` on the gateway for Day 1 dev. When enabled, the gateway validates Keycloak JWTs via JWKS.

## Optional LLM reasoning

Set on `reasoning` and `recommendation` services:

```
ENABLE_LLM_REASONING=true
OPENROUTER_API_KEY=...
```

## Legacy monolith

The original single-process app remains under `backend/app/` for reference during migration.
