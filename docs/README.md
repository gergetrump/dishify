# Dishify documentation

This folder is the long-form companion to the top-level `README.md`. The top-level README is for anyone who just wants to clone and run the project. These docs explain *why* each piece exists, how it's wired in, and what the next person should change when extending it.

## Table of contents

| File | What it covers |
| --- | --- |
| [`architecture.md`](./architecture.md) | High-level system diagram, components, environment variables, and degradation rules. |
| [`running-locally.md`](./running-locally.md) | Step-by-step: venv, env vars, DB, vector index, server, troubleshooting. |
| [`data-loading.md`](./data-loading.md) | Dataset schema, the loader script, diet/allergen inference, embedding cache. |
| [`pipeline-overview.md`](./pipeline-overview.md) | The 6-stage pipeline at a glance and the orchestrator that runs it. |
| [`stage-1-input.md`](./stage-1-input.md) | Stage 1 — request shape, Pydantic models, validation. |
| [`stage-2-normalization.md`](./stage-2-normalization.md) | Stage 2 — Gemini-backed ingredient normalization with deterministic fallback. |
| [`stage-3-hard-filter.md`](./stage-3-hard-filter.md) | Stage 3 — diet + allergen hard constraints (SQL + Python). |
| [`stage-4-vector-retrieval.md`](./stage-4-vector-retrieval.md) | Stage 4 — embedding the query and finding top-K candidates. |
| [`stage-5-ranking.md`](./stage-5-ranking.md) | Stage 5 — deterministic rule-based scoring formula. |
| [`stage-6-llm-reasoning.md`](./stage-6-llm-reasoning.md) | Stage 6 — final LLM rerank + explanations + substitutions. |
| [`gemini-client.md`](./gemini-client.md) | The shared HTTP client used for both generation and embeddings. |
| [`troubleshooting.md`](./troubleshooting.md) | Common failure modes (proxy, 429, missing key, missing DB) and the fix for each. |

## Conventions

- Code paths are written from the repo root: e.g. `backend/app/services/normalization.py`.
- Code references in these docs use the `startLine:endLine:filepath` format so they render as live citations in the IDE.
- "Stage N" always means the same N as the top-level README's pipeline.
