# PanelScan Agent

**Agentic visual inspection with OpenCV 5** — an inspection loop where what the camera
sees changes what the camera does next.

> Submission skeleton for **OpenCV AI Competition 2026, powered by AWS**
> (deadline 2026-10-26 23:45 PDT / 2026-10-27 15:45 JST).

---

## The problem

Manual visual inspection of small production runs (PCB panels, machined parts, 3D-printed
assemblies) is slow and inconsistent. Fixed-camera inspection rigs work only when the part
is perfectly staged: one bad exposure, one refocus, one tilted fixture and the whole batch
either fails or — worse — quietly passes.

Commercial machine-vision suites solve this by closing the loop: *measure the image quality
first, then move the sensor.* That logic usually lives in proprietary hardware drivers.

## What this project does

`PanelScan Agent` implements that loop with nothing but OpenCV 5 on the perception side:

1. **Register** — four ArUco fiducials give a homography; the capture is rectified into
   canonical panel coordinates, so the inspector is invariant to how the part was staged.
2. **Verify parts where they belong** — each expected screw and label is scored by
   normalised cross-correlation against the clean board inside its own neighbourhood
   (brightness/contrast invariant, so an exposure change is not mistaken for a defect).
3. **Find free-form defects** — the remaining interior is differenced against the reference
   and thresholded with Otsu, then classified by shape into scratch / solder blob.
4. **Act on the evidence** — if fiducials are missing, the image is dark, out of focus, or a
   detection is unconvident, the agent does not report: it repositions, raises exposure,
   refocuses, or re-captures at higher quality, then re-measures. The decision trace is
   returned with the verdict.

The agent is not a chatbot on top of a vision result. The visual evidence changes the next
sensor action — which is the qualifier for the *Agentic Vision* focus path.

## Code repository

Public source, MIT licensed:

**https://github.com/maebahesioru/panelscan-agent**

Every number in this README and in `docs/REPORT.md` is reproducible from that tree:
the synthetic bench is generated at runtime, the evaluation harness writes
`results/eval.json`, and the evidence images are committed. `git log` starts at the
submission commit; there is no hidden branch and no uncommitted work.

Demo video (4:20, unlisted YouTube upload of `docs/demo_video.mp4`):
**https://www.youtube.com/watch?v=IoTRT7jfG5M**

## Quick start

Judge-runnable path: the commands below are exactly what `make install`, `make probe`,
`make test`, `make eval` and `make video` run (see `Makefile`), on CPU only, with no
credentials and no network model downloads.

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# one scene, annotated evidence image
.venv/bin/python src/probe.py

# smoke tests
.venv/bin/python -m pytest -q

# full evaluation (writes results/eval.json + results/EVAL_SUMMARY.md)
.venv/bin/python src/eval_harness.py --scenes 80

# HTTP service
.venv/bin/python -m uvicorn src.service:app --host 0.0.0.0 --port 8080
curl -s localhost:8080/healthz
curl -s -X POST "localhost:8080/inspect/scene/1000" | jq .
```

## Repository layout

```
src/scene_sim.py      deterministic synthetic bench + ground truth (evaluation fixture)
src/perception.py     OpenCV 5 stage: ArUco, homography, NCC part check, Otsu diff
src/agent.py          perceive -> decide -> act loop, evidence merge, decision trace
src/service.py        FastAPI endpoints (/inspect, /inspect/scene/{seed}, /metrics)
src/eval_harness.py   agentic vs single-shot baseline, per-defect-type P/R/F1
src/probe.py          quick sanity run that writes annotated images
tests/test_pipeline.py smoke tests
results/              measured output (committed on purpose: this is the evidence)
docs/                 technical report, architecture, checklist, video source + demo_video.mp4
deploy/               Graviton container build, ECS task definition, ECR push script
evidence/             annotated scene frames + the captured competition rules (primary source)
```

## Measured result (40 normal + 40 degraded scenes, `make eval`)

| setting | precision | recall | F1 |
|---|---|---|---|
| single-shot baseline, degraded | 0.976 | 0.494 | 0.656 |
| **agentic loop, degraded** | 0.920 | **0.976** | **0.947** |
| agentic loop, normal | 0.975 | 0.952 | 0.963 |

The loop trades 3.0× latency (72.1 → 218.5 ms p50) and 0.056 precision for +0.482 recall on frames
a single shot cannot read. Per-defect breakdown and the failure cases live in `docs/REPORT.md` §4–5.

## Demo video

`docs/demo_video.mp4` — 4:20, 1280x720, 30 fps, H.264, silent with burned-in subtitles.
Every frame is a picture of a file this repository produced (the recorded terminal output, the
evaluation, the annotated evidence images), so the video cannot drift away from the numbers.
Rebuild it with `make evidence && bash docs/record_terminal.sh && make video`.

## Status — read this before judging the AWS criterion

| Requirement | State |
|---|---|
| Technical report | `docs/REPORT.md` |
| Code repository | public: https://github.com/maebahesioru/panelscan-agent (MIT) |
| Pinned deps + build/deploy/test instructions | `requirements.txt`, `Makefile`, `deploy/` |
| Architecture diagram | `docs/ARCHITECTURE.md` |
| Working endpoint **or** live demo | local endpoint verified; AWS deployment **prepared but not executed** (see below) |
| ≤5 min video | https://www.youtube.com/watch?v=IoTRT7jfG5M (4:20, unlisted); source `docs/demo_video.mp4` |
| Evaluation with failure cases | `results/EVAL_SUMMARY.md` |

**AWS is not deployed.** The container and task definition are written and the
image builds for `linux/arm64`, but this entry has **no AWS account attached**: no AWS
credentials were used and no claim of a running AWS deployment is made anywhere in this
report. The "Cloud delivery" rubric weight is therefore partly unmet, and the *Best Use of
COOL* award is **not** claimed (COOL was never executed).

Local measurement, not cloud measurement: all numbers in `docs/REPORT.md` come from the
CPU-only run recorded in `results/eval.json` on the machine named in that file's metadata.

## Licence

Code: MIT (see `LICENSE`). The synthetic bench is generated at runtime; no third-party
imagery is redistributed.
