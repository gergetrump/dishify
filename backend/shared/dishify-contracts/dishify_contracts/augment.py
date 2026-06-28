from __future__ import annotations

from pydantic import BaseModel, Field


class AugmentRequest(BaseModel):
    """Ask the LLM to expand a recipe's terse stored directions into detailed steps."""

    title: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    directions: list[str] = Field(default_factory=list)
    query: str | None = None
    servings: int | None = None


class AugmentedStep(BaseModel):
    text: str
    tip: str | None = None
    duration_minutes: int | None = None


class AugmentResponse(BaseModel):
    steps: list[AugmentedStep] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    estimated_time_minutes: int | None = None
    latency_ms: int
