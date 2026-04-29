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

See [`pipeline.md`](./pipeline.md) for what each stage does.

## Components

| Layer | Module | Notes |
| --- | --- | --- |
| HTTP | `backend/app/main.py` | FastAPI app, request/response models, route handlers, lifespan. |
| Middleware | `backend/app/observability.py` | Request-id, structured logging, access log. |
| Orchestration | `backend/app/services/pipeline.py` | Runs every stage, records `status` + `latency_ms`, degrades gracefully. |
| LLM client | `backend/app/clients/gemini.py` | One client used for generation **and** embeddings; retries built in. |
| Embedding cache | `backend/app/clients/embedding_cache.py` | Persistent SHA-256 keyed cache used by the loader. |
| DB | `backend/app/db/` | SQLAlchemy 2 declarative; works on SQLite (default) and Postgres. |
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
| `GEMINI_MAX_RETRIES` | Retries for transient Gemini failures (429, 5xx, transport). | `3` |
| `GEMINI_RETRY_BACKOFF` | Base seconds for exponential backoff between retries. | `1.5` |
| `DATABASE_URL` | SQLAlchemy URL. | `sqlite:///<repo>/dishify.db` |
| `QDRANT_URL` | If set, vector search uses Qdrant; otherwise in-memory NumPy. | _unset_ |
| `QDRANT_COLLECTION` | Qdrant collection name. | `dishify_recipes` |
| `EMBEDDINGS_PATH` | Where the loader writes the `.npz` snapshot used by the in-memory backend. | `<repo>/data/embeddings.npz` |
| `EMBEDDING_CACHE_PATH` | Where the loader caches per-text embeddings between runs. | `<repo>/data/embeddings_cache.npz` |
| `LOG_LEVEL` | Root logging level (`DEBUG`/`INFO`/`WARNING`/...). | `INFO` |

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

## Observability

Every request gets a 12-char `x-request-id` (incoming header is honored if present, otherwise a UUID is minted). The id is bound to a `ContextVar` so every log line emitted while handling that request includes it:

```text
2026-04-29T15:08:12 INFO [c220d22e7814] dishify.access: POST /recommend -> 200 in 8.8ms
```

The middleware writes the id back as a response header so clients can quote it when reporting issues.

Per-stage timings live in `PipelineReport.stages[*].latency_ms` and are surfaced in the `/recommend` response, so you can spot which stage is slow without instrumenting anything else.

## Why two vector backends?

Production wants Qdrant (filtering, persistence, scaling). Dev / CI / corp networks behind a proxy often can't run Docker comfortably. The in-memory backend reads a single `.npz` file (~30 MB at 10k recipes × 768-d float32) and gives ~1 ms searches with no extra services. The pipeline doesn't care which one is in use — both implement `search(query_vector, top_k, allowed_ids) -> list[SearchHit]`.

## Gemini client details

`backend/app/clients/gemini.py` is dependency-free (uses only the stdlib) so the smoke test in CI doesn't need extra packages and corp networks with strict pip allowlists don't choke.

```37:51:backend/app/clients/gemini.py
@dataclass
class GeminiClient:
	api_key: Optional[str] = None
	model: str = DEFAULT_MODEL
	embedding_model: str = DEFAULT_EMBEDDING_MODEL
	timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
	max_retries: int = DEFAULT_MAX_RETRIES
	retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS

	def __post_init__(self) -> None:
		if self.api_key is None:
			self.api_key = os.getenv("GEMINI_API_KEY")
```

Surface:

| Method | Purpose | Endpoint |
| --- | --- | --- |
| `generate_text(prompt, *, temperature, response_mime_type)` | Single text completion. | `:generateContent` |
| `generate_json(prompt, *, temperature)` | Same as above with `responseMimeType=application/json`, parsed into a Python value. | `:generateContent` |
| `embed_text(text)` | One 768-d vector. | `:embedContent` |
| `embed_batch(texts)` | Many vectors, batched 100 per call. | `:batchEmbedContents` |
| `ping()` | Liveness probe (used by `/gemini/health`). | `:generateContent` with prompt `"ping"`. |

All methods raise `GeminiError` on transport, HTTP, or response-shape failures. Callers decide whether to fall back to deterministic logic (normalization, ranking) or surface the error to the user (`/gemini/health`).

### Retries

Every HTTP call goes through `_post_json`, which retries on transport errors and on HTTP statuses we know are usually transient (`408`, `429`, `500`, `502`, `503`, `504`). Backoff is exponential — `GEMINI_RETRY_BACKOFF * 2**attempt` seconds — bounded by `GEMINI_MAX_RETRIES` (default 3). Tune both via env vars without touching code.

When a retry fires, the client logs at `WARNING`:

```text
WARNING [01ce2fc3...] app.clients.gemini: Gemini HTTP 429 on attempt 1/4; retrying in 1.5s
```

If the budget is exhausted the original `GeminiError` is raised so the caller can fall back.

### When to consider switching to the official SDK

Move to `google-genai` when you need streaming responses, tool use / function calling, image / audio inputs, or per-request safety setting overrides. For pure text + embeddings, the stdlib client wins on simplicity.
