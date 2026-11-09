"""Highlights block builder: 6 short numeric bullets + a 3-column LinkedIn-style inventory.
Reads highlights.json ({"title","highlights":[...],"columns":[[{"header","items"}...], ...]}).
Run standalone to rebuild the Highlights section in place (idempotent: replaces everything between the
Highlights heading and the next heading). Imported by 04_build_main_page.py."""
from notion_lib import *


def para_bold(text):
    return blk("paragraph", {"rich_text": [{"type": "text", "text": {"content": text}, "annotations": {"bold": True}}]})


def bullet(text):
    return blk("bulleted_list_item", {"rich_text": rich(text)})


def build_blocks(hl):
    blocks = [bullet(t) for t in hl.get("highlights", [])]
    cols = []
    for col in hl.get("columns", []):
        kids = []
        for sec in col:
            kids.append(para_bold(sec["header"]))
            kids += [bullet(t) for t in sec["items"]]
        if kids:
            cols.append({"object": "block", "type": "column", "column": {"children": kids}})
    if len(cols) >= 2:
        blocks.append({"object": "block", "type": "column_list", "column_list": {"children": cols}})
    elif cols:
        blocks += cols[0]["column"]["children"]
    return blocks


def rebuild(hl):
    kids = children(MAIN_PAGE)
    title = hl.get("title", "Highlights")
    idx = next((i for i, b in enumerate(kids) if b["type"].startswith("heading") and rt(b[b["type"]]["rich_text"]).strip() == title), None)
    if idx is None:
        raise SystemExit(f"heading '{title}' not found on the main page; run 04_build_main_page.py first")
    old = []
    for b in kids[idx + 1:]:
        if b["type"].startswith("heading"):
            break
        old.append(b)
    for b in old:
        api("DELETE", f"/blocks/{b['id']}")
    blocks = build_blocks(hl)
    api_ok("PATCH", f"/blocks/{MAIN_PAGE}/children", {"children": blocks, "after": kids[idx]["id"]})
    log(f"Highlights rebuilt: removed {len(old)} blocks, inserted {len(blocks)} top-level blocks")


if __name__ == "__main__":
    rebuild(load_json("highlights.json"))
