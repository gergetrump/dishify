# Dishify iOS

Native SwiftUI client for the Dishify gateway API. The UI mirrors the web client: single-column layout with header navigation (Cook, Preferences, Profile), not a tab bar.

## Requirements

- macOS with **Xcode 15+** (Swift 5.9+)
- iOS **16.0+** simulator or device
- Backend running locally or on a reachable host — see [`../backend/README.md`](../backend/README.md) (Docker Compose, vector store restore, env files)

## Open and run

1. Open `Dishify.xcodeproj` in Xcode.
2. Select the **Dishify** scheme.
3. Use build configuration **Debug** for simulator + local backend (`http://localhost:8000`).
4. **Signing:** choose your Apple Developer team under *Signing & Capabilities*.
5. Press **Run** (⌘R).

From the repo root, start the backend before testing:

```bash
docker compose up -d
curl -s http://localhost:8000/health
```

Retrieval loads the embedding model on first `/recommend`; the first recipe search may take a minute after a cold start.

## What the app does

| Area | Behavior |
|------|----------|
| **Auth** | Register / log in via gateway `POST /auth/register` and `POST /auth/login` (username + password). Tokens in Keychain; refresh via `POST /auth/refresh`. |
| **Cook** | Pantry ingredients (saved locally), natural-language “vibe” query, `POST /recommend`. |
| **Results** | Ranked recipes from the last search; tap for detail. |
| **Preferences** | Diet / allergy hard filters via `GET/PUT /me/preferences`. |
| **Profile** | `GET /me`, log out. |

Navigation is driven by `AppRouter` in `SessionStore.swift` (welcome, login, register, cook, preferences, results, recipe detail, profile).

**Not used in this app:** Keycloak PKCE / browser OAuth. `Info.plist` still registers the `dishify://` URL scheme for future use; login does not open Keycloak in a web session.

## Build configurations

| Configuration | Typical use | API base URL |
|---------------|-------------|--------------|
| **Debug** | Simulator, local dev | `http://localhost:8000` |
| **Release** | Archive / TestFlight | `http://localhost:8000` in xcconfig — override before shipping |
| **Staging** | Device against remote API | Placeholders in `Config/Staging.xcconfig` |

Settings live in `Config/*.xcconfig` and flow into `Info.plist`. At runtime **`Config.swift` only reads `DishifyAPIBaseURL`** (gateway). All auth and recommend traffic goes to that single base URL.

| Build setting | Purpose |
|---------------|---------|
| `DISHIFY_API_BASE_URL` | Gateway: `/health`, `/auth/*`, `/me/*`, `/recommend` |

`DISHIFY_KEYCLOAK_BASE_URL`, `DISHIFY_REALM`, `DISHIFY_IOS_CLIENT_ID`, and `DISHIFY_REDIRECT_URI` remain in xcconfig / plist for compatibility but are not read by app code today.

### Staging on a physical device

1. Copy `Config/Staging.example.xcconfig` → `Config/Staging.local.xcconfig` (gitignored).
2. Set your public gateway URL, e.g. `DISHIFY_API_BASE_URL = https:/$()/api.staging.yourteam.com`
3. In Xcode: **Dishify** target → *Info* → **Based on Configuration File** for **Staging** → `Staging.local.xcconfig`.
4. Product → Scheme → Edit Scheme → Run → Build Configuration → **Staging** (the default scheme runs **Debug**).

Staging builds should use **HTTPS** (App Transport Security).

### Simulator vs physical device (local backend)

- **Simulator:** `http://localhost:8000` works (Debug xcconfig).
- **Physical iPhone:** `localhost` is the phone, not your Mac. Point the app at your Mac’s LAN IP:

```
DISHIFY_API_BASE_URL = http:/$()/192.168.1.42:8000
```

Same Wi‑Fi network; allow incoming connections in macOS firewall if needed. `Info.plist` sets `NSAllowsLocalNetworking` for local HTTP.

Default Keycloak test user (when using Compose auth): `testuser` / `test-secret` — see `keycloak/create-realm.sh`.

## Project layout

```
ios/
├── Config/                     # xcconfig (Debug, Release, Staging)
├── Dishify.xcodeproj/
├── Dishify/
│   ├── Core/                   # APIClient, SessionStore, AppRouter, theme, Keychain
│   ├── Features/
│   │   ├── Auth/               # WelcomePage, LoginPage, RegisterPage
│   │   ├── Preferences/        # PreferencesPage (food restrictions)
│   │   ├── Recommend/          # CookPage, ResultsPage, RecipeDetailPage, pantry stores
│   │   └── Root/               # RootView, ProfilePage
│   ├── Models/
│   └── Assets.xcassets/
├── DishifyTests/
└── scripts/validate_release.sh
```

## Command line

**Unit tests:**

```bash
cd ios
xcodebuild -scheme Dishify \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -configuration Debug \
  -derivedDataPath build/DerivedData test
```

**Release validation** (tests + Release archive + Staging build):

```bash
cd ios
chmod +x scripts/validate_release.sh
./scripts/validate_release.sh
```

Optional live `GET /auth/config` check (for teams still validating OIDC endpoints):

```bash
DISHIFY_API_BASE_URL=https://api.staging.example.com ./scripts/validate_release.sh
```

**Archive for TestFlight** (signing team required):

```bash
xcodebuild -scheme Dishify \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath build/Dishify-Release.xcarchive \
  archive
```

Upload via Xcode Organizer or `xcodebuild -exportArchive`.

## Device validation checklist

On a physical iPhone against staging or Mac LAN IP:

- [ ] Sign up or log in
- [ ] **Preferences** → select restrictions → Save → relaunch → still selected
- [ ] **Cook** → add pantry items → search → **Results** appear
- [ ] Open a recipe → directions, reasoning, inventory match/unmatch
- [ ] Background app → relaunch → still signed in (token refresh)
- [ ] After refresh failure → clean return to login

## API contract

Networking matches [`../docs/API.md`](../docs/API.md). The app uses the gateway REST auth endpoints, not direct Keycloak OIDC from the device.

## TestFlight notes

- `ITSAppUsesNonExemptEncryption` is `false` (HTTPS only in production).
- Bump `MARKETING_VERSION` / `CURRENT_PROJECT_VERSION` before each upload.
- Use HTTPS staging/production URLs in Release / Staging xcconfig.
