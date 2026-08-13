"""Check a rendered episode against what the script promised.

Two things matter and neither is visible from an exit code:

1. Does the video actually last as long as the narration needs? If the mp4 is
   materially shorter than `sum(run_time + wait)` from shots.json, the voice
   track will not fit and the episode has to be reworked.
2. Does it look right? Duration and resolution can be perfect while the frame
   is empty or the Korean is tofu boxes. Sample frames are extracted so a human
   (or a vision pass) can actually look.

    python verify_output.py --episode C:\\manimwork\\my-paper\\ep01_problem --quality qh
    python verify_output.py --episode ... --shots shots.json --frames 4 --json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path


# Windows consoles default to cp949 here, and every one of these scripts prints
# Korean. Without this, a run dies with UnicodeEncodeError *after* it has already
# written its output files — the confusing failure mode of looking broken while
# actually having succeeded.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

QUALITY_DIR = {"ql": "480p15", "qm": "720p30", "qh": "1080p60", "qk": "2160p60"}
TOLERANCE = 0.15  # 15% — beyond this the episode is flagged for REWORK


@dataclass
class VideoReport:
    scene: str
    mp4: str
    duration_sec: float
    width: int
    height: int
    fps: float
    size_mb: float
    expected_sec: float | None = None
    drift_pct: float | None = None
    status: str = "OK"
    note: str = ""
    frames: list[str] = field(default_factory=list)


def ffprobe_json(mp4: Path) -> dict:
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height,avg_frame_rate",
           "-show_entries", "format=duration,size", "-of", "json", str(mp4)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit(f"ffprobe failed on {mp4}: {proc.stderr.strip()[:200]}")
    return json.loads(proc.stdout)


def parse_fps(raw: str) -> float:
    if "/" in raw:
        num, den = raw.split("/", 1)
        return round(float(num) / float(den), 2) if float(den) else 0.0
    return float(raw or 0)


def extract_frames(mp4: Path, out_dir: Path, count: int, duration: float) -> list[str]:
    """Evenly spaced stills, skipping the very first and last moments."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        # Spread across 10%..90% so we never grab a blank lead-in or fade-out.
        t = duration * (0.1 + 0.8 * (i / max(1, count - 1))) if count > 1 else duration * 0.5
        dest = out_dir / f"{mp4.stem}_t{t:05.1f}.png"
        proc = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(mp4),
             "-frames:v", "1", "-vf", "scale=960:-1", str(dest)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode == 0 and dest.exists():
            paths.append(str(dest))
    return paths


def expected_from_shots(shots_path: Path) -> dict[str, float]:
    """Map scene name -> expected seconds, from shots.json.

    Supports both a single-episode file ({"video": ..., "shots": [...]}) and a
    per-scene grouping ({"scenes": {"intro": {"shots": [...]}, ...}}).
    """
    payload = json.loads(shots_path.read_text(encoding="utf-8"))

    def total(shots: list[dict]) -> float:
        return round(sum(float(s.get("run_time", 0)) + float(s.get("wait", 0)) for s in shots), 2)

    if "scenes" in payload:
        return {name: total(block.get("shots", [])) for name, block in payload["scenes"].items()}
    if "shots" in payload:
        grouped: dict[str, list[dict]] = {}
        for shot in payload["shots"]:
            grouped.setdefault(shot.get("scene", payload.get("video", "main")), []).append(shot)
        return {name: total(shots) for name, shots in grouped.items()}
    return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="렌더 결과 검증 (길이 정합 + 프레임 샘플)")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--quality", default="qh", choices=list(QUALITY_DIR))
    ap.add_argument("--shots", help="shots.json (기본: 에피소드 폴더의 shots.json)")
    ap.add_argument("--frames", type=int, default=3, help="씬당 추출할 프레임 수 (0=끄기)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if shutil.which("ffprobe") is None:
        raise SystemExit("ffprobe가 PATH에 없습니다 (FFmpeg 설치 필요).")

    episode = Path(args.episode).resolve()
    video_dir = episode / "media" / "videos" / "main" / QUALITY_DIR[args.quality]
    if not video_dir.is_dir():
        raise SystemExit(f"렌더 결과 폴더가 없습니다: {video_dir}")

    mp4s = sorted(p for p in video_dir.glob("*.mp4"))
    if not mp4s:
        raise SystemExit(f"{video_dir}에 mp4가 없습니다.")

    shots_path = Path(args.shots) if args.shots else episode / "shots.json"
    expected = expected_from_shots(shots_path) if shots_path.is_file() else {}

    reports: list[VideoReport] = []
    for mp4 in mp4s:
        info = ffprobe_json(mp4)
        stream = (info.get("streams") or [{}])[0]
        fmt = info.get("format") or {}
        duration = round(float(fmt.get("duration", 0)), 2)

        rep = VideoReport(
            scene=mp4.stem, mp4=str(mp4), duration_sec=duration,
            width=int(stream.get("width", 0)), height=int(stream.get("height", 0)),
            fps=parse_fps(stream.get("avg_frame_rate", "0/1")),
            size_mb=round(int(fmt.get("size", 0)) / 2**20, 2),
        )

        exp = expected.get(mp4.stem)
        if exp:
            rep.expected_sec = exp
            drift = (duration - exp) / exp if exp else 0.0
            rep.drift_pct = round(drift * 100, 1)
            if abs(drift) > TOLERANCE:
                rep.status = "REWORK"
                rep.note = (f"대본 예상 {exp}s 대비 {rep.drift_pct:+.1f}% 어긋남 "
                            f"(허용 ±{int(TOLERANCE * 100)}%)")
        if duration < 1.0:
            rep.status = "REWORK"
            rep.note = "영상이 1초 미만입니다 — 씬이 사실상 비어 있습니다."

        if args.frames:
            rep.frames = extract_frames(mp4, episode / "verify_frames", args.frames, duration)
        reports.append(rep)

    print("=" * 90)
    for r in reports:
        exp = f" / 예상 {r.expected_sec}s ({r.drift_pct:+.1f}%)" if r.expected_sec else ""
        print(f"  {r.status:<7} {r.scene:<20} {r.duration_sec:>6.2f}s{exp}  "
              f"{r.width}x{r.height}@{r.fps}  {r.size_mb}MB")
        if r.note:
            print(f"          → {r.note}")
        for f in r.frames:
            print(f"          frame: {f}")
    print("=" * 90)

    bad = [r for r in reports if r.status != "OK"]
    print(f"  {len(reports) - len(bad)}/{len(reports)} OK"
          + (f", {len(bad)} REWORK" if bad else ""))
    if not expected:
        print("  (shots.json이 없어 길이 정합은 검사하지 못했습니다)")

    if args.json:
        print(json.dumps({"episode": str(episode), "quality": args.quality,
                          "rework": len(bad), "reports": [asdict(r) for r in reports]},
                         ensure_ascii=False))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
