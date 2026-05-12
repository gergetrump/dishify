from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedIngredient:
    """Structured representation of one ingredient."""

    name: str = ""  # Example: "sugar"
    quantity: float | None = None  # Example: 1.0
    unit: str | None = None  # Example: "cup"
    raw_text: str = ""  # Example: "1 c. sugar"


@dataclass(slots=True)
class RecipeDataPoint:
    """Represents one row from `data/full_dataset.csv`."""

    title: str = ""  # Example: "No-Bake Nut Cookies"

    # Raw ingredient strings from RecipeNLG / CSV
    ingredients: list[str] = field(
        default_factory=list
    )  # Example: ["1 c. sugar", "1/2 c. milk", "1 stick margarine"]

    # Structured ingredient representation for filtering, matching, quantities, units
    parsed_ingredients: list[ParsedIngredient] = field(default_factory=list)

    directions: list[str] = field(
        default_factory=list
    )  # Example: ["In a heavy 2-quart saucepan mix sugar, cocoa, milk and margarine.", ...]

    link: str = ""  # Example: "www.cookbooks.com/Recipe-Details.aspx?id=44874"

    source: str = ""  # Example: "Gathered"

    # Named entities / normalized ingredient names from RecipeNLG
    ner: list[str] = field(
        default_factory=list
    )  # Example: ["sugar", "milk", "margarine", "vanilla"]
