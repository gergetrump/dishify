"""Stage 4 -- vector retrieval.

Embeds the user's normalized ingredient list and asks the vector store for
the top-K most semantically similar candidates, restricted to the IDs that
survived the hard filter.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..clients.gemini import GeminiClient, GeminiError
from ..vectorstore import (
	InMemoryVectorStore,
	QdrantVectorStore,
	SearchHit,
	VectorStoreError,
	get_default_vector_store,
)

VectorStore = "InMemoryVectorStore | QdrantVectorStore"


@dataclass
class RetrievedCandidate:
	recipe_id: int
	vector_score: float


def build_query_text(ingredients: Sequence[str]) -> str:
	"""How a recipe-shaped query gets expressed for the embedding model."""

	if not ingredients:
		return ""
	return "Recipe with ingredients: " + ", ".join(ingredients)


def retrieve_candidates(
	ingredients: Sequence[str],
	*,
	allowed_ids: Sequence[int] | None = None,
	top_k: int = 50,
	gemini_client: GeminiClient | None = None,
	vector_store: InMemoryVectorStore | QdrantVectorStore | None = None,
) -> list[RetrievedCandidate]:
	"""Return up to ``top_k`` candidate recipe IDs ordered by similarity.

	Both the Gemini client and the vector store can be injected. The pipeline
	resolves them once at startup and threads them through, so /recommend
	doesn't pay startup costs per request.
	"""

	if not ingredients:
		return []
	if allowed_ids is not None and len(allowed_ids) == 0:
		return []

	client = gemini_client or GeminiClient()
	if not client.is_configured:
		raise RetrievalUnavailable("GEMINI_API_KEY is not set; cannot embed query")

	try:
		query_vector = client.embed_text(build_query_text(ingredients))
	except GeminiError as exc:
		raise RetrievalUnavailable(f"Embedding failed: {exc}") from exc

	if vector_store is None:
		try:
			vector_store = get_default_vector_store()
		except VectorStoreError as exc:
			raise RetrievalUnavailable(str(exc)) from exc

	hits: list[SearchHit] = vector_store.search(
		query_vector,
		top_k=top_k,
		allowed_ids=allowed_ids,
	)
	return [RetrievedCandidate(h.recipe_id, h.score) for h in hits]


class RetrievalUnavailable(RuntimeError):
	"""Raised when retrieval can't run (no key, no index, no candidates)."""
