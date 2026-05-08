#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
DIST="$DIR/dist"

echo "==> 빌드 시작: gcp_result_ingest"
rm -rf "$DIST" && mkdir -p "$DIST/package"

pip install -r "$DIR/requirements.txt" -t "$DIST/package" -q
cp "$DIR/handler.py" "$DIST/package/"

cd "$DIST/package"
zip -r "$DIST/gcp_result_ingest.zip" . -q

echo "==> 완료: $DIST/gcp_result_ingest.zip ($(du -sh "$DIST/gcp_result_ingest.zip" | cut -f1))"
