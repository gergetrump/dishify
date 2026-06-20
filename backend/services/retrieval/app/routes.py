from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.store import get_recipe_store
from dishify_contracts import HealthResponse, RetrieveRequest, RetrieveResponse

router = APIRouter(tags=["retrieval"])


class CollectionUnavailableError(RuntimeError):
	pass


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
	return HealthResponse(status="ok", service=settings.app_name)


@router.get("/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
	store = get_recipe_store()
	if not store.collection_exists():
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=(
				f"Qdrant collection '{settings.qdrant_collection}' not found. "
				"Run: docker compose run --rm indexing-worker --recreate"
			),
		)
	return HealthResponse(status="ok", service=settings.app_name)


@router.post("/internal/retrieve", response_model=RetrieveResponse)
def retrieve(body: RetrieveRequest) -> RetrieveResponse:
	import time

	retrieve_start = time.perf_counter()
	store = get_recipe_store()
	if not store.collection_exists():
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=(
				f"Qdrant collection '{settings.qdrant_collection}' not found. "
				"Run: docker compose run --rm indexing-worker --recreate"
			),
		)

	recipes = store.retrieve_recipes(
		query=body.query,
		top_k=body.top_k,
		excluded_ingredients=body.exclusion_restrictions,
		available_ingredients=body.available_ingredients,
	)
	latency_ms = int((time.perf_counter() - retrieve_start) * 1000)
	return RetrieveResponse(recipes=recipes, latency_ms=latency_ms)
