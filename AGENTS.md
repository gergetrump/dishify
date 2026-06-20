# Agent scope rules (Dishify)

Paste this into Cursor (or any AI agent) at the start of each session.

## Person A — Backend

```
SCOPE: Only edit files under backend/.
Branch: feature/backend-mvp
Read docs/API.md for request/response shapes.
Do NOT edit ios/, keycloak/, notebooks/, data/, or docs/API.md unless explicitly asked.
Do NOT edit docker-compose.yml without noting it in your summary (Person B may need to review).
Minimal diff only. No repo-wide refactors.
```

## Person B — iOS

```
SCOPE: Only edit files under ios/.
Branch: feature/ios-mvp
Read docs/API.md for request/response shapes.
Backend base URL: http://localhost:8000
Do NOT edit backend/, keycloak/, notebooks/, data/, or docs/API.md unless explicitly asked.
Minimal diff only. No repo-wide refactors.
```

## Shared files (coordinate first)

- `docs/API.md` — frozen during MVP sprint
- `docker-compose.yml` — backend person edits; iOS person reviews
- `.env.example` — document new vars when added
- Root `README.md` — avoid unless onboarding changes

## Git

- One branch per person; never commit to the other's branch
- Rebase on latest `main` / integration branch before each session
- Humans merge PRs; agents do not merge branches
