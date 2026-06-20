# iOS

SwiftUI client with Keycloak login and recipe recommendations.

## Open in Xcode

```bash
open ios/Dishify.xcodeproj
```

Set your **Development Team** in Signing & Capabilities, then run on the simulator.

## Local dev

1. Start infra: `docker compose up -d` (from repo root)
2. Backend: `http://127.0.0.1:8000` — see [`backend/README.md`](../backend/README.md)
3. Keycloak: `http://127.0.0.1:9001` — client `dishify-ios`, redirect `dishify://callback`

## Mock vs real API

In `Dishify/Services/APIClient.swift`:

- `useMock = true` — Day 1 (offline UI dev)
- `useMock = false` — Day 2 (after backend merge)

See [`docs/INTEGRATION.md`](../docs/INTEGRATION.md) for the merge checklist.

## API contract

[`docs/API.md`](../docs/API.md)
