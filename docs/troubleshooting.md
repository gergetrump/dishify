# Troubleshooting

A flat list of failure modes you're likely to hit and the exact fix for each.

## Gemini

### `/gemini/health` → `503 GEMINI_API_KEY is not set`

The server process doesn't see the env var.

* Did you `export GEMINI_API_KEY='AIza...'` in **the same shell** where you ran `uvicorn`? Variables don't propagate across terminals.
* Is the key in `.env` at the repo root? It's loaded automatically at startup.
* Did `--reload` restart uvicorn after a parent shell change? The reloader keeps the original env. Stop and restart manually.

### `/gemini/health` → `502 Gemini HTTP 400: ... API key not valid`

Wrong / typo'd / expired key, or invisible whitespace.

```bash
echo "${GEMINI_API_KEY}" | wc -c        # should match key length + 1 (newline)
echo "${GEMINI_API_KEY:0:6}...${GEMINI_API_KEY: -4}"
```

Generate a fresh key at https://aistudio.google.com/apikey, then re-export.

### `/gemini/health` → `502 Gemini HTTP 403: ... Generative Language API has not been used`

The Gemini API isn't enabled on the underlying GCP project.

The error message includes a link — click it and press Enable. Wait ~30s, retry.

### `/gemini/health` → `502 Gemini HTTP 403: ... PERMISSION_DENIED`

The key has restrictions (HTTP referer, IP allow-list).

Google Cloud Console → **APIs & Services → Credentials** → click the key → relax the restrictions for local dev.

### `/gemini/health` → `502 Gemini HTTP 429: Too Many Requests`

Free-tier rate limit. Three fixes:

* Wait a minute.
* `export GEMINI_MODEL=gemini-1.5-flash` then restart uvicorn — different quota bucket.
* Enable billing on the GCP project for production limits.

### `/gemini/health` → `502 Gemini transport error: <urlopen error ...>`

Network can't reach `generativelanguage.googleapis.com`. From the same shell:

```bash
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' \
  "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}"
```

* `Could not resolve host` / `Connection timed out` → corporate proxy. Set `HTTPS_PROXY` / `HTTP_PROXY` and restart uvicorn (`urllib` honors them automatically).
* `HTTP 200` → it's actually a key/API issue, not network. Re-read the auth-related entries above.

## Database

### `/health` returns `recipe_count: null`

DB unreachable or table missing.

```bash
ls -la dishify.db                       # SQLite file should exist at repo root
python scripts/load_recipes.py --no-embed   # creates the table + seeds it
```

For Postgres, also check your container is up:

```bash
docker compose ps
docker compose logs postgres
```

### `/recommend` reports `hard_filter -> error: no such table: recipes`

You haven't run the loader yet, or you're pointing at the wrong DB.

```bash
echo "${DATABASE_URL:-sqlite:///$(pwd)/dishify.db}"   # what the app will use
python scripts/load_recipes.py --no-embed
```

### `/recommend` reports `candidate_pool_size: 0`

The hard filter eliminated everything. Either:

* Your `profile.diet` is too restrictive for the loaded subset (very few `vegan` recipes in 500 random rows). Try `vegetarian` or omit `diet`.
* Your `allergies` list is too broad. Substring matching means `allergies: ["egg"]` removes any recipe with "egg" or "eggplant" in any clean ingredient.

## Vector retrieval

### `vector_retrieval -> skipped: GEMINI_API_KEY is not set; cannot embed query`

Same as the Gemini section above. Stage 5 still runs over the full pool, but quality drops.

### `vector_retrieval -> skipped: No embeddings snapshot at ...`

Loader was run with `--no-embed`. Re-run without that flag:

```bash
python scripts/load_recipes.py --limit 500
```

### `vector_retrieval -> skipped: Qdrant search failed: ...`

`QDRANT_URL` is set but the server is down or the collection doesn't exist. Either:

* Start it: `docker compose up -d qdrant`.
* Re-run the loader to recreate the collection.
* Or unset `QDRANT_URL` to fall back to in-memory.

## Loader

### `Gemini embedding failed: Gemini HTTP 429`

You've burned the free-tier quota mid-load. The loader doesn't resume; re-run the full thing later or with a smaller `--limit`.

If you'll be loading 10k recipes regularly, enable billing or persist embeddings between runs (TODO: incremental loader).

### `CSV not found`

Pass `--csv path/to/dataset.csv`. The default path assumes the repo layout.

## Server

### `uvicorn` says `address already in use`

Another uvicorn (probably from `--reload`) is still bound. Find and kill it:

```bash
lsof -i :8000
kill <pid>
```

Or pick a different port: `uvicorn app.main:app --reload --port 8001`.

### `--reload` keeps restarting in a loop

You probably have an editor that's touching files on save. Disable `--reload` and run plain `uvicorn app.main:app --port 8000` if it's a problem.
