#!/usr/bin/env bash
# Builds the CareerOS release APK (direct download) and AAB (Play Store) against a live API.
#
#   tool/build_release.sh https://careeros-api.onrender.com/api/v1
#
# Signing: uses android/key.properties when present, otherwise Gradle falls back to the debug key
# and the build is NOT publishable — the script says so rather than letting it pass unnoticed.
set -euo pipefail

API_BASE_URL="${1:-}"
if [[ -z "$API_BASE_URL" ]]; then
  echo "usage: tool/build_release.sh <API base URL, e.g. https://careeros-api.onrender.com/api/v1>" >&2
  exit 2
fi
if [[ "$API_BASE_URL" != https://* ]]; then
  echo "refusing to build against a non-HTTPS API URL: $API_BASE_URL" >&2
  exit 2
fi

cd "$(dirname "$0")/.."

if [[ ! -f android/key.properties ]]; then
  echo "WARNING: android/key.properties not found — this build will be signed with the debug key."
  echo "         Fine for a private test link; Play Console will reject it."
  echo "         See docs/launch/RENDER_LAUNCH.md step 4."
fi

DEFINES=(--dart-define=API_BASE_URL="$API_BASE_URL" --dart-define=ENVIRONMENT=production)

# `flutter` on PATH, or FLUTTER (e.g. C:/flutter/bin/flutter.bat on Windows without PATH set).
FLUTTER="${FLUTTER:-flutter}"

"$FLUTTER" build apk --release "${DEFINES[@]}"
"$FLUTTER" build appbundle --release "${DEFINES[@]}"

echo
echo "APK: $(pwd)/build/app/outputs/flutter-apk/app-release.apk"
echo "AAB: $(pwd)/build/app/outputs/bundle/release/app-release.aab"
