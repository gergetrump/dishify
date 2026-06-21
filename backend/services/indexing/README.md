# Indexing Worker

Offline CLI batch job that reads an annotated recipe CSV, embeds each row with SentenceTransformers, and upserts vectors plus metadata into Qdrant. There is no HTTP API.

## Shared team embeddings

Everyone should query the **same Qdrant Cloud collection** so search results match across dev machines and deploy:

| Variable | Team value |
|----------|------------|
| `QDRANT_URL` | Shared cloud cluster URL (in `.env.secret`) |
| `QDRANT_API_KEY` | Shared API key (in `.env.secret`) |
| `QDRANT_COLLECTION` | `recipes_10000` |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |

**Index once, connect read-only.** One person reindexes the shared cluster when the dataset changes. Everyone else only runs retrieval/recommend — do not `--recreate` on your own.

**Do not run the 2M full-dataset index on the shared dev cluster.** That caused OOM/disk alerts. Use a separate experimental cluster or local Docker Qdrant for large indexing experiments.

## Run with Docker (recommended)

From the repo root (uses `QDRANT_URL` / `QDRANT_API_KEY` from `.env.secret`):

```bash
docker compose run --rm indexing-worker --recreate
```

Place your CSV at `data/dataset_10000_annotated.csv` (mounted read-only as `/data` in the container).

To index a different file:

```bash
docker compose run --rm indexing-worker --csv /data/my_recipes.csv --recreate
```

For **solo offline dev** only, override to local Qdrant:

```bash
QDRANT_URL=http://qdrant:6333 QDRANT_API_KEY= docker compose run --rm indexing-worker --recreate
```

## Run locally

Requires Qdrant reachable at `QDRANT_URL` (default `http://localhost:6333`).

```bash
cd backend/services/indexing
pip install -r requirements.txt ../../shared/dishify-contracts ../../shared/dishify-vector-store
PYTHONPATH=. python -m app.main --csv /path/to/recipes.csv --recreate
```

## CLI

Entry point: [`app/main.py`](app/main.py)

| Flag | Default | Purpose |
|------|---------|---------|
| `--csv` | `/data/dataset_10000_annotated.csv` if present, else `data/dataset_10000_annotated.csv` | Input CSV path |
| `--recreate` | off | Drop and recreate the Qdrant collection before indexing |

Flow:

1. Load `.env` from repo root via `python-dotenv`
2. `load_recipes_from_csv()` → list of `RecipeDataPoint`
3. Connect to Qdrant and load `SentenceTransformer` from settings
4. `RecipeVectorStore.create_collection(recreate=...)`
5. `RecipeVectorStore.index_recipes()` — batch upsert (100 points at a time)

## CSV format

[`app/parsing.py`](app/parsing.py) uses `csv.DictReader` and expects these columns:

- `title`, `ingredients`, `raw_ingredients`, `directions`, `link`, `source`
- `NER`, `normalized_ingredients`, `exclusion_restrictions`, `exclusion_restrictions_count`

List fields (`ingredients`, `directions`, `NER`, etc.) must be Python literal strings in the CSV, e.g. `"['flour', 'sugar']"`, parsed with `ast.literal_eval`.

`normalized_ingredients` is a list of `(name, quantity, unit)` tuples, e.g. `"[('flour', '2', 'cups'), ...]"`.

If `raw_ingredients` is empty, it falls back to `ingredients`.

Each row becomes a [`RecipeDataPoint`](../../shared/dishify-vector-store/dishify_vector_store/models.py).

## Embeddings and Qdrant payload

[`dishify_vector_store`](../../shared/dishify-vector-store/dishify_vector_store/vector_store.py) builds embedding text per recipe:

```
Title: {title}
Title: {title}
Raw ingredients: {comma-separated raw_ingredients}
```

Qdrant points:

- **ID:** row index (`0`, `1`, `2`, …)
- **Vector:** cosine distance; dimension from the embedding model (384 for `all-MiniLM-L6-v2`)
- **Payload:** `title`, `ingredients`, `parsed_ingredients`, `raw_ingredients`, `directions`, `link`, `source`, `ner`, `exclusion_restrictions`, `exclusion_restrictions_count`

Keyword payload indexes exist on `raw_ingredients` and `exclusion_restrictions` for filtered retrieval.

`normalized_ingredients` is parsed but not stored directly in Qdrant; it is used to build `parsed_ingredients`.

## Configuration

[`app/config.py`](app/config.py) — also documented in repo-root [`.env.example`](../../../.env.example):

| Env var | Default | Notes |
|---------|---------|-------|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint |
| `QDRANT_API_KEY` | unset | Optional auth |
| `QDRANT_COLLECTION` | `recipes_10000` | Must match the retrieval service |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Shared with retrieval |

The retrieval service reads from the same collection; collection name and embedding model must align or search will fail or return wrong results.

## Constraints

- Batch only — no incremental or streaming indexing API
- Fixed schema — CSV must match the annotated dataset column layout
- Full reindex — `--recreate` drops the collection; without it, upserts by row index (same index overwrites)
- Dataset not in repo — `data/` is gitignored; supply the CSV locally or on the server

## Legacy scripts

Older standalone scripts outside this service (not the current path):

- [`backend/scripts/index_recipes.py`](../../scripts/index_recipes.py)
- [`backend/scripts/index_full_recipes.py`](../../scripts/index_full_recipes.py)
