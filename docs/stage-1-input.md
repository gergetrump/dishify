# Stage 1 — Input

The HTTP layer in `backend/app/main.py` defines the request and response shapes and validates them with Pydantic before anything else runs.

## Endpoint

`POST /recommend` — runs the full pipeline.

## Request

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
* `profile.diet` — optional. Recognized values: `vegan`, `vegetarian`, `omnivore`, `pescatarian`. Anything else is treated as "no diet preference".
* `profile.allergies` — list of free-text allergen names. Substring-matched against the recipe's clean ingredient list and inferred allergen tags. Common values: `peanuts`, `tree_nuts`, `dairy`, `gluten`, `eggs`, `soy`, `fish`, `shellfish`, `sesame`.
* `top_k` — how many candidates to send to the LLM (1-20, default 5).

## Pydantic models

```31:43:backend/app/main.py
class Profile(BaseModel):
	diet: Optional[str] = Field(default=None, description="e.g. 'vegetarian', 'vegan'")
	allergies: List[str] = Field(default_factory=list)


class RecommendRequest(BaseModel):
	ingredients: List[str] = Field(..., min_length=1)
	profile: Profile = Field(default_factory=Profile)
	top_k: int = Field(default=5, ge=1, le=20)
```

Empty `ingredients` arrays are rejected with `422 Unprocessable Entity`. That's the only hard validation — everything else (unknown diet, weird allergy strings) is handled gracefully downstream.

## Response

```45:62:backend/app/main.py
class StageReportModel(BaseModel):
	name: str
	status: str
	detail: Optional[str] = None


class RecommendationModel(BaseModel):
	recipe_id: int
	rank: int
	reason: str
	missing_ingredients: List[str] = Field(default_factory=list)
	substitutions: List[str] = Field(default_factory=list)


class RecommendResponse(BaseModel):
	normalized_ingredients: List[str]
	profile: Profile
	candidate_pool_size: int
	retrieved_count: int
	scored_count: int
	recommendations: List[RecommendationModel] = Field(default_factory=list)
	stages: List[StageReportModel]
```

* `normalized_ingredients` — what the rest of the pipeline actually used; see [Stage 2](./stage-2-normalization.md).
* `candidate_pool_size` — recipes after the hard filter (Stage 3).
* `retrieved_count` — vector hits (Stage 4); `0` if retrieval was skipped.
* `scored_count` — items the ranker considered (Stage 5).
* `recommendations` — final ranked list (Stage 6 or fallback).
* `stages` — see [`pipeline-overview.md`](./pipeline-overview.md).

## CORS

CORS is currently fully open. That's fine for local dev but should be tightened before deploying behind a public origin:

```70:76:backend/app/main.py
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)
```

## Other endpoints (for completeness)

* `GET /health` — service liveness + recipe count from the DB.
* `GET /gemini/health` — verifies the Gemini connection is configured **and** reachable. Returns the actual error in `detail` (HTTP code, transport message, etc.) — see [`gemini-client.md`](./gemini-client.md).
* `POST /normalize` — runs only Stage 2. Useful for debugging the normalizer in isolation.
* `POST /gemini/generate` — debug passthrough to Gemini.
