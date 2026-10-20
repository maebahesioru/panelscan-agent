#!/usr/bin/env python3
"""Print one /inspect/scene/{seed} response as a readable decision trace.

Used by docs/record_terminal.sh: the video reads this output, so the trace it shows is
the service's own JSON, formatted — never re-typed.

Usage: docs/show_trace.py /tmp/panelscan_2002.json
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: show_trace.py <response.json>", file=sys.stderr)
        return 2
    with open(sys.argv[1], encoding="utf-8") as fh:
        d = json.load(fh)
    print(f"scene {d['scene']}  hard={d['hard']}")
    print(f"ground truth : {[g['type'] for g in d['ground_truth']]}")
    print("trace:")
    for s in d["steps"]:
        print(f"  step {s['n']}  {s['action']:<15} luma {s['brightness']:6.1f}  sharp {s['sharpness']:6.1f}"
              f"  markers {s['markers']}  | {s['reason']}")
    verdict = ", ".join(f"{x['type']} {x['confidence']:.2f}" for x in d["defects"])
    print(f"verdict      : {verdict or 'none'}")
    print(f"total_ms     : {d['total_ms']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
