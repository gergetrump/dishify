import time
import logging

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.llm_reasoning import UnsafeReasoningError, augment_directions_payload, generate_reasoning_payload
from dishify_contracts import (
    AugmentRequest,
    AugmentResponse,
    AugmentedStep,
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
    except UnsafeReasoningError as exc:
        logger.warning("LLM reasoning rejected by output guardrail: %s", exc)
        latency_ms = int((time.perf_counter() - explain_start) * 1000)
        return ExplainResponse(
            results=[],
            latency_ms=latency_ms,
            guardrail_triggered=True,
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
    return ExplainResponse(
        results=results,
        latency_ms=latency_ms,
        guardrail_triggered=False,
    )


@router.post("/internal/augment", response_model=AugmentResponse)
def augment(body: AugmentRequest) -> AugmentResponse:
    if not settings.enable_llm_reasoning or not settings.openrouter_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM reasoning is disabled",
        )

    start = time.perf_counter()
    try:
        payload = augment_directions_payload(
            title=body.title,
            ingredients=body.ingredients,
            directions=body.directions,
            query=body.query,
            servings=body.servings,
            provider=settings.llm_provider,
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=settings.llm_timeout_seconds,
        )
    except Exception as exc:
        logger.exception("Direction augmentation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Direction augmentation failed: {exc}",
        ) from exc

    steps: list[AugmentedStep] = []
    for item in payload.get("steps", []) or []:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            duration = item.get("duration_minutes")
            steps.append(
                AugmentedStep(
                    text=text,
                    tip=(str(item["tip"]).strip() if item.get("tip") else None),
                    duration_minutes=duration
                    if isinstance(duration, int)
                    else None,
                )
            )
        elif isinstance(item, str) and item.strip():
            steps.append(AugmentedStep(text=item.strip()))

    overall_tips = [
        str(tip).strip() for tip in (payload.get("tips") or []) if str(tip).strip()
    ]
    est = payload.get("estimated_time_minutes")
    latency_ms = int((time.perf_counter() - start) * 1000)
    return AugmentResponse(
        steps=steps,
        tips=overall_tips,
        estimated_time_minutes=est if isinstance(est, int) else None,
        latency_ms=latency_ms,
    )
