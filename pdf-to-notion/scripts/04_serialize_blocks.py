"""각 강의자료의 전체 노션 블록 시퀀스를 JSON으로 저장.
03_build_notion.py 의 빌더 함수를 재사용한다.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (CONTENT_CACHE, DECK_TITLES, DRIVE_URLS, EXPLANATIONS,
                    OUT_DIR)

# 03_build_notion.py 의 헬퍼 import (NOTION_TOKEN 우회)
os.environ.setdefault("NOTION_TOKEN", "dummy_for_serialize")
spec = importlib.util.spec_from_file_location(
    "builder", Path(__file__).parent / "03_build_notion.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def main():
    cache = json.loads(CONTENT_CACHE.read_text(encoding="utf-8"))
    expls = json.loads(EXPLANATIONS.read_text(encoding="utf-8"))
    drive = json.loads(DRIVE_URLS.read_text(encoding="utf-8"))

    out = {}
    for slug, info in cache.items():
        title = DECK_TITLES.get(slug, slug)
        h1 = {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": builder.to_rich_text(title),
                "is_toggleable": False,
                "color": "blue_background",
            },
        }
        page_blocks = [h1]

        explanations = expls.get(slug, {}).get("page_explanations", {})
        translations = expls.get(slug, {}).get("page_translations", {})  # (선택) 원문 번역
        section_titles = expls.get(slug, {}).get("section_titles", {})
        urls = drive.get(slug, {})

        for p in info["pages"]:
            page_num = p["page"]
            img_key = f"p{page_num:03d}"
            section_title = section_titles.get(str(page_num)) or img_key
            image_url = urls.get(img_key)
            expl_specs = explanations.get(str(page_num), [])
            expl_blocks = builder.flatten_specs(expl_specs)
            trans_specs = translations.get(str(page_num), [])
            trans_blocks = builder.flatten_specs(trans_specs) if trans_specs else None
            sec = builder.build_section_blocks(
                section_title, image_url, expl_blocks, trans_blocks)
            page_blocks.extend(sec)

        out[slug] = {
            "title": title,
            "blocks": page_blocks,
            "n_blocks": len(page_blocks),
        }

    out_path = OUT_DIR / "page_blocks.json"
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[DONE] {out_path}")
    for slug, body in out.items():
        print(f"  {slug}: {body['n_blocks']} blocks")


if __name__ == "__main__":
    main()
