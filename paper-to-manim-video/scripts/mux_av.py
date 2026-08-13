"""Join the rendered scenes with the narration track and the subtitles.

Produces one finished episode file. Subtitles can ride along as a selectable
track (default — the viewer can switch them off, and the text stays searchable)
or be burned into the picture (`--burn`, needed for platforms that ignore
embedded subtitle streams).

    python mux_av.py --episode <ep> --quality qh
    python mux_av.py --episode <ep> --burn            # 자막을 화면에 태움
    python mux_av.py --episode <ep> --no-audio        # 영상만 이어붙이기

The scene order comes from shots.json, not from the filesystem — alphabetical
order would splice the episode out of sequence.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
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

# Burned-in styling: readable on Manim's black stage without covering the work.
SUB_STYLE = ("FontName=Malgun Gothic,FontSize=20,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=1.6,Shadow=0,"
             "Alignment=2,MarginV=28")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def duration_of(path: Path) -> float:
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)])
    try:
        return round(float(p.stdout.strip()), 2)
    except ValueError:
        return 0.0


def scene_order(episode: Path) -> list[str]:
    shots = episode / "shots.json"
    if shots.is_file():
        payload = json.loads(shots.read_text(encoding="utf-8"))
        if "scenes" in payload:
            return list(payload["scenes"].keys())
    return []


def ffmpeg_escape(path: Path) -> str:
    """Escape a Windows path for use inside an ffmpeg filter argument.

    The subtitles filter parses its own argument string, so backslashes and the
    drive colon have to be escaped or the filter graph fails to build.
    """
    s = path.as_posix()
    return s.replace(":", r"\:")


def main() -> int:
    ap = argparse.ArgumentParser(description="영상 + 음성 + 자막 합치기")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--quality", default="qh", choices=list(QUALITY_DIR))
    ap.add_argument("--burn", action="store_true", help="자막을 화면에 태운다(재인코딩)")
    ap.add_argument("--no-audio", action="store_true", help="나레이션을 넣지 않는다")
    ap.add_argument("--no-subs", action="store_true", help="자막을 넣지 않는다")
    ap.add_argument("--out", help="출력 mp4 경로 (기본: <episode>/<이름>_FINAL.mp4)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for exe in ("ffmpeg", "ffprobe"):
        if shutil.which(exe) is None:
            raise SystemExit(f"{exe}가 PATH에 없습니다.")

    episode = Path(args.episode).resolve()
    video_dir = episode / "media" / "videos" / "main" / QUALITY_DIR[args.quality]
    if not video_dir.is_dir():
        raise SystemExit(f"렌더 결과가 없습니다: {video_dir}")

    available = {p.stem: p for p in video_dir.glob("*.mp4")}
    order = [s for s in scene_order(episode) if s in available]
    order += [s for s in sorted(available) if s not in order]
    if not order:
        raise SystemExit("합칠 mp4가 없습니다.")
    parts = [available[s] for s in order]

    work = episode / "_mux"
    work.mkdir(exist_ok=True)

    # 1) concat the scenes (stream copy — all came from one render pass)
    silent = work / "video_only.mp4"
    listing = work / "concat.txt"
    listing.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts) + "\n",
                       encoding="utf-8")
    proc = run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", str(listing), "-c", "copy", str(silent)])
    if proc.returncode != 0:
        raise SystemExit(f"영상 결합 실패: {proc.stderr.strip()[:300]}")
    print(f"[mux] 씬 {len(parts)}개 결합 → {duration_of(silent)}초")

    audio = episode / "narration.mp3"
    subs = episode / "narration.srt"
    use_audio = (not args.no_audio) and audio.is_file()
    use_subs = (not args.no_subs) and subs.is_file()
    if not args.no_audio and not audio.is_file():
        print("[mux] narration.mp3 가 없습니다 — tts_narrate.py 를 먼저 실행하세요. 무음으로 진행합니다.")
    if not args.no_subs and not subs.is_file():
        print("[mux] narration.srt 가 없습니다 — 자막 없이 진행합니다.")

    out = Path(args.out).resolve() if args.out else episode / f"{episode.name}_FINAL.mp4"

    # Every -i must precede the output options. Putting `-c:v copy` before a
    # later -i makes ffmpeg read `copy` as that input's decoder and fail with
    # "Unknown decoder 'copy'", so inputs are collected first, then codecs.
    burning = bool(args.burn) and use_subs
    inputs = [str(silent)]
    if use_audio:
        inputs.append(str(audio))
    if use_subs and not burning:
        inputs.append(str(subs))

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for src in inputs:
        cmd += ["-i", src]

    cmd += ["-map", "0:v:0"]
    idx = 1
    if use_audio:
        cmd += ["-map", f"{idx}:a:0"]
        idx += 1
    if use_subs and not burning:
        cmd += ["-map", f"{idx}:s:0"]

    if burning:
        # Burning is the only path that re-encodes the picture.
        cmd += ["-vf", f"subtitles='{ffmpeg_escape(subs)}':force_style='{SUB_STYLE}'",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
    else:
        cmd += ["-c:v", "copy"]
        if use_subs:
            cmd += ["-c:s", "mov_text", "-metadata:s:s:0", "language=kor"]

    if use_audio:
        cmd += ["-c:a", "aac", "-b:a", "160k", "-shortest"]

    cmd += [str(out)]
    proc = run(cmd)
    if proc.returncode != 0:
        raise SystemExit(f"mux 실패: {proc.stderr.strip()[:400]}")

    dur, size_mb = duration_of(out), round(out.stat().st_size / 2**20, 2)
    mins, secs = divmod(dur, 60)
    mode = "자막 태움" if (args.burn and use_subs) else ("자막 트랙" if use_subs else "자막 없음")
    print(f"[mux] {out}")
    print(f"[mux] {int(mins)}분 {secs:04.1f}초 · {size_mb} MB · "
          f"{'나레이션 있음' if use_audio else '무음'} · {mode}")

    if args.json:
        print(json.dumps({"out": str(out), "duration_sec": dur, "size_mb": size_mb,
                          "audio": use_audio, "subs": use_subs, "burned": bool(args.burn)},
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
