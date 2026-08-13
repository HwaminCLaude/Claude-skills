"""Turn shots.json into script.md (recording script) and optionally an SRT.

The narration and its timing already live in shots.json; this just presents them
in the two forms a human actually needs — one to read into a microphone, one to
drop onto a timeline.

    python export_script.py --episode C:\\manimwork\\my-paper\\ep01_gap
    python export_script.py --episode ... --srt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def iter_scenes(payload: dict):
    if "scenes" in payload:
        for name, block in payload["scenes"].items():
            yield name, block.get("shots", [])
    elif "shots" in payload:
        yield payload.get("video", "main"), payload["shots"]


def mmss(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:04.1f}"


def srt_stamp(seconds: float) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


def main() -> int:
    ap = argparse.ArgumentParser(description="shots.json → script.md (+ .srt)")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--srt", action="store_true", help="자막 파일도 생성")
    args = ap.parse_args()

    episode = Path(args.episode).resolve()
    shots_path = episode / "shots.json"
    if not shots_path.is_file():
        raise SystemExit(f"shots.json이 없습니다: {shots_path}")
    payload = json.loads(shots_path.read_text(encoding="utf-8"))

    lines = [f"# {payload.get('title', episode.name)}", "",
             f"녹음용 대본 — 총 {payload.get('total_sec', 0)}초 "
             f"({payload.get('shot_count', 0)}컷)", "",
             "> 괄호 안 숫자는 그 문장을 읽는 데 배정된 시간입니다. "
             "크게 벗어나면 영상과 어긋납니다.", ""]

    srt_entries = []
    clock = 0.0
    index = 0

    for scene_name, shots in iter_scenes(payload):
        scene_len = sum(s.get("run_time", 0) + s.get("wait", 0) for s in shots)
        lines += [f"## {scene_name}  ({mmss(clock)} ~ {mmss(clock + scene_len)})", ""]
        for shot in shots:
            dur = shot.get("run_time", 0) + shot.get("wait", 0)
            narration = (shot.get("narration") or "").strip()
            if narration:
                index += 1
                srt_entries.append((index, clock, clock + dur, narration))
                lines.append(f"- **[{mmss(clock)}]** {narration}  "
                             f"<sub>({dur:.1f}s)</sub>")
                visual = (shot.get("visual") or "").strip()
                if visual:
                    lines.append(f"  - 화면: {visual}")
                asset = shot.get("asset")
                if asset:
                    kind = asset.get("kind")
                    tag = "생성 이미지 — 검수 필요" if kind == "generated" else "논문 그림"
                    lines.append(f"  - 에셋: {tag}")
            clock += dur
        lines.append("")

    generated = [s for _, shots in iter_scenes(payload) for s in shots
                 if (s.get("asset") or {}).get("kind") == "generated"]
    if generated:
        lines += ["## 최종 검수 목록 (생성 이미지 사용 컷)", ""]
        lines += [f"- `{s['id']}` — {(s.get('asset') or {}).get('prompt', '')[:80]}"
                  for s in generated]
        lines.append("")

    script_md = episode / "script.md"
    script_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[export_script] {script_md}")

    if args.srt:
        srt_path = episode / "narration.srt"
        blocks = [f"{i}\n{srt_stamp(a)} --> {srt_stamp(b)}\n{text}\n"
                  for i, a, b, text in srt_entries]
        srt_path.write_text("\n".join(blocks), encoding="utf-8")
        print(f"[export_script] {srt_path}  ({len(srt_entries)} cues)")

    print(f"[export_script] 총 {clock:.1f}초, 나레이션 {index}줄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
