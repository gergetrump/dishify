from __future__ import annotations

import threading
import time

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.domain.schemas import PipelineStage, ReasoningDetail, RecipeResult, RecommendResponse
from app.models.retrieval import RetrievedRecipe, RetrievalRequest
from app.services.llm_reasoning import generate_reasoning_payload
from app.services.ranking import score_recipes_by_inventory
from app.vector_db.recipe_vector_store import RecipeVectorStore

_lock = threading.Lock()
_store: RecipeVectorStore | None = None


class PipelineUnavailableError(RuntimeError):
    pass


def get_recipe_store() -> RecipeVectorStore:
    global _store
    if _store is not None:
        return _store

    with _lock:
        if _store is not None:
            return _store

        client_kwargs: dict = {"url": settings.qdrant_url}
        if settings.qdrant_api_key:
            client_kwargs["api_key"] = settings.qdrant_api_key

        qdrant_client = QdrantClient(**client_kwargs)
        model = SentenceTransformer(settings.embedding_model)
        _store = RecipeVectorStore(
            qdrant_client=qdrant_client,
            embedding_model=model,
            collection_name=settings.qdrant_collection,
        )
        return _store


def _normalize_reasoning_key(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _build_reasoning_index(payload: dict | list | None) -> dict[str, dict]:
    results_list: list = []
    if isinstance(payload, dict):
        results_list = payload.get("results", []) or []
    elif isinstance(payload, list):
        results_list = payload

    reasoning_results: dict[str, dict] = {}
    for item in results_list:
        if not isinstance(item, dict):
            continue
        item_id = _normalize_reasoning_key(item.get("id"))
        item_title = _normalize_reasoning_key(item.get("title"))
        if item_id:
            reasoning_results[item_id] = item
        if item_title:
            reasoning_results[item_title] = item
    return reasoning_results


def _fallback_reasoning(recipe: RetrievedRecipe) -> ReasoningDetail:
    positive: list[str] = []
    negative: list[str] = []

    if recipe.inventory_matched:
        positive.append(
            f"Uses ingredients you have: {', '.join(recipe.inventory_matched)}."
        )
    if recipe.inventory_missing:
        negative.append(
            f"You may need: {', '.join(recipe.inventory_missing)}."
        )
    if not positive and not negative:
        positive.append("Matched by semantic similarity to your query.")

    return ReasoningDetail(positive=positive, negative=negative)


def _recipe_to_result(
    recipe: RetrievedRecipe,
    rank: int,
    reasoning_results: dict[str, dict],
) -> RecipeResult:
    key = _normalize_reasoning_key(recipe.id)
    title_key = _normalize_reasoning_key(recipe.title)
    reasoning_item = reasoning_results.get(key) or reasoning_results.get(title_key) or {}

    reasoning_raw = reasoning_item.get("reasoning")
    if isinstance(reasoning_raw, dict):
        reasoning = ReasoningDetail(
            positive=list(reasoning_raw.get("positive") or []),
            negative=list(reasoning_raw.get("negative") or []),
        )
    else:
        reasoning = _fallback_reasoning(recipe)

    return RecipeResult(
        rank=rank,
        id=recipe.id,
        title=recipe.title,
        score=float(recipe.score or 0),
        reasoning=reasoning,
        directions=recipe.directions,
        inventory_matched=recipe.inventory_matched,
        inventory_missing=recipe.inventory_missing,
    )


def run_recommend_pipeline(request: RetrievalRequest) -> RecommendResponse:
    stages: list[PipelineStage] = []
    top_k = request.top_k

    retrieve_start = time.perf_counter()
    store = get_recipe_store()
    if not store.collection_exists():
        raise PipelineUnavailableError(
            f"Qdrant collection '{settings.qdrant_collection}' not found. "
            "Run: python backend/scripts/index_recipes.py"
        )

    retrieved = store.retrieve_recipes(
        query=request.query,
        top_k=top_k,
        excluded_ingredients=request.exclusion_restrictions,
        available_ingredients=request.available_ingredients,
    )
    retrieve_ms = int((time.perf_counter() - retrieve_start) * 1000)
    stages.append(PipelineStage(name="retrieve", status="ok", latency_ms=retrieve_ms))

    rank_start = time.perf_counter()
    ranked = score_recipes_by_inventory(
        retrieved,
        request.available_ingredients,
        ingredient_weight=settings.ingredient_weight,
        semantic_weight=settings.semantic_weight,
    )
    rank_ms = int((time.perf_counter() - rank_start) * 1000)
    stages.append(PipelineStage(name="rank", status="ok", latency_ms=rank_ms))

    explain_start = time.perf_counter()
    reasoning_results: dict[str, dict] = {}
    explain_status = "skipped"

    if settings.enable_llm_reasoning and settings.openrouter_api_key:
        try:
            payload = generate_reasoning_payload(
                request,
                ranked[:top_k],
                provider=settings.llm_provider,
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                timeout=settings.llm_timeout_seconds,
            )
            reasoning_results = _build_reasoning_index(payload)
            explain_status = "ok"
        except Exception:
            explain_status = "error"

    explain_ms = int((time.perf_counter() - explain_start) * 1000)
    stages.append(
        PipelineStage(name="explain", status=explain_status, latency_ms=explain_ms)
    )

    results = [
        _recipe_to_result(recipe, index + 1, reasoning_results)
        for index, recipe in enumerate(ranked[:top_k])
    ]

    return RecommendResponse(results=results, stages=stages)
