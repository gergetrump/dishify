# Roadmap

Living checklist of what's done, what's next, and what's nice-to-have. Update this when you finish work or pull a new item up the stack.

## ✅ Done

### Pipeline (all 6 stages from the README)

- Stage 1 — FastAPI input/output models, validation, CORS.
- Stage 2 — Gemini-backed normalization with deterministic rule fallback.
- Stage 3 — diet + allergen hard filter (SQL + Python).
- Stage 4 — vector retrieval over Gemini embeddings, with two interchangeable backends (Qdrant / in-memory NumPy).
- Stage 5 — rule-based scoring with token-set ingredient matching (no `egg` ↔ `eggplant` leaks).
- Stage 6 — LLM rerank + reasons + substitutions, deterministic fallback when Gemini is unavailable.
- Orchestrator records `status` + `latency_ms` per stage; degrades gracefully when any optional dependency is missing.

### Infra

- `Dockerfile` (multi-stage, non-root, healthcheck) + `docker-compose.yml` (postgres + qdrant + backend).
- SQLite default for dev; Postgres via `DATABASE_URL` (`psycopg[binary]` already in deps).
- Lifespan-managed vector store cached on `app.state` (no per-request reload).
- `.env` loaded automatically via `python-dotenv`.

### Quality

- 45-test pytest suite covering normalization, taxonomy, repository, ranking, embedding cache, and full `/recommend` end-to-end.
- `pyproject.toml` with ruff (lint + format) and pytest config.
- CI runs ruff + pytest + Gemini reachability (when secret is present).

### Operations

- Structured logging with per-request `x-request-id` (incoming honored, outgoing minted).
- Per-stage `latency_ms` in the response.
- Gemini HTTP retries with exponential backoff on 408/429/5xx + transport errors.
- Persistent embedding cache (sha256 keyed, model-tagged) so re-running the loader is cheap and resumable on rate-limit.

### API surface

- `GET /health` — liveness + recipe count + active vector store.
- `GET /gemini/health` — surfaces actual upstream error in `detail`.
- `POST /normalize` — stage 2 only.
- `POST /recommend` — full pipeline; response includes recipe titles, links, ingredients, directions, score components.
- `POST /gemini/generate` — debug passthrough.

## 🔜 Next up

Things we explicitly considered and chose to defer. Pull these up the stack when they start mattering.

| Priority | Item | Why it's deferred |
| --- | --- | --- |
| Medium | `pydantic-settings`-based `Settings` class instead of bare `os.getenv` calls. | Current setup works; add when env vars sprawl further. |
| Medium | `mypy` wired into CI (currently configured in `pyproject.toml` but not enforced). | Adds ~50 MB of CI install time and surfaces a lot of fix-ups; plan a focused pass. |
| Medium | `/ready` endpoint distinct from `/health` (DB + vector store reachable). | Only matters once we deploy behind a load balancer. |
| Low | Streaming responses from `/recommend` (LLM tokens as they arrive). | Latency from Gemini isn't the bottleneck yet. |
| Low | Auth + per-user rate limiting. | Required before any public deploy. |
| Low | Pagination for `/recommend` (or a separate `/recipes` browse endpoint). | Only matters at full-corpus scale. |

## 🎯 Quality / evals

The recommender currently has no objective quality measurement.

- **Eval harness** — hand-label ~50 ingredient sets with expected recipe IDs; report recall@5 / MRR. Without this, every formula tweak is a vibe.
- **A/B harness for the ranker formula** — sweep the `weights` tuple in `score_candidates` against the eval set.
- **Substitution review** — sample N LLM-generated substitutions into a CSV/Notion review file; the free-tier model will hallucinate plausible-but-wrong things.

## 🍒 Product polish

- **Frontend** — even a single static `frontend/index.html` with a vanilla-JS form posting to `/recommend` would prove the loop. The `/recommend` response already includes everything a card needs (title, link, ingredients, available/missing).
- **Curated substitutions** — a small `data/substitutions.yaml` (`butter -> margarine`, `sour cream -> greek yogurt`) gives 80% of the value with zero LLM calls. Used in the deterministic fallback path of Stage 6.
- **Recipe images** — dataset has `link` but no images. OG-image scraping at load time is the lightweight route.
- **Better matching** — fuzzy/synonym layer on top of the token-set matcher in Stage 5 (e.g. "cilantro" ↔ "coriander").

## 🔭 Observability / ops

- **OpenTelemetry traces** — FastAPI + SQLAlchemy auto-instrumentation, export to OTLP.
- **Metrics** — Prometheus middleware (request count, latency histogram, per-stage timings as a histogram).
- **Sentry-style error tracking** for unhandled exceptions and `error`-status stages.

## 🧪 Robustness

- **Backoff + jitter** — current retry uses pure exponential; real `random.uniform(0.5, 1.5)` jitter prevents thundering herd.
- **Per-stage timeouts** — today only Gemini calls have a timeout. The orchestrator could enforce wall-clock budgets per stage and degrade cleanly.
- **Schema migrations** — currently `create_all()` is enough; `alembic` once we change the recipe schema in production.

## How to keep this doc honest

Whenever you finish something on this list, move it under "Done" with a short note. When you find a new gap, add it under "Next up" with a one-line "why it's deferred" so future-you knows whether to pick it up. Don't let this become a wishlist of vague ideas — every entry should be small enough to ship in a focused chunk.
