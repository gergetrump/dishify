from __future__ import annotations

from pydantic import BaseModel, Field

from dishify_contracts.models import ParsedIngredientModel


class TranscribeRequest(BaseModel):
    """Voice input: base64-encoded audio to convert into a natural-language query."""

    audio_base64: str = Field(..., min_length=1)
    mime_type: str = "audio/webm"
    language: str | None = None


class TranscribeResponse(BaseModel):
    text: str
    latency_ms: int


class VoiceResponse(BaseModel):
    """Voice input parsed into pantry ingredients plus any residual dish/vibe intent."""

    transcript: str
    ingredients: list[ParsedIngredientModel] = Field(default_factory=list)
    query: str | None = None
    latency_ms: int


class DetectedIngredient(ParsedIngredientModel):
    """A detected ingredient plus its location in the image.

    ``box`` is ``[x_min, y_min, x_max, y_max]`` normalized to 0..1 (fractions of
    image width/height), ready to render as CSS percentages. ``None`` when the
    model did not localize the item.
    """

    box: list[float] | None = None


class VisionIngredientsRequest(BaseModel):
    """Image input: base64-encoded photo of a pantry/fridge to detect ingredients from."""

    image_base64: str = Field(..., min_length=1)
    mime_type: str = "image/jpeg"


class VisionIngredientsResponse(BaseModel):
    ingredients: list[DetectedIngredient] = Field(default_factory=list)
    raw_text: str | None = None
    latency_ms: int
