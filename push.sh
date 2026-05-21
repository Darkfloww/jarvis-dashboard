#!/bin/bash
# JARVIS daily push — runs collect.py then pushes data.json to GitHub
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== JARVIS DAILY PUSH $(date) ==="

# 1. Collect data
python3 collect.py

# 2. Git add + commit + push
git add data.json
if git diff --staged --quiet; then
  echo "No changes to commit."
  exit 0
fi

git commit -m "data: daily update $(date +%Y-%m-%d)"
git push origin main

echo "=== Done. Dashboard updated. ==="
