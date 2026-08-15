#!/usr/bin/env python
"""구간마다 여러 지점의 프레임을 뽑는다 — 눈으로 보기 위한 것.

verify_output.py는 **길이와 해상도**를 본다. 그것만으로는 글자 겹침, 화면 밖
잘림, 두부(□), 사라졌어야 할 찌꺼기를 못 잡는다. 그런 결함은 렌더가 성공하고
길이도 맞기 때문에 자동으로는 티가 안 난다. 결국 사람(또는 시각 모델)이 봐야 한다.

    python scripts/sweep_frames.py --episode <ep> --quality qh
    python scripts/sweep_frames.py --root <root> --points 0.35 0.70 0.98 --json

기본 지점은 35% / 70% / 끝-0.6초다. 35·70은 구간 중간의 겹침을, 마지막은
"사라졌어야 하는데 남은 것"을 잡는다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

QDIR = {"ql": "480p15", "qm": "720p30", "qh": "1080p60", "qk": "2160p60"}


def _duration(mp4: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(mp4)],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _grab(mp4: Path, t: float, out: Path, width: int) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(mp4),
           "-frames:v", "1"]
    if width:
        cmd += ["-vf", f"scale={width}:-1"]
    cmd.append(str(out))
    return subprocess.run(cmd, capture_output=True).returncode == 0


def sweep_episode(ep: Path, quality: str, points: list[float], width: int,
                  tail: float):
    vdir = ep / "media" / "videos" / "main" / QDIR[quality]
    if not vdir.is_dir():
        return {"episode": ep.name, "error": f"렌더 결과가 없다: {vdir}", "frames": []}

    frames = []
    for mp4 in sorted(vdir.glob("*.mp4")):
        d = _duration(mp4)
        if d <= 0:
            continue
        for p in points:
            # 1.0은 마지막 프레임을 뜻한다 — 끝에서 tail초 앞을 잡는다
            t = max(0.0, d - tail) if p >= 1.0 else d * p
            label = "end" if p >= 1.0 else f"p{int(round(p * 100)):02d}"
            out = ep / "sweep_frames" / f"{mp4.stem}_{label}.png"
            if _grab(mp4, t, out, width):
                frames.append({"scene": mp4.stem, "point": label,
                               "t": round(t, 2), "duration": round(d, 2),
                               "path": str(out)})
    return {"episode": ep.name, "frames": frames}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", help="에피소드 폴더 하나")
    ap.add_argument("--root", help="프로젝트 루트 (ep* 전부)")
    ap.add_argument("--quality", default="qh", choices=list(QDIR))
    ap.add_argument("--points", nargs="*", type=float, default=[0.35, 0.70, 1.0],
                    help="구간 길이 대비 비율. 1.0은 마지막 프레임")
    ap.add_argument("--tail", type=float, default=0.6,
                    help="마지막 프레임을 끝에서 몇 초 앞에서 잡을지")
    ap.add_argument("--width", type=int, default=960,
                    help="가로 픽셀 (0이면 원본 해상도)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    eps: list[Path] = []
    if a.episode:
        eps = [Path(a.episode)]
    elif a.root:
        eps = sorted(p for p in Path(a.root).glob("ep*") if p.is_dir())
    else:
        ap.error("--root 또는 --episode 가 필요하다")

    results = [sweep_episode(e, a.quality, a.points, a.width, a.tail) for e in eps]
    total = sum(len(r["frames"]) for r in results)

    if a.json:
        print(json.dumps({"episodes": results, "total": total},
                         ensure_ascii=False, indent=2))
    else:
        for r in results:
            if r.get("error"):
                print(f"  SKIP  {r['episode']}  {r['error']}")
                continue
            scenes = len({f["scene"] for f in r["frames"]})
            print(f"  {r['episode']:<18} 구간 {scenes}개 → 프레임 {len(r['frames'])}장"
                  f"  ({Path(r['frames'][0]['path']).parent})" if r["frames"] else "")
        print(f"[sweep] 총 {total}장 — 이제 눈으로 본다. 보는 법은 "
              f"references/visual-qa.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
