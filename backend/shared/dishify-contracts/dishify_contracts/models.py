from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from dishify_contracts.restrictions import validate_restriction_tags
from dishify_contracts.text_validation import MAX_QUERY_LENGTH, reject_control_characters


class ParsedIngredientModel(BaseModel):
    name: str = Field(default="", max_length=512)
    quantity: float | None = None
    unit: str | None = None
    raw_text: str = Field(default="", max_length=1024)

    @field_validator("name", "raw_text")
    @classmethod
    def _reject_control_characters(cls, value: str) -> str:
        return reject_control_characters(value, field_name="ingredient text")


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
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    top_k: int = Field(default=5, ge=1, le=100)
    available_ingredients: list[ParsedIngredientModel] | None = None
    exclusion_restrictions: list[str] | None = None

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        return reject_control_characters(value, field_name="query")

    @field_validator("exclusion_restrictions")
    @classmethod
    def _validate_exclusion_restrictions(
        cls, value: list[str] | None
    ) -> list[str] | None:
        return validate_restriction_tags(value)
