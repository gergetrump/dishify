# iOS

SwiftUI client — **not started**.

## Auth (when implemented)

- OIDC login via `ASWebAuthenticationSession`
- Keycloak client: `dishify-ios` (public, PKCE)
- Redirect URI: `dishify://callback`
- API calls to backend with `Authorization: Bearer <access_token>`

Keycloak realm config lives at [`keycloak/`](../keycloak/), not in this folder.

## Backend dependency

The app will call the FastAPI backend in [`backend/`](../backend/) — primarily `POST /recommend`.
