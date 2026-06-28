import base64
import logging
import time

from fastapi import APIRouter, HTTPException, status

from app.audio import AudioTranscodeError, ensure_supported_audio
from app.config import settings
from app.gemini import (
    GeminiError,
    detect_ingredients,
    extract_voice,
    transcribe_audio,
)
from dishify_contracts import (
    HealthResponse,
    TranscribeRequest,
    TranscribeResponse,
    VisionIngredientsRequest,
    VisionIngredientsResponse,
    VoiceResponse,
)

router = APIRouter(tags=["ingest"])
logger = logging.getLogger(__name__)


def _require_gemini() -> str:
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media ingestion is disabled (GEMINI_API_KEY not set)",
        )
    return settings.gemini_api_key


def _check_size(data_base64: str) -> None:
    # base64 encodes 3 bytes per 4 chars; estimate decoded size without decoding.
    approx_bytes = (len(data_base64) * 3) // 4
    if approx_bytes > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Upload too large ({approx_bytes} bytes); "
                f"limit is {settings.max_upload_bytes} bytes"
            ),
        )


def _validate_base64(data_base64: str) -> None:
    try:
        base64.b64decode(data_base64, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payload is not valid base64",
        ) from exc


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@router.post("/internal/transcribe", response_model=TranscribeResponse)
def transcribe(body: TranscribeRequest) -> TranscribeResponse:
    api_key = _require_gemini()
    _check_size(body.audio_base64)
    _validate_base64(body.audio_base64)

    start = time.perf_counter()
    try:
        audio_base64, mime_type = ensure_supported_audio(
            body.audio_base64, body.mime_type
        )
    except AudioTranscodeError as exc:
        logger.exception("Audio transcode failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not process audio format: {exc}",
        ) from exc

    try:
        text = transcribe_audio(
            audio_base64,
            mime_type,
            body.language,
            model=settings.gemini_transcribe_model,
            api_key=api_key,
            base_url=settings.gemini_base_url,
            timeout=settings.request_timeout_seconds,
            thinking_budget=settings.gemini_thinking_budget,
        )
    except GeminiError as exc:
        logger.exception("Audio transcription failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Audio transcription failed: {exc}",
        ) from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    return TranscribeResponse(text=text, latency_ms=latency_ms)


@router.post("/internal/voice", response_model=VoiceResponse)
def voice(body: TranscribeRequest) -> VoiceResponse:
    api_key = _require_gemini()
    _check_size(body.audio_base64)
    _validate_base64(body.audio_base64)

    start = time.perf_counter()
    try:
        audio_base64, mime_type = ensure_supported_audio(
            body.audio_base64, body.mime_type
        )
    except AudioTranscodeError as exc:
        logger.exception("Audio transcode failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not process audio format: {exc}",
        ) from exc

    try:
        transcript, ingredients, query = extract_voice(
            audio_base64,
            mime_type,
            body.language,
            model=settings.gemini_transcribe_model,
            api_key=api_key,
            base_url=settings.gemini_base_url,
            timeout=settings.request_timeout_seconds,
            thinking_budget=settings.gemini_thinking_budget,
        )
    except GeminiError as exc:
        logger.exception("Voice ingredient extraction failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Voice ingredient extraction failed: {exc}",
        ) from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    return VoiceResponse(
        transcript=transcript,
        ingredients=ingredients,
        query=query,
        latency_ms=latency_ms,
    )


@router.post("/internal/vision/ingredients", response_model=VisionIngredientsResponse)
def vision_ingredients(body: VisionIngredientsRequest) -> VisionIngredientsResponse:
    api_key = _require_gemini()
    _check_size(body.image_base64)
    _validate_base64(body.image_base64)

    start = time.perf_counter()
    try:
        ingredients, raw_text = detect_ingredients(
            body.image_base64,
            body.mime_type,
            model=settings.gemini_vision_model,
            api_key=api_key,
            base_url=settings.gemini_base_url,
            timeout=settings.request_timeout_seconds,
            thinking_budget=settings.gemini_thinking_budget,
        )
    except GeminiError as exc:
        logger.exception("Ingredient detection failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ingredient detection failed: {exc}",
        ) from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    return VisionIngredientsResponse(
        ingredients=ingredients, raw_text=raw_text, latency_ms=latency_ms
    )
