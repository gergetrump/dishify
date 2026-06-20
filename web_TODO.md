# Dishify Web Frontend TODO

## Goal

Build a modern React web app for Dishify that preserves the product flow from `Group 1.pdf` while connecting to the current backend gateway API in `docs/API.md`.

Primary user flow:

1. Register or log in.
2. Set allergy/diet hard filters.
3. Add available pantry ingredients.
4. Describe the current food "vibe" in natural language.
5. View recipe recommendations.
6. Open recipe details with reasoning, missing ingredients, and directions.

## Source of Truth

- API base URL: `http://localhost:8000`
- API contract: `docs/API.md`
- Auth provider behind backend: Keycloak
- Frontend client target: `dishify-web`
- Restriction vocabulary: `data/restriction_rules.json`
- Backend-facing public endpoints:
  - `GET /health`
  - `GET /auth/config`
  - `POST /auth/register`
  - `POST /auth/login`
  - `GET /me`
  - `GET /me/preferences`
  - `PUT /me/preferences`
  - `POST /recommend`

## Design Direction

Keep the current friendly food-assistant identity, but modernize the app:

- Use the PDF flow as product guidance, not as pixel-perfect UI.
- Keep the soft off-white background, orange primary actions, and green/orange food identity.
- Replace placeholder chips with real allergy/diet labels.
- Avoid fake mobile keyboard mockups in the actual web UI.
- Make the app responsive for desktop and mobile.
- Use a practical app layout first, not a marketing landing page.
- Keep cards restrained: recipe cards and modals only.
- Make pantry, vibe, and recommendations efficient to scan.

## Phase 1 - Scaffold

- [x] Create a Vite + React + TypeScript app under `web-client/`.
- [x] Add routing.
- [x] Add a minimal design system:
  - [x] colors
  - [x] typography
  - [x] buttons
  - [x] inputs
  - [x] chips
  - [x] recipe cards
  - [x] loading/error states
- [x] Add `.env.example` values for:
  - [x] `VITE_API_URL=http://localhost:8000`
- [x] Add basic README instructions for running the web app.

## Phase 2 - API Client

- [x] Implement a typed API client based on `docs/API.md`.
- [x] Add request/response types:
  - [x] `RegisterRequest`
  - [x] `RegisterResponse`
  - [x] `LoginRequest`
  - [x] `TokenResponse`
  - [x] `UserProfile`
  - [x] `UserPreferences`
  - [x] `ParsedIngredient`
  - [x] `RecommendRequest`
  - [x] `RecommendResponse`
  - [x] `RecipeResult`
  - [x] `PipelineStage`
- [x] Attach `Authorization: Bearer <token>` when logged in.
- [x] Normalize backend errors for UI display:
  - [x] `401` auth/session errors
  - [x] `422` validation errors
  - [x] `503` backend/indexing/service unavailable errors
- [x] Add health check helper for local troubleshooting.

## Phase 3 - Auth

- [x] Build welcome screen.
- [x] Build login screen using `POST /auth/login`.
- [x] Build register screen using `POST /auth/register`.
- [x] Store auth token locally.
- [x] Restore session on page reload.
- [x] Add logout.
- [x] Add protected routes for:
  - [x] preferences
  - [x] pantry/vibe
  - [x] recommendations
  - [x] profile
- [x] Handle expired/invalid token with a clear re-login path.

## Phase 4 - Preferences

- [x] Load restriction keys from a local frontend constant based on `data/restriction_rules.json`.
- [x] Group preferences into user-friendly sections:
  - [x] allergies
  - [x] diets
  - [x] religious/ethical restrictions
  - [x] medical/sensitivity filters
  - [x] ingredient exclusions
- [x] Build preference chip picker.
- [x] Load saved preferences with `GET /me/preferences`.
- [x] Save preferences with `PUT /me/preferences`.
- [x] Support initial preferences during registration.
- [x] Show clear saved/error/loading states.

## Phase 5 - Pantry

- [x] Build pantry ingredient entry form:
  - [x] ingredient name
  - [x] optional quantity
  - [x] optional unit
- [x] Add ingredients to an editable list.
- [x] Support edit/delete per ingredient.
- [x] Support clear all.
- [x] Persist pantry locally for convenience.
- [x] Convert pantry items to backend `available_ingredients`.

## Phase 6 - Vibe Check

- [x] Build free-text query screen.
- [x] Use the PDF's "vibe check" concept, but label it clearly for web users.
- [x] Examples:
  - [x] "quick high-protein dinner"
  - [x] "cozy vegetarian pasta"
  - [x] "spicy lunch with eggs"
- [x] Add `top_k` selector with a sensible default of `5`.
- [x] Submit `POST /recommend`.
- [x] If authenticated, omit `exclusion_restrictions` by default so stored preferences apply.
- [x] Optionally allow one-off preference override later.

## Phase 7 - Recommendations

- [x] Build recommendations list.
- [x] Display per recipe:
  - [x] title
  - [x] score
  - [x] matched ingredients
  - [x] missing ingredients
  - [x] positive reasoning
  - [x] negative reasoning
  - [x] estimated time if present
- [x] Display pipeline stage status in a compact debug/details area.
- [x] Add empty state when no recipes are returned.
- [x] Add retry behavior for transient errors.

## Phase 8 - Recipe Detail

- [x] Build recipe detail page or panel from selected `RecipeResult`.
- [x] Display:
  - [x] recipe title
  - [x] score
  - [x] matched ingredients
  - [x] missing ingredients
  - [x] reasoning
  - [x] directions
- [x] Account for missing backend fields:
  - [x] `summary` may be null
  - [x] `time_minutes` may be null
  - [x] `directions` may be null
- [x] Do not depend on `GET /recipes/{id}` because it does not exist yet.

## Phase 9 - Profile

- [x] Build profile screen using `GET /me`.
- [x] Show username/email.
- [x] Link to preferences.
- [x] Add logout.
- [x] Avoid implementing password change/delete account until backend endpoints exist.

## Phase 10 - Quality

- [x] Add responsive checks for mobile and desktop.
- [x] Add keyboard-accessible forms and chips.
- [x] Add visible focus states.
- [x] Add loading states.
- [x] Add form validation before API calls.
- [x] Add smoke tests or component tests for critical flows.
- [x] Verify against local backend with Docker Compose.
- [ ] Verify with gateway `DISABLE_AUTH=false` after backend auth config is switched for staging.

## Phase 11 - Integration Checklist

- [x] `docker compose up -d`
- [x] `docker compose run --rm indexing-worker --recreate`
- [x] Confirm `GET http://localhost:8000/health`
- [x] Register user via web-client integration script.
- [x] Log in via web-client integration script.
- [x] Save preferences.
- [x] Add pantry ingredients.
- [x] Submit vibe query.
- [x] Confirm recommendation cards render.
- [x] Confirm recipe detail renders.
- [x] Confirm 401/422 errors have useful UI states; 503 is covered by client normalization but not induced against the running stack.

## Known Backend Constraints

- Access token TTL is currently short (`expires_in` around 300 seconds).
- No refresh endpoint exists yet.
- No logout endpoint exists yet.
- No recipe detail endpoint exists yet.
- `summary` and `time_minutes` may not be populated.
- Stored preferences only include `exclusion_restrictions`.
- Auth may be disabled for `/recommend` in local Day 1 mode, but `/me/*` always requires a token.

## Proposed Initial Route Map

- `/` - app home or redirect based on auth state
- `/login` - login
- `/register` - registration
- `/preferences` - allergy/diet filters
- `/app` - pantry and vibe input
- `/results` - recommendation results
- `/recipes/:id` - local detail view from selected recommendation state
- `/profile` - account/profile

## Proposed Frontend Structure

```text
web-client/
  src/
    api/
      client.ts
      types.ts
    auth/
      AuthProvider.tsx
      storage.ts
    components/
      Button.tsx
      Chip.tsx
      Input.tsx
      RecipeCard.tsx
    data/
      restrictions.ts
    pages/
      LoginPage.tsx
      RegisterPage.tsx
      PreferencesPage.tsx
      AppPage.tsx
      ResultsPage.tsx
      RecipeDetailPage.tsx
      ProfilePage.tsx
    styles/
      globals.css
    App.tsx
    main.tsx
```

## First Implementation Pass

- [x] Scaffold `web-client/`.
- [x] Implement API types/client.
- [ ] Implement auth provider and login/register.
- [ ] Implement preferences picker.
- [ ] Implement pantry + vibe screen.
- [ ] Implement recommendations list and recipe detail.
- [ ] Run the app locally against `http://localhost:8000`.
