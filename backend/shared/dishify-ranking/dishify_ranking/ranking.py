from __future__ import annotations

from typing import Iterable

from dishify_contracts import RetrievedRecipe


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _name_tokens(value: str) -> set[str]:
    return {token for token in value.split() if token}


def _ingredient_names_match(recipe_name: str, available_name: str) -> bool:
    if recipe_name == available_name:
        return True

    recipe_tokens = _name_tokens(recipe_name)
    available_tokens = _name_tokens(available_name)
    if not recipe_tokens or not available_tokens:
        return False

    return recipe_tokens.issubset(available_tokens) or available_tokens.issubset(
        recipe_tokens
    )


def _find_available_match(
    recipe_name: str,
    available: dict[str, tuple[float | None, str | None]],
) -> tuple[float | None, str | None] | None:
    if recipe_name in available:
        return available[recipe_name]

    for available_name, values in available.items():
        if _ingredient_names_match(recipe_name, available_name):
            return values

    return None


def _normalize_available_ingredients(
    available_ingredients: Iterable[object] | None,
) -> dict[str, tuple[float | None, str | None]]:
    if not available_ingredients:
        return {}

    normalized: dict[str, tuple[float | None, str | None]] = {}
    for item in available_ingredients:
        if item is None:
            continue

        if isinstance(item, str):
            name = item
            quantity = None
            unit = None
        elif isinstance(item, dict):
            name = item.get("name") or item.get("raw_text") or ""
            quantity = item.get("quantity")
            unit = item.get("unit")
        else:
            name = getattr(item, "name", "") or getattr(item, "raw_text", "")
            quantity = getattr(item, "quantity", None)
            unit = getattr(item, "unit", None)

        normalized_name = _normalize_name(str(name))
        if not normalized_name:
            continue

        normalized[normalized_name] = (
            float(quantity) if quantity is not None else None,
            str(unit).strip().lower() if unit else None,
        )
    return normalized


def score_recipes_by_inventory(
    recipes: list[RetrievedRecipe],
    available_ingredients: Iterable[object] | None,
    *,
    ingredient_weight: float = 0.3,
    semantic_weight: float = 0.7,
) -> list[RetrievedRecipe]:
    """Re-rank recipes using available ingredients with optional qty/unit checks."""

    available = _normalize_available_ingredients(available_ingredients)
    if not available:
        return recipes

    total_weight = semantic_weight + ingredient_weight
    if total_weight <= 0:
        return recipes

    semantic_weight /= total_weight
    ingredient_weight /= total_weight

    scored: list[RetrievedRecipe] = []
    for recipe in recipes:
        semantic_score = float(recipe.score or 0)
        parsed = recipe.parsed_ingredients or []
        recipe_names: list[str] = []
        recipe_matches: dict[str, tuple[float | None, str | None] | None] = {}
        full_matches = 0
        partial_matches = 0

        for item in parsed:
            name = item.name or item.raw_text or ""
            quantity = item.quantity
            unit = item.unit

            normalized_name = _normalize_name(str(name))
            if not normalized_name:
                continue

            recipe_names.append(normalized_name)
            if normalized_name not in recipe_matches:
                recipe_matches[normalized_name] = _find_available_match(
                    normalized_name, available
                )
            available_match = recipe_matches[normalized_name]
            if available_match is None:
                continue

            available_qty, available_unit = available_match
            if (
                quantity is not None
                and unit
                and available_qty is not None
                and available_unit is not None
                and available_unit == str(unit).strip().lower()
                and available_qty >= float(quantity)
            ):
                full_matches += 1
            else:
                partial_matches += 1

        total = len(recipe_names)
        if total == 0:
            inventory_score = 0.0
        else:
            inventory_score = (full_matches + 0.5 * partial_matches) / total

        matched_names = [n for n in recipe_names if recipe_matches.get(n) is not None]
        missing_names = [n for n in recipe_names if recipe_matches.get(n) is None]
        final_score = (semantic_weight * semantic_score) + (
            ingredient_weight * inventory_score
        )

        updated = recipe.model_copy(
            update={
                "inventory_score": inventory_score,
                "inventory_matched": matched_names,
                "inventory_missing": missing_names,
                "score": final_score,
            }
        )
        scored.append(updated)

    return sorted(scored, key=lambda r: r.score, reverse=True)
