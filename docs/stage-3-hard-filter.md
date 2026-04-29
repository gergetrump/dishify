# Stage 3 — Hard filter

Implemented in `backend/app/db/repository.py`. This stage **must be deterministic and must not involve the LLM** (per the README) — these are safety constraints.

## Why hard?

Two things that can never be left to the model:

1. **Diet boundaries** — a vegan user must never see a recipe with meat. Period.
2. **Allergens** — a peanut-allergic user must never see a recipe with peanuts. Period.

A small probability of error from a fluent generator is unacceptable here, so the boundary is enforced with simple, auditable code well before the LLM gets to think about anything.

## How it works

```36:69:backend/app/db/repository.py
def hard_filter(
	session: Session,
	*,
	diet: Optional[str] = None,
	allergies: Sequence[str] = (),
	limit: Optional[int] = None,
) -> List[Recipe]:
	"""Return recipes that satisfy the user's hard constraints.

	* `diet` is matched against compatibility (e.g. vegetarian users can
	  also eat vegan recipes).
	* `allergies` are matched as substrings against any clean ingredient
	  name (cheap and conservative -- prefer false positives over leaks).
	"""

	stmt = select(Recipe)
	allowed_diets = _DIET_COMPATIBILITY.get(normalize_diet(diet) or "", None)
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
```

Two phases:

1. **SQL pre-filter on diet** using a compatibility table so vegetarians can also see vegan recipes, etc.

   ```20:26:backend/app/db/repository.py
   _DIET_COMPATIBILITY: dict[str, set[str]] = {
   	"vegan": {"vegan"},
   	"vegetarian": {"vegan", "vegetarian"},
   	"omnivore": {"vegan", "vegetarian", "omnivore"},
   	"pescatarian": {"vegan", "vegetarian", "pescatarian"},
   }
   ```

2. **Python allergen filter** — substring match against both the clean ingredient list and the inferred allergen tags. Substring is intentional: "peanut" matches "peanut butter" and "raw peanuts" alike.

## Why Python for allergens, not SQL?

Portable JSON-array containment across SQLite and Postgres is awkward. At 10k recipes the in-Python pass is fast enough (sub-millisecond on a laptop), and the logic is much clearer. If we move to >100k recipes or all-Postgres, we can swap to a `?|` / `&&` query.

## Where the diet/allergen labels come from

They're inferred at load time, not at query time — see [`data-loading.md`](./data-loading.md). The classifier is in `backend/app/services/taxonomy.py`. **Read it before adjusting allergen behaviour** — the design decision baked in is "prefer false positives over leaks". Don't quietly relax that.

## Inputs from the user

`profile.diet` is normalized through `normalize_diet`:

```13:18:backend/app/db/repository.py
def normalize_diet(diet: Optional[str]) -> Optional[str]:
	if not diet:
		return None
	value = diet.strip().lower()
	if value in _DIET_COMPATIBILITY:
		return value
	return None
```

Unknown diets (e.g. `"flexitarian"`) silently turn into "no preference". The pipeline still runs, just without a diet constraint.

## Output

A list of `Recipe` ORM objects that survived the constraints. Whatever the size, it's the candidate pool that Stage 4 has to retrieve from. The orchestrator passes their IDs into `retrieve_candidates(allowed_ids=...)`.
