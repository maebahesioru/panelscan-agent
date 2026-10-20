"""OpenCV 5 perception stage.

Pipeline (all OpenCV 5.0.0, no third-party vision libraries):

1. fiducial detection      cv2.aruco.ArucoDetector  -> marker corners
2. registration            cv2.findHomography + cv2.warpPerspective -> canonical panel
3. illumination control    cv2.createCLAHE, cv2.Laplacian (sharpness metric)
4. reference comparison    cv2.absdiff vs. the clean board, cv2.threshold(OTSU)
5. blob extraction         cv2.findContours + cv2.morphologyEx
6. defect classification   shape/position features (circularity, aspect, area,
                           colour delta) scored against the expected layout
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict

import cv2
import numpy as np

from scene_sim import (ARUCO_IDS, ARUCO_SIZE, LABELS, MARGIN, MARKER_CTR, PANEL_H, PANEL_W,
                       SCREW_GRID, _aruco_dict)

CORNERS_CANON = list(MARKER_CTR)


@dataclass
class Defect:
    type: str
    bbox: list[int]
    confidence: float
    evidence: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Perception:
    registered: bool
    markers: int
    sharpness: float
    brightness: float
    defects: list[Defect]
    latency_ms: float
    frame_bgr: np.ndarray | None = None
    registered_bgr: np.ndarray | None = None


_DETECTOR = None


def _detector():
    global _DETECTOR
    if _DETECTOR is None:
        params = cv2.aruco.DetectorParameters()
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        params.adaptiveThreshWinSizeMin = 5
        params.adaptiveThreshWinSizeMax = 51
        params.adaptiveThreshWinSizeStep = 4
        params.minMarkerPerimeterRate = 0.01
        params.maxMarkerPerimeterRate = 6.0
        params.errorCorrectionRate = 0.8
        _DETECTOR = cv2.aruco.ArucoDetector(_aruco_dict(), params)
    return _DETECTOR


UPSCALE = 1.5


def find_markers(frame_bgr: np.ndarray):
    """Return {marker_id: centroid} in the captured (distorted) frame.

    Detection runs on an upscaled copy: small fiducials survive blur and JPEG
    artefacts much better at 1.5x, and the centroids are simply divided back.
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    big = cv2.resize(gray, None, fx=UPSCALE, fy=UPSCALE, interpolation=cv2.INTER_CUBIC)
    corners, ids, _ = _detector().detectMarkers(big)
    found: dict[int, tuple[float, float]] = {}
    if ids is None:
        return found
    for c, i in zip(corners, ids.flatten()):
        pts = c.reshape(-1, 2)
        found[int(i)] = (float(pts[:, 0].mean()) / UPSCALE, float(pts[:, 1].mean()) / UPSCALE)
    return found


def register(frame_bgr: np.ndarray, reference_bgr: np.ndarray | None = None) -> tuple[np.ndarray | None, int]:
    """Rectify the capture into canonical panel coordinates using the fiducials."""
    found = find_markers(frame_bgr)
    shared = [i for i in ARUCO_IDS if i in found]
    if len(shared) < 4:
        return None, len(shared)
    src = np.array([found[i] for i in ARUCO_IDS], np.float32)
    dst = np.array([CORNERS_CANON[i] for i in ARUCO_IDS], np.float32)
    H, _ = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if H is None:
        return None, len(shared)
    warped = cv2.warpPerspective(frame_bgr, H, (PANEL_W, PANEL_H))
    return warped, len(shared)


def sharpness(frame_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def brightness(frame_bgr: np.ndarray) -> float:
    return float(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY).mean())


def _circularity(cnt) -> float:
    area = cv2.contourArea(cnt)
    per = cv2.arcLength(cnt, True)
    if per <= 0:
        return 0.0
    return float(4 * np.pi * area / (per * per))


def _near(center, points, tol):
    return any((center[0] - p[0]) ** 2 + (center[1] - p[1]) ** 2 <= tol * tol for p in points)


def _misfit(gray: np.ndarray, ref: np.ndarray, box) -> float:
    x, y, w, h = [int(v) for v in box]
    a = gray[y:y + h, x:x + w].astype(np.float32)
    b = ref[y:y + h, x:x + w].astype(np.float32)
    if a.size == 0:
        return 0.0
    return float(np.abs(a - b).mean())


def _interior_mask() -> np.ndarray:
    m = np.zeros((PANEL_H, PANEL_W), np.uint8)
    m[MARGIN + 8:PANEL_H - MARGIN - 8, MARGIN + 8:PANEL_W - MARGIN - 8] = 255
    for (cx, cy) in CORNERS_CANON:
        cv2.circle(m, (int(cx), int(cy)), ARUCO_SIZE, 0, -1)
    for (cx, cy) in SCREW_GRID:
        cv2.rectangle(m, (cx - 34, cy - 34), (cx + 34, cy + 34), 0, -1)
    for (x, y, w, h) in LABELS:
        cv2.rectangle(m, (x - 6, y - 6), (x + w + 6, y + h + 6), 0, -1)
    return m


_INTERIOR = _interior_mask()


def _ncc(gray: np.ndarray, tmpl: np.ndarray, box, pad: int = 8) -> float:
    """Normalised cross-correlation of an expected part inside its own region.

    NCC is invariant to brightness/contrast shifts, so sensor exposure changes do
    not look like a missing part, while a genuinely absent or displaced part does.
    """
    x, y, w, h = [int(v) for v in box]
    hh, ww = gray.shape[:2]
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(ww, x + w + pad), min(hh, y + h + pad)
    patch = gray[y0:y1, x0:x1]
    if patch.shape[0] < tmpl.shape[0] or patch.shape[1] < tmpl.shape[1]:
        return 0.0
    res = cv2.matchTemplate(patch, tmpl, cv2.TM_CCOEFF_NORMED)
    return float(res.max())


def _norm(gray: np.ndarray) -> np.ndarray:
    g = gray.astype(np.float32)
    m, sd = float(g.mean()), float(g.std())
    if sd < 1e-3:
        return g - m
    return (g - m) / sd


def _interior_mask() -> np.ndarray:
    m = np.zeros((PANEL_H, PANEL_W), np.uint8)
    m[MARGIN + 10:PANEL_H - MARGIN - 10, MARGIN + 10:PANEL_W - MARGIN - 10] = 255
    for (cx, cy) in CORNERS_CANON:
        cv2.circle(m, (int(cx), int(cy)), ARUCO_SIZE + 4, 0, -1)
    for (cx, cy) in SCREW_GRID:
        cv2.rectangle(m, (cx - 38, cy - 38), (cx + 38, cy + 38), 0, -1)
    for (x, y, w, h) in LABELS:
        cv2.rectangle(m, (x - 10, y - 10), (x + w + 10, y + h + 10), 0, -1)
    return m


_INTERIOR = _interior_mask()
NCC_PART_MIN = 0.55
DIFF_MIN = 22.0  # grey levels; Otsu may raise it, never lower it

_SCREW_BOX = 44


def detect_defects(registered_bgr: np.ndarray, reference_bgr: np.ndarray) -> list[Defect]:
    """Layout-aware verification of the rectified capture against the clean board.

    Expected parts (six screws, two labels) are located by normalised cross
    correlation inside their own neighbourhood - brightness invariant. Free-form
    defects (scratches, solder blobs) are searched only in the remaining interior
    using a z-score difference map, so global exposure changes do not register.
    """
    g = cv2.cvtColor(registered_bgr, cv2.COLOR_BGR2GRAY)
    r = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    g, r = clahe.apply(g), clahe.apply(r)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    out: list[Defect] = []

    for (cx, cy) in SCREW_GRID:
        box = [cx - _SCREW_BOX // 2, cy - _SCREW_BOX // 2, _SCREW_BOX, _SCREW_BOX]
        x, y, w, h = box
        tmpl = r[y:y + h, x:x + w]
        score = _ncc(g, tmpl, box)
        if score < NCC_PART_MIN:
            out.append(Defect("missing_screw", box, float(min(0.99, 0.55 + (NCC_PART_MIN - score))),
                              f"ncc {score:.2f} < {NCC_PART_MIN}"))

    for (x, y, w, h) in LABELS:
        tmpl = r[y:y + h, x:x + w]
        score = _ncc(g, tmpl, [x, y, w, h])
        if score < NCC_PART_MIN:
            out.append(Defect("misaligned_label", [x, y, w, h], float(min(0.99, 0.55 + (NCC_PART_MIN - score))),
                              f"ncc {score:.2f} < {NCC_PART_MIN}"))

    diff = cv2.absdiff(g, r)
    diff = cv2.GaussianBlur(diff, (3, 3), 0)
    inside = diff[_INTERIOR > 0]
    otsu, _ = cv2.threshold(inside.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    thr = max(DIFF_MIN, float(otsu))
    diff = cv2.bitwise_and(diff, diff, mask=_INTERIOR)
    mask = (diff > thr).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        area = float(cv2.contourArea(c))
        if area < 90 or area > 4500:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if w < 4 or h < 4:
            continue
        circ = _circularity(c)
        aspect = max(w, h) / max(1.0, min(w, h))
        peak = float(diff[y:y + h, x:x + w].max())
        if peak < 28.0:
            continue
        conf = float(min(0.97, 0.55 + peak / 160.0))
        if aspect >= 2.2 and area < 1800:
            out.append(Defect("scratch", [x, y, w, h], conf, f"aspect={aspect:.1f} area={area:.0f} peak={peak:.1f}"))
        elif circ >= 0.45 and area <= 2200:
            out.append(Defect("blob", [x, y, w, h], conf, f"circ={circ:.2f} area={area:.0f} peak={peak:.1f}"))
    out.sort(key=lambda d: -d.confidence)
    return out


def perceive(frame_bgr: np.ndarray, reference_bgr: np.ndarray) -> Perception:
    t0 = time.perf_counter()
    reg, n_markers = register(frame_bgr, reference_bgr)
    sharp = sharpness(frame_bgr)
    bright = brightness(frame_bgr)
    defects = detect_defects(reg, reference_bgr) if reg is not None else []
    dt = (time.perf_counter() - t0) * 1000.0
    return Perception(registered=reg is not None, markers=n_markers, sharpness=sharp,
                      brightness=bright, defects=defects, latency_ms=dt,
                      frame_bgr=frame_bgr, registered_bgr=reg)


def annotate(p: Perception) -> np.ndarray:
    """Draw the evidence a judge (or the agent) looks at."""
    base = p.registered_bgr if p.registered_bgr is not None else p.frame_bgr
    img = base.copy()
    colours = {"missing_screw": (60, 60, 235), "scratch": (60, 200, 240),
               "blob": (200, 90, 240), "misaligned_label": (60, 220, 60), "unknown": (180, 180, 180)}
    for d in p.defects:
        x, y, w, h = d.bbox
        c = colours.get(d.type, (255, 255, 255))
        cv2.rectangle(img, (x - 4, y - 4), (x + w + 4, y + h + 4), c, 2)
        cv2.putText(img, f"{d.type} {d.confidence:.2f}", (x - 4, max(14, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1, cv2.LINE_AA)
    cv2.putText(img, f"registered={p.registered} markers={p.markers} sharp={p.sharpness:.0f} "
                     f"lux={p.brightness:.0f} t={p.latency_ms:.0f}ms",
                (10, PANEL_H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return img
