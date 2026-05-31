from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

# Allow running this file directly.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.app.models.recipe import ParsedIngredient, RecipeDataPoint

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
            exclusion_restrictions_count = parse_int(
                row.get("exclusion_restrictions_count")
            )

            recipe = RecipeDataPoint(
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

            recipes.append(recipe)

    return recipes
