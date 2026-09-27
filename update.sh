#!/bin/zsh
# Rebuild the index from the music share and push it to GitHub if it changed.
set -euo pipefail
cd "$(dirname "$0")"

ROOT=$(python3 -c 'import json;print(json.load(open("config.json"))["root"])')
if [[ ! -d "$ROOT" ]]; then
  echo "error: music share is not mounted at: $ROOT" >&2
  exit 2
fi

python3 scan.py

if [[ -z "$(git status --porcelain docs/index.json)" ]]; then
  echo "index unchanged, nothing to push"
  exit 0
fi

COUNT=$(python3 -c 'import json;print(json.load(open("docs/index.json"))["count"])')
git add docs/index.json
git commit -m "Update index: $COUNT entries"
git push
echo "pushed index with $COUNT entries"
