#!/usr/bin/env bash
# Interim loop on the box: every 30 min, every 10 min during 05-08 JST.
while true; do
  date; bash /workspace/fuji-pages/tools/run_live.sh || echo "check failed"
  h=$(TZ=Asia/Tokyo date +%H); if [ "$h" -ge 5 ] && [ "$h" -lt 8 ]; then sleep 600; else sleep 1800; fi
done
