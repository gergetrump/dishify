from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Allow running this file directly with:
# python vector_search/services/indexing_csv_smoketest.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.recipe import ParsedIngredient, RecipeDataPoint
from src.vector_db.recipe_vector_store import RecipeVectorStore


CSV_PATH = PROJECT_ROOT / "data" / "recipes_smoketest.csv"



def parse_list(value: str) -> list[str]:
    """
    Parses CSV string values like:
    '["brown sugar", "milk", "vanilla"]'
    into a Python list.
    """
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
    

def parse_normalized_ingredients(value: str) -> list[ParsedIngredient]:
    """
    Parses CSV string values like:
    "[('brown sugar', '1.0', 'cup'), ('milk', '0.5', 'cup')]"

    into ParsedIngredient objects.
    """
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


def load_recipes_from_csv(csv_path: Path) -> list[RecipeDataPoint]:
    recipes: list[RecipeDataPoint] = []

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            ingredients = parse_list(row["ingredients"])
            directions = parse_list(row["directions"])
            ner = parse_list(row["NER"])
            parsed_ingredients = parse_normalized_ingredients(
                row["normalized_ingredients"]
            )

            recipe = RecipeDataPoint(
                title=row["title"],
                ingredients=ingredients,
                parsed_ingredients=parsed_ingredients,
                directions=directions,
                link=row["link"],
                source=row["source"],
                ner=ner,
            )

            recipes.append(recipe)

    return recipes

