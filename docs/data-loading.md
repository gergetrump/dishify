# Data loading

The loader lives in `scripts/load_recipes.py`. It is a one-shot, idempotent script that turns the CSV into the two artifacts the API needs at runtime: a relational table of recipes and a vector index keyed by recipe id.

## Source dataset

`data/dataset_normalized_10000.csv` (10k rows sampled from a larger corpus). Columns:

| Column | Used as | Notes |
| --- | --- | --- |
| `Unnamed: 0` | `Recipe.id` | Stable across runs; pandas-style export artifact. |
| `title` | `Recipe.title` | |
| `ingredients` | `Recipe.ingredients_raw` | Raw quantity-bearing strings (e.g. `"1 c. firmly packed brown sugar"`). |
| `directions` | `Recipe.directions` | List of step strings. |
| `link`, `source` | `Recipe.link`, `Recipe.source` | URL + provenance. |
| `NER` | `Recipe.ingredients_clean` | Clean ingredient names — used for matching, scoring, diet/allergen inference. |
| `normalized_ingredients` | (unused for now) | Includes quantities + units; could feed substitution logic later. |

The list-shaped fields are stored as Python literals (single quotes), so the loader tries `json.loads` first and then `ast.literal_eval`:

```48:67:scripts/load_recipes.py
def _coerce_list(raw: str) -> List[str]:
	"""The CSV stores list-shaped fields as Python literals (single quotes etc.).
	Try JSON first, fall back to ``ast.literal_eval``."""

	if raw is None:
		return []
	value = str(raw).strip()
	if not value:
		return []
	try:
		parsed = json.loads(value)
	except json.JSONDecodeError:
		try:
			parsed = ast.literal_eval(value)
		except (SyntaxError, ValueError):
			return []
```

## Diet & allergen inference

The dataset has no diet / allergen labels, so the loader infers them from the clean ingredient list using a keyword classifier in `backend/app/services/taxonomy.py`. Two functions:

* `infer_diet(ingredients)` returns one of `vegan` / `vegetarian` / `omnivore`. A recipe with any meat or seafood token becomes `omnivore`; otherwise dairy/eggs/honey demote `vegan` to `vegetarian`.
* `infer_allergens(ingredients)` returns a list of allergen group names: `peanuts`, `tree_nuts`, `gluten`, `dairy`, `eggs`, `soy`, `fish`, `shellfish`, `sesame`.

Design choice: **prefer false positives over leaks**. It's much better to over-restrict (skip a recipe a user could've eaten) than to recommend something containing their allergen. If you make changes here, keep that direction.

## Database write

After parsing, the loader truncates the `recipes` table and inserts the new batch in one transaction:

```104:111:scripts/load_recipes.py
def write_db(recipes: Sequence[Recipe]) -> None:
	create_all()
	with SessionLocal() as session:
		# Truncate-and-replace for idempotency.
		session.query(Recipe).delete()
		session.commit()
		session.add_all(recipes)
		session.commit()
```

Idempotency is on purpose — re-running the loader is the simplest way to get a clean state.

## Embedding the corpus

Each recipe gets a single embedding from a templated string:

```95:97:scripts/load_recipes.py
def _build_query_text_for_recipe(recipe: Recipe) -> str:
	"""Mirror of services.retrieval.build_query_text but on the recipe side."""
	return f"Recipe '{recipe.title}' with ingredients: " + ", ".join(recipe.ingredients_clean)
```

The exact template matters less than **using the same shape for the query side**. Keep `services/retrieval.build_query_text` and `_build_query_text_for_recipe` aligned when you change one.

Embeddings are produced via `GeminiClient.embed_batch`, which uses `batchEmbedContents` (max 100 per request). For 10k recipes that's 100 API calls. Hitting the free-tier rate limit is plausible — if it happens you'll get a `Gemini HTTP 429` and the script aborts. Wait, then re-run.

## Vector store outputs

Two artifacts are written:

* `data/embeddings.npz` — `ids` (`int64`) and L2-normalized `vectors` (`float32`, shape `(N, 768)`). Pre-normalizing means cosine similarity at query time is just a dot product.
* (Optional) Qdrant collection `dishify_recipes` if `QDRANT_URL` is set.

The vector store picks one at runtime — see `backend/app/vectorstore/store.py`.

## Sizing

| Recipes | Rough loader time (Track A) | `embeddings.npz` |
| --- | --- | --- |
| 500 | ~30 s | ~1.5 MB |
| 2 000 | ~2 min | ~6 MB |
| 10 000 | ~10 min (rate-limited) | ~30 MB |

For day-to-day dev, 500 is plenty. Bump the limit when you're benchmarking quality.
