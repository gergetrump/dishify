"""Load recipes from the CSV into the database and the vector index.

Usage:
	python scripts/load_recipes.py                    # default: 500 recipes
	python scripts/load_recipes.py --limit 10000      # full sample
	python scripts/load_recipes.py --csv data/dataset_normalized_10000.csv
	python scripts/load_recipes.py --no-embed         # DB only, skip vectors

Environment:
	DATABASE_URL          target SQL DB (default: sqlite:///./dishify.db)
	GEMINI_API_KEY        required for embeddings (skip with --no-embed)
	QDRANT_URL            if set, also push embeddings to Qdrant
	EMBEDDINGS_PATH       where to write the .npz snapshot (default data/embeddings.npz)
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

# Allow running from repo root: `python scripts/load_recipes.py`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import numpy as np
from app.clients.embedding_cache import EmbeddingCache
from app.clients.gemini import EMBEDDING_DIMENSION, GeminiClient, GeminiError
from app.db import Recipe, SessionLocal, create_all
from app.services.taxonomy import infer_allergens, infer_diet
from app.vectorstore import COLLECTION_NAME, EMBEDDINGS_PATH
from tqdm import tqdm


def _coerce_list(raw: str) -> list[str]:
    """The CSV stores list-shaped fields as Python literals (single quotes etc.).
    Try JSON first, fall back to ``ast.literal_eval``."""

    if raw is None:
        return []
    value = str(raw).strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return []
    if isinstance(parsed, list):
        return [str(x) for x in parsed if x is not None]
    if isinstance(parsed, tuple):
        return [str(x) for x in parsed if x is not None]
    return []


def _build_query_text_for_recipe(recipe: Recipe) -> str:
    """Mirror of services.retrieval.build_query_text but on the recipe side."""
    return f"Recipe '{recipe.title}' with ingredients: " + ", ".join(
        recipe.ingredients_clean
    )


def load_csv(path: Path, limit: int | None) -> list[Recipe]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if limit is not None and i >= limit:
                break
            ingredients_raw = _coerce_list(row.get("ingredients", ""))
            ingredients_clean = _coerce_list(row.get("NER", ""))
            directions = _coerce_list(row.get("directions", ""))
            recipe = Recipe(
                id=int(row.get("Unnamed: 0") or i),
                title=str(row.get("title") or "").strip()[:512],
                link=str(row.get("link") or "").strip()[:1024] or None,
                source=str(row.get("source") or "").strip()[:128] or None,
                ingredients_raw=ingredients_raw,
                ingredients_clean=ingredients_clean,
                directions=directions,
                diet=infer_diet(ingredients_clean),
                allergens=infer_allergens(ingredients_clean),
            )
            rows.append(recipe)
    return rows


def write_db(recipes: Sequence[Recipe]) -> None:
    create_all()
    with SessionLocal() as session:
        # Truncate-and-replace for idempotency.
        session.query(Recipe).delete()
        session.commit()
        session.add_all(recipes)
        session.commit()


def embed_recipes(client: GeminiClient, recipes: Sequence[Recipe]) -> np.ndarray:
    """Embed recipes via Gemini, using a persistent on-disk cache.

    Cached vectors are reused across runs (keyed by sha256(text) + model name),
    so re-running the loader is cheap. On rate-limit (HTTP 429) the partial
    progress is flushed to disk and the script exits with a clear message,
    letting the user resume by simply re-running.
    """

    texts = [_build_query_text_for_recipe(r) for r in recipes]
    cache = EmbeddingCache(model=client.embedding_model)
    cached_count = sum(1 for t in texts if cache.has(t))
    missing_indices = [i for i, t in enumerate(texts) if not cache.has(t)]
    print(
        f"  cache hits: {cached_count}/{len(texts)}; embedding {len(missing_indices)} new texts"
    )

    if missing_indices:
        try:
            for start in tqdm(range(0, len(missing_indices), 100), desc="Embedding"):
                batch_idxs = missing_indices[start : start + 100]
                batch_texts = [texts[i] for i in batch_idxs]
                batch_vectors = client.embed_batch(batch_texts)
                cache.put_many(zip(batch_texts, batch_vectors, strict=False))
                cache.save()
        except GeminiError as exc:
            cache.save()
            raise SystemExit(
                f"Gemini embedding failed: {exc}\n"
                "Partial progress has been cached -- re-run the loader to resume."
            ) from exc

    output: list[np.ndarray] = []
    for t in texts:
        vec = cache.get(t)
        if vec is None:
            raise SystemExit(
                "Internal error: embedding missing from cache after success."
            )
        output.append(vec)
    return np.stack(output, axis=0).astype(np.float32)


def normalize_rows(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


def write_snapshot(path: Path, ids: Sequence[int], vectors: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, ids=np.asarray(ids, dtype=np.int64), vectors=vectors)


def push_to_qdrant(url: str, ids: Sequence[int], vectors: np.ndarray) -> None:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels

    client = QdrantClient(url=url)
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qmodels.VectorParams(
            size=EMBEDDING_DIMENSION, distance=qmodels.Distance.COSINE
        ),
    )
    client.upload_points(
        collection_name=COLLECTION_NAME,
        points=[
            qmodels.PointStruct(id=int(i), vector=v.tolist())
            for i, v in zip(ids, vectors, strict=False)
        ],
        batch_size=256,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv", type=Path, default=ROOT / "data" / "dataset_normalized_10000.csv"
    )
    parser.add_argument("--limit", type=int, default=500, help="0 means load all rows")
    parser.add_argument(
        "--no-embed", action="store_true", help="Skip embedding/vector index"
    )
    args = parser.parse_args()

    limit = None if args.limit in (0, -1) else args.limit
    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}")

    print(f"Loading CSV {args.csv} (limit={limit if limit is not None else 'ALL'})")
    recipes = load_csv(args.csv, limit)
    print(f"Parsed {len(recipes)} recipes. Writing to DB...")
    write_db(recipes)

    if args.no_embed:
        print("Skipping embeddings (--no-embed).")
        return

    client = GeminiClient()
    if not client.is_configured:
        raise SystemExit(
            "GEMINI_API_KEY is not set, so embeddings can't be created. "
            "Re-run with --no-embed if you only want to populate the DB."
        )

    print(f"Embedding {len(recipes)} recipes with {client.embedding_model}...")
    vectors = embed_recipes(client, recipes)
    if vectors.shape[0] != len(recipes):
        raise SystemExit(
            f"Embedding count mismatch: got {vectors.shape[0]} vectors for {len(recipes)} recipes."
        )
    vectors = normalize_rows(vectors)

    ids = [r.id for r in recipes]
    snapshot_path = EMBEDDINGS_PATH
    write_snapshot(snapshot_path, ids, vectors)
    print(f"Wrote snapshot {snapshot_path} ({vectors.shape}).")

    qdrant_url = os.getenv("QDRANT_URL", "").strip()
    if qdrant_url:
        print(f"Uploading to Qdrant at {qdrant_url}...")
        push_to_qdrant(qdrant_url, ids, vectors)
        print(f"Qdrant collection '{COLLECTION_NAME}' is ready.")
    else:
        print(
            "QDRANT_URL not set; skipping Qdrant upload (in-memory store will be used)."
        )


if __name__ == "__main__":
    main()
