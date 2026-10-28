#!/usr/bin/env python
"""영상의 박자(움직임과 멈춤)를 잰다. 자막 띠(아래 16%)는 빼고 잰다.

    python measure_motion.py --video <mp4> [--json <out>]

출처: 스킬 작성자의 내부 측정 도구(움직임, 자막 띠 가리기, 움직임 구간)를 옮겨 다듬었다.
5fps, 192x108 회색조 프레임의 이웃 차이 평균이 0.35를 넘으면 '움직임', 아니면 '멈춤'이다.

- hold_median_s: 멈춤 구간 길이의 중앙값(초).
- short_hold_share: 5초 미만 멈춤에 든 시간 / 영상 전체 시간.
- big_changes_per_min: 이웃 차이가 12를 넘는 표본 수(1초 안의 큰 구성 변화) / 분.
- 판정(설계 §7 A1): hold_median_s ≤ 3 이고 short_hold_share ≥ 0.18 이면 `A1 PASS`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

FPS, GW, GH = 5, 192, 108
MASK_FROM = int(GH * 0.84)  # 이 행부터 아래(약 16%)는 자막 띠라 뺀다
MOVE_THR = 0.35
BIG_THR = 12.0
SHORT_HOLD_S = 5.0
A1_HOLD_MEDIAN_MAX = 3.0
A1_SHORT_SHARE_MIN = 0.18


def gray_frames(video: str) -> np.ndarray:
    data = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-an",
                           "-vf", f"fps={FPS},scale={GW}:{GH}", "-pix_fmt", "gray",
                           "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    n = len(data) // (GW * GH)
    return np.frombuffer(data[: n * GW * GH], np.uint8).reshape(n, GH, GW).astype(np.int16)


def holds_from(moving: np.ndarray) -> list[float]:
    holds, run = [], 0
    for m in moving:
        if not m:
            run += 1
        else:
            if run:
                holds.append(run / FPS)
            run = 0
    if run:
        holds.append(run / FPS)
    return holds


def segments(diffs: np.ndarray) -> list[dict]:
    """움직임 구간(events.py 방식: 한 표본 끊김은 이어 붙인다)."""
    moving = diffs > MOVE_THR
    segs, i = [], 0
    while i < len(moving):
        if moving[i]:
            j = i
            while j + 1 < len(moving) and (moving[j + 1] or (j + 2 < len(moving) and moving[j + 2])):
                j += 1
            seg = diffs[i: j + 1]
            segs.append({"start_s": round(i / FPS, 2), "end_s": round((j + 1) / FPS, 2),
                         "peak_diff": round(float(seg.max()), 2)})
            i = j + 1
        else:
            i += 1
    return segs


def measure(video: str) -> dict:
    g = gray_frames(video)
    if len(g) < 2:
        raise SystemExit(f"프레임이 너무 적다: {video}")
    top = g[:, :MASK_FROM]
    diffs = np.abs(np.diff(top, axis=0)).mean(axis=(1, 2))
    moving = diffs > MOVE_THR
    total_s = len(diffs) / FPS
    dur_min = total_s / 60
    holds = np.array(holds_from(moving) or [0.0])
    short = holds[holds < SHORT_HOLD_S]
    segs = segments(diffs)
    res = {
        "video": str(video),
        "duration_s": round(total_s, 2),
        "hold_median_s": round(float(np.median(holds)), 2),
        "hold_p75_s": round(float(np.quantile(holds, 0.75)), 2),
        "hold_max_s": round(float(holds.max()), 2),
        "short_hold_share": round(float(short.sum() / total_s), 3),
        "big_changes_per_min": round(float((diffs > BIG_THR).sum() / dur_min), 2),
        "moving_time_fraction": round(float(moving.mean()), 3),
        "holds_over_5s_per_min": round(float((holds > SHORT_HOLD_S).sum() / dur_min), 2),
        "segments_per_min": round(len(segs) / dur_min, 2),
    }
    res["A1"] = "PASS" if (res["hold_median_s"] <= A1_HOLD_MEDIAN_MAX
                           and res["short_hold_share"] >= A1_SHORT_SHARE_MIN) else "FAIL"
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="자막 띠를 뺀 박자 측정")
    ap.add_argument("--video", required=True)
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args(argv)
    res = measure(a.video)
    if a.json_out:
        Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json_out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in ("hold_median_s", "short_hold_share", "big_changes_per_min"):
        print(f"{k} {res[k]}")
    print(f"A1 {res['A1']} (hold_median_s <= {A1_HOLD_MEDIAN_MAX}, short_hold_share >= {A1_SHORT_SHARE_MIN})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
