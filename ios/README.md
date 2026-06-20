# Dishify iOS

Native SwiftUI client for the Dishify API. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for the step-by-step build history.

## Requirements

- macOS with **Xcode 15+** (Swift 5.9+)
- iOS **16.0+** simulator or device
- Backend running locally or a reachable staging deployment — see root [`README.md`](../README.md)

## Open and run

1. Open `Dishify.xcodeproj` in Xcode.
2. Select the **Dishify** scheme.
3. Choose **Debug** (simulator + local backend) or **Staging** (device + remote backend).
4. **Signing:** select your Apple Developer team under *Signing & Capabilities*.
5. Press **Run** (⌘R).

The app supports PKCE sign-in, dietary preferences, pantry-aware recipe search, and result detail views.

## Build configurations

| Configuration | Use case | API defaults |
|---|---|---|
| **Debug** | Simulator, local dev | `http://localhost:8000` |
| **Release** | TestFlight / App Store archive | `http://localhost:8000` (override before shipping) |
| **Staging** | Physical device against remote backend | Placeholder hosts in `Config/Staging.xcconfig` |

Settings live in `Config/*.xcconfig` and flow into `Info.plist` via build settings. `Core/Config.swift` reads them at runtime.

| Build setting | Purpose |
|---|---|
| `DISHIFY_API_BASE_URL` | Gateway (`/health`, `/recommend`, `/auth/*`, `/me/*`) |
| `DISHIFY_KEYCLOAK_BASE_URL` | Keycloak fallback (live OIDC URLs come from `GET /auth/config`) |
| `DISHIFY_REALM` | Keycloak realm (`dishify`) |
| `DISHIFY_IOS_CLIENT_ID` | PKCE client (`dishify-ios`) |
| `DISHIFY_REDIRECT_URI` | OAuth redirect (`dishify://callback`) |

### Staging setup

1. Copy `Config/Staging.example.xcconfig` → `Config/Staging.local.xcconfig` (gitignored).
2. Set your real staging hosts in `Staging.local.xcconfig`.
3. In Xcode: select the **Staging** build configuration for the **Dishify** target → *Info* → set **Based on Configuration File** to `Staging.local.xcconfig` (or edit `Staging.xcconfig` directly).
4. Confirm Keycloak has redirect URI `dishify://callback` for client `dishify-ios`.

**Auth config check:** `GET /auth/config` must return **publicly reachable** `authorization_endpoint` and `token_endpoint` URLs. If the backend returns internal Docker hostnames (e.g. `keycloak:9001`), PKCE sign-in will fail on device — that is a backend configuration issue.

```bash
curl -s https://YOUR-STAGING-API/auth/config | python3 -m json.tool
```

## Physical device + local backend

Simulators can use `localhost`; a physical iPhone cannot. Point the app at your Mac's LAN IP:

```
DISHIFY_API_BASE_URL = http:/$()/192.168.1.42:8000
DISHIFY_KEYCLOAK_BASE_URL = http:/$()/192.168.1.42:9001
```

Ensure the device is on the same Wi‑Fi network and macOS firewall allows incoming connections.

## OAuth URL scheme

Registered in `Info.plist`:

- **Scheme:** `dishify`
- **Redirect:** `dishify://callback`

Keycloak must list this redirect URI on the `dishify-ios` public client.

## Project layout

```
ios/
├── Config/                  # xcconfig build settings (Debug / Release / Staging)
├── Dishify.xcodeproj/
├── Dishify/
│   ├── Core/                # Config, networking, auth, theme
│   ├── Features/            # Auth, Preferences, Recommend, Root
│   ├── Models/
│   └── Assets.xcassets/
├── DishifyTests/
└── scripts/validate_release.sh
```

## Command line

**Run unit tests:**

```bash
cd ios
xcodebuild -scheme Dishify \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -configuration Debug \
  -derivedDataPath build/DerivedData test
```

**Release validation (tests + archive + staging build):**

```bash
cd ios
chmod +x scripts/validate_release.sh
./scripts/validate_release.sh
```

Optional auth-config smoke check against a live backend:

```bash
DISHIFY_API_BASE_URL=https://api.staging.example.com ./scripts/validate_release.sh
```

**Archive for TestFlight** (requires signing team):

```bash
xcodebuild -scheme Dishify \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath build/Dishify.xcarchive \
  archive
```

Then upload via Xcode Organizer or `xcodebuild -exportArchive`.

## Device validation checklist

Run on a physical iPhone against staging (or LAN IP for local backend):

- [ ] Register or sign in (PKCE or username/password)
- [ ] Set dietary restrictions in **Preferences** → Save → relaunch → verify persisted
- [ ] Search in **Recommend** with pantry items → results appear
- [ ] Tap a result → detail shows reasoning, inventory, directions
- [ ] Background the app for several minutes → relaunch → still signed in (token refresh)
- [ ] Force expired refresh token → app returns to sign-in cleanly

## API contract

All networking matches [`docs/API.md`](../docs/API.md). Keycloak client: `dishify-ios` (PKCE, redirect `dishify://callback`).

## TestFlight notes

- `ITSAppUsesNonExemptEncryption` is set to `false` (standard HTTPS only).
- Bump `MARKETING_VERSION` / `CURRENT_PROJECT_VERSION` before each upload.
- Staging URLs must use HTTPS for production TestFlight builds (ATS).
