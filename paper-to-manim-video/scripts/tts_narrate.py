"""Synthesize the narration and lay it on the video's own timeline.

Why this can be exact
---------------------
The video was built from shots.json: every shot occupies `run_time + wait`
seconds, in order. So each line's start time is already known — the audio does
not need aligning, it needs *placing*.

One correction is required. The rendered scene also contains transition cuts
that carry no narration and therefore are not in shots.json, so a scene runs
~4-8% longer than the sum of its shots. This script measures each rendered
scene with ffprobe and scales that scene's shot timeline by the real ratio, so
the drift is absorbed evenly instead of accumulating to the end of the episode.
Residual error inside a scene is a few hundred milliseconds.

    python tts_narrate.py --episode <ep> --quality qh
    python tts_narrate.py --episode <ep> --voice ko-KR-SunHiNeural --fit

Outputs, next to shots.json:
    narration.mp3   full-episode track, silence-padded so each line lands on cue
    narration.srt   cue times from the same timeline, durations measured from audio
    tts/            per-shot mp3s (kept, so a single line can be re-recorded)
"""

from __future__ import annotations

import argparse
import asyncio
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

try:
    import edge_tts
except ImportError:  # pragma: no cover
    print("edge-tts가 필요합니다:  uv pip install edge-tts", file=sys.stderr)
    raise SystemExit(1)

QUALITY_DIR = {"ql": "480p15", "qm": "720p30", "qh": "1080p60", "qk": "2160p60"}

# Mixed Korean/English narration is the norm here ("토큰", "RNN", "BPE"),
# and the multilingual voice handles the switch without mangling the English.
DEFAULT_VOICE = "ko-KR-HyunsuMultilingualNeural"

SAMPLE_RATE = 24000  # edge-tts native
OVERRUN_WARN = 0.35  # seconds a line may exceed its slot before we complain


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def duration_of(path: Path) -> float:
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)])
    try:
        return round(float(p.stdout.strip()), 3)
    except ValueError:
        return 0.0


def srt_stamp(seconds: float) -> str:
    h, rem = divmod(max(0.0, seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def scene_blocks(payload: dict) -> list[tuple[str, list[dict]]]:
    if "scenes" in payload:
        return [(name, block.get("shots", [])) for name, block in payload["scenes"].items()]
    if "shots" in payload:
        return [(payload.get("video", "main"), payload["shots"])]
    return []


async def synth(text: str, out: Path, voice: str, rate: str) -> None:
    comm = edge_tts.Communicate(text, voice, rate=rate)
    await comm.save(str(out))


def make_silence(seconds: float, out: Path) -> None:
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono", "-t", f"{max(0.01, seconds):.3f}",
         "-c:a", "libmp3lame", "-q:a", "6", str(out)])


def main() -> int:
    ap = argparse.ArgumentParser(description="대본 → 음성 트랙 + 정확한 자막")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--quality", default="qh", choices=list(QUALITY_DIR),
                    help="씬 길이 실측에 쓸 렌더 품질")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--rate", default="+0%", help="말하기 속도 (예: +10%%)")
    ap.add_argument("--fit", action="store_true",
                    help="슬롯을 넘치는 줄은 속도를 올려 다시 합성해 맞춘다")
    ap.add_argument("--force", action="store_true", help="이미 만든 per-shot mp3도 다시 합성")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for exe in ("ffmpeg", "ffprobe"):
        if shutil.which(exe) is None:
            raise SystemExit(f"{exe}가 PATH에 없습니다.")

    episode = Path(args.episode).resolve()
    shots_path = episode / "shots.json"
    if not shots_path.is_file():
        raise SystemExit(f"shots.json이 없습니다: {shots_path}")
    payload = json.loads(shots_path.read_text(encoding="utf-8"))

    video_dir = episode / "media" / "videos" / "main" / QUALITY_DIR[args.quality]
    tts_dir = episode / "tts"
    tts_dir.mkdir(exist_ok=True)

    # --- 1. build the timeline, scene by scene, scaled to the real render -------
    timeline: list[dict] = []
    clock = 0.0
    scale_report: list[dict] = []

    for scene_name, shots in scene_blocks(payload):
        expected = sum(float(s.get("run_time", 0)) + float(s.get("wait", 0)) for s in shots)
        mp4 = video_dir / f"{scene_name}.mp4"
        actual = duration_of(mp4) if mp4.is_file() else 0.0
        scale = (actual / expected) if (actual > 0 and expected > 0) else 1.0
        scale_report.append({"scene": scene_name, "expected_sec": round(expected, 2),
                             "actual_sec": actual, "scale": round(scale, 4)})

        for shot in shots:
            slot = (float(shot.get("run_time", 0)) + float(shot.get("wait", 0))) * scale
            # The line is spoken while the animation plays, so it starts with the shot.
            timeline.append({
                "id": shot.get("id", f"{scene_name}_?"),
                "scene": scene_name,
                "text": (shot.get("narration") or "").strip(),
                "start": round(clock, 3),
                "slot": round(slot, 3),
            })
            clock += slot
        # Absorb any rounding residue so the next scene starts on its real boundary.
        if actual > 0:
            clock = round(sum(s["actual_sec"] for s in scale_report), 3)

    total = round(clock, 2)
    spoken = [t for t in timeline if t["text"]]
    print(f"[tts] {episode.name} — {len(spoken)}줄 / 타임라인 {total}초")
    for r in scale_report:
        print(f"      {r['scene']:<14} 예상 {r['expected_sec']:>6.1f}s → 실제 "
              f"{r['actual_sec']:>6.2f}s  (×{r['scale']:.3f})")

    # --- 2. synthesize each line ------------------------------------------------
    overruns = []
    for t in spoken:
        clip = tts_dir / f"{t['id']}.mp3"
        if args.force or not clip.is_file():
            asyncio.run(synth(t["text"], clip, args.voice, args.rate))
        t["audio"] = duration_of(clip)

        if args.fit and t["audio"] > t["slot"] - 0.05 and t["slot"] > 0.5:
            # Speak faster rather than run over the animation it belongs to.
            need = t["audio"] / (t["slot"] - 0.05)
            pct = min(60, int(round((need - 1) * 100)) + 2)
            if pct > 0:
                asyncio.run(synth(t["text"], clip, args.voice, f"+{pct}%"))
                t["audio"] = duration_of(clip)
                t["refit"] = f"+{pct}%"
        t["clip"] = clip
        if t["audio"] > t["slot"] + OVERRUN_WARN:
            overruns.append(t)

    # --- 3. lay the clips onto silence so each starts exactly on cue ------------
    parts: list[Path] = []
    listing = tts_dir / "_concat.txt"
    cursor = 0.0
    for i, t in enumerate(spoken):
        gap = t["start"] - cursor
        if gap > 0.02:
            sil = tts_dir / f"_sil{i:03d}.mp3"
            make_silence(gap, sil)
            parts.append(sil)
            cursor += gap
        parts.append(t["clip"])
        cursor += t["audio"]
    if total - cursor > 0.05:
        tail = tts_dir / "_siltail.mp3"
        make_silence(total - cursor, tail)
        parts.append(tail)

    listing.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts) + "\n",
                       encoding="utf-8")
    narration = episode / "narration.mp3"
    proc = run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", str(listing), "-c:a", "libmp3lame", "-ar", str(SAMPLE_RATE),
                "-ac", "1", "-q:a", "4", str(narration)])
    if proc.returncode != 0:
        raise SystemExit(f"오디오 결합 실패: {proc.stderr.strip()[:300]}")

    # --- 4. subtitles from the same timeline, ends measured from real audio ----
    cues = []
    for i, t in enumerate(spoken, 1):
        end = t["start"] + max(t["audio"], 0.8)
        nxt = spoken[i].get("start") if i < len(spoken) else None
        if nxt is not None:
            end = min(end, nxt - 0.05)
        cues.append(f"{i}\n{srt_stamp(t['start'])} --> {srt_stamp(end)}\n{t['text']}\n")
    (episode / "narration.srt").write_text("\n".join(cues), encoding="utf-8")

    # Silence spacers were scaffolding for the concat; keep only the spoken clips
    # so `tts/` stays a re-recordable set of one file per line.
    made = duration_of(narration)
    for junk in list(tts_dir.glob("_sil*.mp3")) + [listing]:
        junk.unlink(missing_ok=True)

    print(f"[tts] {narration}  ({made}초, 목표 {total}초)")
    print(f"[tts] {episode / 'narration.srt'}  ({len(cues)} cues)")
    if overruns:
        print(f"[tts] 슬롯을 {OVERRUN_WARN}초 넘게 초과한 줄 {len(overruns)}개 "
              f"— 문장을 줄이거나 --fit 을 쓰세요:")
        for t in overruns[:8]:
            print(f"      {t['id']}  음성 {t['audio']:.1f}s > 슬롯 {t['slot']:.1f}s")

    if args.json:
        print(json.dumps({"episode": str(episode), "mp3": str(narration),
                          "srt": str(episode / "narration.srt"),
                          "lines": len(spoken), "timeline_sec": total,
                          "audio_sec": made, "overruns": len(overruns),
                          "scenes": scale_report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
