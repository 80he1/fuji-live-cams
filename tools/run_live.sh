#!/usr/bin/env bash
# One cycle, called by live_loop.sh every 30 min (10 min 05:00-07:59 JST). check_live.py itself runs at most
# ~hourly (LIVE_MIN_GAP) on a rolling, budgeted subset and merges into live.json; xtnow runs every cycle.
set -e
# Log to live_loop.log ourselves: the loop's inherited stdout stopped reaching the file on 10/19 (lost writes).
exec >> /workspace/fuji-pages/tools/live_loop.log 2>&1
echo "== $(date '+%F %T %Z') cycle"
cd /workspace/fuji-pages
git pull -q --rebase --autostash || true
python3 tools/check_live.py camidx.json live.json || echo "live check rc=$? (block/back-off: live.json untouched)"
git add live.json
git diff --cached --quiet || { git -c user.name=80he1 -c user.email=80he1@users.noreply.github.com commit -qm "live.json auto-update" && git push -q; echo pushed; }
# World extremes snapshot for the home screen (fallback when Open-Meteo blocks/rate-limits phones). Never touches live.json.
if timeout 600 python3 tools/xt_box.py /workspace/fuji-pages; then
  git pull -q --rebase --autostash || true
  git add xtnow.json && { git diff --cached --quiet || { git -c user.name=80he1 -c user.email=80he1@users.noreply.github.com commit -qm "xtnow.json auto-update" && git push -q; echo xt-pushed; }; }
fi
# Discovery runs only in tools/disco_bg.sh (low rate); here we just commit the catalog it wrote. Never touches live.json.
git pull -q --rebase --autostash || true
git add catalog.json 2>/dev/null && { git diff --cached --quiet || { git -c user.name=80he1 -c user.email=80he1@users.noreply.github.com commit -qm "catalog.json auto-update" && git push -q; echo cat-pushed; }; }
