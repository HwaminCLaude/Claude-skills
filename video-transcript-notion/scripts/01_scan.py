"""1단계 — 영상 폴더를 훑어 차시 목록(units.json)을 만들고 자막을 구조화한다.

입력 폴더 구조:
    <source_dir>/<그룹>/<basename>.mp4      ← 그룹 = 주차·챕터 등 묶음 폴더
                        <basename>.vtt      ← 자막 (없으면 .srt, .merged.md 순으로 찾음)

자막 우선순위는 config.transcript_priority 로 바꿀 수 있다. 기본은
`["merged.md", "vtt", "srt"]` — merged.md 가 문장 정리가 가장 잘 돼 있기 때문.

**대본은 강사가 실제로 한 말만 담는다.** merged.md 에는 화면 OCR 텍스트가 섞여 있는데,
`**[HH:MM:SS]** 문장` 패턴만 뽑으므로 자동으로 발화만 남는다.

산출물
    _out/units.json  : [{key, group, seq, basename, title, duration, video, source, segments:[{t,text}]}]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vt_common as C

VTT_TS = re.compile(r"(\d{2}):(\d{2}):(\d{2})[.,]\d+\s*-->")
SRT_TS = VTT_TS
MD_TS = re.compile(r"\*\*\[(\d{2}):(\d{2}):(\d{2})\]\*\*\s*(.*)")


def secs(h: str, m: str, s: str) -> int:
    return int(h) * 3600 + int(m) * 60 + int(s)


def parse_cue_file(path: Path) -> list[dict]:
    """.vtt / .srt — `HH:MM:SS.mmm --> ...` 다음 줄들이 자막 본문."""
    segs: list[dict] = []
    pending: int | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        m = VTT_TS.match(stripped)
        if m:
            pending = secs(m[1], m[2], m[3])
            continue
        if not stripped or stripped == "WEBVTT" or stripped.isdigit():
            continue
        if pending is not None:
            segs.append({"t": pending, "text": stripped})
            pending = None
        elif segs:
            segs[-1]["text"] = (segs[-1]["text"] + " " + stripped).strip()
    return segs


def parse_merged_md(path: Path) -> list[dict]:
    """`**[HH:MM:SS]** 문장` 만 뽑는다 — 화면 OCR·코드블록은 자동으로 걸러진다."""
    segs: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = MD_TS.match(line.strip())
        if m:
            text = m[4].strip()
            if text:
                segs.append({"t": secs(m[1], m[2], m[3]), "text": text})
        elif segs and line.strip() and not line.startswith(("#", "|", "`", "-", "*")):
            segs[-1]["text"] = (segs[-1]["text"] + " " + line.strip()).strip()
    return segs


def find_transcript(folder: Path, base: str, priority: list[str]) -> tuple[list[dict], str]:
    for ext in priority:
        path = folder / f"{base}.{ext}"
        if not path.exists():
            continue
        segs = parse_merged_md(path) if ext.endswith("md") else parse_cue_file(path)
        if segs:
            return segs, ext
    return [], "none"


def probe_duration(path: Path) -> int:
    """ffprobe 로 실제 길이(초). 없으면 0."""
    ffprobe = C.cfg("ffprobe_bin", "ffprobe")
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, timeout=60)
        return int(float(proc.stdout.decode().strip() or 0))
    except Exception:
        return 0


def load_meta() -> dict:
    """(선택) 외부 메타데이터 파일. basename → {title, subtitle, duration, url ...}"""
    name = C.cfg("meta_file")
    if not name:
        return {}
    path = C.work_dir() / name
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "weeks" in data:      # lectures.json 형태
        out = {}
        for group, items in data["weeks"].items():
            for it in items:
                out[f"{group}/{it['basename']}"] = it
        return out
    if isinstance(data, list):
        return {f"{d['group']}/{d['basename']}": d for d in data}
    return data


def main() -> None:
    C.init()
    src = C.source_dir()
    priority = C.cfg("transcript_priority", ["merged.md", "vtt", "srt"])
    groups = C.cfg("groups") or sorted(
        p.name for p in src.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))
    meta = load_meta()
    probe = C.cfg("probe_duration", True)

    units: list[dict] = []
    for group in groups:
        folder = src / group
        if not folder.exists():
            print(f"  건너뜀(폴더 없음): {group}")
            continue
        for seq, mp4 in enumerate(sorted(folder.glob("*.mp4")), start=1):
            base = mp4.stem
            segs, source = find_transcript(folder, base, priority)
            info = meta.get(f"{group}/{base}", {})
            duration = info.get("duration") or 0
            if probe and not duration:
                duration = probe_duration(mp4)
            units.append({
                "key": f"{group}/{seq:03d}",
                "group": group,
                "seq": seq,
                "basename": base,
                "video": f"{group}/{mp4.name}",
                "size": mp4.stat().st_size,
                "title": info.get("Ctitle") or info.get("title") or base,
                "subtitle": info.get("Mtitle") or info.get("subtitle") or "",
                "duration": duration,
                "source_url": info.get("vimeo_url") or info.get("url") or "",
                "source": source,
                "segments": segs,
            })

    C.save_json("units.json", units)
    no_text = [u["key"] for u in units if not u["segments"]]
    total_seg = sum(len(u["segments"]) for u in units)

    print(f"{'그룹':<14}{'차시':>5}{'대본있음':>8}{'문장':>8}{'시간':>8}")
    for group in groups:
        sub = [u for u in units if u["group"] == group]
        if not sub:
            continue
        have = sum(1 for u in sub if u["segments"])
        print(f"{group:<14}{len(sub):>5}{have:>8}"
              f"{sum(len(u['segments']) for u in sub):>8}"
              f"{sum(u['duration'] for u in sub) / 3600:>7.1f}h")
    print(f"\n총 {len(units)}차시 · 대본 {len(units) - len(no_text)}/{len(units)} · {total_seg:,}문장")
    if no_text:
        print(f"대본 없음 {len(no_text)}개: {no_text[:10]}")
        print("→ 전사한 뒤 이 스크립트를 다시 돌리고 05_fill_missing.py 로 채우면 됩니다.")


if __name__ == "__main__":
    sys.exit(main())
