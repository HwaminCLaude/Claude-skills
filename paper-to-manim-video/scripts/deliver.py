"""Concatenate each episode's scenes and copy the deliverables to one folder.

The render tree (media/videos/main/<quality>/) is a build artifact — nobody wants
to hand that to an editor. This produces a clean handoff folder: one full-episode
mp4 per episode, the recording script, the subtitles, and the individual scene
files for anyone who wants to cut them differently.

    python deliver.py --root C:\\manimwork\\my-paper --out "C:\\Users\\...\\Desktop\\video"
    python deliver.py --root ... --out ... --quality qh --episodes ep01_gap ep02_energy

Concatenation uses ffmpeg's concat demuxer with stream copy — no re-encode, so
it is fast and lossless. All scenes of an episode come from the same render pass,
so their codecs already match.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

QUALITY_DIR = {"ql": "480p15", "qm": "720p30", "qh": "1080p60", "qk": "2160p60"}


def safe_name(text: str) -> str:
    """Filesystem-safe folder name that keeps Korean readable."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "", text).strip().rstrip(".")
    return re.sub(r"\s+", "_", cleaned)[:80] or "episode"


def scene_order(episode: Path) -> list[str]:
    """Scene names in shots.json order — that is the narrative order.

    Falling back to alphabetical would splice the episode out of sequence
    (established/attribution/refuted/verdict would become attribution first).
    """
    shots = episode / "shots.json"
    if shots.is_file():
        payload = json.loads(shots.read_text(encoding="utf-8"))
        if "scenes" in payload:
            return list(payload["scenes"].keys())
    return []


def ffprobe_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return round(float(proc.stdout.strip()), 2)
    except ValueError:
        return 0.0


def concat(parts: list[Path], dest: Path) -> bool:
    listing = dest.with_suffix(".concat.txt")
    # ffmpeg's concat demuxer wants forward slashes and single-quoted paths.
    listing.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in parts) + "\n", encoding="utf-8")
    proc = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(dest)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    listing.unlink(missing_ok=True)
    if proc.returncode != 0:
        print(f"    ! ffmpeg concat 실패: {proc.stderr.strip()[:200]}")
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="에피소드 합치기 + 산출물 납품 폴더 구성")
    ap.add_argument("--root", required=True, help="프로젝트 루트")
    ap.add_argument("--out", required=True, help="납품 폴더")
    ap.add_argument("--quality", default="qh", choices=list(QUALITY_DIR))
    ap.add_argument("--episodes", nargs="*", help="대상 에피소드 (기본: ep* 전부)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg가 PATH에 없습니다.")

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    names = args.episodes or sorted(d.name for d in root.iterdir()
                                    if d.is_dir() and d.name.startswith("ep"))
    summary = []

    for name in names:
        episode = root / name
        video_dir = episode / "media" / "videos" / "main" / QUALITY_DIR[args.quality]
        if not video_dir.is_dir():
            print(f"[skip] {name} — {args.quality} 렌더 결과 없음")
            continue

        title = name
        shots = episode / "shots.json"
        if shots.is_file():
            title = json.loads(shots.read_text(encoding="utf-8")).get("title", name)

        num = name.split("_")[0].replace("ep", "")
        folder = out / f"{num}_{safe_name(title)}"
        (folder / "scenes").mkdir(parents=True, exist_ok=True)

        order = scene_order(episode)
        available = {p.stem: p for p in video_dir.glob("*.mp4")}
        ordered = [available[s] for s in order if s in available]
        # Anything shots.json didn't list still ships, just at the end.
        ordered += [p for stem, p in sorted(available.items()) if stem not in order]

        if not ordered:
            print(f"[skip] {name} — mp4 없음")
            continue

        for i, src in enumerate(ordered, 1):
            shutil.copyfile(src, folder / "scenes" / f"{i:02d}_{src.name}")

        full = folder / f"{num}_{safe_name(title)}.mp4"
        ok = concat(ordered, full) if len(ordered) > 1 else bool(
            shutil.copyfile(ordered[0], full))

        for doc in ("script.md", "narration.srt", "shots.json", "main.py"):
            src = episode / doc
            if src.is_file():
                shutil.copyfile(src, folder / doc)

        gen = episode / "assets" / "generated"
        if gen.is_dir() and any(gen.iterdir()):
            shutil.copytree(gen, folder / "생성이미지", dirs_exist_ok=True)

        dur = ffprobe_duration(full) if ok and full.exists() else 0.0
        size_mb = round(full.stat().st_size / 2**20, 2) if full.exists() else 0.0
        summary.append({"episode": name, "title": title, "folder": str(folder),
                        "scenes": len(ordered), "duration_sec": dur,
                        "size_mb": size_mb})
        mins, secs = divmod(dur, 60)
        print(f"[deliver] {folder.name}")
        print(f"          {len(ordered)} scenes → {int(mins)}분 {secs:04.1f}초, {size_mb} MB")

    if summary:
        total = sum(s["duration_sec"] for s in summary)
        series = root.name
        lines = [f"# {series} 영상 시리즈", "",
                 f"총 {len(summary)}편 · {int(total // 60)}분 {total % 60:.0f}초", ""]
        for s in summary:
            m, sec = divmod(s["duration_sec"], 60)
            lines.append(f"## {Path(s['folder']).name}")
            lines.append(f"- {s['title']}")
            lines.append(f"- {int(m)}분 {sec:04.1f}초 · {s['scenes']}개 구간 · {s['size_mb']} MB")
            lines.append(f"- 대본: `script.md` · 자막: `narration.srt` · "
                         f"구간별 mp4: `scenes/`")
            lines.append("")
        (out / "README.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"[deliver] {out / 'README.md'}")

    print(f"[deliver] 완료 — {len(summary)}편을 {out}에 정리했습니다.")
    if args.json:
        print(json.dumps({"out": str(out), "episodes": summary}, ensure_ascii=False))
    return 0 if summary else 1


if __name__ == "__main__":
    sys.exit(main())
