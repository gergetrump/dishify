from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedIngredient:
    name: str = ""
    quantity: float | None = None
    unit: str | None = None
    raw_text: str = ""


@dataclass(slots=True)
class RecipeDataPoint:
    title: str = ""
    ingredients: list[str] = field(default_factory=list)
    raw_ingredients: list[str] = field(default_factory=list)
    parsed_ingredients: list[ParsedIngredient] = field(default_factory=list)
    normalized_ingredients: list[str] = field(default_factory=list)
    directions: list[str] = field(default_factory=list)
    link: str = ""
    source: str = ""
    ner: list[str] = field(default_factory=list)
    exclusion_restrictions: list[str] = field(default_factory=list)
    exclusion_restrictions_count: int | None = None
