from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
	status: str
	service: str


class RecommendRequest(BaseModel):
	ingredients: list[str] = Field(..., min_length=1)
	limit: int = Field(default=5, ge=1, le=20)


class RecommendationItem(BaseModel):
	recipe_id: str
	title: str
	score: float
	matched_ingredients: list[str]
	missing_ingredients: list[str]
	reason: str


class PipelineStage(BaseModel):
	name: str
	status: str
	latency_ms: int


class RecommendResponse(BaseModel):
	recommendations: list[RecommendationItem]
	stages: list[PipelineStage]
