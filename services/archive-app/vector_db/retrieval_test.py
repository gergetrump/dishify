import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Ensure backend root is on sys.path so `app` imports work.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from services.app.vector_db.recipe_vector_store import RecipeVectorStore

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

    # Ensure payload indexes exist for filtering.
    try:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="raw_ingredients",
            field_schema="keyword",
        )
    except Exception as e:
        print(f"Note: Could not create index on 'raw_ingredients' field: {e}")

    try:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="exclusion_restrictions",
            field_schema="keyword",
        )
    except Exception as e:
        print("Note: Could not create index on 'exclusion_restrictions' field: " f"{e}")

    query = "something italian with tomato"

    results = recipe_store.retrieve_recipes(
        query=query,
    )
    print(f"\nQuery: {query}")
    RecipeVectorStore.print_recipes(results, "WITHOUT FILTERS")

    excluded_ingredients = ["milk_allergy"]
    filtered_results = recipe_store.retrieve_recipes(
        query=query,
        excluded_ingredients=excluded_ingredients,
    )
    print(f"\nQuery: {query}")
    RecipeVectorStore.print_recipes(
        filtered_results,
        f"WITH FILTERS: Excluding {excluded_ingredients}",
    )


if __name__ == "__main__":
    run_smoke_test()
