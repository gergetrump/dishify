from pydantic import BaseModel, Field, field_validator

from dishify_contracts.models import (
    ParsedIngredientModel,
    RetrievedRecipe,
    RetrievalRequest,
)
from dishify_contracts.public import ReasoningDetail
from dishify_contracts.restrictions import validate_restriction_tags
from dishify_contracts.text_validation import MAX_QUERY_LENGTH, reject_control_characters


class RetrieveRequest(BaseModel):
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


class RetrieveResponse(BaseModel):
    recipes: list[RetrievedRecipe]
    latency_ms: int


class ExplainRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    top_k: int = Field(default=5, ge=1, le=100)
    available_ingredients: list[ParsedIngredientModel] | None = None
    exclusion_restrictions: list[str] | None = None
    recipes: list[RetrievedRecipe]

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


class ExplainResultItem(BaseModel):
    id: int | str | None = None
    title: str | None = None
    reasoning: ReasoningDetail = Field(default_factory=ReasoningDetail)


class ExplainResponse(BaseModel):
    results: list[ExplainResultItem]
    latency_ms: int
    guardrail_triggered: bool = False


class InternalRecommendRequest(RetrievalRequest):
    """Internal copy of RecommendRequest for recommendation service."""


class ServiceUnavailableDetail(BaseModel):
    detail: str
