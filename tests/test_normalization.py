"""Stage 2 -- ingredient normalization (rule fallback path).

The CI smoke test depends on the rule path producing exactly these outputs.
If you have to change them, change the workflow too.
"""

from __future__ import annotations

import pytest
from app.services.normalization import IngredientNormalizer, normalize_ingredients


def test_ci_smoke_invariant() -> None:
    # The exact assertion run in .github/workflows/ci.yml.
    assert normalize_ingredients(["tomatoes", "mozzarella cheese", "fresh basil"]) == [
        "tomato",
        "mozzarella",
        "basil",
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (["TOMATOES"], ["tomato"]),
        (["  fresh   basil  "], ["basil"]),
        (["chopped onions"], ["onion"]),
        (["mozzarella cheese"], ["mozzarella"]),
        (["dried apricots"], ["apricot"]),
        (["frozen peas"], ["pea"]),
        (["grated parmesan cheese"], ["parmesan"]),
    ],
)
def test_rule_normalization(raw: list[str], expected: list[str]) -> None:
    assert IngredientNormalizer().normalize(raw) == expected


def test_empty_input_returns_empty_list() -> None:
    assert normalize_ingredients([]) == []
    assert normalize_ingredients(["", "   "]) == []


def test_punctuation_stripped() -> None:
    assert normalize_ingredients(["apple, fresh!"]) == ["apple"]
