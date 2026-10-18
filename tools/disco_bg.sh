#!/usr/bin/env bash
# The ONLY discovery path (live_loop no longer runs disco). Low pressure: every 60-90 min, ~15 videos/run,
# 5-12 s jittered pauses. disco.py skips when a live check is running/ran <10 min ago, or a YouTube block was seen <3h ago
# (shared guard /workspace/disco/yt_guard.json). Writes catalog.json only; run_live.sh commits it.
cd /workspace/fuji-pages
while true; do
  echo "== $(date '+%F %T %Z') bg run"
  DISCO_P=${DISCO_P:-15} DISCO_Q=${DISCO_Q:-2} DISCO_CH=${DISCO_CH:-4} DISCO_BUDGET=${DISCO_BUDGET:-600} timeout 900 python3 tools/disco.py catalog.json || echo "bg run failed"
  sleep $(( 3600 + RANDOM % 1800 ))
done
