# Dishify Web Client

React + Vite web client for the Dishify gateway API. The UI mirrors the iOS app: single-column layout with header navigation (Cook, Preferences, Profile), not a tab bar.

## Requirements

- **Node.js 20+** and npm
- Backend running locally or on a reachable host — see [`../backend/README.md`](../backend/README.md) (Docker Compose, vector store restore, env files)

## Local development

```bash
cd web-client
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`.

Start the backend from the repo root before testing:

```bash
docker compose up -d
docker compose run --rm indexing-worker --recreate   # first time / after data changes
curl -s http://localhost:8000/health
```

Retrieval loads the embedding model on first `/recommend`; the first recipe search may take a minute after a cold start.

## What the app does

| Area | Behavior |
|------|----------|
| **Auth** | Register / log in via gateway `POST /auth/register` and `POST /auth/login` (username + password). Tokens in `localStorage`; refresh via `POST /auth/refresh`. |
| **Cook** | Pantry ingredients (saved locally), natural-language “vibe” query, `POST /recommend`. |
| **Results** | Ranked recipes from the last search; tap for detail. |
| **Preferences** | Diet / allergy hard filters via `GET/PUT /me/preferences`. |
| **Profile** | `GET /me`, log out. |

Routes: `/` (welcome), `/login`, `/register`, `/app`, `/results`, `/recipes/:id`, `/preferences`, `/profile`.

**Not used in this app:** Keycloak PKCE / browser OAuth. Login goes through gateway REST auth endpoints, same as iOS.

## Environment

| Variable | Purpose | Default |
|----------|---------|---------|
| `VITE_API_URL` | Gateway base URL (baked in at build time) | `http://localhost:8000` |

Copy `web-client/.env.example` to `web-client/.env` for local `npm run dev`.

For Docker builds, optionally set `VITE_API_URL` in the repo root `.env`. When unset, the client defaults to `http://localhost:8000` (gateway is published on port 8000 in Compose).

## Docker (full stack)

The `web-client` service is included in root `docker-compose.yml`. Caddy serves the static build and proxies API paths to the gateway:

```bash
docker compose up -d
```

| URL | Service |
|-----|---------|
| `http://localhost` | Web app (via Caddy) |
| `http://localhost:8000` | Gateway API (used by the client unless `VITE_API_URL` is overridden at build time) |
| `http://localhost:5173` | Vite dev server (`npm run dev` only) |

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Vite dev server on port 5173 |
| `npm run build` | Typecheck + production build to `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm test` | Unit tests (Vitest) |
| `npm run test:integration` | Live gateway smoke test (`scripts/integration-smoke.mjs`) |

**Integration smoke** (backend must be up and indexed):

```bash
cd web-client
npm run test:integration
```

Override the API URL if needed:

```bash
VITE_API_URL=http://localhost:8000 npm run test:integration
```

## Project layout

```
web-client/
├── src/
│   ├── api/              # HTTP client, request/response types
│   ├── auth/             # AuthProvider, RequireAuth, token storage
│   ├── components/       # Button, Chip, Input, RecipeCard
│   ├── data/             # Restriction labels / options
│   ├── pages/            # Welcome, auth, Cook, Results, recipe detail, Preferences, Profile
│   ├── pantry/           # localStorage pantry items
│   ├── recommendations/  # Session storage for last search
│   └── styles/
├── scripts/
│   └── integration-smoke.mjs
├── Dockerfile
└── nginx.conf
```

## Manual validation checklist

- [ ] Sign up or log in
- [ ] **Preferences** → select restrictions → Save → reload → still selected
- [ ] **Cook** → add pantry items → search → **Results** appear
- [ ] Open a recipe → directions, reasoning, inventory match/unmatch
- [ ] Reload page → still signed in (stored token)
- [ ] Log out → protected routes redirect to login

## API contract

Networking matches [`../docs/API.md`](../docs/API.md). The app uses gateway REST auth endpoints, not direct Keycloak OIDC from the browser. CORS is enabled for all origins in backend dev mode.
