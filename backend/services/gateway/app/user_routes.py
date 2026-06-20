import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import validate_token
from app.config import settings

router = APIRouter(tags=["user"])
bearer_scheme = HTTPBearer(auto_error=False)


def _optional_bearer(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
	if credentials is None or credentials.scheme.lower() != "bearer":
		return None
	return credentials.credentials


def _require_bearer(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
	if settings.disable_auth:
		if credentials is None or credentials.scheme.lower() != "bearer":
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="Missing bearer token",
			)
		return credentials.credentials

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


async def _proxy(request: Request, path: str, *, token: str | None = None) -> Response:
	url = f"{settings.user_url.rstrip('/')}{path}"
	headers: dict[str, str] = {}
	content_type = request.headers.get("content-type")
	if content_type:
		headers["Content-Type"] = content_type
	if token:
		headers["Authorization"] = f"Bearer {token}"

	body = await request.body()
	try:
		async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
			response = await client.request(
				request.method,
				url,
				content=body if body else None,
				headers=headers,
			)
	except httpx.RequestError as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=f"User service unavailable: {exc}",
		) from exc

	return Response(
		content=response.content,
		status_code=response.status_code,
		media_type=response.headers.get("content-type"),
	)


@router.get("/auth/config")
async def auth_config(request: Request) -> Response:
	return await _proxy(request, "/auth/config")


@router.post("/auth/register")
async def auth_register(request: Request) -> Response:
	return await _proxy(request, "/auth/register")


@router.post("/auth/login")
async def auth_login(request: Request) -> Response:
	return await _proxy(request, "/auth/login")


@router.get("/me")
async def get_me(request: Request, token: str = Depends(_require_bearer)) -> Response:
	return await _proxy(request, "/me", token=token)


@router.get("/me/preferences")
async def get_preferences(
	request: Request, token: str = Depends(_require_bearer)
) -> Response:
	return await _proxy(request, "/me/preferences", token=token)


@router.put("/me/preferences")
async def update_preferences(
	request: Request, token: str = Depends(_require_bearer)
) -> Response:
	return await _proxy(request, "/me/preferences", token=token)
