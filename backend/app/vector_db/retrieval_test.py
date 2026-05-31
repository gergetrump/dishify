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

from backend.app.vector_db.recipe_vector_store import RecipeVectorStore

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

    print("\n" + "=" * 60)
    print("WITHOUT FILTERS")
    print("=" * 60)
    results = recipe_store.retrieve_recipes(
        query=query,
    )

    print(f"\nQuery: {query}")
    print(f"Retrieved {len(results)} recipes:\n")

    def _format_ner(value: object) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if value is None:
            return ""
        return str(value)

    for rank, recipe in enumerate(results, start=1):
        print(f"#{rank}")
        print(f"Score: {recipe.score}")
        print(f"Title: {recipe.title}")
        print(f"Ingredients: {', '.join(recipe.ingredients or [])}")
        print(f"Raw ingredients: {', '.join(recipe.raw_ingredients or [])}")
        print(f"NER: {_format_ner(recipe.ner)}")
        print(
            "Exclusion restrictions: " f"{_format_ner(recipe.exclusion_restrictions)}"
        )
        print("Exclusion restrictions count: " f"{recipe.exclusion_restrictions_count}")
        print(f"Directions: {' '.join(recipe.directions or [])}")
        print(f"Link: {recipe.link}")
        print("-" * 60)

    excluded_ingredients = ["milk_allergy"]
    print("\n" + "=" * 60)
    print(f"WITH FILTERS: Excluding {excluded_ingredients}")
    print("=" * 60)
    filtered_results = recipe_store.retrieve_recipes(
        query=query,
        excluded_ingredients=excluded_ingredients,
    )

    print(f"\nQuery: {query}")
    print(f"Retrieved {len(filtered_results)} recipes (filtered):\n")

    for rank, recipe in enumerate(filtered_results, start=1):
        print(f"#{rank}")
        print(f"Score: {recipe.score}")
        print(f"Title: {recipe.title}")
        print(f"Ingredients: {', '.join(recipe.ingredients or [])}")
        print(f"Raw ingredients: {', '.join(recipe.raw_ingredients or [])}")
        print(f"NER: {_format_ner(recipe.ner)}")
        print(
            "Exclusion restrictions: " f"{_format_ner(recipe.exclusion_restrictions)}"
        )
        print("Exclusion restrictions count: " f"{recipe.exclusion_restrictions_count}")
        print(f"Directions: {' '.join(recipe.directions or [])}")
        print(f"Link: {recipe.link}")
        print("-" * 60)


if __name__ == "__main__":
    run_smoke_test()
