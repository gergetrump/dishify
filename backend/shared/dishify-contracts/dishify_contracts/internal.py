from pydantic import BaseModel, Field

from dishify_contracts.models import ParsedIngredientModel, RetrievedRecipe, RetrievalRequest
from dishify_contracts.public import ReasoningDetail


class RetrieveRequest(BaseModel):
	query: str = Field(..., min_length=1)
	top_k: int = Field(default=5, ge=1, le=100)
	available_ingredients: list[ParsedIngredientModel] | None = None
	exclusion_restrictions: list[str] | None = None


class RetrieveResponse(BaseModel):
	recipes: list[RetrievedRecipe]
	latency_ms: int


class ExplainRequest(BaseModel):
	query: str
	top_k: int = Field(default=5, ge=1, le=100)
	available_ingredients: list[ParsedIngredientModel] | None = None
	exclusion_restrictions: list[str] | None = None
	recipes: list[RetrievedRecipe]


class ExplainResultItem(BaseModel):
	id: int | str | None = None
	title: str | None = None
	reasoning: ReasoningDetail = Field(default_factory=ReasoningDetail)


class ExplainResponse(BaseModel):
	results: list[ExplainResultItem]
	latency_ms: int


class InternalRecommendRequest(RetrievalRequest):
	"""Internal copy of RecommendRequest for recommendation service."""


class ServiceUnavailableDetail(BaseModel):
	detail: str
