# Evaluation summary

OpenCV 5.0.0 · 40 normal + 40 degraded scenes

## single-shot baseline (degraded scenes)

- P/R/F1: **0.976 / 0.494 / 0.656** (tp 41, fp 1, fn 42)
- latency p50/p95/mean: 72.1 / 124.3 / 77.5 ms
- sensing steps per scene (mean): 1.0

| defect | P | R | F1 | tp | fp | fn |
|---|---|---|---|---|---|---|
| missing_screw | 1.00 | 0.37 | 0.54 | 7 | 0 | 12 |
| scratch | 0.93 | 0.68 | 0.79 | 13 | 1 | 6 |
| blob | 1.00 | 0.45 | 0.62 | 9 | 0 | 11 |
| misaligned_label | 1.00 | 0.48 | 0.65 | 12 | 0 | 13 |

## agentic loop (degraded scenes)

- P/R/F1: **0.920 / 0.976 / 0.947** (tp 81, fp 7, fn 2)
- latency p50/p95/mean: 218.5 / 476.6 / 244.5 ms
- sensing steps per scene (mean): 2.9

| defect | P | R | F1 | tp | fp | fn |
|---|---|---|---|---|---|---|
| missing_screw | 1.00 | 1.00 | 1.00 | 19 | 0 | 0 |
| scratch | 0.73 | 1.00 | 0.84 | 19 | 7 | 0 |
| blob | 1.00 | 0.90 | 0.95 | 18 | 0 | 2 |
| misaligned_label | 1.00 | 1.00 | 1.00 | 25 | 0 | 0 |

## agentic loop (normal scenes)

- P/R/F1: **0.975 / 0.952 / 0.963** (tp 79, fp 2, fn 4)
- latency p50/p95/mean: 67.5 / 135.2 / 79.9 ms
- sensing steps per scene (mean): 1.32

| defect | P | R | F1 | tp | fp | fn |
|---|---|---|---|---|---|---|
| missing_screw | 1.00 | 1.00 | 1.00 | 23 | 0 | 0 |
| scratch | 0.91 | 1.00 | 0.95 | 19 | 2 | 0 |
| blob | 1.00 | 0.77 | 0.87 | 13 | 0 | 4 |
| misaligned_label | 1.00 | 1.00 | 1.00 | 24 | 0 | 0 |
