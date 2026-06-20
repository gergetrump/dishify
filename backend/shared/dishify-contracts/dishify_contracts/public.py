from pydantic import BaseModel, Field

from dishify_contracts.models import RetrievalRequest


class HealthResponse(BaseModel):
	status: str
	service: str


class ReasoningDetail(BaseModel):
	positive: list[str] = Field(default_factory=list)
	negative: list[str] = Field(default_factory=list)


class RecipeResult(BaseModel):
	rank: int
	id: int
	title: str | None = None
	summary: str | None = None
	time_minutes: int | None = None
	score: float
	reasoning: ReasoningDetail | None = None
	directions: list[str] | None = None
	inventory_matched: list[str] | None = None
	inventory_missing: list[str] | None = None


class PipelineStage(BaseModel):
	name: str
	status: str
	latency_ms: int


class RecommendRequest(RetrievalRequest):
	"""Same shape as the end-to-end notebook RetrievalRequest."""


class RecommendResponse(BaseModel):
	results: list[RecipeResult]
	stages: list[PipelineStage]
