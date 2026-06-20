from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.pipeline import PipelineUnavailableError, run_recommend_pipeline
from dishify_contracts import HealthResponse, RecommendRequest, RecommendResponse

router = APIRouter(tags=["recommendation"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
	return HealthResponse(status="ok", service=settings.app_name)


@router.post("/internal/recommend", response_model=RecommendResponse)
def recommend(body: RecommendRequest) -> RecommendResponse:
	try:
		return run_recommend_pipeline(body)
	except PipelineUnavailableError as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=str(exc),
		) from exc
