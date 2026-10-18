#!/usr/bin/env bash
# Background discovery booster on the box: runs tools/disco.py between live_loop cycles.
# Writes catalog.json into the pages working tree only (no git); run_live.sh commits it next cycle.
# disco.py holds a lock (skips if the loop's own run is active) and honours its 2h YouTube back-off.
cd /workspace/fuji-pages
while true; do
  echo "== $(date '+%F %T %Z') bg run"
  DISCO_P=${DISCO_P:-45} DISCO_Q=${DISCO_Q:-4} DISCO_CH=${DISCO_CH:-8} timeout 720 python3 tools/disco.py catalog.json || echo "bg run failed"
  sleep $(( 1200 + RANDOM % 300 ))
done
