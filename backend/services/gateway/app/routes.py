import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import validate_token
from app.config import settings
from dishify_contracts import HealthResponse, RecommendRequest, RecommendResponse

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


def _optional_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    return credentials.credentials


def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    if settings.disable_auth:
        return _optional_bearer_token(credentials)
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        validate_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        ) from exc
    return credentials.credentials


def _fetch_stored_restrictions(token: str) -> list[str]:
    try:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            response = client.get(
                f"{settings.user_url.rstrip('/')}/me/preferences",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"User service unavailable: {exc}",
        ) from exc

    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.json().get("detail", response.text),
        )

    payload = response.json()
    return payload.get("exclusion_restrictions") or []


def _recommend_payload(body: RecommendRequest, token: str | None) -> dict:
    payload = body.model_dump(mode="json")
    if token is None:
        return payload

    explicit = body.exclusion_restrictions
    if explicit:
        return payload

    payload["exclusion_restrictions"] = _fetch_stored_restrictions(token)
    return payload


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@router.post("/recommend", response_model=RecommendResponse)
@limiter.limit("20/minute")
def recommend(
    request: Request,
    body: RecommendRequest,
    token: str | None = Depends(require_token),
) -> RecommendResponse:
    payload = _recommend_payload(body, token)
    try:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            response = client.post(
                f"{settings.recommendation_url.rstrip('/')}/internal/recommend",
                json=payload,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Recommendation service unavailable: {exc}",
        ) from exc

    if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.json().get("detail", response.text),
        )
    if not response.is_success:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json().get("detail", response.text),
        )

    return RecommendResponse(**response.json())
