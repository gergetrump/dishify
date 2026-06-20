# Integration checklist (Day 2 lunch)

1. Person A merges `feature/backend-mvp` → `main` (or integration branch)
2. Verify: `curl http://localhost:8000/health` and `POST /recommend` (see `docs/API.md`)
3. Person B: `git fetch && git rebase main` on `feature/ios-mvp`
4. In iOS, set `APIClient.useMock = false` in `Dishify/Services/APIClient.swift`
5. Run backend: `docker compose up -d` or `cd backend && uvicorn app.main:app --reload`
6. Run iOS simulator; login → enter ingredients → confirm real recommendations
7. Person B merges `feature/ios-mvp` → `main`

## CORS

Backend enables CORS for all origins in dev. If the simulator still fails, confirm backend URL is `http://127.0.0.1:8000` vs `localhost`.
