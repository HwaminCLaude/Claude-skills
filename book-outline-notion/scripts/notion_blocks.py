"""
notion_blocks.py — 절 블록 spec → 노션 API block 객체 빌더.

노션 한도 방어:
  * rich_text 한 조각 2,000자 → 넘으면 조각으로 쪼갠다
  * rich_text 배열 100개 → 넘으면 자른다
  * table 은 모든 행의 셀 수가 table_width 와 같아야 한다 → 패딩/절단
"""
from __future__ import annotations

MAX_TEXT = 1900          # 2000자 한도에 여유
MAX_RT = 90              # 100개 한도에 여유
MAX_CELL = 1900


def rt(text: str, bold: bool = False, italic: bool = False,
       code: bool = False, color: str = "default") -> list[dict]:
    """긴 문자열도 안전하게 rich_text 배열로."""
    text = text or ""
    if not text:
        return []
    chunks = [text[i:i + MAX_TEXT] for i in range(0, len(text), MAX_TEXT)][:MAX_RT]
    return [{
        "type": "text",
        "text": {"content": c},
        "annotations": {"bold": bold, "italic": italic, "strikethrough": False,
                        "underline": False, "code": code, "color": color},
    } for c in chunks]


def rt_link(text: str, url: str) -> list[dict]:
    return [{"type": "text", "text": {"content": text[:MAX_TEXT], "link": {"url": url}},
             "annotations": {"bold": False, "italic": False, "strikethrough": False,
                             "underline": False, "code": False, "color": "default"}}]


def paragraph(text: str, **kw) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": rt(text, **kw)}}


def bullet(text: str, children: list[dict] | None = None) -> dict:
    b = {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": rt(text)}}
    if children:
        b["bulleted_list_item"]["children"] = children
    return b


def heading(text: str, level: int = 3, color: str = "default") -> dict:
    t = f"heading_{level}"
    return {"object": "block", "type": t,
            t: {"rich_text": rt(text), "is_toggleable": False, "color": color}}


def callout(text: str, emoji: str = "💡", color: str = "orange_background") -> dict:
    return {"object": "block", "type": "callout",
            "callout": {"rich_text": rt(text),
                        "icon": {"type": "emoji", "emoji": emoji},
                        "color": color}}


def divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def image(url: str) -> dict:
    return {"object": "block", "type": "image",
            "image": {"type": "external", "external": {"url": url}}}


def toggle(text: str, children: list[dict], color: str = "default") -> dict:
    return {"object": "block", "type": "toggle",
            "toggle": {"rich_text": rt(text), "color": color, "children": children}}


def table(rows: list[list[str]], has_header: bool = True) -> dict | None:
    """진짜 노션 표. 모든 행의 셀 수를 최대 열 수에 맞춘다."""
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if not rows:
        return None
    width = max(len(r) for r in rows)
    width = max(1, min(width, 100))
    children = []
    for r in rows:
        cells = list(r) + [""] * (width - len(r))
        children.append({
            "object": "block", "type": "table_row",
            "table_row": {"cells": [rt((c or "")[:MAX_CELL]) for c in cells[:width]]},
        })
    return {"object": "block", "type": "table",
            "table": {"table_width": width, "has_column_header": has_header,
                      "has_row_header": False, "children": children}}


def source_line(text: str) -> dict:
    return paragraph(text, italic=True, color="gray")


def build_body(sec: dict, ocr: dict, urls: dict) -> list[dict]:
    """절의 본문 블록만(요약·하위목차·구분선·꼬리말 제외).

    한 페이지 안에 여러 절을 이어 붙일 때(3단계 구조에서 L4~L7을 L3 본문에 흡수)
    재사용한다.
    """
    out: list[dict] = []
    pending_sub: list[dict] = []

    def flush_sub():
        """모아둔 하위 불릿을 직전 상위 불릿의 children 으로 넣는다."""
        nonlocal pending_sub
        if not pending_sub:
            return
        if out and out[-1].get("type") == "bulleted_list_item":
            kid = out[-1]["bulleted_list_item"].setdefault("children", [])
            kid.extend(pending_sub)
        else:
            out.extend(pending_sub)
        pending_sub = []

    for b in (sec.get("blocks") or []):
        t = b["type"]
        if t == "sub":
            pending_sub.append(bullet(b.get("text", "")))
            continue
        flush_sub()

        if t == "bul":
            out.append(bullet(b.get("text", "")))
        elif t == "p":
            out.append(paragraph(b.get("text", "")))
        elif t == "caption":
            out.append(paragraph(b.get("text", ""), bold=True))
        elif t == "source":
            out.append(source_line(b.get("text", "")))
        elif t == "figure":
            cap = f'{b["label"]} {b.get("caption", "")}'.strip()
            out.append(paragraph(cap, bold=True))
            url = urls.get(b["fig_id"])
            if url:
                out.append(image(url))
            o = ocr.get(b["fig_id"])
            if o and o.get("text"):
                kids = [paragraph(o["text"])]
                if o.get("summary"):
                    kids.insert(0, paragraph(o["summary"], italic=True))
                out.append(toggle("🔍 도식 내용 (검색용)", kids))
            if b.get("source"):
                out.append(source_line(b["source"]))
        elif t == "table":
            if b.get("caption"):
                out.append(paragraph(b["caption"], bold=True))
            tb = table(b.get("rows") or [])
            if tb:
                out.append(tb)
            if b.get("source"):
                out.append(source_line(b["source"]))
    flush_sub()
    return out


def page_tail(sec: dict, pdf_url: str | None) -> list[dict]:
    """페이지 끝: 구분선 + 원문 쪽 링크."""
    span = (f"원문 {sec['page_start']}쪽" if sec["page_start"] == sec["page_end"]
            else f"원문 {sec['page_start']}–{sec['page_end']}쪽")
    return [divider(), {"object": "block", "type": "paragraph", "paragraph": {
        "rich_text": (rt_link(f"📄 {span}", pdf_url) if pdf_url
                      else rt(f"📄 {span}", color="gray"))}}]


# 본문에 흡수된 하위 절의 제목을 어떤 블록으로 표현할지 (레벨 → 블록)
def sub_heading(sec: dict) -> dict:
    lv = sec["level"]
    if lv == 4:
        return heading(sec["display"], 2, color="blue_background")
    if lv == 5:
        return heading(sec["display"], 3)
    return paragraph(sec["display"], bold=True)


def build_leaf_page(sec: dict, descendants: list[dict], summaries: dict,
                    ocr: dict, urls: dict, pdf_url: str | None) -> list[dict]:
    """3단계 구조의 말단(L3) 페이지 = 자기 본문 + 하위 절 전체를 소제목으로 흡수."""
    out: list[dict] = []
    if summaries.get(sec["id"]):
        out.append(callout(summaries[sec["id"]], "💡", "orange_background"))

    # 페이지가 길어지므로 맨 위에 접이식 상세 목차를 둔다
    outline = [d for d in descendants if d["level"] <= 5]
    if len(outline) > 80:
        outline = [d for d in descendants if d["level"] <= 4]
    if outline:
        items = [bullet(f'{d["display"]}  ·  {d["page_start"]}쪽') for d in outline]
        out.append(toggle(f"📑 이 절의 상세 목차 ({len(descendants)}항목)", items))

    own = build_body(sec, ocr, urls)
    if own:
        out.append(divider())
        out.extend(own)

    for d in descendants:
        out.append(sub_heading(d))
        if d["level"] == 4 and summaries.get(d["id"]):
            out.append(paragraph(summaries[d["id"]], italic=True, color="gray"))
        out.extend(build_body(d, ocr, urls))

    out.extend(page_tail(sec, pdf_url))
    return out


def build_branch_page(sec: dict, summaries: dict, pdf_url: str | None) -> list[dict]:
    """3단계 구조의 중간(L1·L2) 페이지 = 요약만. 자식은 아래 인라인 DB가 보여준다."""
    out: list[dict] = []
    if summaries.get(sec["id"]):
        out.append(callout(summaries[sec["id"]], "💡", "orange_background"))
    out.extend(page_tail(sec, pdf_url))
    return out
