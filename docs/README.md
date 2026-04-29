# Dishify documentation

Long-form companion to the top-level `README.md`. The top-level README is for cloning and running. These docs explain *why* each piece exists and how it's wired in.

| File | What it covers |
| --- | --- |
| [`architecture.md`](./architecture.md) | System diagram, components, env vars, degradation rules, observability, Gemini client. |
| [`pipeline.md`](./pipeline.md) | The 6-stage pipeline with one section per stage. |
| [`setup.md`](./setup.md) | Running locally (Track A: SQLite + in-memory; Track B: Docker), dataset loading, tests, CI. |
| [`troubleshooting.md`](./troubleshooting.md) | Common failure modes (proxy, 429, missing key, missing DB) with the fix for each. |
| [`roadmap.md`](./roadmap.md) | What's done, what's next, what's nice-to-have. |

## Conventions

- Code paths are written from the repo root: e.g. `backend/app/services/normalization.py`.
- Code references in these docs use the `startLine:endLine:filepath` format so they render as live citations in the IDE.
- "Stage N" always means the same N as the top-level README's pipeline.
