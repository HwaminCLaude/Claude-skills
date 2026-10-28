"""shots.json + timing.json(+ cuelog, scene_durs) → captions.ass

시각은 이어 붙인 영상(shots.json 씬 순서) 기준이다.
- 씬 오프셋 = 앞 씬들의 실제 영상 길이 합(scene_durs). 없으면 큐 길이 합으로 대신한다.
- 씬 안의 큐 시작 = cuelog 의 실제 start. 없으면 앞 큐의 시작 + 길이로 이어 간다.
  큐 길이는 max(dur, elapsed)다(CueScene 은 dur − 경과가 양수일 때만 기다린다).
- 큐 끝 = 다음 큐 시작(빈틈 0). 씬 마지막 큐 끝 = 씬 경계.
- 길이 0 이 된 자막(씬 영상이 마지막 큐 시작보다 짧은 경우 등)은 `WARN caption zero-length` 를 찍는다.
- cuelog 항목의 start/dur/elapsed 가 null 이면 ValueError(씬·큐 id, render 를 다시 돌리라는 안내).
  cuelog 항목의 모르는 키(예: plays)는 무시한다.

글꼴: 'Noto Sans KR Medium'(정적 NotoSansKR-Medium.ttf 의 가족 이름), Bold 0.
'Noto Sans KR' 을 쓰면 Windows 의 NotoSansKR-VF.ttf(기본 인스턴스 Thin)로 떨어져 Bold 가 듣지 않는다.
libass 가 실제로 고른 글꼴은 check_fontselect() 로 확인한다(preflight.py, assemble.py 가 쓴다).

CLI:
    python captions.py --episode <dir> [--scene-durs <json 파일 경로 또는 JSON 문자열>]
    → <dir>/captions.ass
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cues as _cues  # noqa: E402

TEXT_COLOR = "&H00DCDCDC"
KEY_COLOR = "&H0025CFEA"  # #EACF25 (ASS 는 &HAABBGGRR)

# 설계 §5.6 'Bold' 의 구현: 정적 Medium(굵기 500) 파일을 가족 이름으로 고르고 Bold 0.
# 'Noto Sans KR' + Bold -1 은 VF Thin 에 떨어져 획 2px(참고 영상 약 4px)이 된다.
# 정적 Bold 파일(fontsdir)은 획 6px로 참고 영상보다 무겁다. 2026-10-27 눈 비교로 Medium 을 골랐다.
CAPTION_FONT = "Noto Sans KR Medium"
CAPTION_FONT_PS = "NotoSansKR-Medium"  # libass fontselect 가 골라야 하는 PostScript 이름
CAPTION_BOLD = 0
WORD_JOINER = "⁠"  # 백슬래시 뒤에 끼워 \N, \h 같은 ASS 제어열을 끊는다(보이지 않음)

ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{CAPTION_FONT},64,{TEXT_COLOR},{TEXT_COLOR},&H00000000,&H00000000,{CAPTION_BOLD},0,0,0,100,100,0,0,1,0,0,2,60,60,103,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _cuelog_entries(log) -> dict[str, dict]:
    """cuelog 파일 내용({"scene", "cues": [...]}) 또는 큐 목록 → {id: entry}."""
    if log is None:
        return {}
    entries = log.get("cues", []) if isinstance(log, dict) else log
    return {e["id"]: e for e in entries}


def _logged_num(entry: dict, key: str, scene: str, cid: str, default: float | None = None) -> float:
    """cuelog 항목의 숫자 값. 키가 없으면 default, 값이 null 이면 원인이 보이는 ValueError."""
    if key not in entry:
        if default is None:
            raise ValueError(f"cuelog/{scene}.json cue {cid}: '{key}' missing "
                             f"(re-run render.py for scene {scene})")
        return default
    val = entry[key]
    if val is None:
        raise ValueError(f"cuelog/{scene}.json cue {cid}: '{key}' is null "
                         f"(render did not finish this cue; re-run render.py for scene {scene})")
    return float(val)


def cue_times(shots: dict, timing: dict, cuelogs: dict | None = None,
              scene_durs: dict[str, float] | None = None) -> list[tuple[str, float, float]]:
    """[(t, start, end), ...] 를 shots.json 큐 순서로 돌려준다(이어 붙인 영상 기준 초).

    cuelogs: {scene_name: cuelog/<scene>.json 내용}. 없거나 빠진 씬·큐는 timing 으로 이어 간다.
    scene_durs: {scene_name: 실제 영상 길이(초)}. 있으면 씬 오프셋과 씬 경계에 쓴다.
    길이 0 자막이 생기면 stdout 에 WARN 줄을 찍는다.
    """
    cuelogs = cuelogs or {}
    scene_durs = scene_durs or {}
    items: list[list] = []  # [t, start, end, cid]
    offset = 0.0

    for scene in shots.get("scenes", []):
        name = scene["name"]
        logged = _cuelog_entries(cuelogs.get(name))
        cursor = 0.0  # 씬 안 시각: 다음 큐가 시작할 자리
        scene_items: list[list] = []
        for cue in scene.get("cues", []):
            cid = cue["id"]
            dur = float(timing[cid]["dur"]) if cid in timing else _cues.estimate(cue["t"])
            entry = logged.get(cid)
            if entry is not None:
                start = _logged_num(entry, "start", name, cid)
                length = max(_logged_num(entry, "dur", name, cid, dur),
                             _logged_num(entry, "elapsed", name, cid, 0.0))
            else:
                start = cursor
                length = dur
            scene_items.append([cue["t"], start, None, cid])
            cursor = start + length

        scene_len = float(scene_durs[name]) if name in scene_durs else cursor
        for i, it in enumerate(scene_items):
            last = i + 1 == len(scene_items)
            local_start = it[1]
            local_end = scene_len if last else scene_items[i + 1][1]
            it[1] = offset + local_start
            it[2] = offset + max(local_end, local_start)
            if local_end - local_start <= 1e-6:
                why = (f"scene length {scene_len:.2f}s <= last cue start {local_start:.2f}s" if last
                       else f"next cue starts at {local_end:.2f}s <= {local_start:.2f}s")
                print(f"WARN caption zero-length scene {name} cue {it[3]} at {it[1]:.2f}s ({why})",
                      flush=True)
        items.extend(scene_items)
        offset += scene_len

    return [(t, s, e) for t, s, e, _ in items]


def ass_time(sec: float) -> str:
    """초 → H:MM:SS.cc"""
    cs = int(round(max(0.0, sec) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape(text: str) -> str:
    """큐 문구가 ASS 에서 글자 그대로 보이게 한다.

    - 백슬래시 뒤에 WORD JOINER(U+2060)를 끼워 \\N, \\n, \\h 가 줄바꿈·공백으로 읽히지 않게 한다.
      이 단계를 먼저 해야 아래에서 넣는 \\{ 의 백슬래시를 건드리지 않는다.
    - 중괄호는 \\{ \\} 로 막아 {\\...} 재정의 블록이 되지 않게 한다.
    libass 0.17.5(ffmpeg 8.1.2)에서 둘 다 글자 그대로 그려지는 것을 확인했다(U+2060 은 보이지 않는다).
    """
    text = " ".join(text.splitlines())
    text = text.replace("\\", "\\" + WORD_JOINER)
    return text.replace("{", r"\{").replace("}", r"\}")


def _colorize(t: str, key: str | None) -> str:
    if not key or key not in t:
        return _escape(t)
    i = t.index(key)
    return (_escape(t[:i]) + "{\\c" + KEY_COLOR + "&}" + _escape(key)
            + "{\\c" + TEXT_COLOR + "&}" + _escape(t[i + len(key):]))


def to_ass(items, keys: dict[str, str]) -> str:
    """items: [(t, start, end)], keys: {t: 노랑으로 칠할 부분 문자열}."""
    lines = [ASS_HEADER]
    for t, start, end in items:
        text = _colorize(t, keys.get(t))
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{text}\n")
    return "".join(lines)


_FONTSELECT = re.compile(r"fontselect: \((.+?), (\d+), (\d+)\) -> ([^,\s]+)")
_GLYPH_MISS = re.compile(r"Glyph (0x[0-9A-Fa-f]+) not found")


def check_fontselect(log: str) -> tuple[str | None, list[str]]:
    """ffmpeg subtitles 필터 로그(-loglevel info 이상)로 libass 가 고른 자막 글꼴을 확인한다.

    돌려주는 값: (오류 문구 또는 None, 경고 줄 목록).
    - CAPTION_FONT 에 대한 첫 fontselect 줄이 CAPTION_FONT_PS 가 아니면 오류다(다른 글꼴로 조용히 바뀜).
    - 'Glyph 0x... not found' 는 그 글자만 다른 글꼴로 그렸다는 뜻이라 경고로 돌려준다.
    """
    picked = None
    for m in _FONTSELECT.finditer(log):
        if m.group(1) == CAPTION_FONT:
            picked = m.group(4)
            break
    warns = [f"WARN caption glyph {g} not in {CAPTION_FONT} (drawn with a fallback font)"
             for g in dict.fromkeys(_GLYPH_MISS.findall(log))]
    if picked is None:
        return (f"libass reported no font for '{CAPTION_FONT}' "
                f"(need {CAPTION_FONT_PS}; install static NotoSansKR-Medium.ttf)", warns)
    if picked != CAPTION_FONT_PS:
        return (f"caption font '{CAPTION_FONT}' resolved to {picked}, not {CAPTION_FONT_PS} "
                f"(install static NotoSansKR-Medium.ttf; see references/troubleshooting.md)", warns)
    return None, warns


def keys_from_shots(shots: dict) -> dict[str, str]:
    keys = {}
    for _, cue in _cues.iter_cues(shots):
        if cue.get("key"):
            keys[cue["t"]] = cue["key"]
    return keys


def load_cuelogs(ep: Path) -> dict:
    out = {}
    d = ep / "cuelog"
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            name = data.get("scene", p.stem) if isinstance(data, dict) else p.stem
            out[name] = data
    return out


def _load_scene_durs(arg: str | None) -> dict | None:
    if not arg:
        return None
    p = Path(arg)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return json.loads(arg)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="shots.json + timing/cuelog → captions.ass")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--scene-durs", default=None,
                    help="씬별 실제 영상 길이 JSON 파일 경로(또는 JSON 문자열)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    ep = Path(args.episode)
    shots = json.loads((ep / "shots.json").read_text(encoding="utf-8"))
    timing_path = ep / "timing.json"
    if timing_path.exists():
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
    else:
        timing = _cues.build_timing(shots)
    items = cue_times(shots, timing, load_cuelogs(ep), _load_scene_durs(args.scene_durs))
    ass = to_ass(items, keys_from_shots(shots))
    out = ep / "captions.ass"
    out.write_text(ass, encoding="utf-8")
    print(f"wrote {out} ({len(items)} cues, {items[-1][2] if items else 0:.2f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
