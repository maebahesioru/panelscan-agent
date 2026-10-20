#!/usr/bin/env python3
"""Print the three headline metric rows from results/eval.json, one per line.

Used by docs/record_terminal.sh so the demo video shows the numbers that are actually
in the file, not a hand-typed table.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "eval.json"
    if not path.exists():
        print(f"missing {path} — run .venv/bin/python src/eval_harness.py --scenes 80", file=sys.stderr)
        return 1
    res = json.loads(path.read_text(encoding="utf-8"))
    print(f"generated {res['generated_at']}  opencv {res['opencv']}")
    for key, label in (("hard_baseline", "single-shot / degraded"),
                       ("hard_agentic", "agentic loop / degraded"),
                       ("normal", "agentic loop / normal")):
        o = res[key]["overall"]
        lat = res[key]["latency_ms"]
        steps = res[key]["steps_mean"]
        print(f"  {label:<24} P {o['precision']:.3f}  R {o['recall']:.3f}  F1 {o['f1']:.3f}"
              f"   tp/fp/fn {o['tp']}/{o['fp']}/{o['fn']}"
              f"   p50 {lat['p50']} ms   steps {steps}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
