from dishify_contracts import ParsedIngredientModel, RetrievedRecipe
from dishify_ranking import score_recipes_by_inventory


def _recipe(
    recipe_id: int,
    score: float,
    parsed: list[ParsedIngredientModel],
) -> RetrievedRecipe:
    return RetrievedRecipe(
        id=recipe_id,
        score=score,
        title=f"Recipe {recipe_id}",
        parsed_ingredients=parsed,
    )


def test_no_available_ingredients_returns_original_order() -> None:
    recipes = [
        _recipe(1, 0.9, [ParsedIngredientModel(name="pasta")]),
        _recipe(2, 0.5, [ParsedIngredientModel(name="rice")]),
    ]
    result = score_recipes_by_inventory(recipes, None)
    assert [r.id for r in result] == [1, 2]
    assert result[0].inventory_matched is None


def test_inventory_boosts_matching_recipe() -> None:
    recipes = [
        _recipe(1, 0.55, [ParsedIngredientModel(name="pasta")]),
        _recipe(
            2,
            0.5,
            [ParsedIngredientModel(name="penne", quantity=12, unit="oz")],
        ),
    ]
    available = [ParsedIngredientModel(name="penne", quantity=12, unit="oz")]
    result = score_recipes_by_inventory(recipes, available)
    assert result[0].id == 2
    assert result[0].inventory_matched == ["penne"]
    assert result[0].inventory_missing == []


def test_full_quantity_match_scores_higher_than_partial() -> None:
    recipes = [
        _recipe(
            1,
            0.8,
            [ParsedIngredientModel(name="penne", quantity=12, unit="oz")],
        ),
    ]
    available = [ParsedIngredientModel(name="penne", quantity=12, unit="oz")]
    result = score_recipes_by_inventory(recipes, available)
    assert result[0].inventory_score == 1.0


def test_related_ingredient_names_match_by_words() -> None:
    recipes = [
        _recipe(
            1,
            0.8,
            [ParsedIngredientModel(name="parmesan cheese")],
        ),
    ]
    available = [ParsedIngredientModel(name="parmesan")]

    result = score_recipes_by_inventory(recipes, available)

    assert result[0].inventory_matched == ["parmesan cheese"]
    assert result[0].inventory_missing == []
    assert result[0].inventory_score == 0.5


def test_base_ingredient_matches_specific_forms() -> None:
    recipes = [
        _recipe(
            1,
            0.8,
            [
                ParsedIngredientModel(name="boneless skinless chicken breasts"),
                ParsedIngredientModel(name="chicken thighs"),
                ParsedIngredientModel(name="extra-virgin olive oil"),
                ParsedIngredientModel(name="corn oil"),
            ],
        ),
    ]
    available = [
        ParsedIngredientModel(name="chicken"),
        ParsedIngredientModel(name="oil"),
    ]

    result = score_recipes_by_inventory(recipes, available)

    assert result[0].inventory_matched == [
        "boneless skinless chicken breast",
        "chicken thigh",
        "extra virgin olive oil",
        "corn oil",
    ]
    assert result[0].inventory_missing == []
    assert result[0].inventory_score == 0.5


def test_plural_and_punctuation_variants_match() -> None:
    recipes = [
        _recipe(
            1,
            0.8,
            [
                ParsedIngredientModel(name="tomatoes"),
                ParsedIngredientModel(name="parmesan-cheese"),
            ],
        ),
    ]
    available = [
        ParsedIngredientModel(name="tomato"),
        ParsedIngredientModel(name="parmesan cheese"),
    ]

    result = score_recipes_by_inventory(recipes, available)

    assert result[0].inventory_matched == ["tomato", "parmesan cheese"]
    assert result[0].inventory_missing == []


def test_word_matching_does_not_match_raw_substrings() -> None:
    recipes = [
        _recipe(
            1,
            0.8,
            [ParsedIngredientModel(name="graham crackers")],
        ),
    ]
    available = [ParsedIngredientModel(name="ham")]

    result = score_recipes_by_inventory(recipes, available)

    assert result[0].inventory_matched == []
    assert result[0].inventory_missing == ["graham cracker"]
