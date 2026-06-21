#!/usr/bin/env python3
"""Stream and index the full annotated recipe dataset into Qdrant."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

load_dotenv(REPO_ROOT / ".env")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)


@dataclass(slots=True)
class ParsedIngredient:
    name: str = ""
    quantity: float | None = None
    unit: str | None = None
    raw_text: str = ""


@dataclass(slots=True)
class RecipeDataPoint:
    title: str = ""
    ingredients: list[str] = field(default_factory=list)
    raw_ingredients: list[str] = field(default_factory=list)
    parsed_ingredients: list[ParsedIngredient] = field(default_factory=list)
    normalized_ingredients: list[str] = field(default_factory=list)
    directions: list[str] = field(default_factory=list)
    link: str = ""
    source: str = ""
    ner: list[str] = field(default_factory=list)
    exclusion_restrictions: list[str] = field(default_factory=list)
    exclusion_restrictions_count: int | None = None


class RecipeVectorStore:
    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_model: SentenceTransformer,
        collection_name: str = "recipes",
    ):
        self.client = qdrant_client
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        if hasattr(embedding_model, "get_sentence_embedding_dimension"):
            self.vector_size = embedding_model.get_sentence_embedding_dimension()
        else:
            self.vector_size = embedding_model.get_embedding_dimension()

    def create_collection(self, recreate: bool = False) -> None:
        if recreate:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
        else:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )

        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="raw_ingredients",
            field_schema="keyword",
        )
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="exclusion_restrictions",
            field_schema="keyword",
        )

    def index_recipes(
        self,
        recipes: list[RecipeDataPoint],
        batch_size: int = 100,
        start_id: int = 0,
        embedding_batch_size: int | None = None,
        upload_retries: int = 3,
        retry_sleep_seconds: float = 5.0,
        skip_upload_errors: bool = True,
    ) -> list[dict[str, object]]:
        points: list[PointStruct] = []
        failed_uploads: list[dict[str, object]] = []
        embedding_texts = [recipe_to_embedding_text(recipe) for recipe in recipes]
        vectors = self.embedding_model.encode(
            embedding_texts,
            batch_size=embedding_batch_size or batch_size,
            show_progress_bar=False,
        ).tolist()

        for idx, (recipe, vector) in enumerate(zip(recipes, vectors), start=start_id):
            point = PointStruct(
                id=idx,
                vector=vector,
                payload={
                    "title": recipe.title,
                    "ingredients": recipe.ingredients,
                    "parsed_ingredients": [
                        {
                            "name": ingredient.name,
                            "quantity": ingredient.quantity,
                            "unit": ingredient.unit,
                            "raw_text": ingredient.raw_text,
                        }
                        for ingredient in recipe.parsed_ingredients
                    ],
                    "raw_ingredients": recipe.raw_ingredients,
                    "directions": recipe.directions,
                    "link": recipe.link,
                    "source": recipe.source,
                    "ner": recipe.ner,
                    "exclusion_restrictions": recipe.exclusion_restrictions,
                    "exclusion_restrictions_count": recipe.exclusion_restrictions_count,
                },
            )
            points.append(point)

            if len(points) >= batch_size:
                failure = self._upsert_points(
                    points,
                    upload_retries=upload_retries,
                    retry_sleep_seconds=retry_sleep_seconds,
                    skip_upload_errors=skip_upload_errors,
                )
                if failure:
                    failed_uploads.append(failure)
                points = []

        if points:
            failure = self._upsert_points(
                points,
                upload_retries=upload_retries,
                retry_sleep_seconds=retry_sleep_seconds,
                skip_upload_errors=skip_upload_errors,
            )
            if failure:
                failed_uploads.append(failure)

        return failed_uploads

    def _upsert_points(
        self,
        points: list[PointStruct],
        *,
        upload_retries: int,
        retry_sleep_seconds: float,
        skip_upload_errors: bool,
    ) -> dict[str, object] | None:
        first_id = int(points[0].id)
        last_id = int(points[-1].id)

        for attempt in range(1, upload_retries + 2):
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
                return None
            except Exception as exc:
                if attempt <= upload_retries:
                    print(
                        "Qdrant upsert failed "
                        f"for points {first_id:,}-{last_id:,}; "
                        f"retry {attempt}/{upload_retries} in "
                        f"{retry_sleep_seconds:.1f}s: {exc}"
                    )
                    time.sleep(retry_sleep_seconds)
                    continue

                if not skip_upload_errors:
                    raise

                print(
                    "Skipping failed Qdrant upload after retries: "
                    f"points {first_id:,}-{last_id:,}: {exc}"
                )
                return {
                    "first_id": first_id,
                    "last_id": last_id,
                    "count": len(points),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "updated_at": time.time(),
                }

    def collection_exists(self) -> bool:
        try:
            collections = self.client.get_collections().collections
            return any(
                collection.name == self.collection_name for collection in collections
            )
        except Exception:
            return False


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []

    parsed = ast.literal_eval(value)
    return list(parsed)


def parse_quantity(value: str | None) -> float | None:
    if value is None:
        return None

    value = value.strip()
    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None

    value = value.strip()
    if value == "":
        return None

    try:
        return int(value)
    except ValueError:
        return None


def parse_normalized_ingredients(value: str | None) -> list[ParsedIngredient]:
    if not value:
        return []

    parsed = ast.literal_eval(value)
    ingredients: list[ParsedIngredient] = []

    for name, quantity, unit in parsed:
        ingredients.append(
            ParsedIngredient(
                name=name,
                quantity=parse_quantity(quantity),
                unit=unit,
                raw_text=name,
            )
        )

    return ingredients


def recipe_from_csv_row(row: dict[str, str]) -> RecipeDataPoint:
    ingredients = [
        str(item).strip()
        for item in parse_list(row["ingredients"])
        if item is not None and str(item).strip()
    ]
    raw_ingredients = [
        str(item).strip()
        for item in parse_list(row.get("raw_ingredients") or "")
        if item is not None and str(item).strip()
    ]
    if not raw_ingredients:
        raw_ingredients = list(ingredients)
    directions = parse_list(row["directions"])
    ner = parse_list(row.get("NER") or "")
    parsed_ingredients = parse_normalized_ingredients(
        row.get("normalized_ingredients") or ""
    )
    normalized_ingredients = [
        ingredient.name for ingredient in parsed_ingredients if ingredient.name
    ]
    exclusion_restrictions = parse_list(row.get("exclusion_restrictions") or "")
    exclusion_restrictions_count = parse_int(row.get("exclusion_restrictions_count"))

    return RecipeDataPoint(
        title=row["title"],
        ingredients=ingredients,
        raw_ingredients=raw_ingredients,
        parsed_ingredients=parsed_ingredients,
        normalized_ingredients=normalized_ingredients,
        directions=directions,
        link=row["link"],
        source=row["source"],
        ner=ner,
        exclusion_restrictions=exclusion_restrictions,
        exclusion_restrictions_count=exclusion_restrictions_count,
    )


def recipe_to_embedding_text(recipe: RecipeDataPoint) -> str:
    return f"""
    Title: {recipe.title}
    Title: {recipe.title}
    Raw ingredients: {", ".join(str(item) for item in recipe.raw_ingredients)}
    """


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


def append_skipped_uploads(
    path: Path, skipped_uploads: list[dict[str, object]]
) -> None:
    if not skipped_uploads:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for skipped in skipped_uploads:
            file.write(json.dumps(skipped, sort_keys=True))
            file.write("\n")


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
        default=50,
        help="Number of Qdrant points per upsert request.",
    )
    parser.add_argument(
        "--qdrant-timeout",
        type=positive_int,
        default=120,
        help="Qdrant HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--upload-retries",
        type=int,
        default=3,
        help="Retries per Qdrant upload chunk before skipping or failing.",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=5.0,
        help="Seconds to sleep between Qdrant upload retries.",
    )
    parser.add_argument(
        "--fail-on-upload-error",
        action="store_true",
        help="Stop the run if a Qdrant upload chunk still fails after retries.",
    )
    parser.add_argument(
        "--skipped-upload-log",
        type=Path,
        default=REPO_ROOT / "data" / ".recipes_full_skipped_uploads.jsonl",
        help="JSONL log for upload chunks skipped after all retries fail.",
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
    if args.upload_retries < 0:
        raise ValueError("--upload-retries must be zero or greater.")
    if args.retry_sleep < 0:
        raise ValueError("--retry-sleep must be zero or greater.")

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

    client_kwargs: dict = {"url": QDRANT_URL, "timeout": args.qdrant_timeout}

    print(f"CSV: {csv_path}")
    print(f"Collection: {args.collection}")
    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Start row: {start_row:,}")
    print(f"Dry run: {args.dry_run}")
    print(f"Qdrant timeout: {args.qdrant_timeout}s")
    print(f"Upload batch size: {args.upload_batch_size:,}")
    print(f"Upload retries: {args.upload_retries}")
    print(f"Skip upload errors: {not args.fail_on_upload_error}")
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
    skipped_points = 0

    for batch_start, recipes in iter_recipe_batches(
        csv_path,
        start_row=start_row,
        csv_batch_size=args.csv_batch_size,
        max_rows=args.max_rows,
    ):
        batch_started_at = time.monotonic()

        if args.dry_run:
            texts = [recipe_to_embedding_text(recipe) for recipe in recipes]
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
            skipped_uploads = store.index_recipes(
                recipes,
                batch_size=args.upload_batch_size,
                start_id=batch_start,
                embedding_batch_size=args.embedding_batch_size,
                upload_retries=args.upload_retries,
                retry_sleep_seconds=args.retry_sleep,
                skip_upload_errors=not args.fail_on_upload_error,
            )
            append_skipped_uploads(args.skipped_upload_log, skipped_uploads)
            skipped_points += sum(int(item["count"]) for item in skipped_uploads)
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
            f" | skipped_upload_points={skipped_points:,}"
        )

    elapsed = time.monotonic() - started_at
    mode = "Dry run" if args.dry_run else "Indexing"
    print(f"{mode} complete: {indexed:,} rows in {elapsed / 60:.1f} min")
    if not args.dry_run:
        print(f"Checkpoint: {args.checkpoint}")
        if skipped_points:
            print(f"Skipped upload points: {skipped_points:,}")
            print(f"Skipped upload log: {args.skipped_upload_log}")


if __name__ == "__main__":
    main()
