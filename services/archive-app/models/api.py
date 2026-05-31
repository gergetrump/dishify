from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


# Request payload for search queries and basic filters.
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)
    excluded_ingredients: List[str] | None = None
    available_ingredients: List[str] | None = None


# One search result returned to the client.
class SearchHitModel(BaseModel):
    id: int
    score: float
    title: str | None = None
    ingredients: List[str] | None = None
    directions: List[str] | None = None
    link: str | None = None
    source: str | None = None
    ner: List[str] | None = None


# User preference profile for dietary and exclusion settings.
class UserPreferences(BaseModel):
    excluded_ingredients: List[str] = Field(default_factory=list)
    diet: str | None = None
    allergies: List[str] = Field(default_factory=list)
