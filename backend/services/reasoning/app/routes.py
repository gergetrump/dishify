import time
import logging

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.llm_reasoning import generate_reasoning_payload
from dishify_contracts import (
    ExplainRequest,
    ExplainResponse,
    ExplainResultItem,
    HealthResponse,
    ReasoningDetail,
    RetrievalRequest,
)

router = APIRouter(tags=["reasoning"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@router.post("/internal/explain", response_model=ExplainResponse)
def explain(body: ExplainRequest) -> ExplainResponse:
    if not settings.enable_llm_reasoning or not settings.openrouter_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM reasoning is disabled",
        )

    explain_start = time.perf_counter()
    request = RetrievalRequest(
        query=body.query,
        top_k=body.top_k,
        available_ingredients=body.available_ingredients,
        exclusion_restrictions=body.exclusion_restrictions,
    )

    try:
        payload = generate_reasoning_payload(
            request,
            body.recipes,
            provider=settings.llm_provider,
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=settings.llm_timeout_seconds,
        )
    except Exception as exc:
        logger.exception("LLM reasoning failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM reasoning failed: {exc}",
        ) from exc

    results: list[ExplainResultItem] = []
    for item in payload.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        reasoning_raw = item.get("reasoning")
        if isinstance(reasoning_raw, dict):
            reasoning = ReasoningDetail(
                positive=list(reasoning_raw.get("positive") or []),
                negative=list(reasoning_raw.get("negative") or []),
            )
        else:
            reasoning = ReasoningDetail()
        results.append(
            ExplainResultItem(
                id=item.get("id"),
                title=item.get("title"),
                reasoning=reasoning,
            )
        )

    latency_ms = int((time.perf_counter() - explain_start) * 1000)
    return ExplainResponse(results=results, latency_ms=latency_ms)
