# Stage 4 — Vector retrieval

Implemented in `backend/app/services/retrieval.py`, with the actual ANN search living in `backend/app/vectorstore/store.py`.

## What it does

1. Builds a single text query from the user's normalized ingredients.
2. Embeds it via Gemini's `text-embedding-004` (768-d).
3. Asks the vector store for the top-K most similar recipe IDs, restricted to the IDs that survived Stage 3.

## The query string

```22:26:backend/app/services/retrieval.py
def build_query_text(ingredients: Sequence[str]) -> str:
	"""How a recipe-shaped query gets expressed for the embedding model."""

	if not ingredients:
		return ""
	return "Recipe with ingredients: " + ", ".join(ingredients)
```

This template is mirrored on the recipe side in `scripts/load_recipes.py::_build_query_text_for_recipe`. **Keep them aligned.** If you change one, change the other and re-embed — otherwise query / corpus drift will silently kill recall.

## Embedding

Uses `GeminiClient.embed_text` for the query and `embed_batch` for the corpus. Both go through the shared client documented in [`gemini-client.md`](./gemini-client.md).

## The two backends

A single abstraction with two implementations:

```42:48:backend/app/vectorstore/store.py
@dataclass
class SearchHit:
	recipe_id: int
	score: float


class VectorStoreError(RuntimeError):
	pass
```

Both backends expose `search(query_vector, top_k, allowed_ids) -> list[SearchHit]`.

### `InMemoryVectorStore`

Loads `data/embeddings.npz` once at startup and does brute-force cosine. Vectors are pre-normalized at load time so similarity is a single dot product:

```56:91:backend/app/vectorstore/store.py
class InMemoryVectorStore:
	"""Brute-force cosine similarity over an ``.npz`` snapshot.

	Snapshot layout written by ``scripts/load_recipes.py``:
		ids:       int64 array of shape (N,)
		vectors:   float32 array of shape (N, D), L2-normalized
	"""

	def __init__(self, path: Path = EMBEDDINGS_PATH) -> None:
		if not path.exists():
			raise VectorStoreError(
				f"No embeddings snapshot at {path}. Run scripts/load_recipes.py first."
			)
		data = np.load(path)
		self.ids: np.ndarray = data["ids"].astype(np.int64)
		self.vectors: np.ndarray = data["vectors"].astype(np.float32)
```

For 10k × 768-d this is ~30 MB and a search takes ~1 ms. Plenty for dev and demos.

### `QdrantVectorStore`

Used when `QDRANT_URL` is set. Runs the same `search()` API against a Qdrant server populated by `scripts/load_recipes.py::push_to_qdrant`. Cosine distance, `HasIdCondition` filter for allowed IDs.

### Picking one

```113:119:backend/app/vectorstore/store.py
def get_default_vector_store() -> "InMemoryVectorStore | QdrantVectorStore":
	"""Pick the best available backend at process startup."""

	url = os.getenv("QDRANT_URL", "").strip()
	if url:
		return QdrantVectorStore(url=url)
	return InMemoryVectorStore()
```

Qdrant wins if available; in-memory is the fallback. Either way, the rest of the pipeline doesn't know.

## Filtering by allowed IDs

The candidate pool comes from Stage 3 — usually a small fraction of the corpus. We push that as a hard ID restriction into the vector search so we never spend ranking effort on disqualified recipes:

* In-memory: a boolean mask over the index.
* Qdrant: `Filter(must=[HasIdCondition(has_id=[...])])`.

If the pool is empty (allergens cover everything), Stage 4 short-circuits to empty without calling Gemini at all.

## Failure modes

`retrieve_candidates` raises `RetrievalUnavailable` (caught and logged by the orchestrator) when:

* `GEMINI_API_KEY` is not set.
* Embedding fails (wrapped `GeminiError`).
* No vector index is loadable (no `.npz`, no Qdrant).

The orchestrator records `vector_retrieval` as `skipped` and falls back to overlap-only ranking over the entire candidate pool. So a missing index degrades quality but doesn't fail the request.

## Tuning knobs

| Knob | Where | Default | When to change |
| --- | --- | --- | --- |
| `top_k_retrieval` | `pipeline.run_pipeline` argument | 50 | More = wider candidate pool for the ranker; mostly affects Stage 5 cost. |
| Embedding model | `GEMINI_EMBEDDING_MODEL` env | `text-embedding-004` | Switching models means re-embedding the corpus. |
| Query template | `build_query_text` | `"Recipe with ingredients: ..."` | Try alternative phrasings if recall is poor; remember to re-embed corpus side too. |
| Distance | Qdrant config in loader | Cosine | Cosine is fine for this; only change if you switch to an embedder that prefers dot product. |
