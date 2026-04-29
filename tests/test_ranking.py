"""Stage 5 -- rule-based scoring formula and token matching."""

from __future__ import annotations

from app.db.models import Recipe
from app.services.ranking import (
	_ingredient_match,
	_tokenize_ingredient,
	score_candidates,
)
from app.services.retrieval import RetrievedCandidate


def _recipe(id_: int, ingredients: list[str]) -> Recipe:
	r = Recipe(
		id=id_, title=f"r{id_}", ingredients_clean=ingredients, directions=[], diet="vegan", allergens=[]
	)
	r.link = None
	r.source = None
	return r


def test_tokenize_ingredient_drops_stopwords_and_singularizes() -> None:
	assert _tokenize_ingredient("Chicken Breasts") == {"chicken", "breast"}
	assert _tokenize_ingredient("cream of mushroom soup") == {"cream", "mushroom", "soup"}
	assert _tokenize_ingredient("a") == set()


def test_ingredient_match_handles_head_noun() -> None:
	user = {"chicken"}
	assert _ingredient_match("chicken breasts", user) is True
	# Whole-token semantics: 'egg' should NOT match 'eggplant'.
	assert _ingredient_match("eggplant", {"egg"}) is False


def test_ingredient_match_multitoken_partial() -> None:
	user = {"soy"}
	# Recipe has two tokens; sharing one is enough.
	assert _ingredient_match("soy sauce", user) is True


def test_score_orders_by_overlap() -> None:
	user = ["chicken", "onion", "garlic"]
	r1 = _recipe(1, ["chicken breasts", "onion", "garlic"])  # 3/3
	r2 = _recipe(2, ["chicken", "rice", "soy sauce"])  # 1/3
	r3 = _recipe(3, ["beef", "broccoli", "soy sauce"])  # 0/3
	candidates = [
		RetrievedCandidate(1, 0.0),
		RetrievedCandidate(2, 0.0),
		RetrievedCandidate(3, 0.0),
	]
	ranked = score_candidates(candidates, [r1, r2, r3], user)
	ranked_ids = [c.recipe.id for c in ranked]
	assert ranked_ids == [1, 2, 3]
	assert ranked[0].score > ranked[1].score > ranked[2].score


def test_score_components_recorded() -> None:
	r = _recipe(1, ["chicken breasts", "onion"])
	candidates = [RetrievedCandidate(1, 0.6)]
	ranked = score_candidates(candidates, [r], ["chicken", "onion"])
	c = ranked[0]
	# All four ingredients matched -> ingredient_match = 1.0
	assert c.ingredient_match == 1.0
	# vector_score 0.6 -> rescaled to (0.6 + 1) / 2 = 0.8
	assert c.vector_similarity == 0.8
	assert c.missing_ingredients == []
	assert "chicken breasts" in c.available_ingredients
