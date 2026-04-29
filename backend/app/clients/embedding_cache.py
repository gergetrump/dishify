"""On-disk cache of embedding vectors, keyed by (model, sha256(text)).

Used by ``scripts/load_recipes.py`` so re-running the loader doesn't re-embed
recipes that haven't changed. Format on disk is a single ``.npz`` file:

	hashes:  bytes-array of SHA-256 hex digests, shape (N,)
	vectors: float32 array of shape (N, D)
	model:   bytes (utf-8) -- the model name used to embed; cache is invalidated
	         if you change models.

Load + save are intentionally simple and fully synchronous. For 10k recipes
this is ~30 MB on disk and ~10 ms to load.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_PATH = Path(os.getenv("EMBEDDING_CACHE_PATH") or (_REPO_ROOT / "data" / "embeddings_cache.npz"))


def text_hash(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingCache:
	"""Hash -> vector dictionary backed by an .npz snapshot."""

	def __init__(self, model: str, path: Path = DEFAULT_CACHE_PATH) -> None:
		self.model = model
		self.path = path
		self._store: dict[str, np.ndarray] = {}
		self._loaded_model: str | None = None
		self._dirty = False
		self.load()

	# ---- lifecycle ----

	def load(self) -> None:
		self._store.clear()
		self._loaded_model = None
		self._dirty = False
		if not self.path.exists():
			return
		try:
			data = np.load(self.path, allow_pickle=False)
			loaded_model = bytes(data["model"]).decode("utf-8") if "model" in data else ""
			if loaded_model and loaded_model != self.model:
				# Different model -> cache is stale; treat as empty.
				return
			self._loaded_model = loaded_model
			hashes = data["hashes"]
			vectors = data["vectors"].astype(np.float32)
			for i, h in enumerate(hashes):
				h_str = bytes(h).decode("ascii") if isinstance(h, (bytes, np.bytes_)) else str(h)
				self._store[h_str] = vectors[i]
		except (OSError, KeyError, ValueError):
			# Corrupt cache; start fresh rather than crashing the loader.
			self._store.clear()

	def save(self) -> None:
		if not self._dirty:
			return
		self.path.parent.mkdir(parents=True, exist_ok=True)
		hashes = np.array(list(self._store.keys()), dtype="S64")
		vectors = (
			np.stack(list(self._store.values()), axis=0)
			if self._store
			else np.zeros((0, 0), dtype=np.float32)
		)
		model_bytes = np.frombuffer(self.model.encode("utf-8"), dtype=np.uint8)
		np.savez(self.path, hashes=hashes, vectors=vectors, model=model_bytes)
		self._dirty = False

	# ---- accessors ----

	def __len__(self) -> int:
		return len(self._store)

	def has(self, text: str) -> bool:
		return text_hash(text) in self._store

	def get(self, text: str) -> np.ndarray | None:
		return self._store.get(text_hash(text))

	def put(self, text: str, vector: Sequence[float]) -> None:
		self._store[text_hash(text)] = np.asarray(vector, dtype=np.float32)
		self._dirty = True

	def put_many(self, pairs: Iterable[tuple[str, Sequence[float]]]) -> None:
		for text, vec in pairs:
			self.put(text, vec)

	def vectors_for(self, texts: Sequence[str]) -> list[np.ndarray | None]:
		return [self.get(t) for t in texts]
