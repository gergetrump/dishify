from __future__ import annotations

import json
import os
from typing import Iterable

import requests

from dishify_contracts import RetrievedRecipe, RetrievalRequest

_DEFAULT_MODEL_BY_PROVIDER: dict[str, str] = {
    "openrouter": "openrouter/free",
}


def _build_prompt(
    request: RetrievalRequest,
    recipes: Iterable[RetrievedRecipe],
    *,
    response_format: str = "tags",
) -> str:
    recipe_payloads = [
        {
            "id": getattr(recipe, "id", None),
            "title": recipe.title,
            "ingredients": recipe.ingredients,
            "ner": recipe.ner,
            "directions": recipe.directions,
            "link": recipe.link,
            "source": recipe.source,
        }
        for recipe in recipes
    ]

    available_ingredients = [
        ingredient.name or ingredient.raw_text
        for ingredient in (request.available_ingredients or [])
        if ingredient
    ]
    restrictions = request.exclusion_restrictions or []

    prompt_lines = [
        "You are a helpful recipe recommendation assistant.",
        "",
        "A user will provide:",
        "1. A list of ingredients they currently have at home",
        "2. Any dietary restrictions or allergies they have",
        "",
        "You will be given one or more recipes in the following JSON format:",
        "{",
        '  "id": "...",',
        '  "title": "...",',
        '  "ingredients": [...],',
        '  "ner": [...],',
        '  "directions": [...],',
        '  "link": "...",',
        '  "source": "..."',
        "}",
        "",
        "Your task:",
        "- Check each recipe against the user's available ingredients and restrictions",
        "- For each recipe that is a good match, explain WHY it suits the user:",
        "- Which of their ingredients are used",
        "- What (if anything) they might be missing and how easy it is to substitute or skip",
        "- Why it is safe given their allergies/restrictions",
        "- Why it would be a good choice overall (taste, simplicity, nutrition, etc.)",
        "- If a recipe is NOT suitable (e.g. contains an allergen), clearly say so and briefly explain why",
        "",
        "---",
        "",
        "User input:",
        f"Ingredients I have: {', '.join(available_ingredients) if available_ingredients else 'None'}",
        f"Restrictions / allergies / diets: {', '.join(restrictions) if restrictions else 'None'}",
        "",
        "Recipes to evaluate:",
        json.dumps(recipe_payloads, indent=2),
        "",
    ]

    if response_format == "json":
        prompt_lines.extend(
            [
                "Return a single JSON object only (no markdown, no extra text).",
                "Use this exact schema:",
                "{",
                '  "results": [',
                "    {",
                '      "id": "...",',
                '      "title": "...",',
                '      "suitability": "positive" | "negative" | "mixed",',
                '      "reasoning": {',
                '        "positive": ["..."],',
                '        "negative": ["..."]',
                "      },",
                "    }",
                "  ]",
                "}",
            ]
        )
    else:
        prompt_lines.extend(
            [
                "Only use bullet points and keep the reasoning concise.",
                "Wrap all the bullet points under: <positive></positive> and <negative></negative> tags to indicate suitability.",
            ]
        )

    return "\n".join(prompt_lines)


def _extract_json_payload(text: str) -> str:
    content = text.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return content


def _call_llm(
    prompt: str,
    *,
    provider: str,
    model: str | None,
    api_key: str | None,
    base_url: str | None,
    timeout: int,
) -> str:
    provider_key = provider.strip().lower()
    if provider_key not in _DEFAULT_MODEL_BY_PROVIDER:
        raise ValueError(f"Unsupported provider: {provider}")

    if provider_key == "openrouter":
        resolved_model = (
            model
            or os.getenv("OPENROUTER_MODEL")
            or _DEFAULT_MODEL_BY_PROVIDER[provider_key]
        )
        resolved_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not resolved_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1/chat/completions"
        )
        headers = {
            "Authorization": f"Bearer {resolved_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": resolved_model,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = requests.post(
            url, headers=headers, data=json.dumps(payload), timeout=timeout
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                "OpenRouter request failed "
                f"status={response.status_code} body={response.text[:1000]}"
            ) from exc
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    raise ValueError(f"Unsupported provider: {provider}")


def generate_reasoning_payload(
    request: RetrievalRequest,
    recipes: Iterable[RetrievedRecipe],
    *,
    provider: str = "openrouter",
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: int = 30,
) -> dict:
    prompt = _build_prompt(
        request,
        recipes,
        response_format="json",
    )
    raw = _call_llm(
        prompt,
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )
    return json.loads(_extract_json_payload(raw))
