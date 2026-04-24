# Dishify

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

`/.env` is gitignored, so your key is not committed.

## CI/CD (GitHub Actions)

This repo has a workflow at `.github/workflows/ci.yml` that runs a backend normalization smoke test.

### What you must do on GitHub

1. Push this branch to GitHub.
2. Open your repository on GitHub.
3. Go to **Settings → Secrets and variables → Actions**.
4. Click **New repository secret**.
5. Name: `GEMINI_API_KEY`
6. Value: your real Gemini API key
7. Save.

After that, every push/PR will run the smoke test. The key is injected at runtime only and is never stored in the repository.

