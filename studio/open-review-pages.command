#!/bin/sh
# Explainer Studio: the review page and the editing page (http://localhost:8770), for macOS and Linux.
# macOS: double-click in Finder. Linux: run `sh open-review-pages.command`. Optional: a port as the first argument.
# Keep the window open while you review, close it when you are done.
STUDIO="$(cd "$(dirname "$0")" && pwd)"
PORT="${1:-8770}"
PY="$STUDIO/.venv/bin/python"
export PYTHONIOENCODING=utf-8

stop() {
  echo
  echo "The pages have stopped. If there is an error above, copy it to Claude. Press Enter to close."
  read -r _
  exit "${1:-0}"
}

[ -f "$STUDIO/scripts/gs_review.py" ] || { echo "This file must sit in the studio folder, next to scripts/ and studio.toml."; stop 1; }
"$PY" -c "import sys" >/dev/null 2>&1 || { echo "The studio's Python (.venv) was not found: ask Claude to run setup (install core)."; stop 1; }

cd "$STUDIO/scripts" || stop 1
if [ -z "$STUDIO_NO_BROWSER" ]; then
  ( sleep 4
    if command -v open >/dev/null 2>&1; then open "http://localhost:$PORT"
    elif command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:$PORT"
    fi ) >/dev/null 2>&1 &
fi
"$PY" gs_review.py "$PORT"
stop
