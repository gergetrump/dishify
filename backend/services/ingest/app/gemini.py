from __future__ import annotations

import json
import time
from typing import Any

import requests

from dishify_contracts import DetectedIngredient, ParsedIngredientModel

# Transient Gemini statuses worth retrying (overloaded / rate limited / gateway).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GeminiError(RuntimeError):
    pass


_TRANSCRIBE_PROMPT = (
    "Transcribe the spoken audio into plain text exactly as said. "
    "The speaker is describing what they want to cook and/or the ingredients "
    "they have. Return only the transcription, with no commentary, labels, or "
    "quotation marks."
)

_VISION_PROMPT = (
    "You are a kitchen inventory assistant. Look at the photo and identify every "
    "distinct edible food ingredient you can see (produce, packaged goods, "
    "proteins, condiments, etc.). Ignore non-food objects, utensils, and "
    "background. For each ingredient, estimate a quantity and unit only when "
    "clearly visible; otherwise use null. Also give a bounding box that tightly "
    "encloses the item.\n\n"
    "Return a single JSON object only, with this exact schema:\n"
    "{\n"
    '  "ingredients": [\n'
    "    {\n"
    '      "name": "string",\n'
    '      "quantity": number | null,\n'
    '      "unit": "string" | null,\n'
    '      "raw_text": "string",\n'
    '      "box_2d": [ymin, xmin, ymax, xmax]\n'
    "    }\n"
    "  ]\n"
    "}\n"
    'Use a short normalized "name" (e.g. "tomato") and put the full descriptive '
    'phrase in "raw_text" (e.g. "3 ripe tomatoes"). "box_2d" values are integers '
    "normalized to 0-1000 (top-left origin). If you cannot localize an item, omit "
    '"box_2d".'
)


def _generate_content(
    *,
    model: str,
    parts: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    timeout: int,
    response_json: bool = False,
    thinking_budget: int | None = 0,
    max_retries: int = 3,
    backoff: float = 1.5,
) -> str:
    url = f"{base_url.rstrip('/')}/models/{model}:generateContent?key={api_key}"
    body: dict[str, Any] = {"contents": [{"parts": parts}]}
    generation_config: dict[str, Any] = {}
    if response_json:
        generation_config["response_mime_type"] = "application/json"
    if thinking_budget is not None:
        generation_config["thinkingConfig"] = {"thinkingBudget": thinking_budget}
    if generation_config:
        body["generationConfig"] = generation_config

    last_error: str | None = None
    response: requests.Response | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=body, timeout=timeout)
        except requests.RequestError as exc:
            last_error = f"Gemini request failed: {exc}"
            response = None
        else:
            if response.ok:
                break
            last_error = (
                f"Gemini request failed status={response.status_code} "
                f"body={response.text[:1000]}"
            )
            if response.status_code not in _RETRYABLE_STATUS:
                break

        if attempt < max_retries:
            # exponential backoff: 1.5s, ~2.25s, ~3.4s ...
            time.sleep(backoff * (1.5**attempt))

    if response is None or not response.ok:
        raise GeminiError(last_error or "Gemini request failed")

    payload = response.json()
    candidates = payload.get("candidates") or []
    if not candidates:
        feedback = payload.get("promptFeedback")
        raise GeminiError(f"Gemini returned no candidates (feedback={feedback})")

    content_parts = candidates[0].get("content", {}).get("parts", []) or []
    text = "".join(part.get("text", "") for part in content_parts).strip()
    if not text:
        raise GeminiError("Gemini returned an empty response")
    return text


def _strip_code_fence(text: str) -> str:
    content = text.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return content


_VOICE_PROMPT = (
    "You are a kitchen assistant. The audio is a person describing, in natural "
    "speech, the ingredients they currently have and (optionally) what they feel "
    "like cooking. Do three things:\n"
    "1. Transcribe the speech accurately.\n"
    "2. Extract the food INGREDIENTS the speaker says they HAVE or want to cook "
    "with, as a structured list. Normalize names (e.g. 'tomatoes' -> 'tomato'). "
    "Include quantity and unit only when the speaker states them.\n"
    "3. Capture any remaining intent about the DISH or STYLE they want (e.g. "
    "'something spicy and quick', 'a comforting soup') as a short query string; "
    "use null if they only listed ingredients.\n\n"
    "Return a single JSON object only, with this exact schema:\n"
    "{\n"
    '  "transcript": "string",\n'
    '  "ingredients": [\n'
    '    {"name": "string", "quantity": number | null, "unit": "string" | null, '
    '"raw_text": "string"}\n'
    "  ],\n"
    '  "query": "string" | null\n'
    "}"
)


def _parse_ingredient_items(items: Any) -> list[ParsedIngredientModel]:
    parsed: list[ParsedIngredientModel] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        raw_text = str(item.get("raw_text") or name).strip()
        if not name and not raw_text:
            continue
        quantity = item.get("quantity")
        parsed.append(
            ParsedIngredientModel(
                name=name or raw_text,
                quantity=quantity if isinstance(quantity, (int, float)) else None,
                unit=(str(item["unit"]).strip() if item.get("unit") else None),
                raw_text=raw_text or name,
            )
        )
    return parsed


def extract_voice(
    audio_base64: str,
    mime_type: str,
    language: str | None,
    *,
    model: str,
    api_key: str,
    base_url: str,
    timeout: int,
    thinking_budget: int | None = 0,
) -> tuple[str, list[ParsedIngredientModel], str | None]:
    prompt = _VOICE_PROMPT
    if language:
        prompt += f"\nThe audio language is: {language}."

    parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": mime_type, "data": audio_base64}},
    ]
    raw = _generate_content(
        model=model,
        parts=parts,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        response_json=True,
        thinking_budget=thinking_budget,
    )

    try:
        data = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        raise GeminiError(f"Gemini returned invalid JSON: {raw[:500]}") from exc

    transcript = str(data.get("transcript") or "").strip()
    ingredients = _parse_ingredient_items(data.get("ingredients"))
    query_raw = data.get("query")
    query = str(query_raw).strip() if query_raw else None
    return transcript, ingredients, query or None


def transcribe_audio(
    audio_base64: str,
    mime_type: str,
    language: str | None,
    *,
    model: str,
    api_key: str,
    base_url: str,
    timeout: int,
    thinking_budget: int | None = 0,
) -> str:
    prompt = _TRANSCRIBE_PROMPT
    if language:
        prompt += f"\nThe audio language is: {language}."

    parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": mime_type, "data": audio_base64}},
    ]
    return _generate_content(
        model=model,
        parts=parts,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        thinking_budget=thinking_budget,
    )


def _normalize_box(raw_box: Any) -> list[float] | None:
    """Gemini box_2d is [ymin, xmin, ymax, xmax] in 0-1000 (top-left origin).

    Convert to [x_min, y_min, x_max, y_max] as fractions 0..1 for the client.
    """
    if not isinstance(raw_box, (list, tuple)) or len(raw_box) != 4:
        return None
    try:
        ymin, xmin, ymax, xmax = (float(v) / 1000.0 for v in raw_box)
    except (TypeError, ValueError):
        return None
    x0, x1 = sorted((xmin, xmax))
    y0, y1 = sorted((ymin, ymax))
    clamp = lambda v: max(0.0, min(1.0, v))
    box = [clamp(x0), clamp(y0), clamp(x1), clamp(y1)]
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    return box


def detect_ingredients(
    image_base64: str,
    mime_type: str,
    *,
    model: str,
    api_key: str,
    base_url: str,
    timeout: int,
    thinking_budget: int | None = 0,
) -> tuple[list[DetectedIngredient], str]:
    parts = [
        {"text": _VISION_PROMPT},
        {"inline_data": {"mime_type": mime_type, "data": image_base64}},
    ]
    raw = _generate_content(
        model=model,
        parts=parts,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        response_json=True,
        thinking_budget=thinking_budget,
    )

    try:
        data = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        raise GeminiError(f"Gemini returned invalid JSON: {raw[:500]}") from exc

    ingredients: list[DetectedIngredient] = []
    for item in data.get("ingredients", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        raw_text = str(item.get("raw_text") or name).strip()
        if not name and not raw_text:
            continue
        quantity = item.get("quantity")
        ingredients.append(
            DetectedIngredient(
                name=name or raw_text,
                quantity=quantity if isinstance(quantity, (int, float)) else None,
                unit=(str(item["unit"]).strip() if item.get("unit") else None),
                raw_text=raw_text or name,
                box=_normalize_box(item.get("box_2d")),
            )
        )

    return ingredients, raw
