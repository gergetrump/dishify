#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SIMULATOR="${DISHIFY_SIMULATOR:-iPhone 17 Pro}"
DERIVED_DATA="${ROOT}/build/DerivedData"

echo "==> Unit tests (Debug)"
xcodebuild -scheme Dishify \
  -destination "platform=iOS Simulator,name=${SIMULATOR}" \
  -configuration Debug \
  -derivedDataPath "$DERIVED_DATA" \
  test

echo "==> Release archive (generic iOS, no signing)"
xcodebuild -scheme Dishify \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -derivedDataPath "$DERIVED_DATA" \
  -archivePath "$ROOT/build/Dishify-Release.xcarchive" \
  CODE_SIGNING_ALLOWED=NO \
  archive

echo "==> Staging build (generic iOS, no signing)"
xcodebuild -scheme Dishify \
  -configuration Staging \
  -destination 'generic/platform=iOS' \
  -derivedDataPath "$DERIVED_DATA" \
  CODE_SIGNING_ALLOWED=NO \
  build

if [[ -n "${DISHIFY_API_BASE_URL:-}" ]]; then
  echo "==> Auth config smoke check (${DISHIFY_API_BASE_URL})"
  AUTH_JSON="$(curl -fsS "${DISHIFY_API_BASE_URL%/}/auth/config")"
  python3 -c '
import json, os, sys
config = json.loads(sys.argv[1])
for key in ("authorization_endpoint", "token_endpoint"):
    url = config.get(key, "")
    print(f"{key}: {url}")
    if os.environ.get("DISHIFY_EXPECT_PUBLIC_AUTH") == "1" and ("keycloak:" in url or "localhost" in url):
        print(f"WARNING: {key} may be unreachable from a physical device.", file=sys.stderr)
        sys.exit(1)
' "$AUTH_JSON"
fi

echo "Release validation complete."
