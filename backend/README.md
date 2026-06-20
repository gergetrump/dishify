# Backend

FastAPI recommendation API — **not implemented yet**.

Greenfield design lives in `agent/architecture-plan.md` (local, gitignored).

## Planned layout

```
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── auth/           # JWT validation (consumes Keycloak; does not run it)
│   ├── api/
│   ├── domain/
│   ├── pipeline/
│   ├── db/
│   ├── vector/
│   └── clients/
├── scripts/
├── tests/
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

## Auth note

Keycloak realm provisioning stays at repo root in [`keycloak/`](../keycloak/) — shared by backend and iOS. This folder only contains token validation middleware under `app/auth/`.

## Build order

1. `/health` + config + Dockerfile
2. DB models + recipe loader
3. Qdrant indexing + retrieval
4. Pipeline stages 1–5
5. Keycloak JWT middleware
6. LLM explain stage + `/me/preferences`
