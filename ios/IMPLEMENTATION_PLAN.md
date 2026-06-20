# Dishify iOS — Implementation Plan

A step-by-step build plan for the Dishify iOS app, structured for **agentic development**:
each step is a self-contained unit of work with a clear goal, file scope, dependencies,
implementation notes, and acceptance criteria. Work one step at a time, top to bottom.
Steps within the same phase that list no dependency on each other can be parallelized.

> Backend contract is **frozen** — see [`docs/API.md`](../docs/API.md). Treat it as the
> source of truth for every request/response shape. Do not change backend behavior to
> suit the client; open a coordination note instead.

---

## 1. Goal & scope

Build a native SwiftUI app that lets a user:

1. Sign in (and register) via Keycloak.
2. Set dietary/allergy exclusions once (persisted server-side).
3. Enter a natural-language craving + an optional pantry inventory.
4. Get ranked recipe recommendations with reasoning, directions, and inventory match.

**Out of scope for MVP:** offline caching, push notifications, saved recipes, social
features, iPad-optimized layouts (build iPhone-first, don't break on iPad).

---

## 2. Tech decisions (fixed before coding)

These are chosen to keep the app dependency-free and easy for an agent to reason about.
Deviate only with a noted reason.

| Concern | Decision |
|---|---|
| Min iOS | iOS 16.0 (NavigationStack, `.task`, Swift Concurrency) |
| UI | SwiftUI only |
| Architecture | MVVM — `View` + `@MainActor` `ObservableObject` view models |
| Concurrency | `async`/`await`, no Combine pipelines, no completion handlers |
| Networking | `URLSession` + `Codable`, no third-party HTTP libs |
| Auth | `ASWebAuthenticationSession` for OIDC **Authorization Code + PKCE** (Flow A) |
| Token storage | Keychain (access + refresh token) |
| Dependencies | **Zero** SPM/CocoaPods deps for MVP |
| State | One app-level `SessionStore` (auth state) injected via `.environmentObject` |
| Config | `Config.swift` + build settings; no secrets in source (PKCE = public client) |

**Auth flow choice:** Use **Flow A (PKCE against Keycloak)** as the primary path because
`dishify-ios` is a provisioned public PKCE client (`docs/API.md` §Authentication) and it
avoids handling raw passwords. Keep Flow B (`/auth/login`) notes in Step 5 as a fallback
only if PKCE redirect setup is blocked.

---

## 3. Target architecture

```
DishifyApp                      // @main, injects SessionStore
└── RootView                    // switches on auth state: AuthView vs MainTabView
    ├── AuthView                // sign in / register entry
    └── MainTabView
        ├── RecommendView       // query + pantry -> results
        │   └── ResultDetailView
        └── PreferencesView     // exclusion restrictions editor

Core/
  Config.swift                  // base URL, scheme, client IDs
  APIClient.swift               // generic request, auth header, error mapping
  APIError.swift                // typed errors (401/422/503/decoding/transport)
  KeychainStore.swift           // token persistence
  AuthService.swift             // PKCE flow, token refresh
  SessionStore.swift            // @MainActor observable auth state

Models/                         // Codable mirrors of docs/API.md
Features/                       // one folder per screen: View + ViewModel
```

---

## 4. Conventions (apply to every step)

- **One file = one type** where reasonable; group by feature folder.
- All view models are `@MainActor final class … : ObservableObject`.
- Networking types live in `Core/`; never call `URLSession` from a `View`.
- Every model field name and optionality must match `docs/API.md` exactly
  (use `CodingKeys` for snake_case → camelCase).
- Each screen handles three states explicitly: **loading**, **error**, **content**.
- No force-unwraps (`!`) on network data or optionals from JSON.
- Add a `// MARK:` for each logical section; no narration comments.
- After any step: build succeeds, no new warnings, manual acceptance check passes.

---

## 5. Build steps

> Format per step — **Goal**, **Depends on**, **Files**, **Notes**, **Done when**.
> Check the box when an agent has completed and verified the step.

### Phase A — Foundation

#### [x] Step 0 — Xcode project + repo wiring
- **Goal:** A buildable, runnable empty SwiftUI app.
- **Depends on:** —
- **Files:** `Dishify.xcodeproj`, `DishifyApp.swift`, `ContentView.swift`, `Info.plist`,
  `Assets.xcassets`, `ios/README.md`.
- **Notes:** Bundle id `com.dishify.app` (or team-appropriate). Deployment target iOS 16.0.
  Single iPhone app target. Commit a `.gitignore` covering `xcuserdata/`, `*.xcuserstate`,
  `DerivedData/`. `ios/README.md` documents: open in Xcode, set signing team, run.
- **Done when:** App launches in simulator showing a placeholder screen.

#### [x] Step 1 — Config + environment
- **Goal:** Central, build-configurable settings.
- **Depends on:** Step 0
- **Files:** `Core/Config.swift`.
- **Notes:** Expose `apiBaseURL` (default `http://localhost:8000`), `keycloakBaseURL`
  (`http://localhost:9001`), `realm` (`dishify`), `iosClientID` (`dishify-ios`),
  `redirectURI` (`dishify://callback`). Read overrides from `Info.plist` / build settings so
  dev vs staging vs prod can differ without code edits. Prefer fetching live OIDC endpoints
  from `GET /auth/config` at runtime (Step 4) rather than hardcoding; Config holds fallbacks.
- **Done when:** `Config` returns correct values; referenced from a throwaway log line.

#### [x] Step 2 — Domain models (Codable)
- **Goal:** Type-safe mirrors of every API payload used by the app.
- **Depends on:** Step 0
- **Files:** `Models/RecommendModels.swift`, `Models/UserModels.swift`,
  `Models/AuthModels.swift`.
- **Notes:** Implement from `docs/API.md`:
  - `RecommendRequest` (`query`, `top_k?`, `available_ingredients?`, `exclusion_restrictions?`)
  - `ParsedIngredient` (`name`, `quantity: Double?`, `unit: String?`, `raw_text`)
  - `RecommendResponse` → `results: [RecipeResult]`, `stages: [Stage]`
  - `RecipeResult` (`rank`, `id: Int`, `title`, `summary: String?`, `time_minutes: Int?`,
    `score: Double`, `reasoning: Reasoning?`, `directions: [String]`,
    `inventory_matched: [String]`, `inventory_missing: [String]`)
  - `Reasoning` (`positive: [String]`, `negative: [String]`)
  - `Stage` (`name`, `status`, `latency_ms`)
  - `UserProfile`, `UserPreferences` (`exclusion_restrictions: [String]`)
  - `AuthConfig`, `TokenResponse` (`access_token`, `expires_in`, `refresh_token`, …)
  - Use `CodingKeys` for snake_case. Make optionals exactly where the contract allows null.
- **Done when:** Unit-decodes the sample JSON blobs from `docs/API.md` without error
  (add a small `ModelDecodingTests` using the doc examples as fixtures).

#### [x] Step 3 — Networking core
- **Goal:** A single typed entry point for all HTTP calls.
- **Depends on:** Step 1, Step 2
- **Files:** `Core/APIError.swift`, `Core/APIClient.swift`.
- **Notes:**
  - `APIError`: `.unauthorized`, `.validation(message)`, `.serverUnavailable`,
    `.http(status, body)`, `.decoding(Error)`, `.transport(Error)`.
  - `APIClient` generic `request<T: Decodable>(_ endpoint, method, body?, requiresAuth)`;
    injects `Authorization: Bearer` when a token provider is set; maps 401→`.unauthorized`,
    422→`.validation`, 503→`.serverUnavailable`.
  - Token provider is a closure/protocol so `AuthService` can be wired in Step 4 without a
    cycle. Keep `APIClient` auth-agnostic.
  - Add `GET /health` as the first call to prove the pipeline.
- **Done when:** A debug action hits `/health` and logs `{status: ok}` against local backend.

### Phase B — Auth

#### [x] Step 4 — Keychain + AuthService (PKCE)
- **Goal:** Sign in via Keycloak and securely persist tokens.
- **Depends on:** Step 3
- **Files:** `Core/KeychainStore.swift`, `Core/AuthService.swift`.
- **Notes:**
  - `KeychainStore`: save/load/delete access + refresh tokens (`kSecClassGenericPassword`).
  - `AuthService`: fetch endpoints from `GET /auth/config`; generate PKCE
    `code_verifier`/`code_challenge` (S256); launch `ASWebAuthenticationSession` with
    `dishify://callback`; exchange code at `token_endpoint`; store tokens.
  - Implement `refresh()` using the stored `refresh_token` (Keycloak token endpoint,
    `grant_type=refresh_token`). Access token TTL is 300s (`docs/API.md`), so refresh is
    required for any non-trivial session.
  - Expose `currentAccessToken()` (auto-refresh if near expiry) for `APIClient`.
- **Done when:** Tapping "Sign in" opens Keycloak, completes login, returns to app, and
  a stored token lets `/health`-style authed call succeed; relaunch keeps the session.

#### [x] Step 5 — SessionStore + auth gating (+ Flow B fallback)
- **Goal:** App-wide auth state that drives navigation.
- **Depends on:** Step 4
- **Files:** `Core/SessionStore.swift`, `Features/Root/RootView.swift`,
  `Features/Auth/AuthView.swift`.
- **Notes:**
  - `SessionStore` (`@MainActor ObservableObject`): `state` enum
    `.unknown / .signedOut / .signedIn(UserProfile?)`; methods `bootstrap()`, `signIn()`,
    `signOut()`. On launch, restore from Keychain and validate via `GET /me`.
  - `RootView` shows `AuthView` when signed out, `MainTabView` when signed in.
  - `AuthView`: "Sign in with Dishify" (PKCE) primary button. **Fallback only:** if PKCE
    redirect is blocked, add a username/password form using Flow B
    (`POST /auth/register`, `POST /auth/login`) — keep behind the same `SessionStore` API.
  - Handle `signOut()` = clear Keychain + reset state (client-side logout per API notes).
- **Done when:** Cold launch routes correctly; sign out returns to `AuthView`; sign in
  shows the main app.

### Phase C — Core features

#### [x] Step 6 — Preferences screen
- **Goal:** View and edit `exclusion_restrictions`.
- **Depends on:** Step 5
- **Files:** `Features/Preferences/PreferencesView.swift`,
  `Features/Preferences/PreferencesViewModel.swift`, `Core/RestrictionTags.swift`.
- **Notes:**
  - `GET /me/preferences` on appear; `PUT /me/preferences` on save.
  - The tag vocabulary comes from `data/restriction_rules.json` top-level keys
    (e.g. `nut_allergy`, `vegetarian`, `halal`). Bundle a static list in
    `RestrictionTags.swift` (snapshot the keys) with human-readable labels; note in code
    that it must stay in sync with the backend rules file.
  - UI: searchable multi-select list, grouped (allergies vs diets if labels allow).
  - Handle 422 (unknown tag) and 503 (Postgres) with clear messaging.
- **Done when:** Selecting tags + Save round-trips; reopening shows persisted selection.

#### [x] Step 7 — Pantry / ingredient input
- **Goal:** Reusable component to build `[ParsedIngredient]`.
- **Depends on:** Step 2
- **Files:** `Features/Recommend/PantryEditor.swift`,
  `Features/Recommend/PantryItem.swift`.
- **Notes:**
  - Add/remove rows; each row captures free text (`raw_text`, `name`) and optional
    `quantity` + `unit`. Keep `quantity`/`unit` optional and nullable to match the contract.
  - For MVP, set `name` = trimmed `raw_text`; no client-side ingredient parsing.
  - Pure UI component with a binding to `[ParsedIngredient]`; no networking here.
- **Done when:** Can build/edit a list and it serializes to the exact `ParsedIngredient`
  JSON shape from `docs/API.md`.

#### [x] Step 8 — Recommend query screen
- **Goal:** Compose a request and fetch results.
- **Depends on:** Step 3, Step 5, Step 7
- **Files:** `Features/Recommend/RecommendView.swift`,
  `Features/Recommend/RecommendViewModel.swift`.
- **Notes:**
  - Inputs: `query` (required), `top_k` (default 5, capped 100), pantry (Step 7).
  - **Omit** `exclusion_restrictions` for authenticated users so the backend applies
    stored prefs automatically (`docs/API.md` §`/recommend`). Only send explicit
    restrictions if we add a per-search override later.
  - `POST /recommend`; show loading; render `results`. Surface `stages` (esp. `explain`
    = `skipped`/`error`) subtly so missing LLM reasoning is explained, not silent.
  - Map errors: 401 → trigger re-auth via `SessionStore`; 422 → message; 503 →
    "service warming up / not indexed" copy.
- **Done when:** A query against local backend returns and lists real recommendations.

#### [x] Step 9 — Results list + detail
- **Goal:** Readable recommendation cards and a full detail view.
- **Depends on:** Step 8
- **Files:** `Features/Recommend/ResultRow.swift`,
  `Features/Recommend/ResultDetailView.swift`.
- **Notes:**
  - Row: title, score (as a clear indicator, not raw float), quick matched/missing counts.
  - Detail: `reasoning.positive` (✓) and `reasoning.negative` (✗), `inventory_matched`
    vs `inventory_missing`, numbered `directions`, `time_minutes`/`summary` when present
    (both can be null — handle gracefully).
  - No `GET /recipes/{id}` endpoint exists yet — render only from the `RecommendResponse`.
- **Done when:** Tapping a result opens detail with all available fields correctly shown.

### Phase D — Quality & release

#### [x] Step 10 — Global states, errors, token refresh UX
- **Goal:** Consistent, resilient UX across the app.
- **Depends on:** Steps 5–9
- **Files:** `Core/AsyncState.swift`, shared error/loading views, refresh wiring.
- **Notes:**
  - One reusable `AsyncState<T>` (`idle/loading/loaded/failed`) and shared
    loading/error/empty views; refactor screens to use them.
  - Centralize 401 handling: `APIClient` attempts a single silent token refresh before
    bubbling `.unauthorized`; on failure, `SessionStore.signOut()` → `AuthView`.
  - Honor `expires_in` (300s) — refresh proactively, don't wait for a 401 storm.
- **Done when:** Forcing an expired token auto-recovers once; unrecoverable auth returns
  to sign-in cleanly.

#### [x] Step 11 — Design pass & accessibility
- **Goal:** A polished, accessible iPhone-first UI.
- **Depends on:** Steps 6–10
- **Files:** `Assets.xcassets` (color set, app icon), `Core/Theme.swift`, view tweaks.
- **Notes:** App icon + accent color; Dynamic Type; VoiceOver labels on interactive
  controls; light/dark mode; tap targets ≥ 44pt; empty-state copy. Keep it modern and
  clean (cards, generous spacing).
- **Done when:** Looks intentional in light/dark, scales with large text, VoiceOver reads
  the main flows.

#### [x] Step 12 — Tests
- **Goal:** Lock down the risky, contract-sensitive parts.
- **Depends on:** Steps 2–9
- **Files:** `DishifyTests/` (model decoding, PKCE helpers, error mapping),
  optional `DishifyUITests/` for sign-in → recommend happy path.
- **Notes:** Use the JSON examples in `docs/API.md` as decoding fixtures (regression guard
  against contract drift). Unit-test PKCE `code_challenge` generation and `APIError`
  status mapping. Keep network out of unit tests (inject a stub client).
- **Done when:** `xcodebuild test` is green and covers models, auth helpers, error mapping.

#### [x] Step 13 — Release config & device validation
- **Goal:** Run against staging on a real device, ready for TestFlight.
- **Depends on:** all prior
- **Files:** `Info.plist` (URL scheme `dishify`), build settings, `ios/README.md`.
- **Notes:**
  - Register URL scheme `dishify` (for `dishify://callback`) and confirm Keycloak redirect.
  - Point `apiBaseURL`/`keycloakBaseURL` at staging via build config; verify
    `GET /auth/config` returns reachable public URLs (backend TODO: fix `keycloak:9001` →
    public host).
  - Test the full flow on device: register/login → set prefs → recommend → detail →
    background/relaunch (token refresh).
- **Done when:** End-to-end flow passes on a physical device against staging; archive builds.

---

## 6. Definition of done (whole app)

- [x] PKCE sign-in, session persistence, and token refresh work end-to-end.
- [x] Preferences round-trip to Postgres via `/me/preferences`.
- [x] Recommend flow returns and renders results with reasoning + directions.
- [x] All three states (loading/error/content) handled on every screen.
- [x] No force-unwraps on network data; models match `docs/API.md` exactly.
- [x] Decoding tests pass against the doc's JSON examples.
- [ ] Validated on a physical device against staging (manual — see `ios/README.md` checklist).

---

## 7. Dependency graph (quick reference)

```
0 → 1 → 3 → 4 → 5 → 6
0 → 2 → 3            ↘ 8 → 9
        2 → 7 ───────↗
5,6,7,8,9 → 10 → 11
2..9 → 12
all → 13
```

## 8. Agentic working notes

- Tackle **one step per session/PR**; keep diffs minimal and scoped to the step's files.
- Re-read [`docs/API.md`](../docs/API.md) before any networking step; it is frozen.
- Update the checkbox + a one-line note in this file when a step is verified.
- If a step needs a backend change, **stop** and raise it (contract is frozen) rather than
  working around it on the client.
- Prefer the standard library and first-party Apple frameworks; justify any new dependency.
