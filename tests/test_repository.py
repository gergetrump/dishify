"""Stage 3 -- DB-level hard filter."""

from __future__ import annotations

from app.db import hard_filter


def test_diet_compatibility_table(seed_recipes, session) -> None:
	# Vegan request: only the vegan recipe survives.
	assert {r.id for r in hard_filter(session, diet="vegan")} == {1}

	# Vegetarian: vegan + vegetarian recipes.
	assert {r.id for r in hard_filter(session, diet="vegetarian")} == {1, 3, 4}

	# Omnivore: everything.
	assert {r.id for r in hard_filter(session, diet="omnivore")} == {1, 2, 3, 4}


def test_no_diet_means_no_filter(seed_recipes, session) -> None:
	assert {r.id for r in hard_filter(session)} == {1, 2, 3, 4}


def test_allergens_remove_matching_recipes(seed_recipes, session) -> None:
	# Peanut-allergic vegetarian: cookies (id 3) drops.
	survivors = {r.id for r in hard_filter(session, diet="vegetarian", allergies=["peanuts"])}
	assert 3 not in survivors
	assert 1 in survivors


def test_unknown_diet_is_ignored(seed_recipes, session) -> None:
	# 'flexitarian' isn't a recognized diet; should fall through to no diet filter.
	assert {r.id for r in hard_filter(session, diet="flexitarian")} == {1, 2, 3, 4}


def test_empty_allergens_is_a_noop(seed_recipes, session) -> None:
	assert len(hard_filter(session, diet="omnivore", allergies=[])) == 4
	assert len(hard_filter(session, diet="omnivore", allergies=["", "  "])) == 4
