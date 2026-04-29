# Stage 5 — Rule-based scoring

Implemented in `backend/app/services/ranking.py`. Pure function. No I/O. Easy to unit test.

## The formula

Straight from the README:

```text
score = 0.5 * ingredient_match
      + 0.3 * vector_similarity
      - 0.2 * missing_ingredient_penalty
```

with the three terms defined as:

* **`ingredient_match`** — fraction of the recipe's ingredients the user already has. `|recipe ∩ user| / |recipe|`. Range `[0, 1]`. Asymmetric on purpose — favours recipes whose ingredients are mostly available.
* **`vector_similarity`** — cosine similarity from Stage 4, rescaled from `[-1, 1]` to `[0, 1]` so it composes with the other terms.
* **`missing_ingredient_penalty`** — `min(1, |missing| / 10)`. A recipe missing 10+ ingredients is fully penalized; below 10 the penalty scales linearly.

## Implementation

```43:78:backend/app/services/ranking.py
def score_candidates(
	candidates: Sequence[RetrievedCandidate],
	recipes: Iterable[Recipe],
	user_ingredients: Sequence[str],
	*,
	weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
	missing_normalizer: float = 10.0,
) -> List[RankedCandidate]:
	"""Score a batch of candidates and return them sorted high-to-low."""

	w_match, w_vec, w_miss = weights
	user_set = {_normalize_token(i) for i in user_ingredients if i}
	score_by_id = {c.recipe_id: c.vector_score for c in candidates}

	ranked: List[RankedCandidate] = []
	for recipe in recipes:
		recipe_ingredients = [_split_recipe_ingredient(x) for x in (recipe.ingredients_clean or []) if x]
		if not recipe_ingredients:
			continue

		recipe_set = set(recipe_ingredients)
		available = sorted(recipe_set & user_set)
		missing = sorted(recipe_set - user_set)

		ingredient_match = len(available) / len(recipe_set)
		raw_vec = score_by_id.get(recipe.id, 0.0)
		vector_similarity = max(0.0, min(1.0, (raw_vec + 1.0) / 2.0))
		miss_penalty = min(1.0, len(missing) / max(missing_normalizer, 1.0))

		score = w_match * ingredient_match + w_vec * vector_similarity - w_miss * miss_penalty
		ranked.append(
			RankedCandidate(
				recipe=recipe,
				score=score,
				ingredient_match=ingredient_match,
				vector_similarity=vector_similarity,
				missing_ingredients=missing,
				available_ingredients=available,
			)
		)

	ranked.sort(key=lambda c: c.score, reverse=True)
	return ranked
```

The function returns a `RankedCandidate` per input that includes both the score and the components, so Stage 6 can show the user *why* a recipe was suggested without re-deriving anything.

## Vector-less fallback

When Stage 4 is unavailable (no Gemini key / no index), the orchestrator calls:

```87:96:backend/app/services/ranking.py
def fallback_rank_without_vectors(
	recipes: Iterable[Recipe],
	user_ingredients: Sequence[str],
	*,
	limit: Optional[int] = None,
) -> List[RankedCandidate]:
	"""Used when retrieval (Gemini embeddings / vector store) is unavailable.

	Identical to ``score_candidates`` but with vector_similarity forced to 0,
	so ranking falls back purely to ingredient overlap minus missing penalty.
	"""
```

Same formula, just `vector_similarity = 0` for everyone. The two scoring terms that remain are still meaningful, so the recommender keeps producing sensible results — just without the semantic-similarity boost.

## Token matching gotcha

The matcher compares **whole strings** (`"chicken breast"` vs `"chicken breast"`), not bag-of-words. That means `"chicken"` (user) does not match `"chicken breast"` (recipe). This is intentional for now — partial-word matching produces a lot of weird hits ("egg" matching "eggplant"). The fix is to use the normalizer's output tokens consistently on both sides, which is why Stage 2 always runs first.

If you want fuzzier matching later, the right place is here in `_normalize_token` / `_split_recipe_ingredient` — not anywhere else in the pipeline.

## Tuning

The weights are intentionally easy to override via the `weights` argument. Things you might try:

| Goal | Change |
| --- | --- |
| Trust the LLM's semantics more | Bump vector weight (e.g. `(0.4, 0.5, 0.1)`). |
| Be stricter about completeness | Bump `missing_normalizer` down (e.g. 5) to penalize missing ingredients harder. |
| Always require near-complete matches | Filter `ingredient_match >= 0.5` before sorting. |

Whatever you change, write a unit test pinning the score for a few representative recipes — the moment you tune by feel, you regress quietly.
