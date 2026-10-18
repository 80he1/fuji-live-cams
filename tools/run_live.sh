#!/usr/bin/env bash
# One check: refresh live.json and push if changed. Run every 30 min (every 10 min 05:00-07:59 JST).
set -e
cd /workspace/fuji-pages
git pull -q --rebase || true
python3 tools/check_live.py camidx.json live.json
git add live.json
git diff --cached --quiet || { git -c user.name=80he1 -c user.email=80he1@users.noreply.github.com commit -qm "live.json auto-update" && git push -q; echo pushed; }
# World extremes snapshot for the home screen (fallback when Open-Meteo blocks/rate-limits phones). Never touches live.json.
if timeout 600 python3 tools/xt_box.py /workspace/fuji-pages; then
  git pull -q --rebase --autostash || true
  git add xtnow.json && { git diff --cached --quiet || { git -c user.name=80he1 -c user.email=80he1@users.noreply.github.com commit -qm "xtnow.json auto-update" && git push -q; echo xt-pushed; }; }
fi
# Mass discovery of YouTube live cams -> catalog.json (lazy-loaded search catalog). Paced, resumable (state in /workspace/disco), backs off on 429/bot-check. Never touches live.json.
if timeout 720 python3 tools/disco.py catalog.json; then
  git pull -q --rebase --autostash || true
  git add catalog.json && { git diff --cached --quiet || { git -c user.name=80he1 -c user.email=80he1@users.noreply.github.com commit -qm "catalog.json auto-update" && git push -q; echo cat-pushed; }; }
fi
