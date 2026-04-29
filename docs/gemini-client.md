# Gemini client

`backend/app/clients/gemini.py`. One client, two responsibilities:

* Text generation (Stages 2 + 6).
* Embeddings (Stage 4 + the loader).

It uses only the Python stdlib (`urllib`) — no SDK dependency — so the smoke test in CI doesn't need extra packages and corp networks with strict pip allowlists don't choke.

## Construction

```33:51:backend/app/clients/gemini.py
@dataclass
class GeminiClient:
	api_key: Optional[str] = None
	model: str = DEFAULT_MODEL
	embedding_model: str = DEFAULT_EMBEDDING_MODEL
	timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

	def __post_init__(self) -> None:
		if self.api_key is None:
			self.api_key = os.getenv("GEMINI_API_KEY")

	@property
	def is_configured(self) -> bool:
		return bool(self.api_key)
```

Defaults come from environment variables so 99% of code can just write `GeminiClient()`. `get_default_client()` is a convenience factory used by the FastAPI routes.

## API surface

| Method | Purpose | Endpoint |
| --- | --- | --- |
| `generate_text(prompt, *, temperature, response_mime_type)` | Single text completion. | `:generateContent` |
| `generate_json(prompt, *, temperature)` | Same as above with `responseMimeType=application/json`, parsed into a Python value. | `:generateContent` |
| `embed_text(text)` | One 768-d vector. | `:embedContent` |
| `embed_batch(texts)` | Many vectors, batched 100 per call. | `:batchEmbedContents` |
| `ping()` | Liveness probe (used by `/gemini/health`). | `:generateContent` with prompt `"ping"`. |

All four methods raise `GeminiError` on transport, HTTP, or response-shape failures. Callers decide whether to fall back to deterministic logic (normalization, ranking) or surface the error to the user (`/gemini/health`).

## Error handling

```77:84:backend/app/clients/gemini.py
		try:
			with urlopen(request, timeout=self.timeout_seconds) as response:
				body = response.read().decode("utf-8")
		except HTTPError as exc:
			raise GeminiError(f"Gemini HTTP {exc.code}: {exc.reason}") from exc
		except (URLError, TimeoutError) as exc:
			raise GeminiError(f"Gemini transport error: {exc}") from exc
```

The error message preserves the actual HTTP code and reason — that's what makes `/gemini/health` useful for debugging (you see `Gemini HTTP 429: Too Many Requests` instead of a generic "unreachable").

## Rate limit reality

Free-tier `gemini-2.0-flash` is generous for dev but easy to exhaust if:

* You re-load the corpus repeatedly (each `embed_batch` call = 1 quota unit).
* You spam `/recommend` (each request = 1 generation + 1 embedding call).

When you hit `HTTP 429`:

1. Wait ~60s.
2. Or switch model: `export GEMINI_MODEL=gemini-1.5-flash` (separate bucket).
3. Or enable billing on the underlying GCP project — same key, much higher limits.

## Behind a corporate proxy

`urllib` automatically honors `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` environment variables. No code change needed — just export them in the shell where the API runs.

## When to consider switching to the official SDK

Move to `google-genai` when you need any of:

* Streaming responses.
* Tool use / function calling.
* Image / audio inputs.
* Per-request safety setting overrides.

For pure text + embeddings, the stdlib client wins on simplicity.
