"""Embedding cache used by the loader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from app.clients.embedding_cache import EmbeddingCache, text_hash


def test_text_hash_is_stable() -> None:
    assert text_hash("hello") == text_hash("hello")
    assert text_hash("hello") != text_hash("world")


def test_put_then_get_roundtrips(tmp_path: Path) -> None:
    cache = EmbeddingCache(model="m", path=tmp_path / "cache.npz")
    cache.put("hello", [1.0, 2.0, 3.0])
    assert cache.has("hello")
    np.testing.assert_array_equal(
        cache.get("hello"), np.array([1.0, 2.0, 3.0], dtype=np.float32)
    )


def test_save_and_reload(tmp_path: Path) -> None:
    path = tmp_path / "cache.npz"
    cache = EmbeddingCache(model="m", path=path)
    cache.put_many([("a", [0.1, 0.2]), ("b", [0.3, 0.4])])
    cache.save()
    assert path.exists()

    reloaded = EmbeddingCache(model="m", path=path)
    assert len(reloaded) == 2
    assert reloaded.has("a")
    assert reloaded.has("b")


def test_model_change_invalidates_cache(tmp_path: Path) -> None:
    path = tmp_path / "cache.npz"
    old = EmbeddingCache(model="model-v1", path=path)
    old.put("a", [0.1])
    old.save()

    new = EmbeddingCache(model="model-v2", path=path)
    # Different model should treat the on-disk cache as empty.
    assert len(new) == 0
    assert not new.has("a")
