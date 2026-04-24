# Dishify

Dishify is an AI-powered cooking assistant that helps users decide what to cook based on ingredients they already have.

It addresses a common problem: people have food at home but do not know what they can cook without additional shopping. Beyond recommendations, the system explains why recipes are suggested, highlights available and missing ingredients, and proposes substitutions when helpful.

## Runtime steps

### 1) User enters ingredients and profile constraints

Example input:

```json
{
	"ingredients": ["tomatoes", "pasta", "mozzarella"],
	"profile": {
		"diet": "vegetarian",
		"allergies": ["peanuts"]
	}
}
```

### 2) Ingredient normalization

Input ingredients are normalized via LLM and/or dictionary rules.

Examples:

```text
tomatoes -> tomato
mozzarella cheese -> mozzarella
```

### 3) Hard filtering (non-LLM)

PostgreSQL removes recipes that violate hard constraints:

```text
remove recipes containing peanuts
remove non-vegetarian recipes
```

This stage must be deterministic and should not be done by the LLM.

### 4) Vector retrieval

Qdrant retrieves top-k semantically similar candidates:

```text
top 50 candidate recipes
```

### 5) Rule-based scoring

Candidates are scored using:

- ingredient overlap
- missing ingredients
- diet match
- allergen safety

Example score:

```text
score =
0.5 * ingredient_match
+ 0.3 * vector_similarity
- 0.2 * missing_ingredient_penalty
```

### 6) LLM final reasoning

The LLM sees only the top 5-10 candidates and returns structured JSON recommendations:

```json
{
	"recommendations": [
		{
			"recipe_id": 123,
			"rank": 1,
			"reason": "Best match because most ingredients are available.",
			"missing_ingredients": ["garlic"],
			"substitutions": ["onion can replace garlic"]
		}
	]
}
```

## Gemini API key setup

The normalization service reads `GEMINI_API_KEY` from environment variables.

### Local development

1. Copy `.env.example` to `.env`.
2. Put your real key in `.env`:

	 ```
	 GEMINI_API_KEY=your_real_key_here
	 ```

3. Load it into your shell when needed:

	 ```bash
	 export GEMINI_API_KEY='your_real_key_here'
	 ```

`.env` is gitignored, so your key is not committed.

## CI/CD (GitHub Actions)

This repo has a workflow at `.github/workflows/ci.yml` that runs a backend normalization smoke test.

### What you must do on GitHub

1. Push this branch to GitHub.
2. Open your repository on GitHub.
3. Go to **Settings -> Secrets and variables -> Actions**.
4. Click **New repository secret**.
5. Name: `GEMINI_API_KEY`
6. Value: your real Gemini API key
7. Save.

After that, every push/PR will run the smoke test. The key is injected at runtime only and is never stored in the repository.

