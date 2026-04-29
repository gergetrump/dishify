"""Diet + allergen inference (used at load time)."""

from __future__ import annotations

import pytest
from app.services.taxonomy import infer_allergens, infer_diet


@pytest.mark.parametrize(
	("ingredients", "expected_diet"),
	[
		(["chicken breasts", "onion"], "omnivore"),
		(["beef", "salt"], "omnivore"),
		(["salmon", "lemon"], "omnivore"),
		(["mozzarella", "tomato"], "vegetarian"),
		(["egg", "flour"], "vegetarian"),
		(["honey", "oats"], "vegetarian"),
		(["tomato", "pasta", "olive oil"], "vegan"),
		(["lentils", "carrot"], "vegan"),
	],
)
def test_diet_inference(ingredients: list[str], expected_diet: str) -> None:
	assert infer_diet(ingredients) == expected_diet


def test_allergens_detect_groups() -> None:
	assert "peanuts" in infer_allergens(["peanut butter", "sugar"])
	assert "tree_nuts" in infer_allergens(["walnuts", "flour"])
	assert "dairy" in infer_allergens(["mozzarella"])
	assert "shellfish" in infer_allergens(["shrimp", "garlic"])
	assert "gluten" in infer_allergens(["wheat flour", "yeast"])


def test_allergens_no_false_positive_on_eggplant() -> None:
	# eggplant must not match the eggs allergen group.
	assert "eggs" not in infer_allergens(["eggplant", "tomato"])


def test_allergens_empty_input() -> None:
	assert infer_allergens([]) == []
