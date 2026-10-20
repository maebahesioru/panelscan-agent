# PanelScan Agent — an adaptive-vision inspection loop on OpenCV 5

**OpenCV AI Competition 2026 · Technical report**

Team: 大肥魚 (sole entrant) · Contact: (submission e-mail) · Licence: MIT (code) / CC-BY 4.0 (this report)
Repository: `<repo URL>` · Video: `<YouTube URL>` · Report version: 2026-10-20

---

## 1. Problem

Visual inspection of a small assembly (a mounting panel with four screws, a reference
label and a printed legend) is a solved problem *while the sensor is healthy*. It stops
being solved the moment the camera is not: a dark shop floor, a dirty lens, vibration,
an aggressive JPEG pipeline. A fixed, single-shot inspection pipeline then does the worst
possible thing — it reports "no defects" with high confidence, because nothing it looks
for is above threshold any more.

The competition's published prize pool is **up to $12,000 cash** (Rules §Prizes: 1st $5,000,
2nd $3,000, 3rd $2,000, Best Use of COOL $1,000, Agentic Vision $1,000); the $20,250 figure on
the listing page is not the cash pool. Deadline: `2026-10-27T02:45:00-04:00` (rules text:
Oct 26, 2026 @ 11:45pm PDT) = 2026-10-27 15:45 JST.

The competition asks for OpenCV 5 to sit inside an agentic loop: perception must be able
to change what the sensor does next. PanelScan Agent is that loop, built around one
question: *can a small, explainable decision policy recover inspection accuracy on frames
a single-shot pipeline cannot read?*

## 2. What the system does

One inspection pass is a closed loop of four moves:

```
capture ──► perceive ──► decide ──► act on the sensor ──┐
   ▲                                                    │
   └────────────────── (bounded: max 5 steps) ◄──────────┘
```

* **perceive** (`src/perception.py`, 283 lines) — ArUco marker detection → homography →
  rectify the panel into canonical coordinates → per-region checks:
  * `missing_screw`: 4 screw positions; a screw region that does not correlate with the
    reference template (NCC < 0.55) is missing;
  * `misaligned_label`: NCC of the label patch against the reference;
  * `scratch` / `blob`: threshold the interior residual against the rectified reference
    (Otsu) and classify each blob by aspect ratio, area and peak residual.
* **decide** (`src/agent.py::_decide`) — a readable priority ladder, exposure first:
  `luma < 34 → raise_exposure`, `luma > 245 → lower_exposure`,
  `< 4 fiducials → reposition`, `Laplacian variance < 140 → refocus`,
  `weak detections → cleanup_capture`, otherwise `accept`.
* **act** (`src/agent.py::_act`) — the action is applied to the simulated camera:
  exposure ×1.3/0.8, blur σ ×0.3, yaw/pitch ×0.6.
* **merge** — evidence from every step is merged by IoU, and a defect is reported when a
  single view is confident (≥ 0.62) **or** two independent views saw it. This cross-view
  agreement is what keeps recall high without letting a single noisy frame invent defects.

The trace (`steps[]` in every API response, with a human-readable `reason` for each move)
is a first-class output: a judge or an operator can read *why* the camera moved, not just
what it concluded.

## 3. OpenCV 5 usage

OpenCV **5.0.0** is used throughout, and the pipeline is written against the 5.x API
(`cv2.aruco` marker detection, `cv2.findHomography`, `cv2.matchTemplate`,
`cv2.threshold(..., cv2.THRESH_OTSU)`, `cv2.Laplacian`, `cv2.connectedComponentsWithStats`).
`src/probe.py` asserts version 5 at start-up and reports the exact build in `/healthz`
(measured: `{"ok": true, "opencv": "5.0.0", "numpy": "2.5.4", "arch": "x86_64"}`).

## 4. Results

All numbers below are produced by `make eval` (`src/eval_harness.py`), 40 normal scenes
(seed 1000–1039) and 40 deliberately degraded scenes (seed 2000–2039). Over those 40
degraded seeds the generator actually draws: exposure ×0.553–0.800, Gaussian blur
σ 0.86–2.13, additive sensor noise σ 6.3–11.9, JPEG quality fixed at 58, and a ±6°
staging yaw/pitch error. Every scene carries exact ground truth.

A prediction counts as a detection when it has the same defect type and its centroid lies
within 46 px of the ground-truth centroid, matched greedily one-to-one (`MATCH_PX` in
`src/eval_harness.py`) — not IoU, because a scratch and a blob of the same area overlap
poorly even when both are correct.

| setting | precision | recall | F1 | tp / fp / fn | latency p50 / p95 (ms) | steps/scene |
|---|---|---|---|---|---|---|
| single-shot baseline, degraded scenes | **0.976** | 0.494 | 0.656 | 41 / 1 / 42 | 72.1 / 124.3 | 1.00 |
| **agentic loop, degraded scenes** | 0.920 | **0.976** | **0.947** | 81 / 7 / 2 | 218.5 / 476.6 | 2.90 |
| agentic loop, normal scenes | 0.975 | 0.952 | 0.963 | 79 / 2 / 4 | 67.5 / 135.2 | 1.32 |

Quality numbers are deterministic (the scenes are seeded); latency is wall-clock on the
development CPU (Ryzen 5 5500, 12 threads) and moves a few percent between runs, so the
latencies quoted here are the ones in the committed `results/EVAL_SUMMARY.md`.

The head-line result is the degraded-scene comparison, because it isolates the loop:
**recall 0.494 → 0.976** (+0.482 absolute, ×1.98), F1 0.656 → 0.947, for a median latency
of 219 ms instead of 72 ms. The loop costs 3.0× median latency and 0.056 precision (7 false
scratches on 40 scenes) and buys back half of the missing detections.

Per defect type, degraded scenes:

| defect | baseline P / R / F1 | agentic P / R / F1 |
|---|---|---|
| missing_screw (31) | 1.00 / 0.37 / 0.54 | 1.00 / 1.00 / 1.00 |
| scratch (25) | 0.93 / 0.68 / 0.79 | 0.73 / 1.00 / 0.84 |
| blob (20) | 1.00 / 0.45 / 0.62 | 1.00 / 0.90 / 0.95 |
| misaligned_label (25) | 1.00 / 0.48 / 0.65 | 1.00 / 1.00 / 1.00 |

On normal scenes the remaining misses are 4 `blob` detections (F1 0.87 for that class):
a blob that is small and low-contrast against the legend printing falls under the Otsu
residual floor and no sensing action can invent it, because the frame is already sharp.

## 5. Decision traces and failure cases we keep in the repository

Every trace and frame below is regenerated from the shipped code by
`.venv/bin/python src/make_evidence.py`, which writes `evidence/scene_<seed>.png`
(ground truth yellow, merged prediction red), the matching raw
`evidence/scene_<seed>_input.png`, and `docs/video_src/scene_traces.txt`. The numbers are
that file's, not a retelling.

* **`evidence/scene_2002.png`** — the first frame has mean luma 28.5 and 1 of 4 fiducials.
  The loop raises exposure instead of reporting a clean panel, and accepts 3/3 at step 2
  (`misaligned_label 0.99`, `scratch 0.97`, `missing_screw 0.96`).
* **`evidence/scene_2011.png`** — luma 26.7 with 2 of 4 fiducials → `raise_exposure`, then
  Laplacian variance 70.9 → `refocus`; 3/3 at step 3 with no false positives.
* **`evidence/scene_2005.png`** — the exposure fix alone is not enough: luma 30.4 →
  `raise_exposure`, then variance 127.9 → `refocus`, and the single blob only becomes
  detectable in the sharp view (1/1 in 3 steps).
* **`evidence/scene_2000.png`** — the counter-example that keeps the ladder honest: the
  frame is already bright (luma 35.7, above the 34 floor) and merely soft (variance 81.4),
  so the first move is `refocus`, not an exposure change, and the blob is found in 2 steps.
* **Known weakness:** merged multi-view evidence raises false `scratch` detections
  (precision 0.920 vs 0.976). Two views occasionally see the same JPEG ringing as two
  different thin structures. The fix we did **not** ship in time is a geometric consistency
  check across views (a real scratch rectifies to the same canonical line); it is listed as
  the next step rather than claimed as done.

Award target: this entry is written for the **Agentic Vision Award ($1,000)** as well as the
overall ranking — its rubric (substantive OpenCV 5 + agent integration 30%, orchestration and
appropriate autonomy 25%, task effectiveness and evaluation 20%, failure handling and human
control 15%, documentation and demonstration 10%) is what §2, §4 and §5 answer directly.

## 6. Architecture and AWS deployment

`docs/ARCHITECTURE.md` carries the diagram and the request path. The service is FastAPI
(`src/service.py`, 103 lines) exposing `/healthz`, `/inspect/scene/{seed}`,
`/inspect/upload`, `/annotated/{seed}.jpg`, `/metrics`. Deployment is written and the
container builds for `linux/arm64`; **it has not been deployed to AWS in this entry**,
because no AWS account is attached to this submission. The rubric prices that at 10% of the
score ("Cloud delivery, reproducibility, and responsible operation"), so the entry is
submitted as a 90-point-maximum entry rather than pretending the deployment happened. What exists is:

* `deploy/Dockerfile` — headless OpenCV 5, non-root user, healthcheck, 2 threads;
* `deploy/ecs-taskdef.json` — Fargate task, ARM64 (Graviton), 1 vCPU / 2 GiB, CloudWatch
  logs, read-only root filesystem;
* `deploy/build_and_push.sh` — buildx arm64 build and ECR push;
* `docs/ARCHITECTURE.md` §4 — the ECS/ALB/CloudWatch path and the cost estimate.

Claiming a live endpoint we do not have would be worse than shipping a documented gap.

## 7. Honest scope statement

* Data is **synthetic** (`src/scene_sim.py` renders the panel, reference and defects), so
  the numbers measure the pipeline's behaviour under controlled degradation, not factory
  performance. No customer, no site, no real part was involved.
* The system is **advisory**: it produces a verdict and evidence frames for a human
  inspector. It does not drive machinery and asserts no safety-critical authority.
* Responsible use: no personal data is processed, no images of people are acquired, and
  the model-free pipeline means no training data licensing questions arise.
* Limitation to state in the video: single-panel, single-lighting-condition, top-down
  camera; the homography step assumes four visible fiducials.

## 8. Reproducing

```bash
make install      # uv venv + pip install -r requirements.txt (opencv-python-headless 5.0.0.93)
make probe        # prints the OpenCV build actually in use
make test         # 5 pytest cases
make eval         # 80-scene evaluation -> results/eval.json + results/EVAL_SUMMARY.md
make evidence     # regenerates the annotated frames + traces quoted in §5
make serve        # http://127.0.0.1:8080  (see /healthz, /metrics)
make video        # rebuilds docs/demo_video.mp4 from the recorded material
```

## 9. Repository map

| path | lines | role |
|---|---|---|
| `src/scene_sim.py` | 188 | synthetic bench: panel, reference, defects, degradation |
| `src/perception.py` | 283 | ArUco + homography + per-defect checks + annotation |
| `src/agent.py` | 144 | decision ladder, sensor actions, evidence merge, trace |
| `src/eval_harness.py` | 166 | 80-scene benchmark, per-type P/R/F1, latency, failure dumps |
| `src/service.py` | 103 | FastAPI surface used by the container |
| `src/probe.py` | 41 | OpenCV 5 version assertion |
| `src/make_evidence.py` | 89 | regenerates the §5 frames and the per-scene traces |
| `tests/test_pipeline.py` | 61 | five behaviour tests (`make test`) |
| `deploy/` | — | Dockerfile, ECS task definition, ECR build script |
| `docs/` | — | report, architecture, checklist, video script, `demo_video.mp4` |
| `docs/record_terminal.sh` | 46 | records the real terminal transcript the video renders |
| `docs/make_video_slides.py` | — | renders the video frames (terminal, results, architecture) |
| `docs/make_video.sh` | — | ffmpeg assembly: segments, fades, `drawtext` telops, concat |
| `evidence/` | — | annotated + raw scene frames, captured competition rules |
