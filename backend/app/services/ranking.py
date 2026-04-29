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

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..db.models import Recipe
from .retrieval import RetrievedCandidate


@dataclass
class RankedCandidate:
	recipe: Recipe
	score: float
	ingredient_match: float
	vector_similarity: float
	missing_ingredients: list[str]
	available_ingredients: list[str]


_STOPWORDS: frozenset[str] = frozenset(
	{
		"a",
		"an",
		"the",
		"and",
		"or",
		"of",
		"with",
		"to",
		"for",
		"in",
		"on",
		"at",
		"by",
		"from",
		"&",
	}
)


def _normalize_token(value: str) -> str:
	return value.strip().lower()


def _singularize(word: str) -> str:
	if len(word) <= 3:
		return word
	if word.endswith("ies"):
		return word[:-3] + "y"
	if word.endswith("oes") or word.endswith("ses"):
		return word[:-2]
	if word.endswith("s") and not word.endswith("ss"):
		return word[:-1]
	return word


def _tokenize_ingredient(name: str) -> set[str]:
	"""Bag of meaningful, singularized words.

	Splitting on whitespace + stopword removal + singularization is the cheapest
	way to make ``"chicken"`` match ``"chicken breasts"`` without making
	``"egg"`` match ``"eggplant"`` (they are different whole tokens).
	"""

	tokens: set[str] = set()
	for raw in _normalize_token(name).split():
		stripped = "".join(c for c in raw if c.isalpha())
		if not stripped or stripped in _STOPWORDS or len(stripped) < 2:
			continue
		tokens.add(_singularize(stripped))
	return tokens


def _ingredient_match(recipe_ingredient: str, user_token_set: set[str]) -> bool:
	"""A recipe ingredient counts as available if at least one of its
	meaningful tokens is in the user's combined token set.

	Single-token ingredients (e.g. ``"flour"``) match only on exact identity.
	Multi-token ingredients (e.g. ``"chicken breasts"``) match if any token
	is in the user's set, which fixes the head-noun problem (``"chicken"``
	matches ``"chicken breasts"``) without enabling substring leaks.
	"""

	tokens = _tokenize_ingredient(recipe_ingredient)
	if not tokens:
		return False
	return bool(tokens & user_token_set)


def score_candidates(
	candidates: Sequence[RetrievedCandidate],
	recipes: Iterable[Recipe],
	user_ingredients: Sequence[str],
	*,
	weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
	missing_normalizer: float = 10.0,
) -> list[RankedCandidate]:
	"""Score a batch of candidates and return them sorted high-to-low."""

	w_match, w_vec, w_miss = weights
	user_token_set: set[str] = set()
	for item in user_ingredients:
		if item:
			user_token_set |= _tokenize_ingredient(item)
	score_by_id = {c.recipe_id: c.vector_score for c in candidates}

	ranked: list[RankedCandidate] = []
	for recipe in recipes:
		recipe_ingredients = [_normalize_token(x) for x in (recipe.ingredients_clean or []) if x]
		if not recipe_ingredients:
			continue

		available: list[str] = []
		missing: list[str] = []
		for ingredient in recipe_ingredients:
			if _ingredient_match(ingredient, user_token_set):
				available.append(ingredient)
			else:
				missing.append(ingredient)
		available = sorted(set(available))
		missing = sorted(set(missing))

		ingredient_match = len(available) / max(1, len(set(recipe_ingredients)))
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


def take_top(ranked: Sequence[RankedCandidate], n: int) -> list[RankedCandidate]:
	return list(ranked[:n])


def fallback_rank_without_vectors(
	recipes: Iterable[Recipe],
	user_ingredients: Sequence[str],
	*,
	limit: int | None = None,
) -> list[RankedCandidate]:
	"""Used when retrieval (Gemini embeddings / vector store) is unavailable.

	Identical to ``score_candidates`` but with vector_similarity forced to 0,
	so ranking falls back purely to ingredient overlap minus missing penalty.
	"""

	stub = [RetrievedCandidate(recipe.id, 0.0) for recipe in recipes]
	ranked = score_candidates(stub, recipes, user_ingredients)
	if limit is not None:
		return ranked[:limit]
	return ranked
