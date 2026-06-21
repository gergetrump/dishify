#!/usr/bin/env python3
"""Index annotated recipes into Qdrant for the recommend pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


def _repo_root() -> Path:
    path = Path(__file__).resolve()
    if len(path.parents) > 4:
        return path.parents[4]
    return Path("/")


REPO_ROOT = _repo_root()
load_dotenv(REPO_ROOT / ".env")

from app.config import settings  # noqa: E402
from app.parsing import load_recipes_from_csv  # noqa: E402
from app.vector_store import RecipeVectorStore  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Index recipes into Qdrant")
    parser.add_argument(
        "--csv",
        type=Path,
        default=(
            Path("/data/dataset_10000_annotated.csv")
            if Path("/data/dataset_10000_annotated.csv").exists()
            else REPO_ROOT / "data" / "dataset_10000_annotated.csv"
        ),
        help="Annotated dataset CSV path",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the collection before indexing",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"Dataset not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading recipes from {args.csv}...")
    recipes = load_recipes_from_csv(args.csv)
    print(f"Loaded {len(recipes)} recipes")

    client_kwargs: dict = {"url": settings.qdrant_url}
    if settings.qdrant_api_key:
        client_kwargs["api_key"] = settings.qdrant_api_key

    client = QdrantClient(**client_kwargs)
    model = SentenceTransformer(settings.embedding_model)
    store = RecipeVectorStore(
        qdrant_client=client,
        embedding_model=model,
        collection_name=settings.qdrant_collection,
    )

    print(
        f"Creating collection '{settings.qdrant_collection}' (recreate={args.recreate})..."
    )
    store.create_collection(recreate=args.recreate)

    print("Indexing recipes...")
    store.index_recipes(recipes)
    print("Done.")


if __name__ == "__main__":
    main()
