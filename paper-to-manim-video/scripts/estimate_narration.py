"""Estimate Korean narration read time and derive Manim wait values.

This is the hinge of the whole skill: it is what keeps the spoken script and the
rendered video the same length.

Timing contract
---------------
raenim's `playw` plays THEN waits, so a shot occupies `run_time + wait` seconds.
Putting `est_sec` straight into `wait` overshoots every shot by its run_time,
and `Write()`'s default run_time scales with text length so the error is not
even constant. Therefore:

    wait = max(MIN_WAIT, est_sec - run_time)

and `run_time` must be stated explicitly on every shot.

Usage
-----
    python estimate_narration.py --text "논문이 풀려는 문제부터 봅시다."
    python estimate_narration.py --shots shots.json --write     # fill est_sec + wait in place
    python estimate_narration.py --shots shots.json --json      # report only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Measured against typical Korean explanatory narration. Lower it for a slower,
# more deliberate delivery; raise it for brisk tutorial pacing.
DEFAULT_RATE = 5.5  # syllables per second

MIN_WAIT = 0.2      # never let a shot end the instant the animation stops
MIN_SHOT = 0.6      # floor for an absurdly short line

PAUSE = {
    ",": 0.25, "、": 0.25, ";": 0.3, ":": 0.3,
    ".": 0.55, "!": 0.55, "?": 0.55,
    "…": 0.5, "—": 0.3, "-": 0.0,
    "\n": 0.4,
}

_HANGUL_SYLLABLE = re.compile(r"[가-힣]")
_HANGUL_JAMO = re.compile(r"[ㄱ-ㆎ]")
_LATIN_WORD = re.compile(r"[A-Za-z]+")
_DIGITS = re.compile(r"\d+")
# Symbols a narrator actually pronounces (≈1.5 syllables each in Korean).
_SPOKEN_SYMBOL = re.compile(r"[%+×÷=<>≤≥±∞]")


def count_syllables(text: str) -> float:
    """Approximate spoken syllables for mixed Korean / Latin / numeric text."""
    total = 0.0
    total += len(_HANGUL_SYLLABLE.findall(text))
    total += 0.5 * len(_HANGUL_JAMO.findall(text))

    # An English word read aloud in Korean narration averages ~1 syllable per
    # 2.5 letters ("Fisher" -> 피셔, "classification" -> 클래시피케이션).
    for word in _LATIN_WORD.findall(text):
        total += max(1.0, round(len(word) / 2.5))

    # "2024" is read 이천이십사 — more syllables than digits.
    for run in _DIGITS.findall(text):
        total += len(run) * 1.3

    total += 1.5 * len(_SPOKEN_SYMBOL.findall(text))
    return total


def pause_time(text: str) -> float:
    return sum(PAUSE.get(ch, 0.0) for ch in text)


def estimate(text: str, rate: float = DEFAULT_RATE) -> float:
    """Seconds needed to read `text` aloud, including punctuation pauses."""
    if not text or not text.strip():
        return 0.0
    seconds = count_syllables(text) / rate + pause_time(text)
    return max(MIN_SHOT, round(seconds, 2))


def solve_wait(est_sec: float, run_time: float) -> tuple[float, str | None]:
    """Return (wait, warning). See the timing contract above."""
    wait = round(max(MIN_WAIT, est_sec - run_time), 2)
    warning = None
    if run_time >= est_sec:
        warning = (f"run_time {run_time}s >= est_sec {est_sec}s — the animation outlasts the "
                   f"line. Shorten run_time or split the narration; wait floored at {MIN_WAIT}s "
                   f"(shot will run {round(run_time + MIN_WAIT, 2)}s).")
    return wait, warning


def iter_shots(payload: dict):
    """Yield every shot dict, whichever layout the file uses.

    scaffold_video.py writes {"scenes": {name: {"shots": [...]}}}; a hand-written
    single-scene file may just be {"shots": [...]}. Support both.
    """
    if "scenes" in payload:
        for block in payload["scenes"].values():
            yield from block.get("shots", [])
    yield from payload.get("shots", [])


def process_shots(payload: dict, rate: float) -> tuple[dict, list[str], float]:
    warnings: list[str] = []
    total = 0.0
    count = 0
    for shot in iter_shots(payload):
        count += 1
        sid = shot.get("id", "?")
        narration = shot.get("narration", "")
        est = estimate(narration, rate)
        shot["est_sec"] = est

        run_time = shot.get("run_time")
        if run_time is None:
            # Default pacing: most of the line is animation, the tail is breathing room.
            run_time = round(min(2.0, max(0.8, est * 0.55)), 2)
            shot["run_time"] = run_time

        wait, warn = solve_wait(est, float(run_time))
        shot["wait"] = wait
        if warn:
            warnings.append(f"[{sid}] {warn}")
        total += float(run_time) + wait
    payload["total_sec"] = round(total, 2)
    payload["shot_count"] = count
    return payload, warnings, total


def main() -> int:
    ap = argparse.ArgumentParser(description="한국어 나레이션 낭독 시간 추정 및 wait 산출")
    ap.add_argument("--text", help="한 문장 추정")
    ap.add_argument("--shots", help="shots.json 경로")
    ap.add_argument("--write", action="store_true", help="shots.json을 제자리에서 갱신")
    ap.add_argument("--rate", type=float, default=DEFAULT_RATE, help=f"음절/초 (기본 {DEFAULT_RATE})")
    ap.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = ap.parse_args()

    if args.text:
        est = estimate(args.text, args.rate)
        if args.json:
            print(json.dumps({"text": args.text, "syllables": count_syllables(args.text),
                              "est_sec": est}, ensure_ascii=False))
        else:
            print(f"{est}s  ({count_syllables(args.text):.1f} syllables @ {args.rate}/s)")
        return 0

    if not args.shots:
        ap.error("--text 또는 --shots 중 하나가 필요합니다")

    path = Path(args.shots)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload, warnings, total = process_shots(payload, args.rate)

    if args.write:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps({"total_sec": payload["total_sec"], "shots": payload.get("shot_count", 0),
                          "warnings": warnings}, ensure_ascii=False))
    else:
        mins, secs = divmod(total, 60)
        print(f"{payload.get('shot_count', 0)} shots — 예상 길이 {int(mins)}분 {secs:.1f}초 "
              f"({payload['total_sec']}s)")
        for w in warnings:
            print(f"  WARN {w}")
        if args.write:
            print(f"  → {path} 갱신됨 (est_sec, run_time, wait)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
