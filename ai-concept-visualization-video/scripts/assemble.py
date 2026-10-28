"""씬 영상을 shots.json 순서로 잇고 자막을 구워 최종 영상을 만든다.

    python assemble.py --episode <dir> [--silent]

1. shots.json 씬 순서대로 videos/<S>.mp4 를 ffmpeg concat(-c copy) → _scenes.mp4
   (파일 정의 순서나 알파벳 순서가 아니다. 빠진 씬 영상이 있으면 exit 1)
2. 씬마다 실제 길이(ffprobe)를 scene_durs.json 에 shots.json 순서로 적는다.
3. captions.py 로 captions.ass 를 만든다(cuelog 실제 시각 + scene_durs 오프셋).
4. 에피소드 폴더를 cwd 로 두고 `subtitles=captions.ass`(상대 경로)로 구워
   <episode>_FINAL.mp4 를 만든다. 경로에 공백·한글이 있어도 필터 문법이 깨지지 않는다.
   --silent 면 음성 트랙이 없다(-an). tts·silent 모두 burn() 하나로 굽는다.
   굽기 로그의 libass fontselect 줄로 자막 글꼴이 NotoSansKR-Medium 인지 확인하고,
   다른 글꼴로 바뀌었으면 FAIL(exit 1). 대체 글꼴로 그린 글자는 WARN caption glyph 로 찍는다.

<episode> 는 shots.json 의 "episode" 값(없으면 폴더 이름)이다.

tts 모드(shots.json "mode": "tts", --silent 없음)
- 큐마다 tts/<id>.mp3 (tts.py 가 만든다)를 그 큐의 실제 시작 시각에 놓는다.
  시작 시각 = 앞 씬들의 실제 영상 길이 합(scene_durs) + cuelog 의 start. 자막과 같은 시각이다.
  cuelog 가 실제 시각을 주므로 씬 단위 비율 보정(paper-to-manim-video tts_narrate)은 필요 없다.
- ffmpeg adelay + amix(normalize=0) 로 섞고 apad + -t 로 영상 길이에 맞춰 늘이거나 자른다
  → narration.wav. 굽기 때 AAC 음성 트랙으로 넣는다.
- 음성이 자기 큐 자리보다 0.35초 넘게 길면 WARN audio overrun 을 찍는다.
- 자막을 별도 트랙용 <episode>.srt 로도 쓴다.
- mp3 가 빠진 큐가 있으면 exit 1. --silent 를 주면 tts 모드여도 음성 없이 만든다(미리 보기).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import captions as _captions  # noqa: E402
import cues as _cues  # noqa: E402

SCENES_MP4 = "_scenes.mp4"
CONCAT_LIST = "_concat.txt"
NARRATION = "narration.wav"
AUDIO_FILTER = "_audio_filter.txt"
AUDIO_RATE = 48000
AUDIO_OVERRUN_WARN = 0.35


def probe_duration(mp4: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(mp4)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _ffmpeg(args: list[str], cwd: Path, loglevel: str = "error") -> subprocess.CompletedProcess:
    return subprocess.run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-loglevel", loglevel, *args],
                          cwd=str(cwd), capture_output=True, encoding="utf-8", errors="replace")


def scene_order(shots: dict) -> list[str]:
    return [s["name"] for s in shots.get("scenes", [])]


def final_name(shots: dict, ep: Path) -> str:
    return f"{shots.get('episode') or ep.name}_FINAL.mp4"


def concat_scenes(ep: Path, names: list[str]) -> dict[str, float]:
    """videos/<S>.mp4 를 names 순서로 이어 _scenes.mp4 를 만들고 {S: 길이} 를 돌려준다."""
    durs: dict[str, float] = {}
    lines = []
    for name in names:
        rel = f"videos/{name}.mp4"
        durs[name] = round(probe_duration(ep / rel), 4)
        lines.append(f"file '{rel}'")
    (ep / CONCAT_LIST).write_text("\n".join(lines) + "\n", encoding="utf-8")
    proc = _ffmpeg(["-f", "concat", "-safe", "0", "-i", CONCAT_LIST, "-c", "copy", SCENES_MP4], ep)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed:\n{proc.stderr[-2000:]}")
    return durs


def load_timing(ep: Path, shots: dict) -> dict:
    timing_path = ep / "timing.json"
    if timing_path.exists():
        return json.loads(timing_path.read_text(encoding="utf-8"))
    audio_durs = None
    durs_path = ep / "tts" / "durs.json"
    if shots.get("mode") == "tts" and durs_path.exists():
        audio_durs = json.loads(durs_path.read_text(encoding="utf-8"))
    return _cues.build_timing(shots, audio_durs)


def cue_slots(ep: Path, shots: dict, scene_durs: dict[str, float]) -> list[tuple[str, str, float, float]]:
    """[(id, t, start, end)] — 이어 붙인 영상 기준 초. 자막과 같은 시각."""
    timing = load_timing(ep, shots)
    items = _captions.cue_times(shots, timing, _captions.load_cuelogs(ep), scene_durs)
    ids = [cue["id"] for _, cue in _cues.iter_cues(shots)]
    if len(ids) != len(items):
        raise ValueError(f"cue count mismatch: shots {len(ids)} vs captions {len(items)}")
    return [(cid, t, s, e) for cid, (t, s, e) in zip(ids, items)]


def build_captions(ep: Path, shots: dict, slots: list[tuple[str, str, float, float]]) -> int:
    items = [(t, s, e) for _, t, s, e in slots]
    ass = _captions.to_ass(items, _captions.keys_from_shots(shots))
    (ep / "captions.ass").write_text(ass, encoding="utf-8")
    return len(items)


def srt_time(sec: float) -> str:
    ms = int(round(max(0.0, sec) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(path: Path, slots: list[tuple[str, str, float, float]]) -> None:
    blocks = [f"{i}\n{srt_time(s)} --> {srt_time(e)}\n{t}\n"
              for i, (_, t, s, e) in enumerate(slots, 1)]
    path.write_text("\n".join(blocks), encoding="utf-8")


def build_narration(ep: Path, slots: list[tuple[str, str, float, float]], total: float) -> list[str]:
    """tts/<id>.mp3 를 큐 시작 시각에 놓아 narration.wav(영상 길이)를 만든다. 경고 줄을 돌려준다."""
    missing = [cid for cid, *_ in slots if not (ep / "tts" / f"{cid}.mp3").is_file()]
    if missing:
        raise RuntimeError(f"missing tts audio (run tts.py first): {', '.join(missing)}")

    warnings = []
    inputs: list[str] = []
    chains: list[str] = []
    for i, (cid, _, start, end) in enumerate(slots):
        rel = f"tts/{cid}.mp3"
        inputs += ["-i", rel]
        ms = max(0, int(round(start * 1000)))
        chains.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates={AUDIO_RATE}:channel_layouts=mono,"
                      f"adelay={ms}:all=1[a{i}]")
        over = probe_duration(ep / rel) - (end - start)
        if over > AUDIO_OVERRUN_WARN:
            warnings.append(f"WARN audio overrun {cid} +{over:.2f}s (voice longer than its cue)")
    if len(slots) == 1:
        mix = "[a0]apad[out]"
    else:
        labels = "".join(f"[a{i}]" for i in range(len(slots)))
        mix = f"{labels}amix=inputs={len(slots)}:normalize=0:dropout_transition=0,apad[out]"
    (ep / AUDIO_FILTER).write_text(";\n".join(chains + [mix]) + "\n", encoding="utf-8")

    tmp = "_narration_tmp.wav"
    proc = _ffmpeg([*inputs, "-filter_complex_script", AUDIO_FILTER, "-map", "[out]",
                    "-t", f"{total:.3f}", "-ar", str(AUDIO_RATE), "-ac", "1", "-c:a", "pcm_s16le", tmp], ep)
    if proc.returncode != 0:
        (ep / tmp).unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg audio mix failed:\n{proc.stderr[-2000:]}")
    (ep / tmp).replace(ep / NARRATION)
    (ep / AUDIO_FILTER).unlink(missing_ok=True)
    last_end = max(start + probe_duration(ep / "tts" / f"{cid}.mp3") for cid, _, start, _ in slots)
    if last_end > total + 0.05:
        warnings.append(f"WARN audio cut at video end ({last_end - total:.2f}s past {total:.2f}s)")
    return warnings


def burn(ep: Path, out_name: str, silent: bool, audio: str | None = None) -> list[str]:
    """captions.ass 를 구워 out_name 을 만든다. tts·silent 두 경로가 모두 이 함수를 쓴다.

    libass 로그(-loglevel info)의 fontselect 줄로 자막 글꼴이 captions.CAPTION_FONT_PS 인지 확인한다.
    다른 글꼴로 바뀌었으면 RuntimeError(조용히 대체 글꼴로 굽지 않는다). 대체 글꼴로 그린 글자는 경고로 돌려준다.
    """
    args = ["-i", SCENES_MP4]
    if audio and not silent:
        args += ["-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"]
    args += ["-vf", "subtitles=captions.ass",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart"]
    if silent or not audio:
        args.append("-an")
    tmp = "_FINAL_tmp.mp4"
    proc = _ffmpeg(args + [tmp], ep, loglevel="info")
    if proc.returncode != 0:
        (ep / tmp).unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg subtitles burn failed:\n{proc.stderr[-2000:]}")
    font_err, font_warns = _captions.check_fontselect(proc.stderr)
    if font_err:
        (ep / tmp).unlink(missing_ok=True)
        raise RuntimeError(f"{font_err} (run preflight.py)")
    (ep / tmp).replace(ep / out_name)
    return font_warns


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="씬 잇기 + 자막 굽기 → <episode>_FINAL.mp4")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--silent", action="store_true", help="음성 트랙 없이 만든다")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    ep = Path(args.episode).resolve()
    shots_path = ep / "shots.json"
    if not shots_path.exists():
        print(f"FAIL {shots_path} not found")
        return 1
    shots = json.loads(shots_path.read_text(encoding="utf-8"))
    with_voice = shots.get("mode", "silent") == "tts" and not args.silent

    names = scene_order(shots)
    if not names:
        print("FAIL shots.json has no scenes")
        return 1
    missing = [n for n in names if not (ep / "videos" / f"{n}.mp4").exists()]
    if missing:
        print(f"FAIL missing scene videos (render them first): {', '.join(missing)}")
        return 1

    out_name = final_name(shots, ep)
    (ep / out_name).unlink(missing_ok=True)
    warnings: list[str] = []
    try:
        durs = concat_scenes(ep, names)
        (ep / "scene_durs.json").write_text(json.dumps(durs, ensure_ascii=False, indent=1), encoding="utf-8")
        slots = cue_slots(ep, shots, durs)
        n = build_captions(ep, shots, slots)
        audio = None
        if with_voice:
            (ep / NARRATION).unlink(missing_ok=True)
            warnings = build_narration(ep, slots, probe_duration(ep / SCENES_MP4))
            write_srt(ep / f"{shots.get('episode') or ep.name}.srt", slots)
            audio = NARRATION
        warnings += burn(ep, out_name, silent=not with_voice, audio=audio)
    except (RuntimeError, subprocess.CalledProcessError, ValueError, KeyError) as e:
        print(f"FAIL {e}")
        return 1

    final = ep / out_name
    total = probe_duration(final)
    expected = sum(durs.values())
    for name, d in durs.items():
        print(f"{name}\t{d:.2f}s")
    print(f"captions {n} cues -> {ep / 'captions.ass'}")
    if with_voice:
        print(f"voice {n} clips -> {ep / NARRATION}")
    for w in warnings:
        print(w)
    print(f"FINAL {final} {total:.2f}s (scenes sum {expected:.2f}s)")
    if abs(total - expected) > 0.15:
        print(f"WARN final length differs from scene sum by {total - expected:+.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
