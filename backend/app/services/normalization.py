import json
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from ..clients.gemini import DEFAULT_MODEL, GeminiClient, GeminiError

logger = logging.getLogger(__name__)


_SPACES_PATTERN = re.compile(r"\s+")
_NON_ALPHA_PATTERN = re.compile(r"[^a-z\s-]")


@dataclass
class IngredientNormalizer:
	api_key: str | None = None
	model: str = DEFAULT_MODEL
	timeout_seconds: int = 12
	client: GeminiClient | None = field(default=None, repr=False)

	def __post_init__(self) -> None:
		if self.client is None:
			self.client = GeminiClient(
				api_key=self.api_key,
				model=self.model,
				timeout_seconds=self.timeout_seconds,
			)

	def normalize(self, ingredients: Iterable[str]) -> list[str]:
		prepared = [self._clean_input(item) for item in ingredients if self._clean_input(item)]
		if not prepared:
			return []

		llm_result = self._normalize_with_gemini(prepared)
		if llm_result is not None and len(llm_result) == len(prepared):
			return llm_result

		return [self._normalize_with_rules(item) for item in prepared]

	def _normalize_with_gemini(self, ingredients: list[str]) -> list[str] | None:
		assert self.client is not None
		if not self.client.is_configured:
			return None

		prompt = (
			"Normalize each ingredient into a canonical kitchen base ingredient. "
			"Return singular, lower-case, concise names only. Remove descriptors like 'fresh', "
			"'dried', and type suffixes when not essential, e.g. 'mozzarella cheese' -> 'mozzarella'. "
			"Keep ingredient identity, and do not invent ingredients. "
			'Return strict JSON with this shape: {"normalized": ["..."]}. '
			"The output list length must exactly match the input list order.\n"
			f"Input: {json.dumps(ingredients)}"
		)

		try:
			payload = self.client.generate_json(prompt)
		except GeminiError as exc:
			logger.info("Normalization LLM call failed; falling back to rules: %s", exc)
			return None

		try:
			normalized = payload["normalized"]
		except (KeyError, TypeError):
			return None

		if not isinstance(normalized, list):
			return None

		cleaned = [self._clean_input(str(item)) for item in normalized]
		if any(not item for item in cleaned):
			return None
		return cleaned

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
	api_key: str | None = None,
	model: str = DEFAULT_MODEL,
) -> list[str]:
	normalizer = IngredientNormalizer(api_key=api_key, model=model)
	return normalizer.normalize(ingredients)
