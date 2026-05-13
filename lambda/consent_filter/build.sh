#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
DIST="$DIR/dist"

echo "==> 빌드 시작: consent_filter"
rm -rf "$DIST" && mkdir -p "$DIST/package"

pip install -r "$DIR/requirements.txt" -t "$DIST/package" -q
cp "$DIR/handler.py" "$DIST/package/"

cd "$DIST/package"
zip -r "$DIST/consent_filter.zip" . -q

echo "==> 완료: $DIST/consent_filter.zip ($(du -sh "$DIST/consent_filter.zip" | cut -f1))"
