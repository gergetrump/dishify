# Setup

Two tracks, both supported:

* **Track A — zero infra** (SQLite + in-memory vector store). Fastest path. Recommended for first-time setup.
* **Track B — Postgres + Qdrant + containerized backend** via Docker Compose. Closer to production.

## Prerequisites

* Python 3.12 or 3.13
* `git`
* (Track B only) Docker + Docker Compose

## 1. One-time setup

```bash
git clone <this repo>
cd dishify
bash start.sh                 # creates .venv and installs requirements.txt
source .venv/bin/activate
```

Put your Gemini key in `.env` (gitignored):

```bash
echo "GEMINI_API_KEY=AIza...your_real_key..." > .env
```

The API loads `.env` automatically at startup, so you don't need to `export` it.

## 2. Load the dataset

### Track A (default)

```bash
python scripts/load_recipes.py --limit 500
```

This:

1. Parses `data/dataset_normalized_10000.csv`.
2. Infers diet (`vegan` / `vegetarian` / `omnivore`) and allergens for each recipe.
3. Writes them to `dishify.db` (SQLite at the repo root).
4. Embeds each recipe with `text-embedding-004` and writes `data/embeddings.npz`.

For dev iteration, `--limit 500` is fine. Use `--limit 0` for the full 10k once you're ready.

If you don't have a Gemini key yet, you can still populate the DB (no embeddings, retrieval will be skipped):

```bash
python scripts/load_recipes.py --limit 500 --no-embed
```

### Track B (Postgres + Qdrant + containerized backend)

`docker-compose.yml` ships three services: `postgres`, `qdrant`, and `backend` (the FastAPI app, built from the repo `Dockerfile`).

```bash
docker compose up -d --build
docker compose exec backend python scripts/load_recipes.py --limit 10000
```

Want to run uvicorn on the host instead of in a container (for fast iteration)?

```bash
docker compose up -d postgres qdrant
export DATABASE_URL='postgresql+psycopg://dishify:dishify@localhost:5432/dishify'
export QDRANT_URL='http://localhost:6333'
python scripts/load_recipes.py --limit 10000
cd backend && uvicorn app.main:app --reload --port 8000
```

`psycopg[binary]` is in `requirements.txt`, so the Postgres URL works out of the box.

## 3. Run the API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Visit:

* `http://localhost:8000/docs` — interactive Swagger UI.
* `http://localhost:8000/health` — quick liveness + recipe count + active vector store.
* `http://localhost:8000/gemini/health` — verifies the Gemini connection.

Try a recommendation:

```bash
curl -s http://localhost:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{
    "ingredients": ["chicken", "cream of mushroom soup", "sour cream"],
    "profile": {"diet": "omnivore", "allergies": ["peanuts"]},
    "top_k": 3
  }' | python -m json.tool
```

The response includes a `stages` array showing exactly which stages ran. See [`pipeline.md`](./pipeline.md) for what each stage means.

## 4. Tests + lint

```bash
pip install pytest ruff      # already in requirements.txt
pytest                       # 45 tests, ~1s
ruff check backend tests scripts
ruff format --check backend tests scripts
```

`pyproject.toml` controls all three tools. `mypy` is also configured but not yet wired into CI.

### How tests are isolated

`tests/conftest.py` does two unusual but important things:

1. Sets `DATABASE_URL`, `EMBEDDINGS_PATH`, `EMBEDDING_CACHE_PATH` to a temp dir at **module load time**, before any `app.*` import. This binds the SQLAlchemy engine to a clean SQLite file per pytest session.
2. Truncates the `recipes` table before every test (`autouse` fixture). Hermetic, no module reloads.

`GEMINI_API_KEY` is unset, so tests never accidentally hit the network.

### What the suite covers

| File | What it pins |
| --- | --- |
| `test_normalization.py` | Stage 2 rule path matches the CI smoke test invariant + parametrized cases. |
| `test_taxonomy.py` | Diet + allergen inference; the `eggplant` ↛ `eggs` regression. |
| `test_repository.py` | Diet compatibility table + allergen substring filter. |
| `test_ranking.py` | Token tokenizer + `chicken` ↔ `chicken breasts` match + score components. |
| `test_pipeline.py` | End-to-end `/recommend` via TestClient: titles in response, per-stage `latency_ms`, `x-request-id`, every degradation path. |
| `test_embedding_cache.py` | Roundtrip + reload + model-change invalidation. |

## 5. CI

`.github/workflows/ci.yml`:

1. `ruff check` + `ruff format --check`
2. `pytest`
3. The original normalization smoke test (kept for backwards compat).
4. **Gemini reachability check** — only runs when the `GEMINI_API_KEY` secret is present. Fails the build if `GeminiClient.generate_text(...)` raises. PRs from forks (no secret) skip this step gracefully.

## 6. Dataset details

### Source

`data/dataset_normalized_10000.csv` (10k rows sampled from a larger corpus). Columns:

| Column | Used as | Notes |
| --- | --- | --- |
| `Unnamed: 0` | `Recipe.id` | Stable across runs; pandas-style export artifact. |
| `title` | `Recipe.title` | |
| `ingredients` | `Recipe.ingredients_raw` | Raw quantity-bearing strings. |
| `directions` | `Recipe.directions` | List of step strings. |
| `link`, `source` | `Recipe.link`, `Recipe.source` | URL + provenance. |
| `NER` | `Recipe.ingredients_clean` | Clean ingredient names — used for matching, scoring, diet/allergen inference. |
| `normalized_ingredients` | (unused for now) | Includes quantities + units; could feed substitution logic later. |

List-shaped fields are stored as Python literals (single quotes), so the loader tries `json.loads` first and then `ast.literal_eval`.

### Diet & allergen inference

The dataset has no labels, so the loader infers them from the clean ingredient list using a keyword classifier in `backend/app/services/taxonomy.py`. Two functions:

* `infer_diet(ingredients)` returns one of `vegan` / `vegetarian` / `omnivore`.
* `infer_allergens(ingredients)` returns a list of allergen group names: `peanuts`, `tree_nuts`, `gluten`, `dairy`, `eggs`, `soy`, `fish`, `shellfish`, `sesame`.

**Design choice: prefer false positives over leaks.** Don't quietly relax that.

### Embedding cache

The loader caches every embedding to `data/embeddings_cache.npz`, keyed by `sha256(text)` and tagged with the model name. Re-running the loader after a corpus tweak only re-embeds the rows whose text actually changed.

If you hit `Gemini HTTP 429` mid-run, the partial cache is flushed before the script exits and the failure message tells you to re-run — the next run resumes from where it stopped, with no quota wasted on what's already been embedded.

Switching `GEMINI_EMBEDDING_MODEL` invalidates the cache automatically.

### Sizing

| Recipes | Loader time (Track A) | `embeddings.npz` |
| --- | --- | --- |
| 500 | ~30 s | ~1.5 MB |
| 2 000 | ~2 min | ~6 MB |
| 10 000 | ~10 min (rate-limited) | ~30 MB |

## 7. Cleaning up

```bash
rm -f dishify.db data/embeddings.npz data/embeddings_cache.npz   # Track A
docker compose down -v                                           # Track B (wipes volumes too)
```
