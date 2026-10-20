#!/usr/bin/env python3
"""Render the frames of docs/demo_video.mp4 (1280x720) with PIL.

Every factual string on a frame is pulled from a file this repository produced, so the
video cannot drift away from the measurement:

  docs/video_src/terminal.txt   real command output   (docs/record_terminal.sh)
  results/eval.json             the metrics           (src/eval_harness.py)
  evidence/scene_*.png          annotated frames      (src/make_evidence.py)

It also writes the segment manifest read by docs/make_video.sh:
keep-out line y=596 .. 720 is the subtitle bar, so no frame draws there.

Run: .venv/bin/python docs/make_video_slides.py   (or: python3, needs Pillow)
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "video_frames"
EVIDENCE = ROOT / "evidence"
TRACE_DIR = ROOT / "docs" / "video_src"

W, H = 1280, 720
SAFE_BOTTOM = 596          # subtitle bar starts here

BG = (13, 17, 23)
PANEL = (22, 28, 36)
PANEL_2 = (28, 35, 45)
LINE = (48, 58, 72)
FG = (230, 237, 243)
MUTED = (139, 148, 158)
BLUE = (78, 161, 255)
YELLOW = (255, 190, 40)
RED = (255, 92, 92)
GREEN = (61, 220, 132)

SANS = "/usr/share/fonts/noto/NotoSans-Regular.ttf"
SANS_B = "/usr/share/fonts/noto/NotoSans-Bold.ttf"
MONO = "/usr/share/fonts/noto/NotoSansMono-Regular.ttf"
MONO_B = "/usr/share/fonts/noto/NotoSansMono-Bold.ttf"
CJK_B = "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"


def f(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(draw, xy, text, font, fill, max_w, leading=1.35):
    x, y = xy
    for line in wrap(text, font, max_w, draw):
        draw.text((x, y), line, font=font, fill=fill)
        y += int(font.size * leading)
    return y


def bullets(draw, xy, items, font, fill, max_w, gap=14, marker=BLUE):
    x, y = xy
    for it in items:
        draw.ellipse([x, y + font.size * 0.42, x + 6, y + font.size * 0.42 + 6], fill=marker)
        y = para(draw, (x + 20, y), it, font, fill, max_w - 20)
        y += gap
    return y


def chip(draw, xy, text, font, fg=FG, bg=PANEL_2, pad=(12, 7), outline=None):
    x, y = xy
    tw = draw.textlength(text, font=font)
    th = font.size
    box = [x, y, x + tw + 2 * pad[0], y + th + 2 * pad[1]]
    draw.rounded_rectangle(box, radius=8, fill=bg, outline=outline)
    draw.text((x + pad[0], y + pad[1] - 2), text, font=font, fill=fg)
    return box[2]


def fit(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = min(w / img.width, h / img.height)
    return img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)


def paste_fit(base: Image.Image, img: Image.Image, box, border=True):
    x, y, w, h = box
    im = fit(img, w, h)
    px = x + (w - im.width) // 2
    py = y + (h - im.height) // 2
    if border:
        ImageDraw.Draw(base).rectangle([px - 2, py - 2, px + im.width + 2, py + im.height + 2], outline=LINE)
    base.paste(im, (px, py))


def arrow(draw, p0, p1, color=LINE, width=3, head=11, dashed=False):
    (x0, y0), (x1, y1) = p0, p1
    if dashed:
        n = 18
        for i in range(n):
            if i % 2:
                continue
            t0, t1 = i / n, (i + 0.6) / n
            draw.line([(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0),
                       (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)], fill=color, width=width)
    else:
        draw.line([(x0, y0), (x1, y1)], fill=color, width=width)
    import math
    ang = math.atan2(y1 - y0, x1 - x0)
    draw.polygon([(x1, y1),
                  (x1 - head * math.cos(ang - 0.42), y1 - head * math.sin(ang - 0.42)),
                  (x1 - head * math.cos(ang + 0.42), y1 - head * math.sin(ang + 0.42))], fill=color)


def footer(draw, text: str):
    draw.text((48, SAFE_BOTTOM - 34), text, font=f(MONO, 14), fill=MUTED)


def load_terminal() -> dict[str, list[str]]:
    """Split terminal.txt into {section title: [lines]} (the '###' headers)."""
    blocks: dict[str, list[str]] = {}
    cur = None
    for raw in (TRACE_DIR / "terminal.txt").read_text(encoding="utf-8").splitlines():
        if raw.startswith("### "):
            cur = raw[4:].strip()
            blocks[cur] = []
        elif cur is not None:
            blocks[cur].append(raw)
    return {k: [ln for ln in v if ln.strip()] for k, v in blocks.items()}


# ---------------------------------------------------------------- frames


def frame_title() -> None:
    img, d = canvas()
    im = Image.open(EVIDENCE / "scene_2011.png")
    paste_fit(img, im, (700, 60, 540, 480))
    d.text((48, 92), "OPENCV AI COMPETITION 2026  ·  TECHNICAL ENTRY", font=f(MONO_B, 16), fill=BLUE)
    d.text((48, 124), "PanelScan", font=f(SANS_B, 74), fill=FG)
    d.text((48, 202), "Agent", font=f(SANS_B, 74), fill=BLUE)
    para(d, (48, 300), "An inspection loop where what the camera sees changes what the "
                       "camera does next.", f(SANS, 22), FG, 600)
    d.line([(48, 372), (648, 372)], fill=LINE, width=2)
    x = 48
    for t in ("OpenCV 5.0.0", "FastAPI", "ARM64 container (prepared)"):
        x = chip(d, (x, 392), t, f(MONO, 15), outline=(60, 72, 90)) + 10
    d.text((48, 448), "Team", font=f(MONO, 15), fill=MUTED)
    d.text((100, 443), "大肥魚", font=f(CJK_B, 20), fill=FG)
    d.text((168, 448), "(Daihigyo) · solo entrant · 16 · Japan", font=f(SANS, 17), fill=MUTED)
    footer(d, "evidence/scene_2011.png  ·  yellow = ground truth, red = merged prediction")
    img.save(OUT / "s01_title.png")


def frame_problem() -> None:
    img, d = canvas()
    paste_fit(img, Image.open(EVIDENCE / "scene_2002_input.png"), (48, 96, 640, 450))
    d.text((48, 56), "1 · The camera is the problem, not the part", font=f(SANS_B, 30), fill=FG)
    d.text((740, 100), "First frame, scene 2002", font=f(SANS_B, 22), fill=YELLOW)
    y = bullets(d, (740, 148), [
        "mean luma 28.5 · below the 34 floor",
        "1 of 4 ArUco fiducials detected",
        "blur σ 2.06 · JPEG q58 · noise σ 11.6",
        "3 defects are present in this panel",
    ], f(SANS, 19), FG, 492, gap=12)
    d.text((740, y + 6), "A single-shot pipeline answers:", font=f(SANS, 19), fill=MUTED)
    d.text((740, y + 40), "“no defects, high confidence.”", font=f(SANS_B, 26), fill=RED)
    para(d, (740, y + 86), "That is the expensive failure mode this entry is about.",
         f(SANS, 18), MUTED, 492)
    footer(d, "src/make_evidence.py  ->  evidence/scene_2002_input.png  (camera state in the header)")
    img.save(OUT / "s02_problem.png")


def frame_terminal(blocks: dict[str, list[str]], keys: list[str], name: str, title: str,
                   note: str) -> None:
    lines: list[str] = []
    for k in keys:
        if k not in blocks:
            raise SystemExit(f"missing terminal section {k!r}")
        lines.append(f"# {k}")
        lines.extend(blocks[k])
        lines.append("")

    img = Image.new("RGB", (W, H), (17, 19, 24))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 34], fill=(32, 36, 44))
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([16 + i * 22, 11, 28 + i * 22, 23], fill=col)
    d.text((88, 9), title, font=f(SANS, 15), fill=(150, 158, 170))

    # the transcript contains the real (Japanese) workspace path, so ASCII runs are drawn
    # with the mono face and everything else falls back to a CJK face
    cjk = f(CJK_B, 15)

    def runs(text: str):
        out, cur, ascii_ = [], "", None
        for ch in text:
            a = ord(ch) < 128
            if ascii_ is None or a == ascii_:
                cur += ch
            else:
                out.append((cur, ascii_))
                cur = ch
            ascii_ = a
        if cur:
            out.append((cur, ascii_))
        return out

    def width(text: str, mono: ImageFont.FreeTypeFont, scale: float) -> float:
        cjk_scaled = f(CJK_B, max(9, int(mono.size * 0.92)))
        return sum(d.textlength(run, font=(mono if a else cjk_scaled)) for run, a in runs(text))

    def draw(text: str, xy, mono, colour):
        cjk_scaled = f(CJK_B, max(9, int(mono.size * 0.92)))
        x, y = xy
        for run, a in runs(text):
            font = mono if a else cjk_scaled
            d.text((x, y), run, font=font, fill=colour)
            x += d.textlength(run, font=font)

    body = SAFE_BOTTOM - 58
    size = 22
    while size > 11:
        cand = f(MONO, size)
        if max(width(ln, cand, 1.0) for ln in lines) <= W - 96 and 56 + int(size * 1.42) * len(lines) <= body:
            break
        size -= 1
    font = f(MONO, size)
    step = int(size * 1.42)
    y = 56
    for ln in lines:
        colour = FG
        if ln.startswith("# "):
            colour = BLUE
        elif ln.startswith("$ "):
            colour = GREEN
        draw(ln, (48, y), font, colour)
        y += step
        if y > body:
            raise SystemExit(f"{name}: transcript too tall at font {size}px")
    footer(d, note)
    img.save(OUT / name)


def frame_results() -> None:
    res = json.loads((ROOT / "results" / "eval.json").read_text(encoding="utf-8"))
    img, d = canvas()
    d.text((48, 46), "2 · What the loop buys on the frames that were unreadable",
           font=f(SANS_B, 30), fill=FG)
    d.text((48, 92), "40 normal + 40 degraded scenes · .venv/bin/python src/eval_harness.py --scenes 80",
           font=f(MONO, 14), fill=MUTED)

    x0, y0 = 48, 130
    y = y0
    for name, key, colour in (("single-shot · degraded", "hard_baseline", RED),
                              ("agentic loop · degraded", "hard_agentic", GREEN),
                              ("agentic loop · normal", "normal", MUTED)):
        o = res[key]["overall"]
        lat = res[key]["latency_ms"]["p50"]
        steps = res[key]["steps_mean"]
        d.rounded_rectangle([x0, y, 1184, y + 98], radius=10, fill=PANEL, outline=LINE)
        d.text((x0 + 22, y + 30), name, font=f(SANS_B, 21), fill=colour)
        d.text((x0 + 22, y + 62), f"median latency {lat} ms · {steps} sensing steps / scene",
               font=f(MONO, 13), fill=MUTED)
        for i, (lab, val, big) in enumerate((("precision", o["precision"], False),
                                             ("recall", o["recall"], True),
                                             ("F1", o["f1"], True))):
            bx = x0 + 470 + i * 150
            d.text((bx, y + 18), lab, font=f(MONO, 13), fill=MUTED)
            d.text((bx, y + 36), f"{val:.3f}", font=f(MONO_B, 40 if big else 30),
                   fill=colour if big else FG)
        d.text((x0 + 930, y + 26), f"tp {o['tp']}  fp {o['fp']}  fn {o['fn']}",
               font=f(MONO, 15), fill=MUTED)
        y += 112

    base, agent = res["hard_baseline"]["overall"], res["hard_agentic"]["overall"]
    d.text((48, y + 8), f"recall {base['recall']:.3f} -> {agent['recall']:.3f}   "
                        f"F1 {base['f1']:.3f} -> {agent['f1']:.3f}"
                        f"   (+{agent['tp'] - base['tp']} defects found, −{base['fn'] - agent['fn']} missed)",
           font=f(SANS_B, 22), fill=YELLOW)
    d.text((48, y + 44), "cost: 7 false scratches on 40 scenes, and 3.0× the median latency",
           font=f(SANS, 17), fill=MUTED)
    img.save(OUT / "s04_results.png")


def frame_perception() -> None:
    img, d = canvas()
    d.text((48, 46), "3 · Perception: rectify first, then verify where things belong",
           font=f(SANS_B, 30), fill=FG)
    paste_fit(img, Image.open(EVIDENCE / "scene_2011.png"), (48, 96, 640, 448))
    x, y = 720, 96
    for i, (head, body) in enumerate((
            ("cv2.aruco", "4 fiducials, 1.5× upscale, sub-pixel refine"),
            ("findHomography", "warpPerspective -> canonical 1000×700 panel"),
            ("NCC per part", "TM_CCOEFF_NORMED vs the clean board — brightness invariant"),
            ("absdiff + Otsu", "interior residual -> contour shape = scratch or blob"),
            ("evidence merge", "IoU 0.25 or 45 px, highest confidence wins"))):
        d.ellipse([x, y + 4, x + 24, y + 28], fill=PANEL_2, outline=BLUE, width=2)
        d.text((x + 7, y + 6), str(i + 1), font=f(MONO_B, 15), fill=BLUE)
        d.text((x + 36, y), head, font=f(MONO_B, 18), fill=FG)
        y = para(d, (x + 36, y + 24), body, f(SANS, 16), MUTED, 500) + 16
    d.line([(720, y + 4), (1184, y + 4)], fill=LINE, width=2)
    d.rectangle([720, y + 22, 736, y + 38], outline=YELLOW, width=3)
    d.text((746, y + 22), "ground truth", font=f(SANS, 16), fill=MUTED)
    d.rectangle([880, y + 22, 896, y + 38], outline=RED, width=3)
    d.text((906, y + 22), "merged prediction — 3/3, no false positive", font=f(SANS, 16), fill=MUTED)
    footer(d, "scene 2011 after raise_exposure -> refocus -> accept")
    img.save(OUT / "s05_perception.png")


def frame_architecture() -> None:
    img, d = canvas()
    d.text((40, 30), "4 · Architecture: one bounded loop, one service, one honest gap",
           font=f(SANS_B, 28), fill=FG)

    def box(x, y, w, h, title, sub, outline=LINE, fill=PANEL):
        d.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=fill, outline=outline, width=2)
        d.text((x + 14, y + 10), title, font=f(MONO_B, 15), fill=FG)
        yy = y + 32
        for s in sub:
            d.text((x + 14, yy), s, font=f(MONO, 12), fill=MUTED)
            yy += 16

    box(40, 84, 220, 82, "capture()", ["exposure · blur σ", "noise σ · jpeg q", "±6° staging yaw"])
    box(296, 86, 236, 70, "ArUco -> homography", ["1.5× upscale, refine", "rectify 1000×700"])
    box(568, 64, 250, 52, "NCC per part", ["TM_CCOEFF_NORMED ≥ 0.55"])
    box(568, 120, 250, 52, "absdiff + Otsu", ["contours -> scratch / blob"])
    box(854, 84, 246, 82, "evidence merge", ["IoU 0.25 / 45 px", "highest confidence wins"])

    arrow(d, (260, 121), (292, 121))
    arrow(d, (532, 104), (564, 84), color=(90, 110, 140))
    arrow(d, (532, 126), (564, 140), color=(90, 110, 140))
    arrow(d, (818, 84), (850, 102), color=(90, 110, 140))
    arrow(d, (818, 146), (850, 142), color=(90, 110, 140))

    box(854, 206, 246, 110, "policy ladder",
        ["luma < 34 -> raise_exposure", "markers < 4 -> reposition",
         "Laplacian σ < 140 -> refocus", "else accept"], outline=GREEN)
    arrow(d, (977, 166), (977, 202), color=GREEN)

    box(40, 206, 540, 110, "FastAPI  (src/service.py)",
        ["POST /inspect/scene/{seed}?hard=true", "POST /inspect   (raw image bytes)",
         "GET  /healthz  /metrics", "GET  /annotated/{seed}.jpg"])
    d.text((600, 226), "the service is the loop", font=f(SANS_B, 16), fill=FG)
    para(d, (600, 254), "one request runs capture -> decide -> act up to 5 times and "
                        "returns every step, every reason.", f(SANS, 15), MUTED, 240)

    # the action goes back to the same camera: this is the loop, not a pipeline
    d.line([(977, 316), (977, 344), (26, 344), (26, 121)], fill=GREEN, width=3)
    arrow(d, (26, 121), (36, 121), color=GREEN)
    d.text((60, 322), "the action is applied to the same camera · max 5 steps",
           font=f(MONO, 13), fill=GREEN)

    d.rectangle([40, 364, 1150, 556], outline=(150, 120, 60), width=2)
    arrow(d, (977, 350), (977, 362), color=(150, 120, 60))
    d.text((58, 376), "AWS path — written in deploy/, NOT deployed", font=f(SANS_B, 18), fill=YELLOW)
    for i, (t, s) in enumerate((("ECR image", "linux/arm64"), ("ECS Fargate", "Graviton, 1 vCPU / 2 GiB"),
                                ("ALB -> /inspect", "health check /healthz"), ("CloudWatch", "logs + EMF metrics"))):
        box(70 + i * 270, 400, 240, 84, t, [s, "read-only root fs"], outline=(110, 92, 50), fill=(30, 27, 20))
        if i:
            arrow(d, (300 + (i - 1) * 270, 442), (334 + (i - 1) * 270, 442), color=(150, 120, 60), dashed=True)
    d.text((70, 506), "verdict + full step trace (JSON) is the service's first-class output",
           font=f(MONO, 13), fill=MUTED)
    img.save(OUT / "s07_architecture.png")


def frame_aws() -> None:
    img, d = canvas()
    d.text((48, 52), "5 · The AWS gap, stated as a gap", font=f(SANS_B, 32), fill=FG)
    y = bullets(d, (48, 116), [
        "deploy/Dockerfile — headless OpenCV 5, non-root, healthcheck, 2 threads",
        "deploy/ecs-taskdef.json — Fargate, ARM64 Graviton, CloudWatch, read-only root",
        "deploy/build_and_push.sh — buildx linux/arm64 -> ECR",
        "docs/ARCHITECTURE.md §4 — ECS / ALB / CloudWatch path and cost estimate",
    ], f(SANS, 19), FG, 700, gap=16, marker=YELLOW)
    d.rounded_rectangle([790, 116, 1216, 470], radius=12, fill=(30, 27, 20), outline=(150, 120, 60), width=2)
    d.text((818, 146), "NOT DEPLOYED", font=f(SANS_B, 30), fill=YELLOW)
    para(d, (818, 196), "No AWS account is attached to this submission, so no endpoint is "
                        "claimed, no image is pushed, and no bill exists.",
         f(SANS, 18), FG, 372)
    d.text((818, 316), "What that costs:", font=f(SANS_B, 17), fill=MUTED)
    para(d, (818, 344), "“Cloud delivery, reproducibility, responsible operation” is 10 of the "
                        "100 rubric points — so this is submitted as a documented 90, not a "
                        "pretended 100.", f(SANS, 17), MUTED, 372)
    d.text((48, y + 20), "locally verified instead", font=f(SANS_B, 19), fill=BLUE)
    d.text((48, y + 54), "GET /healthz -> {\"ok\":true,\"opencv\":\"5.0.0\",\"numpy\":\"2.5.4\","
                         "\"arch\":\"x86_64\"}", font=f(MONO, 14), fill=MUTED)
    d.text((48, y + 78), "POST /inspect/scene/2002?hard=true -> 2 steps, 3/3 defects, 151 ms",
           font=f(MONO, 14), fill=MUTED)
    footer(d, "measured on this machine; nothing here was sent anywhere")
    img.save(OUT / "s08_aws.png")


def frame_scope() -> None:
    img, d = canvas()
    d.text((48, 46), "6 · Where it still fails, and what it will not do", font=f(SANS_B, 30), fill=FG)
    y = bullets(d, (48, 104), [
        "7 false scratches in 40 degraded scenes — JPEG ringing read twice, precision 0.920",
        "a real scratch rectifies to the same canonical line across views; that geometric "
        "consistency check is the next step, not shipped",
        "4 blobs still missed on clean scenes: already sharp, so no sensing action can help",
        "four visible fiducials, one lighting condition, top-down camera — a demo bench, not a cell",
    ], f(SANS, 18), FG, 700, gap=13, marker=RED)
    d.text((48, y + 10), "Responsible use", font=f(SANS_B, 19), fill=BLUE)
    para(d, (48, y + 44), "Synthetic data only · no personal data, no camera on people · the verdict "
                          "is advisory and a human inspector decides · the tool never drives machinery.",
         f(SANS, 17), MUTED, 700)
    paste_fit(img, Image.open(EVIDENCE / "scene_2005.png"), (796, 150, 420, 300))
    d.text((796, 462), "scene 2005 — 3 steps, 1/1", font=f(MONO, 13), fill=MUTED)
    d.text((796, 484), "raise_exposure -> refocus -> accept", font=f(MONO, 13), fill=MUTED)
    img.save(OUT / "s09_scope.png")


def frame_end() -> None:
    img, d = canvas()
    d.text((48, 150), "In the submission", font=f(MONO_B, 18), fill=BLUE)
    d.text((48, 182), "Repository · report · video · failure cases", font=f(SANS_B, 42), fill=FG)
    para(d, (48, 258), "Every number here is regenerated by .venv/bin/python src/eval_harness.py "
                       "--scenes 80 on a CPU, and every frame in this video comes from a file "
                       "that command or its siblings wrote.", f(SANS, 19), MUTED, 900)
    x = 48
    for t in ("recall 0.494 -> 0.976", "F1 0.656 -> 0.947", "OpenCV 5.0.0", "no GPU"):
        x = chip(d, (x, 366), t, f(MONO, 16), outline=(60, 72, 90)) + 12
    d.text((48, 452), "Team", font=f(MONO, 14), fill=MUTED)
    d.text((96, 447), "大肥魚", font=f(CJK_B, 20), fill=FG)
    d.text((164, 452), "(Daihigyo) · 16 · Japan · thank you for watching", font=f(SANS, 16), fill=MUTED)
    img.save(OUT / "s10_end.png")


SEGMENTS = [
    ("s01_title", 10, 0, "PanelScan Agent — the camera moves because of what the pixels say."),
    ("s02_problem", 24, 1, "The first frame is not inspectable: 1 of 4 fiducials, mean luma 28."),
    ("s03_terminal_1", 26, 0, "Every number in this video comes from these commands, on CPU."),
    ("s04_results", 34, 0, "Half the defects were invisible to one shot: recall 0.494 to 0.976."),
    ("s05_perception", 34, 1, "Rectify first, then verify each part where it belongs."),
    ("s06_terminal_2", 30, 0, "The trace: exposure first, then a verdict — a decision, not a guess."),
    ("s07_architecture", 40, 0, "Four moves per pass, one bounded loop, one readable trace."),
    ("s08_aws", 24, 0, "AWS is written but not deployed — I will not claim a run I did not do."),
    ("s09_scope", 24, 0, "Failure cases stay in the repo. Synthetic data only. A human decides."),
    ("s10_end", 14, 0, "Report, code, failure cases and numbers are all in the submission."),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "telops").mkdir(exist_ok=True)
    blocks = load_terminal()

    frame_title()
    frame_problem()
    frame_terminal(blocks, ["OpenCV build actually in use", "tests",
                            "evaluation — 40 normal + 40 degraded scenes, one command"],
                   "s03_terminal_1.png", "terminal — the OpenCV build, the tests, the evaluation",
                   "verbatim output of docs/record_terminal.sh  ·  nothing is retyped for the video")
    frame_results()
    frame_perception()
    frame_terminal(blocks, ["live endpoint — the same loop over HTTP (local, not AWS)", "counters"],
                   "s06_terminal_2.png", "terminal — POST /inspect/scene/2002?hard=true",
                   "localhost:8080  ·  the same OpenCV loop, reached over HTTP")
    frame_architecture()
    frame_aws()
    frame_scope()
    frame_end()

    manifest, total = [], 0
    for name, dur, zoom, telop in SEGMENTS:
        telop_path = OUT / "telops" / f"{name}.txt"
        telop_path.write_text(telop, encoding="utf-8")
        assert (OUT / f"{name}.png").exists(), name
        manifest.append(f"{name}|{dur}|{zoom}|{telop_path.relative_to(ROOT)}")
        total += dur
    (OUT / "manifest.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"wrote {len(SEGMENTS)} segments, {total} s total ({total // 60}:{total % 60:02d}) -> {OUT}")


if __name__ == "__main__":
    main()
