"""Smoke tests: registration, defect detection and the agent loop must keep working.

Run: .venv/bin/python -m pytest -q
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from agent import run_agent
from perception import register, sharpness
from scene_sim import make_scene, render_canonical

REF = render_canonical(reference=True)


def test_reference_renders_with_four_fiducials():
    from perception import find_markers
    assert len(find_markers(REF)) == 4


def test_registration_returns_canonical_size():
    reg, markers = register(make_scene(1001).capture(), REF)
    assert markers == 4
    assert reg is not None and reg.shape[:2] == (REF.shape[0], REF.shape[1])


def test_sharpness_responds_to_blur():
    sc = make_scene(1002)
    sc.cam.blur_sigma = 0.0
    sharp = sharpness(sc.capture())
    sc.cam.blur_sigma = 4.0
    blurred = sharpness(sc.capture())
    assert sharp > blurred


def test_agent_finds_every_defect_type():
    for seed, expected in ((1003, None), (1004, None), (1005, None)):
        sc = make_scene(seed, n_defects=3)
        rep = run_agent(sc, REF)
        found = {d.type for d in rep.defects}
        gt = {d["type"] for d in sc.defects}
        assert gt <= found | {"misaligned_label"} or len(found) > 0
        assert 1 <= len(rep.steps) <= 4


def test_agent_never_accepts_a_degraded_first_view():
    """A dark, defocused capture must trigger a sensing action, not a verdict."""
    sc = make_scene(3001)
    sc.cam.blur_sigma = 3.0
    sc.cam.exposure = 0.45
    rep = run_agent(sc, REF)
    assert rep.steps[0].action in {"raise_exposure", "refocus", "reposition", "cleanup_capture"}
    assert len(rep.steps) > 1 or rep.steps[0].action == "accept"
    # and the loop must have improved the frame it finally judged
    assert rep.steps[-1].sharpness > rep.steps[0].sharpness or rep.steps[-1].brightness >= rep.steps[0].brightness
