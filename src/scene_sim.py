"""Synthetic visual-inspection bench used to evaluate the pipeline offline.

Every scene is fully deterministic given a seed: the same seed always produces the
same panel, the same defects and the same camera artefacts. Ground truth lives in
the *canonical* panel coordinate frame so that detections can be scored after
registration.

Nothing here is part of the product; it is the evaluation fixture (see
docs/EVALUATION.md for why a simulated bench is used and what its limits are).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

PANEL_W, PANEL_H = 1000, 700
PAD_X, PAD_Y = 90, 90
CANVAS_W, CANVAS_H = PANEL_W + 2 * PAD_X, PANEL_H + 2 * PAD_Y
MARGIN = 150
ARUCO_IDS = (0, 1, 2, 3)
ARUCO_SIZE = 110
MARKER_CTR = [(75, 75), (PANEL_W - 75, 75), (75, PANEL_H - 75), (PANEL_W - 75, PANEL_H - 75)]
SCREW_GRID = [
    (250, 200), (500, 200), (750, 200),
    (250, 600), (500, 600), (750, 600),
]
LABELS = [(150, 350, 240, 80), (560, 350, 220, 80)]
DEFECT_TYPES = ("missing_screw", "scratch", "blob", "misaligned_label")


def _aruco_dict():
    return cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def render_canonical(reference: bool = False, misaligned: bool = False) -> np.ndarray:
    """Render the panel in its canonical (rectified) frame."""
    img = np.full((PANEL_H, PANEL_W, 3), 28, np.uint8)
    # board tint + texture
    img[:] = (34, 48, 40)
    rng = np.random.default_rng(7)
    for _ in range(160):
        x, y = rng.integers(0, PANEL_W), rng.integers(0, PANEL_H)
        cv2.line(img, (x, y), (x + int(rng.integers(-40, 40)), y + int(rng.integers(-40, 40))),
                 (44, 66, 52), 1, cv2.LINE_AA)
    cv2.rectangle(img, (MARGIN, MARGIN), (PANEL_W - MARGIN, PANEL_H - MARGIN), (52, 78, 60), 3)

    # fiducial markers (corners) - these are what registration locks onto
    d = _aruco_dict()
    for idx, (cx, cy) in enumerate(MARKER_CTR):
        marker = cv2.aruco.generateImageMarker(d, ARUCO_IDS[idx], ARUCO_SIZE)
        x0, y0 = cx - ARUCO_SIZE // 2, cy - ARUCO_SIZE // 2
        img[y0:y0 + ARUCO_SIZE, x0:x0 + ARUCO_SIZE] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)

    # traces
    for y in (140, 440, 620):
        cv2.line(img, (MARGIN + 20, y), (PANEL_W - MARGIN - 20, y), (150, 120, 70), 4, cv2.LINE_AA)
    # labels
    for (x, y, w, h) in LABELS:
        cv2.rectangle(img, (x, y), (x + w, y + h), (200, 200, 195), -1)
        cv2.putText(img, "SN-0000", (x + 8, y + h - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2, cv2.LINE_AA)
    if misaligned:
        x, y, w, h = LABELS[0]
        patch = img[y:y + h, x:x + w].copy()
        img[y:y + h, x:x + w] = (52, 78, 60)
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 17.0, 1.0)
        M[0, 2] += 34
        M[1, 2] -= 18
        rot = cv2.warpAffine(patch, M, (w, h), borderValue=(52, 78, 60))
        img[y:y + h, x:x + w] = rot

    if reference:
        # reference = clean board with every screw present, no scratch/blob
        for (cx, cy) in SCREW_GRID:
            cv2.circle(img, (cx, cy), 26, (120, 120, 125), -1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), 26, (190, 190, 195), 2, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), 9, (70, 70, 75), -1, cv2.LINE_AA)
        return img

    for (cx, cy) in SCREW_GRID:
        cv2.circle(img, (cx, cy), 26, (120, 120, 125), -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), 26, (190, 190, 195), 2, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), 9, (70, 70, 75), -1, cv2.LINE_AA)
        cv2.line(img, (cx - 18, cy), (cx + 18, cy), (60, 60, 65), 2, cv2.LINE_AA)
    return img


@dataclass
class CameraState:
    """Knobs the agent is allowed to move (this is the 'act' half of the loop)."""
    yaw: float = 0.0
    pitch: float = 0.0
    blur_sigma: float = 0.0
    exposure: float = 1.0
    noise_sigma: float = 2.0
    jpeg_quality: int = 92


@dataclass
class Scene:
    seed: int
    defects: list[dict] = field(default_factory=list)
    cam: CameraState = field(default_factory=CameraState)

    def canonical(self) -> np.ndarray:
        mis = any(d["type"] == "misaligned_label" for d in self.defects)
        img = render_canonical(reference=False, misaligned=mis)
        for d in self.defects:
            t = d["type"]
            if t == "missing_screw":
                cx, cy = d["center"]
                cv2.circle(img, (cx, cy), 27, (52, 78, 60), -1, cv2.LINE_AA)
                cv2.circle(img, (cx, cy), 27, (60, 60, 60), 1, cv2.LINE_AA)
            elif t == "scratch":
                p0, p1 = d["p0"], d["p1"]
                cv2.line(img, tuple(p0), tuple(p1), (215, 215, 220), 3, cv2.LINE_AA)
                cv2.line(img, tuple(p0), tuple(p1), (150, 150, 160), 1, cv2.LINE_AA)
            elif t == "blob":
                cv2.circle(img, tuple(d["center"]), d["r"], (90, 105, 140), -1, cv2.LINE_AA)
                cv2.circle(img, tuple(d["center"]), d["r"], (150, 170, 200), 2, cv2.LINE_AA)
        return img

    def capture(self) -> np.ndarray:
        """Apply the current camera state to the canonical panel and return a frame."""
        img = self.canonical()
        # the panel sits on a larger platen so a tilted camera does not clip a fiducial
        canvas = np.full((CANVAS_H, CANVAS_W, 3), (20, 25, 22), np.uint8)
        canvas[PAD_Y:PAD_Y + PANEL_H, PAD_X:PAD_X + PANEL_W] = img
        M = cv2.getRotationMatrix2D((CANVAS_W / 2, CANVAS_H / 2), self.cam.yaw, 1.0)
        M[1, 2] += self.cam.pitch
        frame = cv2.warpAffine(canvas, M, (CANVAS_W, CANVAS_H), borderValue=(20, 25, 22))
        # sensor pipeline
        frame = cv2.convertScaleAbs(frame, alpha=self.cam.exposure, beta=0)
        if self.cam.blur_sigma > 0.05:
            frame = cv2.GaussianBlur(frame, (0, 0), self.cam.blur_sigma)
        if self.cam.noise_sigma > 0.05:
            rng = np.random.default_rng(self.seed)
            noise = rng.normal(0, self.cam.noise_sigma, frame.shape).astype(np.float32)
            frame = np.clip(frame.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(self.cam.jpeg_quality)])
        if ok:
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return frame


def make_scene(seed: int, n_defects: int | None = None, hard: bool = False) -> Scene:
    rng = np.random.default_rng(seed)
    n = n_defects if n_defects is not None else int(rng.integers(1, 4))
    kinds = list(rng.choice(DEFECT_TYPES, size=n, replace=False))
    defects: list[dict] = []
    for k in kinds:
        k = str(k)
        if k == "missing_screw":
            cx, cy = SCREW_GRID[int(rng.integers(0, len(SCREW_GRID)))]
            defects.append({"type": k, "center": [int(cx), int(cy)], "bbox": [cx - 27, cy - 27, 54, 54]})
        elif k == "scratch":
            x0 = int(rng.integers(200, PANEL_W - 300)); y0 = int(rng.integers(255, 315))
            p0 = [x0, y0]; p1 = [x0 + int(rng.integers(90, 170)), y0 + int(rng.integers(-8, 8))]
            defects.append({"type": k, "p0": p0, "p1": p1,
                            "bbox": [p0[0], p0[1] - 6, p1[0] - p0[0], 12]})
        elif k == "blob":
            cx = int(rng.integers(210, PANEL_W - 210)); cy = int(rng.integers(480, 555)); r = int(rng.integers(13, 21))
            defects.append({"type": k, "center": [cx, cy], "r": r,
                            "bbox": [cx - r, cy - r, 2 * r, 2 * r]})
        else:  # misaligned_label
            x, y, w, h = LABELS[0]
            defects.append({"type": k, "bbox": [x, y, w, h]})
    cam = CameraState(
        yaw=float(rng.uniform(-6, 6)),
        pitch=float(rng.uniform(-6, 6)),
        blur_sigma=float(rng.uniform(0.8, 2.2)) if hard else float(rng.uniform(0.0, 0.8)),
        exposure=float(rng.uniform(0.55, 0.8)) if hard else float(rng.uniform(0.9, 1.1)),
        noise_sigma=float(rng.uniform(6, 12)) if hard else float(rng.uniform(1, 4)),
        jpeg_quality=58 if hard else int(rng.integers(80, 95)),
    )
    return Scene(seed=seed, defects=defects, cam=cam)


def save_gt(scene: Scene, path: str | Path) -> None:
    Path(path).write_text(json.dumps({
        "seed": scene.seed,
        "defects": scene.defects,
        "camera": scene.cam.__dict__,
    }, indent=1), encoding="utf-8")
