# Backend

FastAPI recommendation API.

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Or via Docker Compose from repo root: `docker compose up -d backend`

## Endpoints

- `GET /health`
- `POST /recommend` — MVP stub matching [`docs/API.md`](../docs/API.md)
- OpenAPI: http://localhost:8000/docs

## Auth

Set `DISABLE_AUTH=true` in `.env` for Day 1 dev (default). JWT validation to be added on `feature/backend-mvp`.

Keycloak provisioning: [`keycloak/`](../keycloak/) at repo root.

## Build order

See [`agent/architecture-plan.md`](../agent/architecture-plan.md) (local) or root README.
