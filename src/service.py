"""HTTP service exposing the inspection loop.

Endpoints
  GET  /healthz                     liveness + build info
  POST /inspect                     multipart PNG/JPEG  -> verdict + decision trace
  POST /inspect/scene/{seed}        synthetic bench scene -> verdict (demo / QA)
  GET  /annotated/{seed}.jpg        annotated evidence image for a bench scene
  GET  /metrics                     trivial counters (requests, defects, p50 latency)

Everything runs on CPU inside a single container; the same image is built for
linux/amd64 (developer laptop) and linux/arm64 (AWS Graviton).
"""

from __future__ import annotations

import io
import statistics
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response

import sys
sys.path.insert(0, str(Path(__file__).parent))

from agent import run_agent
from perception import annotate, perceive
from scene_sim import make_scene, render_canonical

app = FastAPI(title="PanelScan Agent", version="0.1.0")
REFERENCE = render_canonical(reference=True)
COUNTERS = {"requests": 0, "defects": 0, "latencies": []}


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "opencv": cv2.__version__, "numpy": np.__version__,
            "arch": __import__("platform").machine(), "service": "panelscan-agent", "version": "0.1.0"}


def _decode(raw: bytes) -> np.ndarray:
    buf = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="image could not be decoded")
    return img


@app.post("/inspect")
async def inspect(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="image larger than 12 MiB")
    frame = _decode(raw)
    t0 = time.perf_counter()
    p = perceive(frame, REFERENCE)
    dt = (time.perf_counter() - t0) * 1000.0
    verdict = {
        "registered": p.registered,
        "markers": p.markers,
        "sharpness": round(p.sharpness, 1),
        "brightness": round(p.brightness, 1),
        "defects": [d.as_dict() for d in p.defects],
        "pass": p.registered and not p.defects,
        "latency_ms": round(dt, 2),
        "action": "accept" if (p.registered and p.defects and all(d.confidence >= 0.62 for d in p.defects)) else
                  ("reject_retake" if not p.registered else "review"),
    }
    COUNTERS["requests"] += 1
    COUNTERS["defects"] += len(p.defects)
    COUNTERS["latencies"].append(dt)
    return verdict


@app.post("/inspect/scene/{seed}")
def inspect_scene(seed: int, hard: bool = False) -> dict:
    scene = make_scene(seed=seed, hard=hard)
    report = run_agent(scene, REFERENCE)
    COUNTERS["requests"] += 1
    COUNTERS["defects"] += len(report.defects)
    COUNTERS["latencies"].append(report.total_ms)
    return {"scene": seed, "hard": hard, "ground_truth": scene.defects, **report.as_dict()}


@app.get("/annotated/{seed}.jpg")
def annotated(seed: int, hard: bool = False) -> Response:
    scene = make_scene(seed=seed, hard=hard)
    p = perceive(scene.capture(), REFERENCE)
    ok, buf = cv2.imencode(".jpg", annotate(p), [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not ok:
        raise HTTPException(status_code=500, detail="encode failed")
    return Response(content=buf.tobytes(), media_type="image/jpeg")


@app.get("/metrics")
def metrics() -> dict:
    lat = COUNTERS["latencies"]
    return {"requests": COUNTERS["requests"], "defects_total": COUNTERS["defects"],
            "latency_ms_p50": round(statistics.median(lat), 1) if lat else None,
            "latency_ms_max": round(max(lat), 1) if lat else None}
