"""Remove process/meta phrasing that reads as machine-written from every item page.
Config keys (portfolio.config.json):
  forbidden_phrases        paragraphs/bullets containing any of these are deleted
  quote_drop_prefixes      lines in the summary quote starting with these are dropped
  delete_section_headings  heading + following list/paragraph blocks are deleted
Defaults cover the phrases this skill used to emit (근거:, 근거 수준:, 기재 예정, 측정 계획:, 월 단위)."""
from notion_lib import *

items = load_json("items.json")
FORBIDDEN = CFG.get("forbidden_phrases", ["근거: 본 페이지", "측정 계획:", "(월 단위 기록)", "2026-11-10 기준"])
DROP_PREFIX = tuple(CFG.get("quote_drop_prefixes", ["근거 수준:", "기간: 기재 예정"]))
DEL_HEADINGS = set(CFG.get("delete_section_headings", ["근거", "기록 메모", "측정"]))
stats = {"blocks_removed": 0, "sections_removed": 0, "quotes_fixed": 0}


def split_lines(rich_):
    lines = [[]]
    for seg in rich_:
        if seg.get("type") != "text":
            lines[-1].append(seg)
            continue
        parts = seg["text"]["content"].split("\n")
        for j, part in enumerate(parts):
            if j > 0:
                lines.append([])
            if part:
                s2 = {"type": "text", "text": {"content": part}, "annotations": seg.get("annotations", {})}
                if seg["text"].get("link"):
                    s2["text"]["link"] = seg["text"]["link"]
                lines[-1].append(s2)
    return lines


def line_text(line):
    return "".join(s["text"]["content"] for s in line if s.get("type") == "text")


def join_lines(lines):
    out = []
    for i, line in enumerate(lines):
        if i > 0:
            out.append({"type": "text", "text": {"content": "\n"}})
        out.extend(line)
    return out


for key, it in items.items():
    pid = it.get("page_id")
    if not pid:
        continue
    kids = children(pid)
    i = 0
    while i < len(kids):
        b = kids[i]
        t = b["type"]
        txt = rt(b.get(t, {}).get("rich_text", [])).strip() if isinstance(b.get(t), dict) else ""
        if t in ("paragraph", "bulleted_list_item") and any(p in txt for p in FORBIDDEN):
            api("DELETE", f"/blocks/{b['id']}")
            stats["blocks_removed"] += 1
        elif t.startswith("heading") and txt in DEL_HEADINGS:
            api("DELETE", f"/blocks/{b['id']}")
            j = i + 1
            while j < len(kids) and kids[j]["type"] in ("bulleted_list_item", "numbered_list_item", "paragraph"):
                api("DELETE", f"/blocks/{kids[j]['id']}")
                j += 1
            stats["sections_removed"] += 1
            i = j
            continue
        elif t == "quote":
            lines = split_lines(b["quote"]["rich_text"])
            kept = [l for l in lines if line_text(l).strip() and not line_text(l).strip().startswith(DROP_PREFIX)]
            if len(kept) != len(lines):
                api_ok("PATCH", f"/blocks/{b['id']}", {"quote": {"rich_text": join_lines(kept)}})
                stats["quotes_fixed"] += 1
        i += 1
log(f"cleanup done: {stats}")
