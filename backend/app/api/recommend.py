import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.domain.schemas import (
	PipelineStage,
	RecommendRequest,
	RecommendResponse,
	RecommendationItem,
)

router = APIRouter(tags=["recommend"])
bearer_scheme = HTTPBearer(auto_error=False)


def require_token(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
	if settings.disable_auth:
		return None
	if credentials is None or credentials.scheme.lower() != "bearer":
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Missing bearer token",
		)
	return credentials.credentials


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
	body: RecommendRequest,
	_token: str | None = Depends(require_token),
) -> RecommendResponse:
	"""MVP stub — returns sample data matching docs/API.md until pipeline is wired."""
	start = time.perf_counter()
	normalized = [i.strip().lower() for i in body.ingredients if i.strip()]
	latency_ms = int((time.perf_counter() - start) * 1000)

	items = [
		RecommendationItem(
			recipe_id="sample-1",
			title="Caprese Pasta",
			score=0.87,
			matched_ingredients=normalized[:2],
			missing_ingredients=["basil"],
			reason="Uses most of what you have.",
		),
		RecommendationItem(
			recipe_id="sample-2",
			title="Simple Tomato Pasta",
			score=0.75,
			matched_ingredients=normalized[:1],
			missing_ingredients=["garlic", "olive oil"],
			reason="Quick pantry pasta with strong ingredient overlap.",
		),
	][: body.limit]

	return RecommendResponse(
		recommendations=items,
		stages=[
			PipelineStage(name="normalize", status="ok", latency_ms=latency_ms),
			PipelineStage(name="filter", status="pending", latency_ms=0),
			PipelineStage(name="retrieve", status="pending", latency_ms=0),
			PipelineStage(name="score", status="pending", latency_ms=0),
			PipelineStage(name="explain", status="pending", latency_ms=0),
		],
	)
