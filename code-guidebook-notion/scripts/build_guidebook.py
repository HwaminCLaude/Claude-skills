"""
build_guidebook.py
가이드북 spec JSON(gb_<slug>.json: {title, blocks[spec]})을 노션 블록으로 변환하고
청크(25블록)로 분할 저장한다. (이미지/column_list 없음, 순수 블록 시퀀스)

사용법:
  python build_guidebook.py <gb_json_path> <chunk_out_dir> <chunk_prefix>
  예: python build_guidebook.py 6주차/_guidebook/gb_실습2.json 6주차/_guidebook/chunks 실습2
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import unicodedata
from pathlib import Path

os.environ.setdefault("NOTION_TOKEN", "dummy_for_build")
_spec = importlib.util.spec_from_file_location(
    "builder", Path(__file__).parent / "03_build_notion.py"
)
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)


def _circled(n: int) -> str:
    """1..20 -> ①..⑳, 0 -> ⓪, 그 외 -> (n)."""
    if n == 0:
        return "⓪"        # ⓪
    if 1 <= n <= 20:
        return chr(0x245F + n)  # ①..⑳
    return f"({n})"


def _disp_width(s: str) -> int:
    """CJK/전각 문자는 2칸으로 계산해 monospace 정렬을 맞춘다."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _disp_width(s))


def main():
    gb_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    prefix = sys.argv[3]
    out_dir.mkdir(parents=True, exist_ok=True)

    gb = json.loads(gb_path.read_text(encoding="utf-8"))
    title = gb["title"]
    specs = gb["blocks"]

    # 그림 key -> 드라이브 URL 매핑 (있으면)
    drive_path = gb_path.parent / "gb_drive_urls.json"
    drive_urls = {}
    if drive_path.exists():
        drive_urls = json.loads(drive_path.read_text(encoding="utf-8"))

    def convert(spec):
        """output/image_ref/h2 커스텀 spec 처리, 나머지는 03_build_notion에 위임."""
        t = spec.get("type")
        if t == "h2":
            # block_from_spec엔 heading_2가 없어 누락되므로 여기서 직접 생성(파란 배경)
            text = spec.get("text", "")
            st = spec.get("stage")
            if st is not None:
                # 흐름 지도의 몇 단계인지 [②] 배지로 표시
                text = f"[{_circled(int(st))}] {text}"
            return {
                "object": "block", "type": "heading_2",
                "heading_2": {
                    "rich_text": builder.to_rich_text(text),
                    "is_toggleable": False, "color": "blue_background",
                },
            }
        if t == "output":
            txt = spec.get("text", "")
            if not txt:
                return None
            return {
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "📤 실행 결과\n" + txt[:1900]}}],
                    "language": "plain text",
                },
            }
        if t == "image_ref":
            url = drive_urls.get(spec.get("key", ""))
            if not url:
                return None  # URL 없으면 스킵
            return {
                "object": "block", "type": "image",
                "image": {"type": "external", "external": {"url": url}},
            }
        if t == "flowmap":
            # 📍 흐름 지도: 주황 callout(목적) + 회색 code block(단계별 데이터 shape 여정)
            goal = spec.get("goal", "")
            stages = spec.get("stages", [])
            head = "**이 노트북 한눈에 보기 (흐름 지도)**"
            if goal:
                head += "\n목적: " + goal
            head += "\n아래 각 섹션 제목의 [번호] 배지가 지금 몇 단계인지 알려줘요."
            callout = {
                "object": "block", "type": "callout",
                "callout": {
                    "rich_text": builder.to_rich_text(head),
                    "icon": {"type": "emoji", "emoji": "📍"},
                    "color": "orange_background",
                },
            }
            labels = [
                f"{_circled(int(st.get('n', i + 1)))} {st.get('name', '')}"
                for i, st in enumerate(stages)
            ]
            w = max((_disp_width(l) for l in labels), default=0)
            lines = [
                (_pad(lbl, w + 4) + st.get("data", "")) if st.get("data") else lbl
                for lbl, st in zip(labels, stages)
            ]
            code = {
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(lines)}}],
                    "language": "plain text",
                },
            }
            return [callout, code]
        return builder.block_from_spec(spec)

    flat = []
    for s in specs:
        b = convert(s)
        if b is None:
            continue
        if isinstance(b, list):
            flat.extend(b)
        else:
            flat.append(b)

    h1 = {
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": builder.to_rich_text(title),
            "is_toggleable": False,
            "color": "blue_background",
        },
    }
    blocks = [h1] + flat

    N = 25
    chunks = [blocks[i:i + N] for i in range(0, len(blocks), N)]
    for i, ch in enumerate(chunks, 1):
        (out_dir / f"{prefix}_c{i:02d}.json").write_text(
            json.dumps(ch, ensure_ascii=False), encoding="utf-8"
        )
    print(f"{prefix}: {len(blocks)} blocks -> {len(chunks)} chunks")


if __name__ == "__main__":
    main()
