# Stage 6 — LLM reasoning

Implemented in `backend/app/services/explanation.py`. The final, user-facing step.

## What it does

Takes the top 5-10 ranked candidates from Stage 5 and asks Gemini to:

1. Re-order them, possibly disagreeing with the rule-based ranker.
2. Write a one-sentence reason per recommendation.
3. Suggest pragmatic substitutions for missing ingredients.

The output is parsed back into a structured list of `Recommendation` objects.

## Why the LLM is last

* **Cheap inputs only.** It sees 5-10 small candidate dicts, never the whole corpus.
* **Bounded blast radius.** It can't "invent" a recipe — it picks from the candidates we hand it. A wrong pick is a bad recommendation; not a safety violation.
* **Replaceable.** If the LLM goes down or the key expires, the deterministic fallback takes over and the UI keeps working.

## Prompt

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

Two important constraints baked in:

1. **"Do not invent recipes or ingredients."** Reduces hallucination risk.
2. **Strict JSON shape with `responseMimeType: application/json`** (handled by `GeminiClient.generate_json`). Lets us parse without regexes.

The candidate dicts already include the rule-based score, the available/missing split, and the diet — so the LLM has every signal Stage 5 used and can't disagree out of ignorance.

## Validation

```68:91:backend/app/services/explanation.py
	raw_recs = payload.get("recommendations") if isinstance(payload, dict) else None
	if not isinstance(raw_recs, list):
		return _deterministic_recommendations(candidates)

	by_id = {c.recipe.id: c for c in candidates}
	recs: list[Recommendation] = []
	for idx, item in enumerate(raw_recs):
		if not isinstance(item, dict):
			continue
		try:
			recipe_id = int(item["recipe_id"])
		except (KeyError, TypeError, ValueError):
			continue
		if recipe_id not in by_id:
			continue
		fallback = by_id[recipe_id]
		recs.append(
			Recommendation(
				recipe_id=recipe_id,
				rank=int(item.get("rank", idx + 1)),
				reason=str(item.get("reason", "")).strip(),
				missing_ingredients=[str(x) for x in item.get("missing_ingredients", []) or fallback.missing_ingredients],
				substitutions=[str(x) for x in item.get("substitutions", []) or []],
			)
		)
```

Three safety nets:

1. Wrong shape → fall back to deterministic explanations.
2. Recipe IDs the LLM made up → silently dropped.
3. Missing fields → take from the rule-based candidate (`missing_ingredients` is always known accurately from Stage 5).

## Deterministic fallback

```96:108:backend/app/services/explanation.py
def _deterministic_recommendations(candidates: Sequence[RankedCandidate]) -> List[Recommendation]:
	return [
		Recommendation(
			recipe_id=c.recipe.id,
			rank=idx + 1,
			reason=(
				f"You already have {len(c.available_ingredients)} of "
				f"{len(c.available_ingredients) + len(c.missing_ingredients)} ingredients."
			),
			missing_ingredients=c.missing_ingredients,
			substitutions=[],
		)
		for idx, c in enumerate(candidates)
	]
```

Used when:

* `GEMINI_API_KEY` is not set.
* The Gemini call raises `GeminiError`.
* The response has the wrong shape.

The reasons are plain and accurate (count-based, not invented), and `substitutions` is empty since we can't synthesize them without a model.

## Cost knob

`top_k_explanation` (default 5, max 20) controls how many candidates the LLM sees per request. Each extra candidate adds ~50-150 tokens to the prompt. For most cases 5 is plenty; bump to 10 if you want richer ranking but check your token budget.

## What this stage doesn't do

* It doesn't filter for safety — Stage 3 already did that.
* It doesn't compute scores — Stage 5 already did that.
* It doesn't fetch recipes from the DB — they were passed in.

If you find yourself adding I/O here, push it back into the orchestrator instead. This stage is meant to be a thin LLM adapter.
