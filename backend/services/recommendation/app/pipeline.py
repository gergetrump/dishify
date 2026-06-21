from __future__ import annotations

import time

import httpx

from app.config import settings
from dishify_contracts import (
    ExplainRequest,
    ExplainResultItem,
    PipelineStage,
    ReasoningDetail,
    RecipeResult,
    RecommendRequest,
    RecommendResponse,
    RetrieveRequest,
    RetrievedRecipe,
)
from dishify_ranking import score_recipes_by_inventory


class PipelineUnavailableError(RuntimeError):
    pass


def _normalize_reasoning_key(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _build_reasoning_index(
    results: list[ExplainResultItem],
) -> dict[str, ReasoningDetail]:
    reasoning_results: dict[str, ReasoningDetail] = {}
    for item in results:
        item_id = _normalize_reasoning_key(item.id)
        item_title = _normalize_reasoning_key(item.title)
        if item_id:
            reasoning_results[item_id] = item.reasoning
        if item_title:
            reasoning_results[item_title] = item.reasoning
    return reasoning_results


def _fallback_reasoning(recipe: RetrievedRecipe) -> ReasoningDetail:
    positive: list[str] = []
    negative: list[str] = []

    if recipe.inventory_matched:
        positive.append(
            f"Uses ingredients you have: {', '.join(recipe.inventory_matched)}."
        )
    if recipe.inventory_missing:
        negative.append(f"You may need: {', '.join(recipe.inventory_missing)}.")
    if not positive and not negative:
        positive.append("Matched by semantic similarity to your query.")

    return ReasoningDetail(positive=positive, negative=negative)


def _recipe_to_result(
    recipe: RetrievedRecipe,
    rank: int,
    reasoning_results: dict[str, ReasoningDetail],
) -> RecipeResult:
    key = _normalize_reasoning_key(recipe.id)
    title_key = _normalize_reasoning_key(recipe.title)
    reasoning = reasoning_results.get(key) or reasoning_results.get(title_key)
    if reasoning is None:
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


def run_recommend_pipeline(request: RecommendRequest) -> RecommendResponse:
    stages: list[PipelineStage] = []
    top_k = request.top_k
    timeout = settings.request_timeout_seconds

    retrieve_start = time.perf_counter()
    with httpx.Client(timeout=timeout) as client:
        retrieve_response = client.post(
            f"{settings.retrieval_url.rstrip('/')}/internal/retrieve",
            json=RetrieveRequest(
                query=request.query,
                top_k=top_k,
                available_ingredients=request.available_ingredients,
                exclusion_restrictions=request.exclusion_restrictions,
            ).model_dump(mode="json"),
        )
        if retrieve_response.status_code == 503:
            raise PipelineUnavailableError(
                retrieve_response.json().get("detail", retrieve_response.text)
            )
        retrieve_response.raise_for_status()
        retrieved_payload = retrieve_response.json()
        retrieved = [RetrievedRecipe(**item) for item in retrieved_payload["recipes"]]
        retrieve_ms = retrieved_payload.get("latency_ms") or int(
            (time.perf_counter() - retrieve_start) * 1000
        )
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
    reasoning_results: dict[str, ReasoningDetail] = {}
    explain_status = "skipped"

    if settings.enable_llm_reasoning:
        try:
            with httpx.Client(timeout=timeout) as client:
                explain_response = client.post(
                    f"{settings.reasoning_url.rstrip('/')}/internal/explain",
                    json=ExplainRequest(
                        query=request.query,
                        top_k=top_k,
                        available_ingredients=request.available_ingredients,
                        exclusion_restrictions=request.exclusion_restrictions,
                        recipes=ranked[:top_k],
                    ).model_dump(mode="json"),
                )
                if explain_response.is_success:
                    explain_payload = explain_response.json()
                    items = [
                        ExplainResultItem(**item)
                        for item in explain_payload.get("results", [])
                    ]
                    reasoning_results = _build_reasoning_index(items)
                    explain_status = "ok"
                else:
                    explain_status = "error"
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
