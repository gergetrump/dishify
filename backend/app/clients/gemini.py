"""Reusable HTTP client for Google's Gemini generative-language REST API.

This module is intentionally dependency-free (uses only the stdlib) so it can be
imported from any service without pulling extra packages into the smoke test
environment used by CI. The official ``google-genai`` SDK is a fine alternative
if richer features (streaming, tool-use, etc.) are needed later.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
DEFAULT_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "12"))
EMBEDDING_DIMENSION = 768  # text-embedding-004 returns 768-d vectors
_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiError(RuntimeError):
	"""Raised when the Gemini API cannot be reached or returns an unusable body."""


@dataclass
class GeminiClient:
	api_key: Optional[str] = None
	model: str = DEFAULT_MODEL
	embedding_model: str = DEFAULT_EMBEDDING_MODEL
	timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

	def __post_init__(self) -> None:
		if self.api_key is None:
			self.api_key = os.getenv("GEMINI_API_KEY")

	@property
	def is_configured(self) -> bool:
		return bool(self.api_key)

	def generate_text(
		self,
		prompt: str,
		*,
		temperature: float = 0.0,
		response_mime_type: Optional[str] = None,
	) -> str:
		"""Call ``generateContent`` and return the first candidate's text.

		Raises ``GeminiError`` on transport, HTTP, or shape failures so callers
		can decide whether to fall back to deterministic logic.
		"""

		if not self.api_key:
			raise GeminiError("GEMINI_API_KEY is not set")

		generation_config: dict[str, Any] = {"temperature": temperature}
		if response_mime_type:
			generation_config["responseMimeType"] = response_mime_type

		payload = {
			"contents": [{"parts": [{"text": prompt}]}],
			"generationConfig": generation_config,
		}

		endpoint = f"{_API_BASE}/{self.model}:generateContent?key={self.api_key}"
		request = Request(
			endpoint,
			data=json.dumps(payload).encode("utf-8"),
			headers={"Content-Type": "application/json"},
			method="POST",
		)

		try:
			with urlopen(request, timeout=self.timeout_seconds) as response:
				body = response.read().decode("utf-8")
		except HTTPError as exc:
			raise GeminiError(f"Gemini HTTP {exc.code}: {exc.reason}") from exc
		except (URLError, TimeoutError) as exc:
			raise GeminiError(f"Gemini transport error: {exc}") from exc

		try:
			parsed = json.loads(body)
			return parsed["candidates"][0]["content"]["parts"][0]["text"]
		except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
			raise GeminiError(f"Unexpected Gemini response shape: {body[:200]}") from exc

	def generate_json(self, prompt: str, *, temperature: float = 0.0) -> Any:
		"""Convenience wrapper that asks Gemini to respond with strict JSON."""

		text = self.generate_text(
			prompt,
			temperature=temperature,
			response_mime_type="application/json",
		)
		try:
			return json.loads(text)
		except json.JSONDecodeError as exc:
			raise GeminiError(f"Gemini returned non-JSON text: {text[:200]}") from exc

	def embed_text(self, text: str) -> list[float]:
		"""Embed a single string with ``text-embedding-004`` (768-d)."""

		if not self.api_key:
			raise GeminiError("GEMINI_API_KEY is not set")

		endpoint = f"{_API_BASE}/{self.embedding_model}:embedContent?key={self.api_key}"
		payload = {"content": {"parts": [{"text": text}]}}
		request = Request(
			endpoint,
			data=json.dumps(payload).encode("utf-8"),
			headers={"Content-Type": "application/json"},
			method="POST",
		)
		try:
			with urlopen(request, timeout=self.timeout_seconds) as response:
				body = response.read().decode("utf-8")
		except HTTPError as exc:
			raise GeminiError(f"Gemini HTTP {exc.code}: {exc.reason}") from exc
		except (URLError, TimeoutError) as exc:
			raise GeminiError(f"Gemini transport error: {exc}") from exc

		try:
			return list(json.loads(body)["embedding"]["values"])
		except (KeyError, TypeError, json.JSONDecodeError) as exc:
			raise GeminiError(f"Unexpected embedding response: {body[:200]}") from exc

	def embed_batch(self, texts: list[str]) -> list[list[float]]:
		"""Embed many strings via ``batchEmbedContents`` (max 100 per call)."""

		if not self.api_key:
			raise GeminiError("GEMINI_API_KEY is not set")
		if not texts:
			return []

		results: list[list[float]] = []
		batch_size = 100
		for start in range(0, len(texts), batch_size):
			chunk = texts[start : start + batch_size]
			endpoint = f"{_API_BASE}/{self.embedding_model}:batchEmbedContents?key={self.api_key}"
			payload = {
				"requests": [
					{
						"model": f"models/{self.embedding_model}",
						"content": {"parts": [{"text": t}]},
					}
					for t in chunk
				]
			}
			request = Request(
				endpoint,
				data=json.dumps(payload).encode("utf-8"),
				headers={"Content-Type": "application/json"},
				method="POST",
			)
			try:
				with urlopen(request, timeout=self.timeout_seconds) as response:
					body = response.read().decode("utf-8")
			except HTTPError as exc:
				raise GeminiError(f"Gemini HTTP {exc.code}: {exc.reason}") from exc
			except (URLError, TimeoutError) as exc:
				raise GeminiError(f"Gemini transport error: {exc}") from exc

			try:
				parsed = json.loads(body)
				for item in parsed["embeddings"]:
					results.append(list(item["values"]))
			except (KeyError, TypeError, json.JSONDecodeError) as exc:
				raise GeminiError(f"Unexpected batch embedding response: {body[:200]}") from exc

		return results

	def ping(self) -> bool:
		"""Lightweight liveness probe used by the ``/gemini/health`` endpoint."""

		try:
			self.generate_text("ping", temperature=0.0)
			return True
		except GeminiError:
			return False


def get_default_client() -> GeminiClient:
	"""Return a process-wide default client. Fresh instance per call is fine
	because construction is cheap and stateless."""

	return GeminiClient()
