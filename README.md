# Dishify

Dishify is an AI-powered cooking assistant: given ingredients you already have plus diet and allergy constraints, it recommends recipes, explains why they fit, and suggests substitutions.

## Current repo state

The old backend was removed (June 2026). Git history still has everything if we need to recover a file. What works today:

- **Data cleaning pipeline** — `notebooks/data_cleaning/` and `data/restriction_rules.json`
- **Infra** — Postgres, Keycloak, and Qdrant via Docker Compose
- **Backend** — Microservice stack in `backend/` (`/health`, `/recommend`, auth, user preferences)

## Repo layout

```
dishify/
├── backend/       # FastAPI microservices
├── keycloak/      # Shared auth infra
├── data/
├── notebooks/
└── docker-compose.yml
```

| Folder | Role |
|--------|------|
| `keycloak/` | Standalone identity provider for backend API clients |
| `backend/services/gateway/` | Public API, JWT validation, CORS |

## Quick start

```bash
bash start.sh
source .venv/bin/activate
```

Copy `.env.example` to `.env` and fill in API keys when you need them. Never commit `.env`.

## Data

| File | Purpose |
|------|---------|
| `data/dataset.csv` | Full raw corpus (~2.2M recipes, 2.1 GB, gitignored) |
| `data/dataset_10000_normalized.csv` | 10k-row dev sample, normalized ingredients |
| `data/dataset_10000_annotated.csv` | 10k-row dev sample with restriction tags |
| `data/restriction_rules.json` | Keyword rules for allergen/diet annotation |

Use `data/dataset_10000_annotated.csv` for backend development and indexing experiments.

### Data cleaning pipeline

Notebooks in `notebooks/data_cleaning/`:

1. `0_eda.ipynb` — exploratory analysis
2. `1_clean_data.ipynb` — cleaning
3. `2_normalize_data.ipynb` — ingredient normalization (`ingredient-parser-nlp`)
4. `3_annotate_restrictions.ipynb` — restriction tagging

Batch script equivalents: `2_normalize_data_full.py`, `3_annotate_restrictions_full.py`.

## Infrastructure

Start Postgres, Keycloak, Qdrant, and backend:

```bash
docker compose up -d
```

| Service | URL |
|---------|-----|
| Backend | `http://localhost:8000` |
| Postgres | `localhost:5432` (user/pass/db: `dishify`) |
| Keycloak | `http://localhost:9001` |
| Qdrant | `http://localhost:6333` |

Keycloak realm provisioning runs automatically via `keycloak/create-realm.sh`. Clients: `dishify-web`, `dishify-ios` (PKCE), and `dishify-backend` (confidential).

## Collaboration

- API contract: [`docs/API.md`](docs/API.md)
- Agent scope rules: [`AGENTS.md`](AGENTS.md)
- Integration: [`docs/INTEGRATION.md`](docs/INTEGRATION.md)

## Backend

```bash
docker compose up -d
docker compose run --rm indexing-worker --recreate
curl http://localhost:8000/health
```

See [`backend/README.md`](backend/README.md) for local multi-service development.

## Notebooks (reference only)

`notebooks/end_to_end_pipeline.ipynb` and `notebooks/scoring_inspection.ipynb` reference the old `backend/` layout. Kept for reference — not runnable without recovering code from git history.

## Recovering old code

```bash
git log --all --full-history -- <path>
git show <commit>:<path>
```

Example: `git show HEAD~1:services/archive-app/vector_db/recipe_vector_store.py`
