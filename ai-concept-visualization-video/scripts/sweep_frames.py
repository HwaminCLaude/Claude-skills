#!/usr/bin/env python
"""영상에서 일정 간격으로 프레임을 뽑아 3x3 시트(시각 라벨)를 만든다. 눈으로 검수하기 위한 것.

    python sweep_frames.py --video <mp4> --every <s> --out <dir>

<out>/frames/f_0001.jpg ...(원본 해상도)와 <out>/sheet_01.jpg ...(640x360 칸 3x3)를 만든다.
라벨의 시각은 그 프레임을 뽑은 실제 시각(0, every, 2*every, ...)이다.
출처: 스킬 작성자의 내부 측정 도구를 옮겨 다듬었다.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

TW, TH = 640, 360


def duration(video: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def grab(video: str, t: float, out: Path) -> bool:
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video),
                        "-an", "-frames:v", "1", "-q:v", "2", str(out)], capture_output=True)
    return r.returncode == 0 and out.is_file()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="프레임 스윕 시트")
    ap.add_argument("--video", required=True)
    ap.add_argument("--every", type=float, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.every <= 0:
        raise SystemExit("--every는 0보다 커야 한다")

    out = Path(a.out)
    fdir = out / "frames"
    fdir.mkdir(parents=True, exist_ok=True)
    for old in list(fdir.glob("f_*.jpg")) + list(out.glob("sheet_*.jpg")):
        old.unlink()

    dur = duration(a.video)
    shots: list[tuple[float, Path]] = []
    i = 0
    while i * a.every < dur - 0.02:
        t = i * a.every
        f = fdir / f"f_{i + 1:04d}.jpg"
        if grab(a.video, t, f):
            shots.append((t, f))
        i += 1

    sheets = []
    for si in range(0, len(shots), 9):
        sheet = Image.new("RGB", (TW * 3, TH * 3), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for j, (ts, f) in enumerate(shots[si: si + 9]):
            im = Image.open(f).convert("RGB").resize((TW, TH), Image.BILINEAR)
            x, y = (j % 3) * TW, (j // 3) * TH
            sheet.paste(im, (x, y))
            d.rectangle([x, y, x + 150, y + 22], fill=(255, 255, 0))
            d.text((x + 4, y + 4), f"{f.stem} {int(ts // 60)}:{ts % 60:05.2f}", fill=(0, 0, 0))
        p = out / f"sheet_{si // 9 + 1:02d}.jpg"
        sheet.save(p, quality=88)
        sheets.append(p)

    print(f"frames {len(shots)} sheets {len(sheets)} -> {out}")
    for p in sheets:
        print(p)
    return 0 if shots else 1


if __name__ == "__main__":
    sys.exit(main())
