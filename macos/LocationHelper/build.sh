#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$ROOT/../.." && pwd)
APP="$REPO/src/qiantong/_macos/LocationHelper.app"
TMP="${TMPDIR:-/tmp}/qiantong-location-helper.$$"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP"
mkdir -p "$APP/Contents/MacOS"
swiftc -O -target arm64-apple-macosx11.0 -framework CoreLocation -framework Foundation "$ROOT/main.swift" -o "$TMP/LocationHelper-arm64"
swiftc -O -target x86_64-apple-macosx10.15 -framework CoreLocation -framework Foundation "$ROOT/main.swift" -o "$TMP/LocationHelper-x86_64"
lipo -create "$TMP/LocationHelper-arm64" "$TMP/LocationHelper-x86_64" -output "$APP/Contents/MacOS/LocationHelper"
cp "$ROOT/Info.plist" "$APP/Contents/Info.plist"
codesign --force --deep --sign - "$APP" >/dev/null
echo "Built $APP"
