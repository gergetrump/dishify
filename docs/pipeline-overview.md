# Pipeline overview

Every `/recommend` call runs a fixed 6-stage pipeline. The orchestrator is `backend/app/services/pipeline.py` and the response always echoes the per-stage outcome so callers can tell exactly what happened.

## The stages

| # | Name | Module | Purpose | Can be skipped? |
| --- | --- | --- | --- | --- |
| 1 | Input | `main.py` | Validate the request shape (Pydantic). | No — rejected with 422. |
| 2 | Normalize | `services/normalization.py` | Map raw ingredient strings → canonical tokens. | No (always runs; fallback is deterministic). |
| 3 | Hard filter | `db/repository.py` | Drop recipes that violate diet / allergens. | Skipped if DB is unreachable (logged as `error`). |
| 4 | Vector retrieval | `services/retrieval.py` + `vectorstore/` | Embed the query and ANN-search top-K candidates. | Skipped if no Gemini key or no vector index. |
| 5 | Rule-based scoring | `services/ranking.py` | Deterministic formula combining overlap + similarity − missing penalty. | No — has a vector-less fallback. |
| 6 | LLM reasoning | `services/explanation.py` | Final Gemini rerank + reasons + substitutions. | Skipped if no Gemini key (deterministic explanations are returned). |

## Why this order?

* **Hard filter before retrieval** — small set of cheap SQL constraints first, so we don't burn a vector search on candidates we'd reject anyway. Also a hard safety boundary: an LLM should never be the thing keeping peanuts away from someone with a peanut allergy.
* **Vector retrieval before scoring** — the score formula uses vector similarity as one of its three terms. If we have no vector signal we fall back to a 2-term version.
* **LLM last** — the LLM only ever sees 5-10 candidates. This is the cost knob: increase `top_k_explanation` for richer reasoning at the cost of more tokens per request.

## Stage signalling

The orchestrator records every stage in `PipelineReport.stages`:

```19:33:backend/app/services/pipeline.py
@dataclass
class StageReport:
	name: str
	status: str  # "ok" | "skipped" | "error" | "pending"
	detail: Optional[str] = None


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
* `pending` — defined for forward compatibility (currently unused).

Example response from a no-Gemini-key run:

```json
{
  "normalized_ingredients": ["chicken breast", "cream of mushroom soup", "sour cream"],
  "candidate_pool_size": 192,
  "retrieved_count": 0,
  "scored_count": 50,
  "recommendations": [
    {"recipe_id": 1, "rank": 1, "reason": "You already have 2 of 4 ingredients.",
     "missing_ingredients": ["beef", "chicken breasts"], "substitutions": []}
  ],
  "stages": [
    {"name": "normalize",          "status": "ok",      "detail": "3 ingredients"},
    {"name": "hard_filter",        "status": "ok",      "detail": "192 recipes survived hard constraints"},
    {"name": "vector_retrieval",   "status": "skipped", "detail": "GEMINI_API_KEY is not set; cannot embed query"},
    {"name": "rule_based_scoring", "status": "ok",      "detail": "50 scored"},
    {"name": "llm_reasoning",      "status": "skipped", "detail": "GEMINI_API_KEY not set; using deterministic fallback ranking."}
  ]
}
```

Use `stages` in the frontend to show users when the recommender is degraded (e.g. "explanations unavailable today" badge), and in monitoring to alert on any `error`.

## Adding a new stage

1. Add a service module in `backend/app/services/`.
2. Hook it into `services/pipeline.py` with its own `_record(stages, ...)` calls so it shows up in the response.
3. Update this doc.
4. Update `architecture.md` if it introduces a new external dependency.
