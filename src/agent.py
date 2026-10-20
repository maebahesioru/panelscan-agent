"""Agentic stage: the perception result changes the next sensing action.

This is deliberately not a chatbot. Every step is:

    perceive(frame) -> decide(action) -> apply(action to the camera) -> perceive again

and the loop only stops when the evidence is good enough or the action budget is
spent. The trace is emitted alongside the verdict so a judge can replay why the
system moved the sensor the way it did.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from perception import Defect, Perception, perceive
from scene_sim import Scene

MAX_STEPS = 5
CONF_OK = 0.62
SHARP_MIN = 140.0
BRIGHT_MIN = 34.0
BRIGHT_MAX = 245.0


@dataclass
class Step:
    n: int
    action: str
    reason: str
    registered: bool
    markers: int
    sharpness: float
    brightness: float
    defects: list[dict]
    latency_ms: float


@dataclass
class Report:
    defects: list[Defect]
    steps: list[Step] = field(default_factory=list)
    total_ms: float = 0.0

    def as_dict(self) -> dict:
        return {
            "defects": [d.as_dict() for d in self.defects],
            "steps": [s.__dict__ for s in self.steps],
            "total_ms": round(self.total_ms, 2),
        }


def _iou(a, b) -> float:
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    iw, ih = max(0, x2 - x1), max(0, y2 - y1)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def merge(prev: list[Defect], new: list[Defect]) -> list[Defect]:
    """Fuse evidence from successive views; the highest-confidence hit wins."""
    out = list(prev)
    for d in new:
        dcx = d.bbox[0] + d.bbox[2] / 2; dcy = d.bbox[1] + d.bbox[3] / 2
        dup = next((i for i, e in enumerate(out)
                    if _iou(e.bbox, d.bbox) > 0.25 or
                    (e.type == d.type and
                     (e.bbox[0] + e.bbox[2] / 2 - dcx) ** 2 + (e.bbox[1] + e.bbox[3] / 2 - dcy) ** 2 < 45 ** 2)), None)
        if dup is None:
            out.append(d)
        elif d.confidence > out[dup].confidence:
            out[dup] = d
    return out


def _decide(p: Perception, step: int) -> tuple[str, str]:
    # exposure first: a dark frame both loses fiducials and depresses Laplacian variance,
    # so treating it as a framing problem sends the camera hunting for the wrong cause
    if p.brightness < BRIGHT_MIN:
        return "raise_exposure", f"mean luma {p.brightness:.0f} < {BRIGHT_MIN:.0f}"
    if p.brightness > BRIGHT_MAX:
        return "lower_exposure", f"mean luma {p.brightness:.0f} > {BRIGHT_MAX:.0f}"
    if p.markers < 4:
        return "reposition", f"only {p.markers}/4 fiducials visible; registration impossible"
    if p.sharpness < SHARP_MIN:
        return "refocus", f"laplacian variance {p.sharpness:.0f} < {SHARP_MIN:.0f}"
    weak = [d for d in p.defects if d.confidence < CONF_OK]
    if weak:
        return "cleanup_capture", f"{len(weak)} detection(s) below confidence {CONF_OK}"
    return "accept", "registration stable, sharpness and exposure acceptable, all detections confident"


def _act(action: str, scene: Scene) -> None:
    cam = scene.cam
    if action == "reposition":
        cam.yaw *= 0.6
        cam.pitch *= 0.6
        cam.exposure = max(cam.exposure, 1.0)
    elif action == "raise_exposure":
        cam.exposure = min(1.6, cam.exposure * 1.3)
    elif action == "lower_exposure":
        cam.exposure = max(0.4, cam.exposure * 0.8)
    elif action == "refocus":
        cam.blur_sigma *= 0.3
    elif action == "cleanup_capture":
        cam.jpeg_quality = 96
        cam.noise_sigma *= 0.5
        cam.blur_sigma *= 0.7


def _bucket(d: Defect) -> tuple:
    return d.type, int((d.bbox[0] + d.bbox[2] / 2) // 40), int((d.bbox[1] + d.bbox[3] / 2) // 40)


def run_agent(scene: Scene, reference: np.ndarray) -> Report:
    defects: list[Defect] = []
    steps: list[Step] = []
    votes: dict[tuple, int] = {}
    total = 0.0
    for n in range(1, MAX_STEPS + 1):
        frame = scene.capture()
        p = perceive(frame, reference)
        total += p.latency_ms
        action, reason = _decide(p, n)
        steps.append(Step(n=n, action=action, reason=reason, registered=p.registered,
                          markers=p.markers, sharpness=round(p.sharpness, 1),
                          brightness=round(p.brightness, 1),
                          defects=[d.as_dict() for d in p.defects], latency_ms=round(p.latency_ms, 2)))
        defects = merge(defects, p.defects)
        for d in p.defects:
            votes[_bucket(d)] = votes.get(_bucket(d), 0) + 1
        if action == "accept":
            break
        _act(action, scene)
    # cross-view agreement: report a defect when a single view is confident about it, or
    # when two independent views saw it even if each was unsure
    defects = [d for d in defects
               if d.type != "unknown" and (d.confidence >= CONF_OK or votes.get(_bucket(d), 0) >= 2)]
    return Report(defects=defects, steps=steps, total_ms=total)
