"""Stage 5 -- deterministic rule-based scoring.

Implements the README formula:

	score = 0.5 * ingredient_match
	      + 0.3 * vector_similarity
	      - 0.2 * missing_ingredient_penalty

* ``ingredient_match`` is the fraction of the recipe's ingredients the user
  already has (Jaccard-flavoured but asymmetric -- it favours recipes whose
  ingredients are mostly available).
* ``vector_similarity`` is rescaled from [-1, 1] to [0, 1].
* ``missing_ingredient_penalty`` is the count of missing ingredients,
  normalized by 10 and clipped to [0, 1].
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from ..db.models import Recipe
from .retrieval import RetrievedCandidate


@dataclass
class RankedCandidate:
	recipe: Recipe
	score: float
	ingredient_match: float
	vector_similarity: float
	missing_ingredients: List[str]
	available_ingredients: List[str]


def _normalize_token(value: str) -> str:
	return value.strip().lower()


def _split_recipe_ingredient(name: str) -> str:
	"""The dataset's NER strings are short but can contain modifiers; we keep the whole
	lower-cased phrase as the canonical token."""
	return _normalize_token(name)


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


def take_top(ranked: Sequence[RankedCandidate], n: int) -> List[RankedCandidate]:
	return list(ranked[:n])


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

	stub = [RetrievedCandidate(recipe.id, 0.0) for recipe in recipes]
	ranked = score_candidates(stub, recipes, user_ingredients)
	if limit is not None:
		return ranked[:limit]
	return ranked
