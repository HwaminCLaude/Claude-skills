"""5단계(선택) — 뒤늦게 전사한 대본을 이미 만든 페이지에 채워 넣는다.

자막이 없던 차시는 페이지에 `H2 🎙 강의 대본 — 없음` + `▫️ 자막이 없어…` 로 남아 있다.
전사를 마치고 자막 파일이 생기면 이 스크립트가 그 자리를 실제 대본으로 바꾼다.

    python 01_scan.py --work <폴더>          # 자막을 다시 읽어 units.json 갱신
    python 05_fill_missing.py --work <폴더> --dry
    python 05_fill_missing.py --work <폴더>

메타데이터 길이가 0 이던 차시는 `--fix-duration` 으로 정보 callout 도 같이 고친다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vt_common as C

EMPTY_MARK = "자막이 없어"


def main() -> None:
    C.init()
    argv = sys.argv
    dry = "--dry" in argv
    fix_dur = "--fix-duration" in argv

    units = {u["key"]: u for u in (C.load_json("units.json") or [])}
    state = C.load_json("pages.json", {}) or {}
    targets = [k for k, v in state.items() if not v.get("segments")]
    print(f"대본 없이 만든 차시 {len(targets)}개: {targets or '없음'}")
    if not targets:
        return

    # 03 과 같은 방식으로 대본 문단을 만든다
    sys.path.insert(0, str(Path(__file__).parent))
    mod = __import__("03_build_pages")

    filled = 0
    for key in targets:
        info = state[key]
        unit = units.get(key)
        if not unit:
            print(f"  {key}: units.json 에 없음")
            continue
        segs = unit.get("segments") or []
        if not segs:
            print(f"  {key}: 아직 자막 없음 — 전사 대기")
            continue
        print(f"  {key}: {len(segs)}문장 ({unit['source']}) 확보")
        if dry:
            continue

        blocks = C.get_children(info["page_id"])
        head = next((b for b in blocks if b["type"] == "heading_2"), None)
        placeholder = next((b for b in blocks
                            if b["type"] == "callout" and EMPTY_MARK in C.rich_text_of(b)), None)
        if head is None:
            print("    구조 이상 — 건너뜀")
            continue

        C.api(f"https://api.notion.com/v1/blocks/{head['id']}", "PATCH",
              {"heading_2": {"rich_text": C.to_rich_text(f"🎙 강의 대본 ({len(segs)}문장)")}})
        C.append_blocks(info["page_id"], mod.transcript_blocks(segs),
                        after=(placeholder or head)["id"])
        if placeholder:
            C.api(f"https://api.notion.com/v1/blocks/{placeholder['id']}", "PATCH",
                  {"archived": True})

        if fix_dur and unit.get("duration"):
            first = blocks[0]
            if first["type"] == "callout":
                old = C.rich_text_of(first)
                new = old.replace("· 00:00 ·", f"· {C.hhmmss(unit['duration'])} ·")
                if new != old:
                    C.api(f"https://api.notion.com/v1/blocks/{first['id']}", "PATCH",
                          {"callout": {"rich_text": C.to_rich_text(new)}})

        info["segments"] = len(segs)
        info["source"] = unit["source"]
        filled += 1
        C.save_json("pages.json", state)
        print(f"    채움 완료 — {info['title'][:50]}", flush=True)

    print(f"\n{'(dry) ' if dry else ''}대본 채운 차시 {filled}개")


if __name__ == "__main__":
    sys.exit(main())
