from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from dishify_contracts.text_validation import MAX_QUERY_LENGTH, reject_control_characters


class AugmentRequest(BaseModel):
    """Ask the LLM to expand a recipe's terse stored directions into detailed steps."""

    title: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    directions: list[str] = Field(default_factory=list)
    query: str | None = None
    servings: int | None = None

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str | None) -> str | None:
        if value is None or not value:
            return value
        if len(value) > MAX_QUERY_LENGTH:
            raise ValueError("query must not exceed 512 characters")
        return reject_control_characters(value, field_name="query")


class AugmentedStep(BaseModel):
    text: str
    tip: str | None = None
    duration_minutes: int | None = None


class AugmentResponse(BaseModel):
    steps: list[AugmentedStep] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    estimated_time_minutes: int | None = None
    latency_ms: int
