import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is on sys.path so `src` package imports work
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from qdrant_client import QdrantClient
from src.vector_db.recipe_vector_store import RecipeVectorStore
from sentence_transformers import SentenceTransformer
from src.vector_db.parsing import load_recipes_from_csv


CSV_PATH = PROJECT_ROOT / "data" / "dataset_normalized_10000.csv"
COLLECTION_NAME = "recipes_10000"


def run_smoke_test() -> None:
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    recipes = load_recipes_from_csv(CSV_PATH)

    recipe_store = RecipeVectorStore(
        qdrant_client=client,
        embedding_model=model,
        collection_name=COLLECTION_NAME,
    )

    recipe_store.create_collection(recreate=False)
    recipe_store.index_recipes(recipes)

    print(f"Loaded and indexed {len(recipes)} recipes from {CSV_PATH}")


if __name__ == "__main__":
    run_smoke_test()
