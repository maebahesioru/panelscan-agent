"""Quick sanity probe: does the loop register, detect and self-correct?

Run: .venv/bin/python src/probe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cv2

from agent import run_agent
from perception import annotate, perceive
from scene_sim import make_scene, render_canonical

OUT = Path(__file__).resolve().parent.parent / "results"
OUT.mkdir(exist_ok=True)


def main() -> None:
    ref = render_canonical(reference=True)
    cv2.imwrite(str(OUT / "reference.png"), ref)
    for seed in (11, 23, 31):
        sc = make_scene(seed)
        rep = run_agent(sc, ref)
        print(f"seed={seed} gt={[d['type'] for d in sc.defects]} "
              f"found={[d.type for d in rep.defects]} steps={len(rep.steps)} "
              f"actions={[s.action for s in rep.steps]} ms={rep.total_ms:.0f}")
        p = perceive(sc.capture(), ref)
        cv2.imwrite(str(OUT / f"seed{seed}_annotated.png"), annotate(p))
    sc = make_scene(5, hard=True)
    rep = run_agent(sc, ref)
    print(f"HARD seed=5 gt={[d['type'] for d in sc.defects]} found={[d.type for d in rep.defects]} "
          f"actions={[s.action for s in rep.steps]}")


if __name__ == "__main__":
    main()
