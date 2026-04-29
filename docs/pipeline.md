# Pipeline

Every `/recommend` call runs a fixed 6-stage pipeline. The orchestrator is `backend/app/services/pipeline.py` and the response always echoes the per-stage outcome so callers can tell exactly what happened.

| # | Name | Module | Purpose | Can be skipped? |
| --- | --- | --- | --- | --- |
| 1 | Input | `main.py` | Validate the request shape (Pydantic). | No — rejected with 422. |
| 2 | Normalize | `services/normalization.py` | Map raw ingredient strings → canonical tokens. | No (always runs; fallback is deterministic). |
| 3 | Hard filter | `db/repository.py` | Drop recipes that violate diet / allergens. | Skipped if DB is unreachable (`error`). |
| 4 | Vector retrieval | `services/retrieval.py` + `vectorstore/` | Embed the query and ANN-search top-K candidates. | Skipped if no Gemini key or no vector index. |
| 5 | Rule-based scoring | `services/ranking.py` | Deterministic formula: overlap + similarity − missing penalty. | No — has a vector-less fallback. |
| 6 | LLM reasoning | `services/explanation.py` | Final Gemini rerank + reasons + substitutions. | Skipped if no Gemini key (deterministic explanations are returned). |

## Why this order?

* **Hard filter before retrieval** — small set of cheap SQL constraints first, so we don't burn a vector search on candidates we'd reject anyway. Also a hard safety boundary: an LLM should never be the thing keeping peanuts away from someone with a peanut allergy.
* **Vector retrieval before scoring** — the score formula uses vector similarity as one of its three terms. If we have no vector signal we fall back to a 2-term version.
* **LLM last** — the LLM only ever sees 5-10 candidates. This is the cost knob: increase `top_k_explanation` for richer reasoning at the cost of more tokens per request.

## Stage signalling

```19:33:backend/app/services/pipeline.py
@dataclass
class StageReport:
	name: str
	status: str  # "ok" | "skipped" | "error" | "pending"
	detail: Optional[str] = None
	latency_ms: Optional[float] = None


@dataclass
class PipelineReport:
	normalized_ingredients: List[str]
	stages: List[StageReport] = field(default_factory=list)
	candidate_pool_size: int = 0
	retrieved_count: int = 0
	scored_count: int = 0
	recommendations: List[Recommendation] = field(default_factory=list)
```

Statuses:

* `ok` — ran and produced a useful result.
* `skipped` — couldn't run because an optional dependency was missing; the pipeline continued without it.
* `error` — tried to run and failed; downstream stages may also be skipped.

`latency_ms` is populated for every stage that ran — useful for spotting slow stages without instrumenting anything else.

---

## Stage 1 — Input

`POST /recommend` is the entry point. Pydantic validates request and response shapes.

**Request:**

```json
{
  "ingredients": ["tomatoes", "pasta", "mozzarella"],
  "profile": {
    "diet": "vegetarian",
    "allergies": ["peanuts"]
  },
  "top_k": 5
}
```

* `ingredients` — required, at least one entry.
* `profile.diet` — optional. Recognized: `vegan`, `vegetarian`, `omnivore`, `pescatarian`. Anything else is treated as "no preference".
* `profile.allergies` — list of free-text allergen names. Substring-matched against the recipe's clean ingredient list and inferred allergen tags.
* `top_k` — how many candidates to send to the LLM (1–20, default 5).

Empty `ingredients` → `422`. That's the only hard validation; everything else is handled gracefully downstream.

**Response shape** (full Pydantic models live in `backend/app/main.py`):

```json
{
  "normalized_ingredients": ["tomato", "pasta", "mozzarella"],
  "candidate_pool_size": 192,
  "retrieved_count": 50,
  "scored_count": 50,
  "recommendations": [
    {
      "recipe_id": 1, "rank": 1,
      "title": "Jewell Ball's Chicken",
      "link": "www.cookbooks.com/...",
      "ingredients": ["chicken breasts", "..."],
      "directions": ["..."],
      "available_ingredients": ["..."],
      "missing_ingredients": ["..."],
      "substitutions": ["..."],
      "reason": "...",
      "score": 0.81, "ingredient_match": 1.0, "vector_similarity": 0.7
    }
  ],
  "stages": [
    {"name": "normalize",        "status": "ok", "latency_ms": 0.02, "detail": "..."},
    {"name": "hard_filter",      "status": "ok", "latency_ms": 4.93, "detail": "..."},
    {"name": "vector_retrieval", "status": "ok", "latency_ms": 8.12, "detail": "..."},
    {"name": "rule_based_scoring","status": "ok","latency_ms": 0.40, "detail": "..."},
    {"name": "llm_reasoning",    "status": "ok", "latency_ms": 850.0,"detail": "..."}
  ]
}
```

Other endpoints: `GET /health`, `GET /gemini/health`, `POST /normalize` (stage 2 only), `POST /gemini/generate` (debug passthrough).

---

## Stage 2 — Normalization

Two paths in priority order; first valid one wins.

```24:33:backend/app/services/normalization.py
	def normalize(self, ingredients: Iterable[str]) -> List[str]:
		prepared = [self._clean_input(item) for item in ingredients if self._clean_input(item)]
		if not prepared:
			return []

		llm_result = self._normalize_with_gemini(prepared)
		if llm_result is not None and len(llm_result) == len(prepared):
			return llm_result

		return [self._normalize_with_rules(item) for item in prepared]
```

1. **Clean** — lower-case, strip non-alphabetic, collapse whitespace.
2. **Try Gemini** — one batched JSON-mode call returning `{"normalized": [...]}`. Validated for length, non-empty, list-shape.
3. **Fallback to rules** — singularization, removing common modifiers and "cheese" suffix, plus a tiny synonym dictionary.

**Why both?** The LLM handles the long tail (`"Parmigiano-Reggiano D.O.P."` → `"parmigiano reggiano"`) but costs an API call and can fail. The rules cover common cases deterministically, are free, and let CI run without a Gemini key. A malformed LLM response (wrong length, extra keys, etc.) is dropped entirely — half-trusting the model is worse than ignoring it.

**CI guarantee:** the workflow asserts `normalize_ingredients(["tomatoes", "mozzarella cheese", "fresh basil"]) == ["tomato", "mozzarella", "basil"]`. Both paths produce that output, so CI passes either way. Don't break it.

---

## Stage 3 — Hard filter

This stage **must be deterministic and must not involve the LLM** — it's a safety boundary.

* **Diet boundaries** — a vegan user must never see a recipe with meat. Period.
* **Allergens** — a peanut-allergic user must never see a recipe with peanuts. Period.

```36:69:backend/app/db/repository.py
def hard_filter(
	session: Session,
	*,
	diet: Optional[str] = None,
	allergies: Sequence[str] = (),
	limit: Optional[int] = None,
) -> List[Recipe]:
	"""Return recipes that satisfy the user's hard constraints.

	* `diet` is matched against compatibility (e.g. vegetarian users can
	  also eat vegan recipes).
	* `allergies` are matched as substrings against any clean ingredient
	  name (cheap and conservative -- prefer false positives over leaks).
	"""
```

Two phases:

1. **SQL pre-filter on diet** using a compatibility table — vegetarians can also see vegan recipes, etc.
2. **Python allergen filter** — substring match against both the clean ingredient list and the inferred allergen tags. Substring is intentional: "peanut" matches "peanut butter" and "raw peanuts" alike.

**Why Python for allergens, not SQL?** Portable JSON-array containment across SQLite and Postgres is awkward. At 10k recipes the in-Python pass is sub-millisecond and the logic is clearer. If we move to >100k recipes, swap to a `?|` / `&&` Postgres query.

**Where do diet/allergen labels come from?** Inferred at load time from the dataset's clean ingredient list — the classifier is in `backend/app/services/taxonomy.py`. Design choice: **prefer false positives over leaks**. Don't quietly relax that.

---

## Stage 4 — Vector retrieval

1. Build a single text query from the user's normalized ingredients.
2. Embed it via Gemini's `text-embedding-004` (768-d).
3. Ask the vector store for the top-K most similar recipe IDs, restricted to the IDs that survived Stage 3.

```22:26:backend/app/services/retrieval.py
def build_query_text(ingredients: Sequence[str]) -> str:
	"""How a recipe-shaped query gets expressed for the embedding model."""

	if not ingredients:
		return ""
	return "Recipe with ingredients: " + ", ".join(ingredients)
```

This template is mirrored on the recipe side in `scripts/load_recipes.py::_build_query_text_for_recipe`. **Keep them aligned.** If you change one, change the other and re-embed — otherwise query / corpus drift will silently kill recall.

### Backends

Both expose `search(query_vector, top_k, allowed_ids) -> list[SearchHit]`:

* **`InMemoryVectorStore`** — loads `data/embeddings.npz` once at startup, brute-force cosine. Vectors are pre-normalized at load time so similarity is a single dot product. ~30 MB / ~1 ms search at 10k recipes.
* **`QdrantVectorStore`** — used when `QDRANT_URL` is set. Same `search()` API against a Qdrant server populated by the loader.

```113:119:backend/app/vectorstore/store.py
def get_default_vector_store() -> "InMemoryVectorStore | QdrantVectorStore":
	"""Pick the best available backend at process startup."""

	url = os.getenv("QDRANT_URL", "").strip()
	if url:
		return QdrantVectorStore(url=url)
	return InMemoryVectorStore()
```

The store is instantiated once during FastAPI lifespan and stashed on `app.state.vector_store`, then threaded into `retrieve_candidates()` per request.

### Filtering by allowed IDs

The candidate pool from Stage 3 is pushed as a hard ID restriction into the vector search — we never spend ranking effort on disqualified recipes. If the pool is empty, Stage 4 short-circuits without calling Gemini.

### Failure modes

`retrieve_candidates` raises `RetrievalUnavailable` (caught by the orchestrator) when there's no key, embedding fails, or the index isn't loadable. Stage 4 reports `skipped` and Stage 5 falls back to overlap-only ranking over the entire candidate pool — request still succeeds.

---

## Stage 5 — Rule-based scoring

Pure function, no I/O, easy to unit test. Formula straight from the README:

```text
score = 0.5 * ingredient_match
      + 0.3 * vector_similarity
      - 0.2 * missing_ingredient_penalty
```

* **`ingredient_match`** — fraction of the recipe's ingredients the user already has (`|recipe ∩ user| / |recipe|`). Asymmetric — favours recipes whose ingredients are mostly available.
* **`vector_similarity`** — cosine similarity from Stage 4, rescaled from `[-1, 1]` to `[0, 1]`.
* **`missing_ingredient_penalty`** — `min(1, |missing| / 10)`.

When Stage 4 is unavailable, `fallback_rank_without_vectors` runs the same formula with `vector_similarity = 0` for everyone.

### Token matching

The matcher is **word-level, not whole-string and not substring**. Both the user's ingredients and each recipe's ingredients are tokenized into a bag of meaningful, singularized words (stopwords like "of"/"and" dropped, very short tokens dropped). A recipe ingredient is "available" if at least one of its tokens is in the user's combined token set.

Why this shape:

* Whole-string matching missed obvious cases (`"chicken"` from the user not matching `"chicken breasts"` in the recipe).
* Substring matching produces silent leaks (`"egg"` matching `"eggplant"`, `"pea"` matching `"peanut butter"`).
* Word-level set matching with singularization gets both right: `chicken` ⊆ `{chicken, breast}` ✅, `egg` ⊄ `{eggplant}` ✅.

---

## Stage 6 — LLM reasoning

Takes the top 5–10 ranked candidates and asks Gemini to re-order them, write a one-sentence reason per pick, and suggest pragmatic substitutions for missing ingredients.

```37:54:backend/app/services/explanation.py
def _build_prompt(
	user_ingredients: Sequence[str],
	profile: dict,
	candidates: Sequence[RankedCandidate],
) -> str:
	return (
		"You are a cooking assistant ranking recipe candidates for a user.\n"
		"Pick the best matches based on which ingredients the user already has, "
		"the user's profile, and how few additional ingredients they would need.\n"
		"For each pick, write a one-sentence reason and propose pragmatic substitutions "
		"for missing items when reasonable. Do not invent recipes or ingredients.\n"
		"Return STRICT JSON with this shape:\n"
		'{"recommendations": [{"recipe_id": int, "rank": int, "reason": str, '
		'"missing_ingredients": [str], "substitutions": [str]}]}\n'
		f"User ingredients: {json.dumps(list(user_ingredients))}\n"
		f"User profile: {json.dumps(profile)}\n"
		f"Candidates: {json.dumps([_candidate_to_prompt_dict(c) for c in candidates])}\n"
	)
```

Two important constraints baked into the prompt:

1. **"Do not invent recipes or ingredients."** Reduces hallucination risk.
2. **Strict JSON shape with `responseMimeType: application/json`** — parses without regexes.

The candidate dicts already include the rule-based score, the available/missing split, and the diet — so the LLM has every signal Stage 5 used.

### Validation safety nets

1. Wrong shape → fall back to deterministic explanations.
2. Recipe IDs the LLM made up → silently dropped.
3. Missing fields → take from the rule-based candidate.

### Deterministic fallback

Used when there's no key, the call fails, or the response is malformed. Reasons are plain and accurate (`"You already have N of M ingredients"`); `substitutions` is empty since we can't synthesize them without a model.

### What this stage doesn't do

It doesn't filter for safety (Stage 3 did), doesn't compute scores (Stage 5 did), doesn't fetch recipes from the DB (they were passed in). Keep it a thin LLM adapter — push I/O into the orchestrator.

---

## Adding a new stage

1. Add a service module in `backend/app/services/`.
2. Hook it into `services/pipeline.py` inside a `_stage(stages, "name")` block so it shows up in the response with status + latency.
3. Update this doc.
4. Update `architecture.md` if it introduces a new external dependency.
