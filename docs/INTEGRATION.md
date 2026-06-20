# Integration checklist

1. Index Qdrant: `docker compose up -d qdrant && docker compose run --rm indexing-worker --recreate`
2. Verify: `curl http://localhost:8000/health` and `POST /recommend` (see `docs/API.md`), or `python backend/scripts/smoke_test_api.py`
3. Run backend: `docker compose up -d`
4. Test auth: `python backend/scripts/workflow_test.py`
5. Confirm `/recommend` returns real results with `exclusion_restrictions` hard-filtering

## CORS

Backend enables CORS for all origins in dev.
