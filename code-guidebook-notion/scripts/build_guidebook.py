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
from pathlib import Path

os.environ.setdefault("NOTION_TOKEN", "dummy_for_build")
_spec = importlib.util.spec_from_file_location(
    "builder", Path(__file__).parent / "03_build_notion.py"
)
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)


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
            return {
                "object": "block", "type": "heading_2",
                "heading_2": {
                    "rich_text": builder.to_rich_text(spec.get("text", "")),
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
