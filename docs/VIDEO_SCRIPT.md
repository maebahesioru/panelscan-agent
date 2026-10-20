# Video script — PanelScan Agent (target 4:30, hard limit 5:00)

Rules require: the team, the application working, the architecture, and the principal
results — all inside five minutes. Screen recording + voice-over; no live camera needed.

| time | shot | narration (English) |
|---|---|---|
| 0:00–0:20 | webcam / facecam, name card | "Hi, I'm [NAME], 16, from Japan. This is PanelScan Agent: an inspection loop where what the camera sees changes what the camera does next. It is built on OpenCV 5." |
| 0:20–0:50 | terminal: `make eval` scroll | "Every number you'll see is produced by this command on an ordinary CPU machine. Forty normal scenes, forty deliberately degraded ones — dark, blurred, noisy, JPEG-compressed — with ground truth." |
| 0:50–1:30 | `results/EVAL_SUMMARY.md` | "F1 on normal scenes [X]. On degraded scenes the single-shot baseline gets [Y] and the agentic loop gets [Z]. Here is exactly why." |
| 1:30–2:20 | split screen: raw capture → annotated output | "Four ArUco fiducials give a homography, so the panel is rectified into canonical coordinates. Then each screw and each label is verified where it belongs with normalised cross-correlation — brightness-invariant, so an exposure swing is not a false defect. The remaining interior is differenced and thresholded with Otsu: that finds scratches and solder blobs." |
| 2:20–3:10 | terminal: `curl -X POST /inspect/scene/2002` | "Watch the trace. Step one: luma 28, too dark — it raises exposure instead of reporting. Step two: Laplacian variance low — it refocuses. Step three: all four fiducials, sharp, confident — accept. Four measures, one verdict." |
| 3:10–3:50 | `docs/ARCHITECTURE.md` diagram | "The service is FastAPI in a container. The AWS path is an ECS Fargate task on Graviton with an ALB, logs to CloudWatch. It is written and the image builds for arm64 — I did not deploy it: I have no AWS account, and I am not going to claim a deployment I did not run." |
| 3:50–4:20 | `results/EVAL_SUMMARY.md` failure rows | "Where it still fails: [read 1–2 failures]. Those are in the repo with the annotated frames. Responsible use: synthetic data only, human review required, and the tool never drives machinery." |
| 4:20–4:30 | facecam | "Repo, numbers and failure cases are in the submission. Thanks for watching." |

## Recording checklist

- [ ] 1440p or 1080p, single window, font size ≥ 16 pt in terminal
- [ ] show the full command typed, not a prepared screenshot
- [ ] narration must match the numbers in `results/eval.json` **at record time** (re-run
      `make eval` immediately before recording so the file and the video agree)
- [ ] upload unlisted to YouTube; paste the link in the Devpost submission
- [ ] length ≤ 5:00 — check the exported duration, not the timeline estimate

---

**Status (2026-10-20): produced.** The shipped video is `docs/demo_video.mp4` (4:20, 1280x720),
built by `docs/make_video_slides.py` + `docs/make_video.sh` from the recorded terminal output and the
evaluation, not by a screen recorder. This file stays as the intent-and-beats plan; where the produced
video differs (no narration, numeric values taken live from `results/eval.json`), the video wins.
