from __future__ import annotations

import unicodedata

from pydantic import BaseModel, Field, field_validator

from dishify_contracts.restrictions import validate_restriction_tags


class ParsedIngredientModel(BaseModel):
    name: str = Field(default="", max_length=512)
    quantity: float | None = None
    unit: str | None = None
    raw_text: str = Field(default="", max_length=1024)

    @field_validator("name", "raw_text")
    @classmethod
    def _reject_control_characters(cls, value: str) -> str:
        if any(unicodedata.category(character) == "Cc" for character in value):
            raise ValueError("ingredient text must not contain control characters")
        return value


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


class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)
    available_ingredients: list[ParsedIngredientModel] | None = None
    exclusion_restrictions: list[str] | None = None

    @field_validator("exclusion_restrictions")
    @classmethod
    def _validate_exclusion_restrictions(
        cls, value: list[str] | None
    ) -> list[str] | None:
        return validate_restriction_tags(value)
