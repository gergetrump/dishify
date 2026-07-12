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
| `ingest` | 8005 | Voice transcription + image→ingredient detection (Gemini) |
| `indexing-worker` | — | Offline batch indexing into Qdrant (10k CSV only; see below) |

Shared libraries: `shared/dishify-contracts`, `shared/dishify-ranking`, `shared/dishify-vector-store`.

## Teammate quick start

Most devs should **restore the shared Qdrant volume** (about 7 GB) instead of indexing 2.2M recipes locally.

### 1. Env files (repo root)

```bash
cp .env.example .env
cp .env.example .env.secret   # or create .env.secret for API keys only
```

- **`.env` / `.env.example`** — tracked template; safe to commit.
- **`.env.secret`** — real keys (OpenRouter, etc.); **never commit** (gitignored).
- Copy [`../.env.example`](../.env.example) values as needed. Docker Compose overrides `QDRANT_URL` to `http://qdrant:6333` inside containers.

Production Compose sets `DISABLE_AUTH=false` on the gateway. For local testing without JWTs, set `DISABLE_AUTH=true` on the `gateway` service in `docker-compose.yml` or recreate the gateway with that env var.

### 2. Install the shared vector store (`data/qdrant_volume.tar.gz`)

The team shares a pre-built Qdrant Docker volume as **`data/qdrant_volume.tar.gz`** (about 7 GB). It contains collection **`recipes_full`** (2.2M recipe vectors). **Do not commit this file** — use Drive, S3, or similar.

**Teammates — from the repo root:**

1. Put the archive at **`data/qdrant_volume.tar.gz`** (exact path and name).
2. Restore into Docker (Qdrant must be stopped while restoring):

```bash
docker compose up -d qdrant
docker compose stop qdrant

docker volume ls | grep qdrant   # expect dishify_qdrant_data (adjust -v if different)

docker run --rm \
  -v dishify_qdrant_data:/data \
  -v "$PWD/data":/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/qdrant_volume.tar.gz -C /data"

docker compose up -d
```

3. Verify before using the API:

```bash
curl -s http://localhost:6333/collections/recipes_full | python3 -m json.tool
curl -s http://localhost:8002/ready
```

You should see about 2,230,125 points on `recipes_full` and retrieval `/ready` OK. No indexing or `dataset_full_annotated.csv` required for search.

**Whoever creates the archive** (already indexed locally):

```bash
docker compose stop qdrant
docker run --rm \
  -v dishify_qdrant_data:/data \
  -v "$PWD/data":/backup \
  alpine tar czf /backup/qdrant_volume.tar.gz -C /data .
docker compose start qdrant
```

Share **`data/qdrant_volume.tar.gz`** out of band. Run `docker compose stop qdrant` — not `git docker compose`.

### 3. Run the stack

```bash
docker compose up -d
curl http://localhost:8000/health
```

| URL | Purpose |
|-----|---------|
| `http://localhost:8000` | API (gateway) |
| `http://localhost` | Web UI + API via Caddy |
| `http://localhost:6333` | Qdrant (local only) |

First `/recommend` after startup can be slow while retrieval loads `sentence-transformers/all-MiniLM-L6-v2` (about 1–2 min). Later requests are faster; search over 2M vectors is typically sub-second to a few seconds once warm.

### 4. Test endpoints

**Health:**

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8002/ready
```

**Recommend (no auth)** — set `DISABLE_AUTH=true` on gateway first, or use login below:

```bash
curl -s -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "creamy tomato pasta", "top_k": 5}'
```

**With auth** (default Compose: `DISABLE_AUTH=false`):

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test-secret"}'

TOKEN="<access_token from response>"

curl -s -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "chicken rice bowl", "top_k": 5}'
```

Smoke script (gateway must be up; auth disabled or add token support):

```bash
source .venv/bin/activate
python backend/scripts/smoke_test_api.py
```

Check `stages` in the `/recommend` response — `retrieve` vs `explain` latency. LLM explain requires `OPENROUTER_API_KEY` in `.env.secret`; without it, explain is skipped.

## Vector search config

| Variable | Docker default | Notes |
|----------|----------------|-------|
| `QDRANT_URL` | `http://qdrant:6333` (in Compose) | `http://localhost:6333` on host |
| `QDRANT_COLLECTION` | `recipes_full` | 2.2M recipes |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Must match indexed vectors |

You do **not** need `dataset_full_annotated.csv` for search if Qdrant is restored. You still need `data/restriction_rules.json` for restriction tagging in the API.

## Indexing (only if you are rebuilding the index)

**Do not re-run indexing on every startup.** `docker compose up` reuses the `qdrant_data` volume.

- **Full dataset (2.2M rows):** streaming script on the host (not the Docker indexing-worker):

  ```bash
  docker compose up -d qdrant
  source .venv/bin/activate
  python backend/scripts/index_full_recipes.py --recreate --count-total --device mps
  ```

  See [`scripts/index_full_recipes.py`](scripts/index_full_recipes.py) for `--resume`, checkpoints, and flags.

- **10k dev sample:** Docker worker loads the whole CSV into memory — **do not** run with `--recreate` against `recipes_full` (it would wipe 2M points). See [`services/indexing/README.md`](services/indexing/README.md).

Reindex only when the dataset or embedding model changes, or after `docker compose down -v` wipes volumes.

## Run locally (without Docker)

Start Qdrant first, then run each service in separate terminals:

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

# Terminal 5 — ingest (voice + image; needs GEMINI_API_KEY)
cd backend/services/ingest
pip install -r requirements.txt ../../shared/dishify-contracts
GEMINI_API_KEY=... PYTHONPATH=. uvicorn app.main:app --reload --port 8005

# Terminal 6 — gateway
cd backend/services/gateway
pip install -r requirements.txt ../../shared/dishify-contracts
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Set `QDRANT_COLLECTION=recipes_full` in `.env` and ensure local Qdrant has that collection before starting retrieval.

## Endpoints (public)

- `GET /health` — on gateway (`:8000`)
- `POST /recommend` — on gateway (`:8000`)
- `POST /transcribe` — voice → text (proxied to `ingest`)
- `POST /vision/ingredients` — image → ingredients (proxied to `ingest`)
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

Set `DISABLE_AUTH=true` on the gateway to skip JWT checks on `/recommend` (local dev). When `DISABLE_AUTH=false`, the gateway validates Keycloak JWTs via JWKS.

## Optional LLM reasoning

Set on `reasoning` and `recommendation` services:

```
ENABLE_LLM_REASONING=true
OPENROUTER_API_KEY=...
```

## Media ingestion (voice & image)

The `ingest` service turns voice/image input into the existing `query` / `available_ingredients`
fields. It needs a Gemini key; without it, `/transcribe` and `/vision/ingredients` return `503`.

```
GEMINI_API_KEY=...
# optional model overrides
GEMINI_TRANSCRIBE_MODEL=gemini-2.5-flash
GEMINI_VISION_MODEL=gemini-2.5-flash
```
