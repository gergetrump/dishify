from __future__ import annotations

from dataclasses import dataclass, field


# Parsed ingredient used for structured ingredient data.
@dataclass(slots=True)
class ParsedIngredient:
    """Structured representation of one ingredient."""

    name: str = ""  # Example: "sugar"
    quantity: float | None = None  # Example: 1.0
    unit: str | None = None  # Example: "cup"
    raw_text: str = ""  # Example: "1 c. sugar"


# Dataset recipe payload used during indexing and filtering.
@dataclass(slots=True)
class RecipeDataPoint:
    """Represents one row from `data/full_dataset.csv`."""

    title: str = ""  # Example: "No-Bake Nut Cookies"

    # Raw ingredient strings from RecipeNLG / CSV
    ingredients: list[str] = field(
        default_factory=list
    )  # Example: ["1 c. sugar", "1/2 c. milk", "1 stick margarine"]

    # Raw ingredient strings (verbatim) used for filtering and payloads
    raw_ingredients: list[str] = field(default_factory=list)

    # Structured ingredient representation for filtering, matching, quantities, units
    parsed_ingredients: list[ParsedIngredient] = field(default_factory=list)

    # Normalized ingredient names derived from parsed_ingredients (token-free strings)
    normalized_ingredients: list[str] = field(default_factory=list)

    directions: list[str] = field(
        default_factory=list
    )  # Example: ["In a heavy 2-quart saucepan mix sugar, cocoa, milk and margarine.", ...]

    link: str = ""  # Example: "www.cookbooks.com/Recipe-Details.aspx?id=44874"

    source: str = ""  # Example: "Gathered"

    # Named entities / normalized ingredient names from RecipeNLG
    ner: list[str] = field(
        default_factory=list
    )  # Example: ["sugar", "milk", "margarine", "vanilla"]

    # Dietary or allergen-based exclusions derived from the dataset
    exclusion_restrictions: list[str] = field(default_factory=list)

    # Count of exclusion restrictions if provided in the dataset
    exclusion_restrictions_count: int | None = None
