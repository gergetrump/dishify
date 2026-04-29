# Running locally

Two tracks, both supported:

* **Track A — zero infra** (SQLite + in-memory vector store). Fastest path. Recommended for first-time setup.
* **Track B — Postgres + Qdrant** via Docker Compose. Closer to production.

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

For dev iteration, `--limit 500` is fine and uses ~5 batched embedding calls. Use `--limit 0` for the full 10k once you're ready.

If you don't have a Gemini key yet, you can still populate the DB (no embeddings, retrieval will be skipped):

```bash
python scripts/load_recipes.py --limit 500 --no-embed
```

### Track B (Postgres + Qdrant)

```bash
docker compose up -d
export DATABASE_URL='postgresql+psycopg://dishify:dishify@localhost:5432/dishify'
export QDRANT_URL='http://localhost:6333'
pip install 'psycopg[binary]'   # only needed for Postgres URLs
python scripts/load_recipes.py --limit 10000
```

Same script, just picks up the env vars and uploads to Qdrant in addition to writing the snapshot.

## 3. Run the API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Visit:

* `http://localhost:8000/docs` — interactive Swagger UI.
* `http://localhost:8000/health` — quick liveness + recipe count.
* `http://localhost:8000/gemini/health` — verifies the Gemini connection.

Try a recommendation:

```bash
curl -s http://localhost:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{
    "ingredients": ["chicken breasts", "cream of mushroom soup", "sour cream"],
    "profile": {"diet": "omnivore", "allergies": ["peanuts"]},
    "top_k": 3
  }' | python -m json.tool
```

The response includes a `stages` array showing exactly which stages ran. See [`pipeline-overview.md`](./pipeline-overview.md) for what each stage means.

## 4. Common gotchas

* **`/gemini/health` returns 502** with detail `Gemini HTTP 429` — you've hit the free-tier rate limit. Wait a minute, or switch to `gemini-1.5-flash` (different quota bucket), or enable billing.
* **Behind a corporate proxy** — `urllib` honors `HTTPS_PROXY` / `HTTP_PROXY`. Export them in the same shell where you launch uvicorn. See [`troubleshooting.md`](./troubleshooting.md).
* **`/recommend` returns `pool_size: 0`** — your DB is empty. Run the loader.
* **`vector_retrieval` reports `skipped`** — either no Gemini key, or no `.npz` snapshot. Re-run the loader without `--no-embed`.
* **CSV not found** — the loader looks at `data/dataset_normalized_10000.csv` by default. Pass `--csv path/to/file.csv` if yours lives elsewhere.

## 5. Cleaning up

```bash
rm -f dishify.db data/embeddings.npz   # Track A
docker compose down -v                 # Track B (also wipes volumes)
```
