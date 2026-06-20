# Agent scope rules (Dishify)

Paste this into Cursor (or any AI agent) at the start of each session.

## Backend

```
SCOPE: Only edit files under backend/.
Branch: feature/backend-mvp
Read docs/API.md for request/response shapes.
Do NOT edit keycloak/, notebooks/, data/, or docs/API.md unless explicitly asked.
Do NOT edit docker-compose.yml without noting it in your summary.
Minimal diff only. No repo-wide refactors.
```

## Shared files (coordinate first)

- `docs/API.md` — frozen during MVP sprint
- `docker-compose.yml` — backend person edits
- `.env.example` — document new vars when added
- Root `README.md` — avoid unless onboarding changes

## Git

- Rebase on latest `main` / integration branch before each session
- Humans merge PRs; agents do not merge branches
