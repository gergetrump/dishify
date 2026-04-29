"""Read helpers used by the pipeline.

For a 10k recipe corpus we can afford to do allergen/diet filtering in
Python after a coarse SQL pre-filter on diet. Pushing JSON-array filters
into SQL portably across SQLite + Postgres is painful and not worth it
at this scale.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Recipe

# Recipes whose ``diet`` is one of these are safe for the requested diet.
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
	"""Return recipes that satisfy the user's hard constraints.

	* `diet` is matched against compatibility (e.g. vegetarian users can
	  also eat vegan recipes).
	* `allergies` are matched as substrings against any clean ingredient
	  name (cheap and conservative -- prefer false positives over leaks).
	"""

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
		corpus = " ".join(str(name).lower() for name in (recipe.ingredients_clean or []))
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
