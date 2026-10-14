#!/usr/bin/env bash
# One check: refresh live.json and push if changed. Run every 30 min (every 10 min 05:00-07:59 JST).
set -e
cd /workspace/fuji-pages
git pull -q --rebase || true
python3 tools/check_live.py camidx.json live.json
git add live.json
git diff --cached --quiet || { git -c user.name=80he1 -c user.email=80he1@users.noreply.github.com commit -qm "live.json auto-update" && git push -q; echo pushed; }
