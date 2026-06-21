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
