# Stage 2 — Ingredient normalization

Implemented in `backend/app/services/normalization.py`. Two paths run in priority order; the first one to produce a valid result wins.

## Goal

Given user-typed ingredient strings — possibly plural, with descriptors like "fresh"/"chopped", with synonyms like "mozzarella cheese" — produce one canonical token per input that's safe to compare against the dataset's `NER` field.

Example:

```text
"Tomatoes"             -> "tomato"
"mozzarella cheese"    -> "mozzarella"
"Fresh basil leaves"   -> "basil leaf"
```

## Pipeline

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

## Why both?

* The LLM handles the long tail (`"Parmigiano-Reggiano D.O.P."` → `"parmigiano reggiano"`) but costs an API call and can fail.
* The rules cover the common cases deterministically, are free, and let CI run without a Gemini key.
* If Gemini's response is malformed (wrong length, extra keys, etc.) we drop it entirely and fall through. Half-trusting the model is worse than fully ignoring it.

## Prompt

```39:47:backend/app/services/normalization.py
		prompt = (
			"Normalize each ingredient into a canonical kitchen base ingredient. "
			"Return singular, lower-case, concise names only. Remove descriptors like 'fresh', "
			"'dried', and type suffixes when not essential, e.g. 'mozzarella cheese' -> 'mozzarella'. "
			"Keep ingredient identity, and do not invent ingredients. "
			"Return strict JSON with this shape: {\"normalized\": [\"...\"]}. "
			"The output list length must exactly match the input list order.\n"
			f"Input: {json.dumps(ingredients)}"
		)
```

The prompt is intentionally explicit about **list length** because length-validating the response is what protects us from the LLM dropping items.

## Rule fallback

```89:113:backend/app/services/normalization.py
	def _normalize_with_rules(self, ingredient: str) -> str:
		dictionary = {
			"tomatoes": "tomato",
			"mozzarella cheese": "mozzarella",
		}

		if ingredient in dictionary:
			return dictionary[ingredient]

		removable_words = {
			"fresh",
			"dried",
			"frozen",
			"chopped",
			"sliced",
			"grated",
			"cheese",
		}

		words = [word for word in ingredient.split() if word not in removable_words]
		if not words:
			words = ingredient.split()

		singular_words = [self._singularize(word) for word in words]
		return " ".join(singular_words)
```

Three pieces:

1. A small explicit dictionary for cases the singularizer can't handle (irregular plurals, multi-word collapses).
2. A descriptor-removal pass that drops words like `fresh`, `chopped`, etc.
3. A tiny English singularizer (handles `-ies`, `-oes`, `-ses`, plain `-s`).

If you want richer behaviour without an LLM, the next thing to add is the `ingredient-parser-nlp` library that's already in `requirements.txt`. It does NER-style parsing on raw "1 cup chopped onions, finely diced" strings and returns the bare ingredient.

## CI guarantee

The CI smoke test in `.github/workflows/ci.yml` calls `normalize_ingredients(["tomatoes", "mozzarella cheese", "fresh basil"])` and asserts the result equals `["tomato", "mozzarella", "basil"]`. Both the Gemini path and the rule path produce that output, so CI passes either way. **Don't break this assertion** — if you change the rules, also update the test (and ideally add a Gemini-only path test too).
