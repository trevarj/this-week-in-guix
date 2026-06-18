#!/usr/bin/env bash
# Build and serve the This Week in Guix site locally.
#
# The site hardcodes a /this-week-in-guix/ URL prefix (its GitHub Pages
# subpath), so we serve _site under that prefix via a symlinked root — this
# matches production exactly, including asset and favicon links.
#
# Usage: scripts/serve.sh [port]   (default port 8000)

set -euo pipefail

PORT="${1:-8000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVE_ROOT="${TWIG_SERVE_ROOT:-/tmp/twig-serve}"

echo ">> Building site"
guix shell -m "$ROOT/manifest.scm" -- \
  python3 "$ROOT/scripts/render.py" --out "$ROOT/_site"

echo ">> Mounting under /this-week-in-guix/ at $SERVE_ROOT"
rm -rf "$SERVE_ROOT"
mkdir -p "$SERVE_ROOT"
ln -s "$ROOT/_site" "$SERVE_ROOT/this-week-in-guix"

echo ">> Serving on http://127.0.0.1:$PORT/this-week-in-guix/"
echo "   (press Ctrl-C to stop)"
exec guix shell -m "$ROOT/manifest.scm" -- \
  python3 -m http.server -d "$SERVE_ROOT" "$PORT"