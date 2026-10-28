"""자막 큐 길이 계산과 timing.json 생성.

shots.json(스키마는 references/shots-schema.md)의 큐마다 길이(초)를 정한다.
- silent 모드: estimate(t) = max(1.2, n_syll/5.5 + 0.25*쉼표 + 0.55*물음표)
- tts 모드: 합성한 음성의 실측 길이(audio_durs)

CLI:
    python cues.py --episode <dir> [--audio <dir>/tts]
    → <dir>/timing.json 을 쓰고 씬별 길이와 총길이를 찍는다.
    tts 모드는 --audio 폴더(기본 <dir>/tts)의 durs.json(tts.py 가 쓴다)을 쓴다.
    durs.json 이 없거나 빠진 큐가 있으면 FAIL 줄을 찍고 exit 1.

timing.json 형식(CueScene.setup()이 읽는다):
    {"c001": {"scene": "Hook", "dur": 1.2}, ...}   # shots.json 큐 순서 유지
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MIN_DUR = 1.2
SYLL_PER_SEC = 5.5
COMMA_PAUSE = 0.25
QUESTION_PAUSE = 0.55
MAX_CHARS_PER_SEC = 6.4  # 공백 뺀 글자 속도 상한(참고 영상 중앙값). 넘으면 큐를 쪼갤 것.
MODES = ("silent", "tts")

_HANGUL = re.compile(r"[가-힣]")
_LATIN_WORD = re.compile(r"[A-Za-z]+")
# 숫자 덩어리: 1,000 / 3.14 / 16 처럼 자리 구분 쉼표나 소수점으로 이어진 것은 한 덩어리
_NUMBER = re.compile(r"[0-9]+(?:[.,][0-9]+)*")
_COMMA = re.compile(r"[,，、]")
_QUESTION = re.compile(r"[?？]")


def syllables(t: str) -> int:
    """한글 음절 수 + 라틴 단어 수 + 숫자 덩어리 수."""
    return len(_HANGUL.findall(t)) + len(_LATIN_WORD.findall(t)) + len(_NUMBER.findall(t))


def _pause_counts(t: str) -> tuple[int, int]:
    # 숫자 자리 구분 쉼표(1,000)는 쉼으로 세지 않는다
    no_numbers = _NUMBER.sub("0", t)
    return len(_COMMA.findall(no_numbers)), len(_QUESTION.findall(no_numbers))


def estimate(t: str) -> float:
    """무음 모드 큐 길이(초). 반올림하지 않는다."""
    commas, questions = _pause_counts(t)
    return max(MIN_DUR, syllables(t) / SYLL_PER_SEC + COMMA_PAUSE * commas + QUESTION_PAUSE * questions)


def iter_cues(shots: dict):
    """(scene_name, cue) 를 shots.json 순서대로 돌려준다."""
    for scene in shots.get("scenes", []):
        name = scene["name"]
        for cue in scene.get("cues", []):
            yield name, cue


def build_timing(shots: dict, audio_durs: dict[str, float] | None = None) -> dict[str, dict]:
    """{cue_id: {"scene": str, "dur": float}} 를 shots.json 큐 순서로 만든다.

    silent 모드는 estimate(t), tts 모드는 audio_durs[cue_id] 를 쓴다.
    hold 는 표식일 뿐 길이에 반영하지 않는다(references/shots-schema.md).
    """
    mode = shots.get("mode", "silent")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    if mode == "tts" and audio_durs is None:
        raise ValueError("tts mode needs audio_durs (run tts.py first)")

    timing: dict[str, dict] = {}
    for scene_name, cue in iter_cues(shots):
        cid = cue["id"]
        if cid in timing:
            raise ValueError(f"duplicate cue id {cid!r} (scenes {timing[cid]['scene']!r}, {scene_name!r})")
        if mode == "tts":
            if cid not in audio_durs:
                raise KeyError(f"no audio duration for cue {cid!r}")
            dur = float(audio_durs[cid])
        else:
            dur = round(estimate(cue["t"]), 3)
        timing[cid] = {"scene": scene_name, "dur": dur}
    return timing


def scene_totals(timing: dict[str, dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for v in timing.values():
        totals[v["scene"]] = totals.get(v["scene"], 0.0) + v["dur"]
    return totals


def rate_warnings(shots: dict, timing: dict[str, dict]) -> list[str]:
    out = []
    for _, cue in iter_cues(shots):
        n = len(re.sub(r"\s", "", cue["t"]))
        dur = timing[cue["id"]]["dur"]
        if dur > 0 and n / dur > MAX_CHARS_PER_SEC:
            out.append(f"WARN rate {cue['id']} {n / dur:.1f} chars/s > {MAX_CHARS_PER_SEC} (split the cue)")
    return out


def _fmt(sec: float) -> str:
    m, s = divmod(sec, 60)
    return f"{int(m)}:{s:05.2f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="shots.json → timing.json")
    ap.add_argument("--episode", required=True, help="에피소드 폴더(shots.json 이 있는 곳)")
    ap.add_argument("--audio", default=None,
                    help="tts 모드: durs.json 이 있는 폴더(기본 <episode>/tts, tts.py 가 쓴다)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    ep = Path(args.episode)
    shots = json.loads((ep / "shots.json").read_text(encoding="utf-8"))
    audio_durs = None
    if shots.get("mode") == "tts":
        durs_path = Path(args.audio or ep / "tts") / "durs.json"
        if not durs_path.exists():
            print(f"FAIL {durs_path} not found (tts mode: run tts.py --episode first)")
            return 1
        audio_durs = json.loads(durs_path.read_text(encoding="utf-8"))
        missing = [c["id"] for _, c in iter_cues(shots) if c["id"] not in audio_durs]
        if missing:
            print(f"FAIL no audio duration for cues {', '.join(missing)} (run tts.py again)")
            return 1
    timing = build_timing(shots, audio_durs)

    (ep / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")

    totals = scene_totals(timing)
    for name, sec in totals.items():
        n = sum(1 for v in timing.values() if v["scene"] == name)
        print(f"{name}\t{n} cues\t{sec:.2f}s ({_fmt(sec)})")
    total = sum(totals.values())
    print(f"TOTAL\t{len(timing)} cues\t{total:.2f}s ({_fmt(total)})")
    for w in rate_warnings(shots, timing):
        print(w)
    print(f"wrote {ep / 'timing.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
