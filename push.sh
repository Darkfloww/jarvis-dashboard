#!/bin/bash
# JARVIS daily push — collect.py (vault + ActivityWatch) then whoop_collect.py (physiology),
# then push data.json to GitHub and redeploy.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# launchd starts with a bare PATH — without this, git/vercel/node are simply not found.
# vercel lives under nvm, whose version directory changes on every node upgrade, so resolve
# the newest one at runtime instead of hardcoding a path that will silently rot.
NVM_BIN="$(ls -d "$HOME"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -1)"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${NVM_BIN:-}:$HOME/Library/Python/3.9/bin:$PATH"

echo "=== JARVIS DAILY PUSH $(date) ==="

# 1. Declared data + Mac activity. Non-fatal: the vault may be unreadable under launchd.
python3 collect.py || echo "⚠️  collect.py failed — continuing"

# 2. Objective physiology from WHOOP. Non-fatal: the API may be unreachable.
python3 whoop_collect.py || echo "⚠️  whoop_collect.py failed — continuing"

# 3. Git add + commit + push
git add data.json
if git diff --staged --quiet; then
  echo "No changes to commit."
  exit 0
fi

git commit -m "data: daily update $(date +%Y-%m-%d)"
git push origin main

# 4. Redeploy on Vercel. The `deploy` subcommand is required — `vercel --prod` only prints help.
vercel deploy --prod --yes

echo "=== Done. Dashboard updated. ==="
