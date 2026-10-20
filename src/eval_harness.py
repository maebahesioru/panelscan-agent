"""Evaluation harness: agentic loop vs. single-shot baseline on the same scenes.

Produces the evidence the rules ask for ("evaluation evidence appropriate to the
project, including failure cases or limitations"):

  results/eval.json        machine-readable metrics for both modes
  results/EVAL_SUMMARY.md  human-readable table + failure analysis
  results/scenes/*.png     annotated evidence for the failure cases

Run: .venv/bin/python src/eval_harness.py --scenes 60
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cv2

from agent import run_agent
from perception import annotate, perceive
from scene_sim import Scene, make_scene, render_canonical

OUT = Path(__file__).resolve().parent.parent / "results"
TYPES = ("missing_screw", "scratch", "blob", "misaligned_label")
MATCH_PX = 46


def _center(bbox):
    return bbox[0] + bbox[2] / 2.0, bbox[1] + bbox[3] / 2.0


def _match(gt: list[dict], pred: list) -> tuple[int, int, int, list[str]]:
    """Greedy one-to-one match on (type, centroid distance). Returns tp, fp, fn, notes."""
    used = set()
    tp = 0
    notes: list[str] = []
    for g in gt:
        gx, gy = _center(g["bbox"])
        best, bestd = None, 1e9
        for i, p in enumerate(pred):
            if i in used or p.type != g["type"]:
                continue
            px, py = _center(p.bbox)
            d = ((px - gx) ** 2 + (py - gy) ** 2) ** 0.5
            if d < bestd:
                best, bestd = i, d
        if best is not None and bestd <= MATCH_PX:
            used.add(best)
            tp += 1
        else:
            got = [p.type for p in pred]
            notes.append(f"FN {g['type']} at ({gx:.0f},{gy:.0f}) — predicted {got or 'nothing'}")
    fp = len(pred) - len(used)
    for i, p in enumerate(pred):
        if i not in used:
            notes.append(f"FP {p.type} bbox={p.bbox} conf={p.confidence:.2f} ({p.evidence})")
    return tp, fp, len(gt) - tp, notes


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3)}


def run_mode(scene_factories: list, ref, mode: str) -> dict:
    scenes = [f() for f in scene_factories]  # fresh camera state per mode: the agent mutates it
    per_type = {t: {"tp": 0, "fp": 0, "fn": 0} for t in TYPES}
    latencies: list[float] = []
    steps_used: list[int] = []
    failures: list[dict] = []
    tp = fp = fn = 0
    for sc in scenes:
        if mode == "agentic":
            rep = run_agent(sc, ref)
            pred, ms, steps = rep.defects, rep.total_ms, len(rep.steps)
        else:  # single-shot baseline: one capture, no corrective sensing
            p = perceive(sc.capture(), ref)
            pred, ms, steps = [d for d in p.defects if d.type != "unknown"], p.latency_ms, 1
        a, b, c, notes = _match(sc.defects, pred)
        tp += a; fp += b; fn += c
        latencies.append(ms); steps_used.append(steps)
        # per-type accounting
        gt_types = [g["type"] for g in sc.defects]
        pred_types = [p.type for p in pred]
        for t in TYPES:
            gtn = gt_types.count(t); pdn = pred_types.count(t)
            hit = min(gtn, pdn)
            per_type[t]["tp"] += hit
            per_type[t]["fn"] += gtn - hit
            per_type[t]["fp"] += pdn - hit
        if notes:
            failures.append({"seed": sc.seed, "hard": sc.cam.jpeg_quality < 70,
                             "gt": sc.defects, "pred": [p.as_dict() for p in pred],
                             "notes": notes, "steps": steps})
    return {
        "mode": mode,
        "scenes": len(scenes),
        "overall": _prf(tp, fp, fn),
        "per_type": {t: _prf(**(per_type[t])) for t in TYPES},
        "latency_ms": {"p50": round(statistics.median(latencies), 1),
                       "p95": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 1),
                       "mean": round(statistics.fmean(latencies), 1)},
        "steps_mean": round(statistics.fmean(steps_used), 2),
        "failures": failures,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", type=int, default=60)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    (OUT / "scenes").mkdir(exist_ok=True)
    ref = render_canonical(reference=True)

    n = args.scenes
    normal = [lambda i=i: make_scene(seed=1000 + i) for i in range(n // 2)]
    hard = [lambda i=i: make_scene(seed=2000 + i, hard=True) for i in range(n - len(normal))]

    t0 = time.perf_counter()
    res = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "opencv": cv2.__version__,
           "normal": run_mode(scene_factories=normal, ref=ref, mode="agentic"),
           "hard_agentic": run_mode(scene_factories=hard, ref=ref, mode="agentic"),
           "hard_baseline": run_mode(scene_factories=hard, ref=ref, mode="baseline"),
           "total_runtime_s": round(time.perf_counter() - t0, 2)}
    (OUT / "eval.json").write_text(json.dumps(res, indent=1), encoding="utf-8")

    # annotated evidence for the interesting failures
    for f in res["hard_agentic"]["failures"][:6]:
        sc = make_scene(seed=f["seed"], hard=True)
        rep = run_agent(sc, ref)
        p = perceive(sc.capture(), ref)
        cv2.imwrite(str(OUT / "scenes" / f"fail_seed{f['seed']}.png"), annotate(p))

    lines = ["# Evaluation summary", "", f"OpenCV {cv2.__version__} · {len(normal)} normal + {len(hard)} degraded scenes", ""]
    for key, label in (("hard_baseline", "single-shot baseline (degraded scenes)"),
                       ("hard_agentic", "agentic loop (degraded scenes)"),
                       ("normal", "agentic loop (normal scenes)")):
        r = res[key]
        o = r["overall"]
        lines += [f"## {label}", "",
                  f"- P/R/F1: **{o['precision']:.3f} / {o['recall']:.3f} / {o['f1']:.3f}** "
                  f"(tp {o['tp']}, fp {o['fp']}, fn {o['fn']})",
                  f"- latency p50/p95/mean: {r['latency_ms']['p50']} / {r['latency_ms']['p95']} / {r['latency_ms']['mean']} ms",
                  f"- sensing steps per scene (mean): {r['steps_mean']}",
                  "", "| defect | P | R | F1 | tp | fp | fn |", "|---|---|---|---|---|---|---|"]
        for t, m in r["per_type"].items():
            lines.append(f"| {t} | {m['precision']:.2f} | {m['recall']:.2f} | {m['f1']:.2f} | {m['tp']} | {m['fp']} | {m['fn']} |")
        lines.append("")
    (OUT / "EVAL_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: res[k]["overall"] for k in ("normal", "hard_agentic", "hard_baseline")}, indent=1))
    print("wrote", OUT / "eval.json")


if __name__ == "__main__":
    main()
