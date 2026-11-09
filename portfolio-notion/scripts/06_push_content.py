"""Push page body specs (pages/*.json) into Notion.
- Existing blocks are never moved or recreated (Notion-hosted images cannot be re-created from URLs).
- The summary quote is inserted right after the first block (image or first heading) and only once.
- Appended sections start with a divider; the run is idempotent (skips when the first appended heading
  already exists) and prunes a section whose heading the page already has (e.g. 관련 자료).
Spec DSL: {"h2"|"h3"|"p"|"quote": str}, {"bullets"|"numbered": [str]}, {"table": {"header": [...], "rows": [[...]]}},
{"image": url}, {"bookmark": url}, {"divider": true}. Inline: **bold**, `code`, [label](url).
Usage: python 06_push_content.py [pages/<key>.json ...]"""
import sys
import glob
from notion_lib import *


def build(item):
    k = next(iter(item))
    v = item[k]
    if k in ("h2", "h3"):
        return [blk("heading_2" if k == "h2" else "heading_3", {"rich_text": rich(v)})]
    if k == "p":
        return [blk("paragraph", {"rich_text": rich(v)})]
    if k == "quote":
        return [blk("quote", {"rich_text": rich(v)})]
    if k == "bullets":
        return [blk("bulleted_list_item", {"rich_text": rich(b)}) for b in v]
    if k == "numbered":
        return [blk("numbered_list_item", {"rich_text": rich(b)}) for b in v]
    if k == "divider":
        return [blk("divider", {})]
    if k == "bookmark":
        return [blk("bookmark", {"url": v})]
    if k == "image":
        return [blk("image", {"type": "external", "external": {"url": v}})]
    if k == "table":
        rows = [v["header"]] + v["rows"]
        width = max(len(r) for r in rows)
        trs = [blk("table_row", {"cells": [rich(str(c)) for c in (r + [""] * (width - len(r)))]}) for r in rows]
        return [blk("table", {"table_width": width, "has_column_header": True, "has_row_header": False, "children": trs})]
    raise ValueError(f"unknown spec item {item}")


def heading_texts(blocks):
    return {rt(b[b["type"]].get("rich_text", [])).strip() for b in blocks if b["type"].startswith("heading")}


def push(spec):
    pid = spec["page_id"]
    rep = {"page": pid, "removed": 0, "quote": False, "appended": 0}
    kids = children(pid)
    for pat in spec.get("remove_text_contains", []):
        for b in kids:
            t = b["type"]
            if t in ("paragraph", "bulleted_list_item") and pat in rt(b[t].get("rich_text", [])):
                if "error" not in api("DELETE", f"/blocks/{b['id']}"):
                    rep["removed"] += 1
    kids = children(pid)
    ts = spec.get("top_summary")
    if ts and ts.get("lines"):
        first_plain = ts["lines"][0].replace("**", "").replace("`", "")[:60]
        if not any(b["type"] == "quote" and rt(b["quote"].get("rich_text", [])).startswith(first_plain) for b in kids[:4]):
            body = {"children": [blk("quote", {"rich_text": rich("\n".join(ts["lines"]))})]}
            if kids:
                body["after"] = kids[0]["id"]
            api_ok("PATCH", f"/blocks/{pid}/children", body)
            rep["quote"] = True
    app = spec.get("append") or []
    if app:
        kids = children(pid)
        existing = heading_texts(kids)
        first_heading = next((v for it in app for k, v in it.items() if k in ("h2", "h3")), None)
        if first_heading and first_heading.strip() in existing and any(b["type"] == "divider" for b in kids):
            return rep
        pruned, skip = [], False
        for it in app:
            k = next(iter(it))
            if k in ("h2", "h3") and it[k].strip() in existing:
                skip = True
                continue
            if skip and k in ("bullets", "numbered", "p", "table"):
                continue
            skip = False
            pruned.append(it)
        if pruned:
            blocks = [blk("divider", {})]
            for it in pruned:
                blocks += build(it)
            for i in range(0, len(blocks), 90):
                r = api_ok("PATCH", f"/blocks/{pid}/children", {"children": blocks[i:i + 90]})
                rep["appended"] += len(r["results"])
    return rep


if __name__ == "__main__":
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "pages", "*.json")))
    results = []
    for f in files:
        spec = load_json(f)
        try:
            rep = push(spec)
            log(f"{os.path.basename(f)}: removed={rep['removed']} quote={'yes' if rep['quote'] else 'skip'} appended={rep['appended']}")
        except Exception as e:
            rep = {"page": spec.get("page_id"), "error": str(e)}
            log(f"{os.path.basename(f)}: ERROR {e}")
        results.append(rep)
    save_json(results, "logs/push_content_report.json")
