"""Vector index abstraction used by stage 4 (retrieval).

Two backends:

* ``QdrantVectorStore`` -- talks to a Qdrant server when ``QDRANT_URL`` is set.
* ``InMemoryVectorStore`` -- numpy brute-force cosine search; loaded from a
  ``.npz`` snapshot saved by the loader script. Plenty fast for 10k recipes
  and means the project works without Docker.

The two share the same ``search()`` signature, so the rest of the pipeline
doesn't need to know which one is in use.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "dishify_recipes")
_REPO_ROOT = Path(__file__).resolve().parents[3]
EMBEDDINGS_PATH = Path(os.getenv("EMBEDDINGS_PATH") or (_REPO_ROOT / "data" / "embeddings.npz"))


@dataclass
class SearchHit:
	recipe_id: int
	score: float


class VectorStoreError(RuntimeError):
	pass


def _filter_ids(
	candidate_ids: Iterable[int],
	*,
	allowed_ids: Sequence[int] | None,
) -> list[int]:
	if allowed_ids is None:
		return list(candidate_ids)
	allowed = set(int(x) for x in allowed_ids)
	return [int(i) for i in candidate_ids if int(i) in allowed]


class InMemoryVectorStore:
	"""Brute-force cosine similarity over an ``.npz`` snapshot.

	Snapshot layout written by ``scripts/load_recipes.py``:
		ids:       int64 array of shape (N,)
		vectors:   float32 array of shape (N, D), L2-normalized
	"""

	def __init__(self, path: Path = EMBEDDINGS_PATH) -> None:
		if not path.exists():
			raise VectorStoreError(f"No embeddings snapshot at {path}. Run scripts/load_recipes.py first.")
		data = np.load(path)
		self.ids: np.ndarray = data["ids"].astype(np.int64)
		self.vectors: np.ndarray = data["vectors"].astype(np.float32)
		if self.vectors.ndim != 2 or self.ids.shape[0] != self.vectors.shape[0]:
			raise VectorStoreError("Embeddings snapshot has inconsistent shape.")

	def search(
		self,
		query_vector: Sequence[float],
		*,
		top_k: int = 50,
		allowed_ids: Sequence[int] | None = None,
	) -> list[SearchHit]:
		query = np.asarray(query_vector, dtype=np.float32)
		norm = float(np.linalg.norm(query))
		if norm == 0.0:
			return []
		query = query / norm
		scores = self.vectors @ query  # rows already L2-normalized

		mask = np.ones(self.ids.shape[0], dtype=bool)
		if allowed_ids is not None:
			allowed = set(int(x) for x in allowed_ids)
			mask = np.array([int(i) in allowed for i in self.ids], dtype=bool)
			if not mask.any():
				return []

		eligible_scores = np.where(mask, scores, -np.inf)
		top_n = min(top_k, int(mask.sum()))
		if top_n <= 0:
			return []
		top_indices = np.argpartition(eligible_scores, -top_n)[-top_n:]
		top_indices = top_indices[np.argsort(-eligible_scores[top_indices])]
		return [SearchHit(int(self.ids[i]), float(scores[i])) for i in top_indices]


class QdrantVectorStore:
	def __init__(self, url: str, collection: str = COLLECTION_NAME) -> None:
		try:
			from qdrant_client import QdrantClient
		except ImportError as exc:
			raise VectorStoreError("qdrant-client is not installed") from exc
		self._client = QdrantClient(url=url)
		self._collection = collection

	def search(
		self,
		query_vector: Sequence[float],
		*,
		top_k: int = 50,
		allowed_ids: Sequence[int] | None = None,
	) -> list[SearchHit]:
		from qdrant_client.http import models as qmodels

		query_filter = None
		if allowed_ids is not None:
			query_filter = qmodels.Filter(must=[qmodels.HasIdCondition(has_id=list(allowed_ids))])

		try:
			hits = self._client.search(
				collection_name=self._collection,
				query_vector=list(query_vector),
				limit=top_k,
				query_filter=query_filter,
			)
		except Exception as exc:  # qdrant-client raises a variety of errors
			raise VectorStoreError(f"Qdrant search failed: {exc}") from exc
		return [SearchHit(int(h.id), float(h.score)) for h in hits]


def get_default_vector_store() -> InMemoryVectorStore | QdrantVectorStore:
	"""Pick the best available backend at process startup."""

	url = os.getenv("QDRANT_URL", "").strip()
	if url:
		return QdrantVectorStore(url=url)
	return InMemoryVectorStore()
