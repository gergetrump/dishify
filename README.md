# Dishify

Dishify is an AI-powered cooking assistant: given ingredients you already have plus diet and allergy constraints, it recommends recipes, explains why they fit, and suggests substitutions.

## What works today

| Layer | Status |
|-------|--------|
| **Backend** | FastAPI microservices in `backend/` — gateway, recommendation pipeline, vector retrieval (2.2M recipes), optional LLM reasoning, user auth & preferences |
| **Web client** | React + Vite app in `web-client/` — Cook, Preferences, Profile |
| **iOS client** | Native SwiftUI app in `ios/` — same flows as the web app |
| **Data pipeline** | Notebooks in `notebooks/data_cleaning/` and `data/restriction_rules.json` |
| **Infra** | Postgres, Keycloak, Qdrant, Caddy via Docker Compose |

All clients talk to the **gateway** (`http://localhost:8000`) using REST auth (`POST /auth/register`, `/auth/login`, `/auth/refresh`) — not browser or device PKCE against Keycloak directly.

## Repo layout

```
dishify/
├── backend/       # FastAPI microservices + shared libraries
├── web-client/    # React web app
├── ios/           # SwiftUI iOS app
├── keycloak/      # Realm provisioning scripts
├── data/          # Recipe corpus, restriction rules, Qdrant volume archive
├── notebooks/     # Data cleaning & reference notebooks
├── docs/          # API contract, integration notes
└── docker-compose.yml
```

| Folder | Role |
|--------|------|
| `backend/services/gateway/` | Public API, JWT validation, CORS |
| `backend/services/recommendation/` | Retrieve → rank → explain orchestration |
| `backend/services/retrieval/` | Embeddings + Qdrant search |
| `backend/services/reasoning/` | Optional LLM reasoning (OpenRouter) |
| `backend/services/user/` | Registration, login, profile & preferences |
| `keycloak/` | Identity provider; realm auto-provisioned on startup |

## Quick start (full stack)

### 1. Environment

From the repo root:

```bash
cp .env.example .env
cp .env.example .env.secret   # add real API keys here (OpenRouter, etc.)
```

- **`.env`** — tracked template; safe defaults for local dev.
- **`.env.secret`** — real secrets; **never commit** (gitignored).

For Python scripts (indexing, smoke tests):

```bash
bash start.sh
source .venv/bin/activate
```

### 2. Vector search (Qdrant)

Most teammates should **restore the shared Qdrant volume** (~7 GB) instead of indexing 2.2M recipes locally.

1. Obtain `data/qdrant_volume.tar.gz` from the team (Drive, S3, etc.) — **do not commit** this file.
2. Restore it (see [backend/README.md](backend/README.md) for exact commands).
3. Verify: collection `recipes_full` should have ~2.23M points.

Re-indexing is only needed when the dataset or embedding model changes. The Docker `indexing-worker` is for the 10k dev sample only.

### 3. Start services

```bash
docker compose up -d
curl -s http://localhost:8000/health
```

| URL | Service |
|-----|---------|
| `http://localhost` | Web app (Caddy → static build) |
| `http://localhost:8000` | Gateway API |
| `http://localhost:5173` | Vite dev server (`npm run dev` in `web-client/` only) |
| `http://localhost:9001` | Keycloak admin |
| `http://localhost:6333` | Qdrant (local debugging) |

Default test user (Compose): `testuser` / `test-secret`.

The first `/recommend` after startup can take 1–2 minutes while retrieval loads the embedding model; later searches are much faster.

## Clients

### Web

```bash
cd web-client
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173` with the backend at `http://localhost:8000`.

Or use the Docker stack — Caddy serves the production build at `http://localhost`.

See [web-client/README.md](web-client/README.md) for routes, env vars, tests, and validation checklist.

### iOS

1. Open `ios/Dishify.xcodeproj` in Xcode 15+.
2. Select the **Dishify** scheme, **Debug** configuration.
3. Run on simulator (`http://localhost:8000`) or point `Config/Staging.local.xcconfig` at your Mac's LAN IP for a physical device.

See [ios/README.md](ios/README.md) for build configurations, staging setup, CLI tests, and device checklist.

## Backend

Microservice stack on ports 8000–8004 plus offline indexing tools:

```bash
docker compose up -d
curl -s http://localhost:8000/health
python backend/scripts/smoke_test_api.py   # optional smoke test
```

Public endpoints on the gateway: `GET /health`, `POST /recommend`, `GET /auth/config`, `POST /auth/register`, `POST /auth/login`, `GET /me`, `GET/PUT /me/preferences`.

Set `DISABLE_AUTH=true` on the gateway for local testing without JWTs (`.env.example` default). Production Compose sets `DISABLE_AUTH=false`.

See [backend/README.md](backend/README.md) for architecture, Qdrant restore, indexing, local multi-service dev, and auth details.

## Data

| File | Purpose |
|------|---------|
| `data/dataset.csv` | Full raw corpus (~2.2M recipes, gitignored) |
| `data/dataset_10000_normalized.csv` | 10k-row dev sample, normalized ingredients |
| `data/dataset_10000_annotated.csv` | 10k-row dev sample with restriction tags |
| `data/restriction_rules.json` | Keyword rules for allergen/diet annotation |
| `data/qdrant_volume.tar.gz` | Shared Qdrant volume backup (~7 GB, gitignored) |

Use `data/dataset_10000_annotated.csv` for backend development experiments. Production search uses the restored `recipes_full` collection — no full CSV required on disk for API use.

### Data cleaning pipeline

Notebooks in `notebooks/data_cleaning/`:

1. `0_eda.ipynb` — exploratory analysis
2. `1_clean_data.ipynb` — cleaning
3. `2_normalize_data.ipynb` — ingredient normalization (`ingredient-parser-nlp`)
4. `3_annotate_restrictions.ipynb` — restriction tagging

Batch script equivalents: `2_normalize_data_full.py`, `3_annotate_restrictions_full.py`.

## Infrastructure

Docker Compose starts Postgres, Keycloak, Qdrant, all backend services, the web client build, and Caddy.

Keycloak realm provisioning runs automatically via `keycloak/create-realm.sh`. Clients: `dishify-web`, `dishify-ios` (PKCE, reserved for future OIDC flows), and `dishify-backend` (confidential service account).

| Service | Default credentials |
|---------|---------------------|
| Postgres | user/pass/db: `dishify` |
| Keycloak admin | see `.env.example` |

Optional LLM reasoning: set `OPENROUTER_API_KEY` in `.env.secret` and `ENABLE_LLM_REASONING=true` on reasoning/recommendation services. Without a key, explain stages are skipped.

## Collaboration

- API contract: [docs/API.md](docs/API.md)
- Integration notes: [docs/INTEGRATION.md](docs/INTEGRATION.md)
- Agent scope rules: [AGENTS.md](AGENTS.md)

## Notebooks (reference only)

`notebooks/end_to_end_pipeline.ipynb` and `notebooks/scoring_inspection.ipynb` reference an older backend layout. Kept for reference — not runnable without recovering code from git history.

## Recovering old code

```bash
git log --all --full-history -- <path>
git show <commit>:<path>
```

Example: `git show HEAD~1:services/archive-app/vector_db/recipe_vector_store.py`
