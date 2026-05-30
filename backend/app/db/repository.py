"""Read helpers used by the pipeline."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Recipe, UserPreference

_DIET_COMPATIBILITY: dict[str, set[str]] = {
    "vegan": {"vegan"},
    "vegetarian": {"vegan", "vegetarian"},
    "omnivore": {"vegan", "vegetarian", "omnivore"},
    "pescatarian": {"vegan", "vegetarian", "pescatarian"},
}


def normalize_diet(diet: str | None) -> str | None:
    if not diet:
        return None
    value = diet.strip().lower()
    if value in _DIET_COMPATIBILITY:
        return value
    return None


def hard_filter(
    session: Session,
    *,
    diet: str | None = None,
    allergies: Sequence[str] = (),
    limit: int | None = None,
) -> list[Recipe]:
    """Return recipes that satisfy the user's hard constraints."""

    stmt = select(Recipe)
    allowed_diets = _DIET_COMPATIBILITY.get(normalize_diet(diet) or "")
    if allowed_diets is not None:
        stmt = stmt.where(Recipe.diet.in_(allowed_diets))
    if limit is not None:
        stmt = stmt.limit(limit)

    rows = session.scalars(stmt).all()
    if not allergies:
        return list(rows)

    allergens_lower = {a.strip().lower() for a in allergies if a and a.strip()}
    if not allergens_lower:
        return list(rows)

    def is_safe(recipe: Recipe) -> bool:
        corpus = " ".join(
            str(name).lower() for name in (recipe.ingredients_clean or [])
        )
        corpus += " " + " ".join(str(name).lower() for name in (recipe.allergens or []))
        return not any(allergen in corpus for allergen in allergens_lower)

    return [r for r in rows if is_safe(r)]


def get_by_ids(session: Session, recipe_ids: Iterable[int]) -> list[Recipe]:
    ids = [int(i) for i in recipe_ids]
    if not ids:
        return []
    rows = session.scalars(select(Recipe).where(Recipe.id.in_(ids))).all()
    by_id = {r.id: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


def count(session: Session) -> int:
    from sqlalchemy import func

    return int(session.scalar(select(func.count()).select_from(Recipe)) or 0)


def get_user_preferences(session: Session, user_id: str) -> dict:
    row = session.get(UserPreference, user_id)
    if row is None:
        return {
            "excluded_ingredients": [],
            "diet": None,
            "allergies": [],
        }
    return {
        "excluded_ingredients": list(row.excluded_ingredients or []),
        "diet": normalize_diet(row.diet) if row.diet else None,
        "allergies": list(row.allergies or []),
    }


def set_user_preferences(
    session: Session,
    *,
    user_id: str,
    excluded_ingredients: Sequence[str],
    diet: str | None,
    allergies: Sequence[str],
) -> dict:
    exclusions = [
        str(item).strip() for item in excluded_ingredients if str(item).strip()
    ]
    allergy_values = [str(item).strip() for item in allergies if str(item).strip()]
    normalized_diet = normalize_diet(diet)
    prefs = session.get(UserPreference, user_id)
    if prefs is None:
        prefs = UserPreference(
            user_id=user_id,
            excluded_ingredients=exclusions,
            diet=normalized_diet,
            allergies=allergy_values,
        )
        session.add(prefs)
    else:
        prefs.excluded_ingredients = exclusions
        prefs.diet = normalized_diet
        prefs.allergies = allergy_values
    session.commit()
    return {
        "excluded_ingredients": list(exclusions),
        "diet": normalized_diet,
        "allergies": list(allergy_values),
    }


def allowed_recipe_ids_by_exclusions(
    session: Session,
    excluded_ingredients: Sequence[str],
    *,
    base_ids: Sequence[int] | None = None,
) -> list[int] | None:
    """Return allowed recipe ids after applying excluded-ingredient matching."""

    excluded = {
        str(item).strip().lower() for item in excluded_ingredients if str(item).strip()
    }
    if not excluded:
        return None
    if base_ids is not None:
        base_ids = [int(item) for item in base_ids]
        if not base_ids:
            return []

    stmt = select(Recipe.id, Recipe.ingredients_clean, Recipe.allergens)
    if base_ids is not None:
        stmt = stmt.where(Recipe.id.in_(base_ids))

    rows = session.execute(stmt).all()
    allowed: list[int] = []
    for recipe_id, ingredients_clean, allergens in rows:
        corpus = " ".join(str(name).lower() for name in (ingredients_clean or []))
        corpus += " " + " ".join(str(name).lower() for name in (allergens or []))
        if not any(excl in corpus for excl in excluded):
            allowed.append(int(recipe_id))
    return allowed


def allowed_recipe_ids_by_profile(
    session: Session,
    *,
    diet: str | None,
    allergies: Sequence[str],
    excluded_ingredients: Sequence[str],
) -> list[int] | None:
    base_ids: list[int] | None = None
    if diet or allergies:
        recipes = hard_filter(session, diet=diet, allergies=allergies)
        base_ids = [r.id for r in recipes]
        if not base_ids:
            return []

    allowed_ids = allowed_recipe_ids_by_exclusions(
        session,
        excluded_ingredients,
        base_ids=base_ids,
    )
    if allowed_ids is None:
        return base_ids
    return allowed_ids
