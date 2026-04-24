import json
import os
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


_SPACES_PATTERN = re.compile(r"\s+")
_NON_ALPHA_PATTERN = re.compile(r"[^a-z\s-]")


@dataclass
class IngredientNormalizer:
	api_key: Optional[str] = None
	model: str = "gemini-2.0-flash"
	timeout_seconds: int = 12

	def __post_init__(self) -> None:
		if self.api_key is None:
			self.api_key = os.getenv("GEMINI_API_KEY")

	def normalize(self, ingredients: Iterable[str]) -> List[str]:
		prepared = [self._clean_input(item) for item in ingredients if self._clean_input(item)]
		if not prepared:
			return []

		llm_result = self._normalize_with_gemini(prepared)
		if llm_result is not None and len(llm_result) == len(prepared):
			return llm_result

		return [self._normalize_with_rules(item) for item in prepared]

	def _normalize_with_gemini(self, ingredients: List[str]) -> Optional[List[str]]:
		if not self.api_key:
			return None

		prompt = (
			"Normalize each ingredient into a canonical kitchen base ingredient. "
			"Return singular, lower-case, concise names only. Remove descriptors like 'fresh', "
			"'dried', and type suffixes when not essential, e.g. 'mozzarella cheese' -> 'mozzarella'. "
			"Keep ingredient identity, and do not invent ingredients. "
			"Return strict JSON with this shape: {\"normalized\": [\"...\"]}. "
			"The output list length must exactly match the input list order.\n"
			f"Input: {json.dumps(ingredients)}"
		)

		payload = {
			"contents": [{"parts": [{"text": prompt}]}],
			"generationConfig": {
				"temperature": 0,
				"responseMimeType": "application/json",
			},
		}

		endpoint = (
			"https://generativelanguage.googleapis.com/v1beta/models/"
			f"{self.model}:generateContent?key={self.api_key}"
		)

		request = Request(
			endpoint,
			data=json.dumps(payload).encode("utf-8"),
			headers={"Content-Type": "application/json"},
			method="POST",
		)

		try:
			with urlopen(request, timeout=self.timeout_seconds) as response:
				body = response.read().decode("utf-8")
		except (URLError, TimeoutError, ValueError):
			return None

		try:
			response_json = json.loads(body)
			text = response_json["candidates"][0]["content"]["parts"][0]["text"]
			normalized_payload = json.loads(text)
			normalized = normalized_payload["normalized"]
			if not isinstance(normalized, list):
				return None
			cleaned = [self._clean_input(str(item)) for item in normalized]
			if any(not item for item in cleaned):
				return None
			return cleaned
		except (KeyError, IndexError, TypeError, json.JSONDecodeError):
			return None

	def _normalize_with_rules(self, ingredient: str) -> str:
		dictionary = {
			"tomatoes": "tomato",
			"mozzarella cheese": "mozzarella",
		}

		if ingredient in dictionary:
			return dictionary[ingredient]

		removable_words = {
			"fresh",
			"dried",
			"frozen",
			"chopped",
			"sliced",
			"grated",
			"cheese",
		}

		words = [word for word in ingredient.split() if word not in removable_words]
		if not words:
			words = ingredient.split()

		singular_words = [self._singularize(word) for word in words]
		return " ".join(singular_words)

	def _clean_input(self, text: str) -> str:
		normalized = text.strip().lower()
		normalized = _NON_ALPHA_PATTERN.sub(" ", normalized)
		normalized = _SPACES_PATTERN.sub(" ", normalized).strip()
		return normalized

	def _singularize(self, word: str) -> str:
		if len(word) <= 3:
			return word

		if word.endswith("ies"):
			return f"{word[:-3]}y"
		if word.endswith("oes"):
			return word[:-2]
		if word.endswith("ses"):
			return word[:-2]
		if word.endswith("s") and not word.endswith("ss"):
			return word[:-1]
		return word


def normalize_ingredients(
	ingredients: Iterable[str],
	api_key: Optional[str] = None,
	model: str = "gemini-2.0-flash",
) -> List[str]:
	normalizer = IngredientNormalizer(api_key=api_key, model=model)
	return normalizer.normalize(ingredients)
