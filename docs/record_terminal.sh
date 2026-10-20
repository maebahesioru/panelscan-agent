#!/usr/bin/env bash
# Records the terminal transcript used by the demo video.
#
# Nothing in docs/video_src/terminal.txt is typed by hand: each block below is a real
# command run on this machine, with its real stdout/stderr. docs/make_video_slides.py
# renders that file into 1280x720 frames, so the video shows measured numbers only.
#
# Run: bash docs/record_terminal.sh
set -u
cd "$(dirname "$0")/.."

PY=.venv/bin/python
OUT=docs/video_src/terminal.txt
: > "$OUT"

section() { printf '\n### %s\n' "$1" >> "$OUT"; }
show()    { printf '$ %s\n' "$1" >> "$OUT"; }

section "OpenCV build actually in use"
show ".venv/bin/python src/probe.py"
$PY src/probe.py 2>&1 | tee -a "$OUT"

section "tests"
show ".venv/bin/python -m pytest -q"
$PY -m pytest -q 2>&1 | tee -a "$OUT"

section "evaluation — 40 normal + 40 degraded scenes, one command"
show ".venv/bin/python src/eval_harness.py --scenes 80"
$PY src/eval_harness.py --scenes 80 2>&1 | tail -1 | tee -a "$OUT"
show ".venv/bin/python docs/show_metrics.py"
$PY docs/show_metrics.py 2>&1 | tee -a "$OUT"

# the HTTP service must be up for the next block
if ! curl -sf --max-time 3 http://127.0.0.1:8080/healthz > /dev/null; then
    nohup $PY -m uvicorn src.service:app --host 127.0.0.1 --port 8080 > docs/video_src/server.log 2>&1 &
    sleep 8
fi

section "live endpoint — the same loop over HTTP (local, not AWS)"
show "curl -s http://127.0.0.1:8080/healthz"
curl -s --max-time 20 http://127.0.0.1:8080/healthz | tee -a "$OUT"; echo >> "$OUT"
show "curl -s -X POST 'http://127.0.0.1:8080/inspect/scene/2002?hard=true' -o /tmp/panelscan_2002.json"
curl -s --max-time 60 -X POST "http://127.0.0.1:8080/inspect/scene/2002?hard=true" -o /tmp/panelscan_2002.json
show ".venv/bin/python docs/show_trace.py /tmp/panelscan_2002.json"
$PY docs/show_trace.py /tmp/panelscan_2002.json 2>&1 | tee -a "$OUT"

section "counters"
show "curl -s http://127.0.0.1:8080/metrics"
curl -s --max-time 20 http://127.0.0.1:8080/metrics | tee -a "$OUT"; echo >> "$OUT"

echo "wrote $OUT"
