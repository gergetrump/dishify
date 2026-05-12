import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is on sys.path so `src` package imports work
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from src.vector_db.recipe_vector_store import RecipeVectorStore

COLLECTION_NAME = "recipes_10000"


def run_smoke_test() -> None:
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    recipe_store = RecipeVectorStore(
        qdrant_client=client,
        embedding_model=model,
        collection_name=COLLECTION_NAME,
    )

    query = "quick meal with tomato and cheese"

    results = recipe_store.retrieve_recipes(
        query=query,
        top_k=10,
    )

    print(f"\nQuery: {query}")
    print(f"Retrieved {len(results)} recipes:\n")

    for rank, recipe in enumerate(results, start=1):
        print(f"#{rank}")
        print(f"Score: {recipe['score']}")
        print(f"Title: {recipe['title']}")
        print(f"Ingredients: {', '.join(recipe['ingredients'])}")
        print(f"Directions: {' '.join(recipe['directions'])}")
        print(f"Link: {recipe['link']}")
        print("-" * 60)


if __name__ == "__main__":
    run_smoke_test()
