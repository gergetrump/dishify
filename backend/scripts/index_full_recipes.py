#!/usr/bin/env python3
"""Stream and index the full annotated recipe dataset into Qdrant."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / ".env.secret", override=True)

from app.models.recipe import RecipeDataPoint  # noqa: E402
from app.vector_db.parsing import recipe_from_csv_row  # noqa: E402
from app.vector_db.recipe_vector_store import RecipeVectorStore  # noqa: E402


QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)


@dataclass
class Checkpoint:
    csv_path: str
    collection_name: str
    embedding_model: str
    next_row: int = 0
    updated_at: float = 0.0


def load_checkpoint(path: Path) -> Checkpoint | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return Checkpoint(**json.load(file))


def save_checkpoint(path: Path, checkpoint: Checkpoint) -> None:
    checkpoint.updated_at = time.time()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(asdict(checkpoint), file, indent=2, sort_keys=True)
    tmp_path.replace(path)


def validate_checkpoint(
    checkpoint: Checkpoint,
    csv_path: Path,
    collection_name: str,
    embedding_model: str,
) -> None:
    if checkpoint.csv_path != str(csv_path):
        raise ValueError(
            f"Checkpoint CSV mismatch: {checkpoint.csv_path} != {csv_path}"
        )
    if checkpoint.collection_name != collection_name:
        raise ValueError(
            "Checkpoint collection mismatch: "
            f"{checkpoint.collection_name} != {collection_name}"
        )
    if checkpoint.embedding_model != embedding_model:
        raise ValueError(
            "Checkpoint embedding model mismatch: "
            f"{checkpoint.embedding_model} != {embedding_model}"
        )


def iter_recipe_batches(
    csv_path: Path,
    *,
    start_row: int,
    csv_batch_size: int,
    max_rows: int | None,
) -> Iterator[tuple[int, list[RecipeDataPoint]]]:
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        batch: list[RecipeDataPoint] = []
        batch_start = start_row
        emitted = 0

        for row_number, row in enumerate(reader):
            if row_number < start_row:
                continue
            if max_rows is not None and emitted >= max_rows:
                break

            if not batch:
                batch_start = row_number
            batch.append(recipe_from_csv_row(row))
            emitted += 1

            if len(batch) >= csv_batch_size:
                yield batch_start, batch
                batch = []

        if batch:
            yield batch_start, batch


def count_csv_rows(csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        return max(sum(1 for _ in file) - 1, 0)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream-index annotated recipes into Qdrant."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=REPO_ROOT / "data" / "dataset_full_annotated.csv",
        help="Annotated CSV path.",
    )
    parser.add_argument(
        "--collection",
        default="recipes_full",
        help="Target Qdrant collection.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=REPO_ROOT / "data" / ".recipes_full_index_checkpoint.json",
        help="Checkpoint file used for resume.",
    )
    parser.add_argument(
        "--csv-batch-size",
        type=positive_int,
        default=5_000,
        help="Number of CSV rows parsed and embedded per outer batch.",
    )
    parser.add_argument(
        "--upload-batch-size",
        type=positive_int,
        default=100,
        help="Number of Qdrant points per upsert request.",
    )
    parser.add_argument(
        "--embedding-batch-size",
        type=positive_int,
        default=256,
        help="SentenceTransformer encode batch size.",
    )
    parser.add_argument(
        "--max-rows",
        type=positive_int,
        default=None,
        help="Index at most this many rows, useful for benchmarks.",
    )
    parser.add_argument(
        "--count-total",
        action="store_true",
        help="Count total rows before indexing. This scans the whole CSV once.",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the collection before indexing from row 0.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the checkpoint file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and embed rows without creating/upserting to Qdrant.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Optional SentenceTransformer device, e.g. cpu, mps, cuda.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = args.csv.resolve()

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    if args.recreate and args.resume:
        raise ValueError("Use either --recreate or --resume, not both.")

    checkpoint = load_checkpoint(args.checkpoint) if args.resume else None
    if checkpoint:
        validate_checkpoint(
            checkpoint,
            csv_path,
            args.collection,
            EMBEDDING_MODEL,
        )
        start_row = checkpoint.next_row
    else:
        start_row = 0
        checkpoint = Checkpoint(
            csv_path=str(csv_path),
            collection_name=args.collection,
            embedding_model=EMBEDDING_MODEL,
        )

    total_rows = count_csv_rows(csv_path) if args.count_total else None

    client_kwargs: dict = {"url": QDRANT_URL}
    if QDRANT_API_KEY:
        client_kwargs["api_key"] = QDRANT_API_KEY

    print(f"CSV: {csv_path}")
    print(f"Collection: {args.collection}")
    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Start row: {start_row:,}")
    print(f"Dry run: {args.dry_run}")
    if total_rows is not None:
        print(f"Total rows: {total_rows:,}")

    client = QdrantClient(**client_kwargs)
    model_kwargs = {"device": args.device} if args.device else {}
    model = SentenceTransformer(EMBEDDING_MODEL, **model_kwargs)
    store = RecipeVectorStore(
        qdrant_client=client,
        embedding_model=model,
        collection_name=args.collection,
    )

    if not args.dry_run:
        if args.recreate:
            if start_row != 0:
                raise ValueError("--recreate requires starting from row 0.")
            print(f"Recreating collection {args.collection}...")
            store.create_collection(recreate=True)
            save_checkpoint(args.checkpoint, checkpoint)
        elif start_row == 0 and not store.collection_exists():
            print(f"Creating collection {args.collection}...")
            store.create_collection(recreate=False)

    started_at = time.monotonic()
    indexed = 0

    for batch_start, recipes in iter_recipe_batches(
        csv_path,
        start_row=start_row,
        csv_batch_size=args.csv_batch_size,
        max_rows=args.max_rows,
    ):
        batch_started_at = time.monotonic()

        if args.dry_run:
            texts = [
                f"""
                Title: {recipe.title}
                Title: {recipe.title}
                Raw ingredients: {", ".join(str(item) for item in recipe.raw_ingredients)}
                """
                for recipe in recipes
            ]
            vectors = model.encode(
                texts,
                batch_size=args.embedding_batch_size,
                show_progress_bar=False,
            )
            if indexed == 0 and recipes:
                print(f"Sample title: {recipes[0].title}")
                print(f"Sample vector dimensions: {len(vectors[0])}")
                print(f"Sample restrictions: {recipes[0].exclusion_restrictions[:10]}")
        else:
            store.index_recipes(
                recipes,
                batch_size=args.upload_batch_size,
                start_id=batch_start,
                embedding_batch_size=args.embedding_batch_size,
            )
            checkpoint.next_row = batch_start + len(recipes)
            save_checkpoint(args.checkpoint, checkpoint)

        indexed += len(recipes)
        elapsed = time.monotonic() - started_at
        batch_elapsed = time.monotonic() - batch_started_at
        rows_per_second = indexed / elapsed if elapsed > 0 else 0.0
        next_row = batch_start + len(recipes)
        progress = f"{next_row:,}"
        if total_rows is not None:
            progress = f"{progress}/{total_rows:,}"

        print(
            f"Rows {progress} | batch={len(recipes):,} "
            f"in {batch_elapsed:.1f}s | avg={rows_per_second:.1f} rows/s"
        )

    elapsed = time.monotonic() - started_at
    mode = "Dry run" if args.dry_run else "Indexing"
    print(f"{mode} complete: {indexed:,} rows in {elapsed / 60:.1f} min")
    if not args.dry_run:
        print(f"Checkpoint: {args.checkpoint}")


if __name__ == "__main__":
    main()
