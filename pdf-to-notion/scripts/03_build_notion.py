"""
03_build_notion.py
content_cache.json + explanations.json + drive_urls.json 을 읽고
노션 DB(36c734f9...) 안에 강의자료별 페이지를 생성한다.

페이지 구조:
  H1: 강의자료 제목
  --- 페이지별 반복 ---
    (optional) H2 (파란 배경): section_titles[i] 또는 "p{NNN}"
    column_list
      ├ column1: image (구글드라이브 외부 URL)
      └ column2: explanations[i] 블록들 (없으면 placeholder)
    divider

주의:
  - 노션 API는 한번에 100블록 제한 → 청크 분할로 append.
  - 이미지는 외부 URL(external) 사용: https://lh3.googleusercontent.com/d/{FILE_ID}
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# notion_client (https://github.com/ramnes/notion-sdk-py)
try:
    from notion_client import Client
except ImportError:
    print("[ERROR] notion-client 미설치. pip install notion-client", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from config import (CONTENT_CACHE, DECK_TITLES, DRIVE_URLS,
                    EXPLANATIONS, NOTION_DB_ID, NOTION_PAGE_MAP)

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
if not NOTION_TOKEN:
    print("[ERROR] NOTION_TOKEN 환경변수가 필요해. PowerShell:")
    print('  $env:NOTION_TOKEN = "secret_..."')
    sys.exit(1)

notion = Client(auth=NOTION_TOKEN)


# ───────────────────────────────────────────────────────────
# 리치 텍스트 파서: **굵게**, _이탤릭_, `code`
# ───────────────────────────────────────────────────────────
_INLINE_RE = re.compile(r"(\*\*.+?\*\*|_.+?_|`.+?`)")


def to_rich_text(text: str) -> list[dict]:
    """간단한 마크다운-ish 인라인 → 노션 rich_text 배열."""
    if not text:
        return []
    parts = _INLINE_RE.split(text)
    result = []
    for part in parts:
        if not part:
            continue
        ann = {"bold": False, "italic": False, "code": False}
        content = part
        if part.startswith("**") and part.endswith("**"):
            ann["bold"] = True
            content = part[2:-2]
        elif part.startswith("_") and part.endswith("_") and len(part) > 2:
            ann["italic"] = True
            content = part[1:-1]
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            ann["code"] = True
            content = part[1:-1]
        if not content:
            continue
        result.append({
            "type": "text",
            "text": {"content": content},
            "annotations": {**{
                "bold": False, "italic": False, "strikethrough": False,
                "underline": False, "code": False, "color": "default",
            }, **ann},
        })
    return result


# ───────────────────────────────────────────────────────────
# 블록 변환기: schema dict → notion block
# ───────────────────────────────────────────────────────────
def block_from_spec(spec: dict) -> dict | None:
    """explanations.json 의 블록 spec → 노션 API block 객체."""
    t = spec.get("type")
    if t == "p":
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": to_rich_text(spec.get("text", ""))},
        }
    if t == "h3":
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": to_rich_text(spec.get("text", ""))},
        }
    if t == "callout":
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": to_rich_text(spec.get("text", "")),
                "icon": {"type": "emoji", "emoji": spec.get("emoji", "💡")},
                "color": spec.get("color", "default_background"),
            },
        }
    if t == "quote":
        return {
            "object": "block",
            "type": "quote",
            "quote": {"rich_text": to_rich_text(spec.get("text", ""))},
        }
    if t == "num":
        # numbered_list_item 은 형제 블록으로 여러 개 — 호출자가 flatten 해야 함.
        return [
            {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": to_rich_text(it)},
            }
            for it in spec.get("items", [])
        ]
    if t == "bul":
        return [
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": to_rich_text(it)},
            }
            for it in spec.get("items", [])
        ]
    if t == "mermaid":
        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": spec.get("code", "")}}],
                "language": "mermaid",
            },
        }
    if t == "code":
        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": spec.get("code", "")}}],
                "language": spec.get("language", "python"),
            },
        }
    if t == "divider":
        return {"object": "block", "type": "divider", "divider": {}}
    if t == "eq":
        return {
            "object": "block",
            "type": "equation",
            "equation": {"expression": spec.get("expression", "")},
        }
    if t == "toggle":
        # 접이식 토글. children 에 하위 블록 spec 배열(원문 전체 번역 등)을 넣는다.
        return {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": to_rich_text(spec.get("text", "원문 번역")),
                "color": spec.get("color", "default"),
                "children": flatten_specs(spec.get("children", [])),
            },
        }
    return None


def flatten_specs(specs: list[dict]) -> list[dict]:
    out = []
    for s in specs:
        b = block_from_spec(s)
        if b is None:
            continue
        if isinstance(b, list):
            out.extend(b)
        else:
            out.append(b)
    return out


# ───────────────────────────────────────────────────────────
# 페이지/섹션 빌더
# ───────────────────────────────────────────────────────────
def build_section_blocks(
    section_title: str,
    image_url: str | None,
    explanation_blocks: list[dict],
    translation_blocks: list[dict] | None = None,
    translation_title: str = "📖 원문 전체 번역 (English → 한국어)",
) -> list[dict]:
    """한 페이지(=섹션) 블록 시퀀스 만들기.
    [H2(파란 배경), column_list(image|explanation), (선택)toggle(원문 번역), divider]

    번역 토글은 column 안이 아니라 **column_list 와 형제(full-width)** 로 둔다.
    노션 API는 한 요청에서 중첩을 2단계까지만 허용하는데, column_list→column→블록
    이 이미 2단계라 토글을 column 안에 넣으면 toggle→children 이 3단계가 돼 거부된다.
    """
    h2 = {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": to_rich_text(section_title),
            "is_toggleable": False,
            "color": "blue_background",
        },
    }

    left_children = []
    if image_url:
        left_children.append({
            "object": "block",
            "type": "image",
            "image": {"type": "external", "external": {"url": image_url}},
        })
    else:
        left_children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": to_rich_text("_이미지 URL 준비 중_")},
        })

    right_children = explanation_blocks if explanation_blocks else [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": []},
        }
    ]

    column_list = {
        "object": "block",
        "type": "column_list",
        "column_list": {
            "children": [
                {
                    "object": "block",
                    "type": "column",
                    "column": {"children": left_children},
                },
                {
                    "object": "block",
                    "type": "column",
                    "column": {"children": right_children},
                },
            ],
        },
    }

    divider = {"object": "block", "type": "divider", "divider": {}}

    section = [h2, column_list]
    if translation_blocks:
        section.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": to_rich_text(translation_title),
                "color": "default",
                "children": translation_blocks,
            },
        })
    section.append(divider)
    return section


def desurrogate(obj):
    """깨진 lone surrogate(U+D800–DFFF) 문자 제거 → UTF-8/JSON 인코딩 에러 방지.
    OCR·LLM 산출물에 가끔 섞이며, 노션 API가 '400 no low surrogate' 로 거부한다."""
    if isinstance(obj, str):
        return "".join(c for c in obj if not (0xD800 <= ord(c) <= 0xDFFF))
    if isinstance(obj, list):
        return [desurrogate(x) for x in obj]
    if isinstance(obj, dict):
        return {k: desurrogate(v) for k, v in obj.items()}
    return obj


def _count_blocks(b: dict) -> int:
    """블록 + 모든 중첩 children 재귀 카운트 (노션 100블록/요청 한계 계산용)."""
    n = 1
    t = b.get("type")
    for k in (b.get(t, {}).get("children") or []):
        n += _count_blocks(k)
    return n


def chunked_append(page_id: str, blocks: list[dict], limit: int = 85) -> None:
    """노션 100블록/요청 제한을 중첩 children 까지 세어 안전 분할 append.
    column_list·toggle 등 top-level 블록 경계에서만 자르고, 누적 블록수 ≤ limit."""
    cur, cur_n = [], 0
    for b in blocks:
        bn = _count_blocks(b)
        if cur and cur_n + bn > limit:
            notion.blocks.children.append(block_id=page_id, children=desurrogate(cur))
            time.sleep(0.36)  # rate limit (3 req/s)
            cur, cur_n = [], 0
        cur.append(b)
        cur_n += bn
    if cur:
        notion.blocks.children.append(block_id=page_id, children=desurrogate(cur))
        time.sleep(0.36)


# ───────────────────────────────────────────────────────────
# 메인
# ───────────────────────────────────────────────────────────
def main():
    cache = json.loads(CONTENT_CACHE.read_text(encoding="utf-8"))
    expls = json.loads(EXPLANATIONS.read_text(encoding="utf-8")) if EXPLANATIONS.exists() else {}
    drive = json.loads(DRIVE_URLS.read_text(encoding="utf-8")) if DRIVE_URLS.exists() else {}

    created = {}
    for slug, info in cache.items():
        title = DECK_TITLES.get(slug, slug)
        print(f"\n[CREATE PAGE] {title}")

        # 빈 페이지 먼저 생성
        page = notion.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties={
                "이름": {  # 기본 title property — DB가 다른 이름이면 자동 감지로 바꿔야 함
                    "title": [{"type": "text", "text": {"content": title}}],
                },
            },
        )
        page_id = page["id"]
        created[slug] = {"page_id": page_id, "url": page["url"]}

        # H1: 자료 제목
        h1 = {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": to_rich_text(title),
                "is_toggleable": False,
                "color": "blue_background",
            },
        }
        chunked_append(page_id, [h1])

        # 페이지별 섹션
        explanations = expls.get(slug, {}).get("page_explanations", {})
        translations = expls.get(slug, {}).get("page_translations", {})  # (선택) 원문 번역
        section_titles = expls.get(slug, {}).get("section_titles", {})
        urls = drive.get(slug, {})  # {"p001": "https://lh3...", ...}

        all_blocks: list[dict] = []
        for p in info["pages"]:
            page_num = p["page"]
            img_key = f"p{page_num:03d}"
            section_title = section_titles.get(str(page_num)) or img_key
            image_url = urls.get(img_key)
            expl_specs = explanations.get(str(page_num), [])
            expl_blocks = flatten_specs(expl_specs)
            trans_specs = translations.get(str(page_num), [])
            trans_blocks = flatten_specs(trans_specs) if trans_specs else None
            section_blocks = build_section_blocks(
                section_title, image_url, expl_blocks, trans_blocks)
            all_blocks.extend(section_blocks)

        chunked_append(page_id, all_blocks)
        print(f"   페이지 {info['n_pages']}개 섹션 추가 완료 → {page['url']}")

    NOTION_PAGE_MAP.write_text(
        json.dumps(created, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[DONE] {len(created)}개 페이지 생성. 매핑: {NOTION_PAGE_MAP}")


if __name__ == "__main__":
    main()
