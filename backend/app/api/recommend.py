from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.domain.schemas import RecommendRequest, RecommendResponse
from app.services.pipeline import PipelineUnavailableError, run_recommend_pipeline

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
	"""Retrieve, rank, and explain recipes (matches end_to_end_pipeline.ipynb)."""
	try:
		return run_recommend_pipeline(body)
	except PipelineUnavailableError as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=str(exc),
		) from exc
