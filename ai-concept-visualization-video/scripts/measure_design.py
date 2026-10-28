#!/usr/bin/env python
"""자막을 굽기 전 영상(_scenes.mp4)의 디자인 지표를 잰다.

    python measure_design.py --video <mp4-without-captions> [--json <out>] [--every 2]

출처: 스킬 작성자의 내부 측정 도구(배경, 덩어리, 내용 폭, 띠 침범, 테두리 상자)를 옮겨 다듬었다.
프레임은 `--every`초(기본 2초)마다 뽑아 960x540으로 줄여 계산한다.

원본과 다른 점
- 배경색: 원본은 5비트 칸의 가운데(+4)를 써서 검정이 #040404로 나온다.
  여기서는 가장 많은 칸 안 화소의 실제 RGB 최빈값을 쓴다(검정은 #000000).
  yuv420p → BGR 변환은 `full_chroma_int`로 한다. 기본 축소는 검정을 #000001로 바꾼다.
- 자막 띠: 원본은 참고 영상 자막 자리(0.82~0.93 H)를 뺐다. 우리 내용 하한은 y ≥ −2.7(위에서 0.8375 H)이므로
  아래 15%(0.85 H 이하)를 자막 띠로 본다. 본문 지표와 상자 셈에서는 이 띠를 빼고,
  띠 안 잉크 비율이 0.002를 넘는 프레임 수를 caption_band_content_frames로 센다.

판정(설계 §7 A2): bg #000000, caption_band_content_frames 0, outline_boxes_median 0,
outline_boxes_ge3_share < 0.05, xspan_median ≤ 0.6, clusters_median ≤ 2 이면 `A2 PASS`.
덩어리와 폭은 내용이 있는 프레임(본문 잉크 ≥ 0.003)만으로 중앙값을 낸다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

W, H = 960, 540
BAND0 = int(0.85 * H)                 # 자막 띠 시작 행
K_DIL = np.ones((41, 41), np.uint8)   # 원본 기준 약 80px
LIVE_INK = 0.003
BAND_INK = 0.002


def frames_bgr(video: str, every: float) -> np.ndarray:
    data = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-an",
                           "-vf", f"fps=1/{every},scale={W}:{H}:flags=area+accurate_rnd+full_chroma_int",
                           "-pix_fmt", "bgr24", "-f", "rawvideo", "-"],
                          capture_output=True, check=True).stdout
    n = len(data) // (W * H * 3)
    return np.frombuffer(data[: n * W * H * 3], np.uint8).reshape(n, H, W, 3)


def background(img: np.ndarray) -> np.ndarray:
    """가장 많은 5비트 칸 안에서 실제 BGR 최빈값."""
    px = img.reshape(-1, 3)
    q = (px // 8).astype(np.int32)
    keys = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
    mode = np.bincount(keys).argmax()
    inside = px[keys == mode].astype(np.int32)
    exact = inside[:, 0] * 65536 + inside[:, 1] * 256 + inside[:, 2]
    v, c = np.unique(exact, return_counts=True)
    e = int(v[c.argmax()])
    return np.array([e // 65536, (e // 256) % 256, e % 256])


def outline_filled(img: np.ndarray, bg: np.ndarray) -> tuple[int, int]:
    """design_boxes.py: 테두리만 있는 상자와 면으로 채운 상자 개수."""
    diff = np.abs(img.astype(np.int16) - bg[None, None, :]).max(axis=2)
    m = (diff > 12).astype(np.uint8)   # 옅은 면 채우기도 잡도록 낮은 문턱
    m[BAND0:] = 0
    outline = filled = 0
    cnts, _ = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w < 30 or h < 14 or w * h < 900:
            continue
        ap = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(ap) < 4 or len(ap) > 8:
            continue
        if cv2.contourArea(c) < 0.85 * w * h:   # 직사각형 모양이 아님
            continue
        inner = m[y + 4:y + h - 4, x + 4:x + w - 4]
        if inner.size == 0:
            continue
        r = inner.mean()
        if r < 0.35:
            outline += 1
        elif r > 0.80:
            filled += 1
    return outline, filled


def frame_metrics(img: np.ndarray) -> dict:
    bg = background(img)
    diff = np.abs(img.astype(np.int16) - bg[None, None, :].astype(np.int16)).max(axis=2)
    ink = diff > 40
    body = ink.copy()
    body[BAND0:] = False
    n_body = int(body.sum())
    dil = cv2.dilate(body.astype(np.uint8), K_DIL)
    n, _lab, stats, _ = cv2.connectedComponentsWithStats(dil, 8)
    clusters = int(sum(1 for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 0.003 * W * H))
    if n_body:
        xs = np.nonzero(body)[1]
        x5, x95 = np.percentile(xs, [5, 95]) / W
        xspan = float(x95 - x5)
    else:
        xspan = float("nan")
    outline, filled = outline_filled(img, bg)
    return {"bg_hex": "#%02X%02X%02X" % (bg[2], bg[1], bg[0]),
            "ink_body": n_body / (W * H), "band_ink": float(ink[BAND0:].mean()),
            "clusters": clusters, "xspan": xspan, "outline": outline, "filled": filled}


def _median(vals) -> float | None:
    v = np.array([x for x in vals if x == x], float)  # nan 제외
    return round(float(np.median(v)), 4) if len(v) else None


def measure(video: str, every: float = 2.0) -> dict:
    frames = frames_bgr(video, every)
    if not len(frames):
        raise SystemExit(f"프레임을 뽑지 못했다: {video}")
    rows = [frame_metrics(f) for f in frames]
    live = [r for r in rows if r["ink_body"] >= LIVE_INK]
    bgs: dict[str, int] = {}
    for r in rows:
        bgs[r["bg_hex"]] = bgs.get(r["bg_hex"], 0) + 1
    outl = np.array([r["outline"] for r in rows])
    band_frames = [i for i, r in enumerate(rows) if r["band_ink"] > BAND_INK]
    res = {
        "video": str(video), "sample_every_s": every,
        "n_frames": len(rows), "n_live": len(live),
        "bg_hex": max(bgs.items(), key=lambda kv: kv[1])[0],
        "bg_share": round(max(bgs.values()) / len(rows), 3),
        "caption_band_content_frames": len(band_frames),
        "caption_band_content_times_s": [round(i * every, 2) for i in band_frames[:20]],
        "outline_boxes_median": round(float(np.median(outl)), 2),
        "outline_boxes_ge3_share": round(float(np.mean(outl >= 3)), 3),
        "filled_boxes_median": round(float(np.median([r["filled"] for r in rows])), 2),
        "xspan_median": _median([r["xspan"] for r in live]),
        "clusters_median": _median([r["clusters"] for r in live]),
        "empty_rate": round(1 - len(live) / len(rows), 3),
    }
    checks = {
        "bg": res["bg_hex"] == "#000000",
        "caption_band": res["caption_band_content_frames"] == 0,
        "outline_median": res["outline_boxes_median"] == 0,
        "outline_ge3": res["outline_boxes_ge3_share"] < 0.05,
        "xspan": res["xspan_median"] is None or res["xspan_median"] <= 0.6,
        "clusters": res["clusters_median"] is None or res["clusters_median"] <= 2,
    }
    res["A2_checks"] = checks
    res["A2"] = "PASS" if all(checks.values()) else "FAIL"
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="자막 없는 영상의 디자인 지표")
    ap.add_argument("--video", required=True)
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--every", type=float, default=2.0, help="표본 간격(초)")
    a = ap.parse_args(argv)
    res = measure(a.video, a.every)
    if a.json_out:
        Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json_out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in ("bg_hex", "caption_band_content_frames", "outline_boxes_median",
              "outline_boxes_ge3_share", "xspan_median", "clusters_median"):
        print(f"{k} {res[k]}")
    failed = [k for k, ok in res["A2_checks"].items() if not ok]
    print(f"A2 {res['A2']}" + (f" ({', '.join(failed)})" if failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
