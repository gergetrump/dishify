# Architecture

## At a glance

```
                    ┌─────────────────┐
                    │  HTTP client    │
                    └───────┬─────────┘
                            │  POST /recommend
                            ▼
                  ┌────────────────────┐
                  │ FastAPI (main.py)  │
                  └────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  pipeline.run_pipeline │   <-- single orchestrator
              └────────┬───────────────┘
                       │
       ┌───────────────┼─────────────────────────────┐
       ▼               ▼                             ▼
 ┌───────────┐   ┌─────────────┐                 ┌────────────┐
 │ normalize │   │ hard_filter │                 │ explain    │
 │ (Gemini)  │   │ (SQLAlchemy │                 │ (Gemini)   │
 └───────────┘   │  + Python)  │                 └────────────┘
                 └──────┬──────┘
                        │ candidate IDs
                        ▼
                 ┌────────────────────┐
                 │ vector retrieval   │  -> Qdrant or in-memory NumPy
                 │ (Gemini embeddings)│
                 └──────┬─────────────┘
                        ▼
                 ┌────────────────────┐
                 │ rule-based scoring │
                 └────────────────────┘
```

## Components

| Layer | Module | Notes |
| --- | --- | --- |
| HTTP | `backend/app/main.py` | FastAPI app, request/response models, route handlers. |
| Orchestration | `backend/app/services/pipeline.py` | Runs every stage, records per-stage status, degrades gracefully. |
| Stage 2 | `backend/app/services/normalization.py` | Gemini + deterministic rule fallback. |
| Stage 3 | `backend/app/db/repository.py` | Hard constraints over the recipes table. |
| Stage 4 | `backend/app/services/retrieval.py` + `backend/app/vectorstore/store.py` | Embedding the query and ANN search. |
| Stage 5 | `backend/app/services/ranking.py` | Pure scoring function over candidates. |
| Stage 6 | `backend/app/services/explanation.py` | Final Gemini call returning structured JSON. |
| LLM client | `backend/app/clients/gemini.py` | One client used for generation **and** embeddings. |
| DB | `backend/app/db/` | SQLAlchemy 2 declarative; works on SQLite and Postgres. |
| Vector store | `backend/app/vectorstore/` | Two backends behind a common `search()` API. |
| Loader | `scripts/load_recipes.py` | One-shot CSV → DB → vector index. |
| Taxonomy | `backend/app/services/taxonomy.py` | Cheap diet/allergen classifier from ingredient lists. |

## Environment variables

| Var | Purpose | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | Required for stages 2 (LLM path), 4, 6. | _unset_ |
| `GEMINI_MODEL` | Generation model. | `gemini-2.0-flash` |
| `GEMINI_EMBEDDING_MODEL` | Embedding model. | `text-embedding-004` |
| `GEMINI_TIMEOUT_SECONDS` | HTTP timeout for every Gemini call. | `12` |
| `DATABASE_URL` | SQLAlchemy URL. | `sqlite:///<repo>/dishify.db` |
| `QDRANT_URL` | If set, vector search uses Qdrant; otherwise in-memory NumPy. | _unset_ |
| `QDRANT_COLLECTION` | Qdrant collection name. | `dishify_recipes` |
| `EMBEDDINGS_PATH` | Where `load_recipes.py` writes the `.npz` snapshot used by the in-memory backend. | `<repo>/data/embeddings.npz` |

`.env` at the repo root is loaded automatically at startup via `python-dotenv`.

## Degradation rules

The pipeline never fails the request because an optional dependency is missing. Each stage records `ok` / `skipped` / `error` in the response, so clients can see exactly what happened.

| Missing dependency | Behaviour |
| --- | --- |
| `GEMINI_API_KEY` | Stage 2 falls back to deterministic rules; stages 4 & 6 are skipped; stage 5 still scores using ingredient overlap only. |
| Vector index (no `.npz`, no Qdrant) | Stage 4 is skipped; stage 5 falls back to overlap-only ranking over the entire post-filter pool. |
| DB unreachable / empty | Stage 3 reports `error`; stages 4-6 are skipped; the response still returns normalized ingredients. |
| Qdrant unreachable but `.npz` present | The in-memory backend is used. |
| `.npz` missing but `QDRANT_URL` set | Qdrant is used. |

This makes local dev painless and surfaces real outages clearly in production.

## Why two vector backends?

Production wants Qdrant (filtering, persistence, scaling). Dev / CI / corp networks behind a proxy often can't run Docker comfortably. The in-memory backend reads a single `.npz` file (~30 MB at 10k recipes × 768-d float32) and gives ~1 ms searches with no extra services. The pipeline doesn't care which one is in use — both implement `search(query_vector, top_k, allowed_ids) -> list[SearchHit]`.
