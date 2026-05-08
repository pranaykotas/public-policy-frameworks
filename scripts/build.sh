#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo "==> Checking framework pages..."
python scripts/check-frameworks.py

echo "==> Rebuilding frameworks.json..."
python scripts/build-finder-index.py

echo "==> Rendering site..."
quarto render

echo "==> Done."
