from __future__ import annotations

from pydantic import BaseModel, Field


class ParsedIngredientModel(BaseModel):
    name: str = ""
    quantity: float | None = None
    unit: str | None = None
    raw_text: str = ""


class RetrievedRecipe(BaseModel):
    id: int
    score: float = 0.0
    title: str | None = None
    ingredients: list[str] | None = None
    raw_ingredients: list[str] | None = None
    parsed_ingredients: list[ParsedIngredientModel] = Field(default_factory=list)
    directions: list[str] | None = None
    link: str | None = None
    source: str | None = None
    ner: list[str] | None = None
    exclusion_restrictions: list[str] | None = None
    exclusion_restrictions_count: int | None = None
    inventory_score: float | None = None
    inventory_matched: list[str] | None = None
    inventory_missing: list[str] | None = None
