"""Build the main page: Highlights section + one heading and one linked view block per section, each block
carrying the tabs defined in portfolio.config.json ("sections"). Idempotent via state.json.
Usage: python 04_build_main_page.py [--dry-run] [--cleanup]
  --dry-run  print the plan, no API calls
  --cleanup  afterwards trash the blocks listed in config "cleanup_block_ids" (old inline DBs, callouts)
Notes (verified against the Notion API, 2026-03-11): linked views can only be created with parent
type page_id (never inside a callout/column), gallery cover on create must be page_content|page_cover|
property, extra tabs are added with POST /views using database_id = the linked block id returned in
parent.database_id, and a timeline draws one row per item (no packing)."""
import sys
import datetime
import importlib
from notion_lib import *

DRY = "--dry-run" in sys.argv
CLEANUP = "--cleanup" in sys.argv
state = load_state()
db_id, DS = master_ids(state)
P, _ = prop_ids(state)
hl = load_json("highlights.json") if os.path.exists(os.path.join(ROOT, "highlights.json")) else None
layout = importlib.import_module("10_highlights_layout")
created = state.setdefault("created_blocks", {})
RESULT_PROP = {"property_id": P["한줄 성과"], "visible": True}


def filt(spec):
    conds = []
    if not spec:
        return None
    if spec.get("section"):
        conds.append({"property": "섹션", "select": {"equals": spec["section"]}})
    if spec.get("type"):
        conds.append({"property": "분류", "select": {"equals": spec["type"]}})
    if spec.get("titles"):
        conds.append({"or": [{"property": "이름", "title": {"equals": t}} for t in spec["titles"]]})
    if spec.get("period_not_empty"):
        conds.append({"property": "기간", "date": {"is_not_empty": True}})
    return conds[0] if len(conds) == 1 else ({"and": conds} if conds else None)


def group_by(kind, hide_empty=True, sort="manual"):
    if kind == "half_year":
        g = {"type": "formula", "property_id": P["시기"], "group_by": {"type": "text", "group_by": "exact", "sort": {"type": "ascending"}}, "sort": {"type": "ascending"}}
    else:
        name = {"section": "섹션", "type": "분류"}[kind]
        g = {"type": "select", "property_id": P[name], "sort": {"type": sort}}
    if hide_empty:
        g["hide_empty_groups"] = True
    return g


def view_body(tab):
    t = tab["type"]
    if t == "gallery":
        cfg = {"type": "gallery", "properties": [{"property_id": "title", "visible": True}] + ([RESULT_PROP] if tab.get("show_result", True) else [])}
        if tab.get("cover", True):
            cfg["cover"] = {"type": "page_content"}
            cfg["cover_aspect"] = "cover"
        else:
            cfg["cover"] = None
        for k in ("cover_size", "card_layout"):
            if tab.get(k):
                cfg[k] = tab[k]
        return cfg, filt(tab.get("filter")), [{"property": "정렬", "direction": "ascending"}]
    if t == "timeline":
        center = datetime.datetime.fromisoformat(CFG.get("timeline_center", "2025-09-01")).replace(tzinfo=datetime.timezone.utc)
        cfg = {"type": "timeline", "date_property_id": P["기간"], "show_table": False,
               "properties": [{"property_id": P["분류"], "visible": True}],
               "preference": {"zoom_level": tab.get("zoom", "year"), "center_timestamp": int(center.timestamp() * 1000)}, "color_by": True}
        return cfg, {"property": "기간", "date": {"is_not_empty": True}}, [{"property": "기간", "direction": "ascending"}]
    if t == "chart":
        cfg = {"type": "chart", "chart_type": tab.get("chart_type", "column"), "x_axis": group_by(tab.get("x", "section")),
               "y_axis": {"aggregator": "count"}, "group_style": "normal", "color_theme": "colorful", "height": "medium",
               "legend_position": "bottom", "show_data_labels": True, "axis_labels": "both", "grid_lines": "horizontal"}
        if tab.get("stack_by"):
            cfg["stack_by"] = group_by(tab["stack_by"], hide_empty=False, sort="ascending")
        return cfg, {"property": "기간", "date": {"is_not_empty": True}}, None
    if t == "board":
        cfg = {"type": "board", "group_by": group_by(tab.get("x", "half_year")), "cover": None, "card_layout": "compact",
               "properties": [{"property_id": "title", "visible": True}, {"property_id": P["분류"], "visible": True}, {**RESULT_PROP, "card_property_width_mode": "full_line"}]}
        return cfg, {"property": "기간", "date": {"is_not_empty": True}}, [{"property": "기간", "direction": "ascending"}]
    raise ValueError(f"unknown tab type {t}")


def heading_block(h):
    body = {"rich_text": [{"type": "text", "text": {"content": h["text"]}, "annotations": {"bold": True, "italic": h.get("level") == "heading_1"}}]}
    if h.get("color"):
        body["color"] = h["color"]
    return blk(h.get("level", "heading_2"), body)


def append_after(after_id, blocks):
    body = {"children": blocks}
    if after_id:
        body["after"] = after_id
    r = api_ok("PATCH", f"/blocks/{MAIN_PAGE}/children", body)
    return [b["id"] for b in r["results"]]


# ---- Highlights ------------------------------------------------------------------------------
after = CFG.get("insert_after_block_id")
if hl and CFG.get("highlights", {}).get("enabled", True):
    if DRY:
        print(f"[plan] Highlights: heading + {len(hl.get('highlights', []))} bullets + {len(hl.get('columns', []))} columns")
    elif "highlights" not in created:
        anchor = CFG.get("highlights", {}).get("after_block_id") or after
        ids = append_after(anchor, [heading_block({"text": hl.get("title", "Highlights"), "level": "heading_2"})] + layout.build_blocks(hl))
        created["highlights"] = ids[0]
        save_state(state)
        log("Highlights created")
    if "highlights" in created:
        after = after or created["highlights"]

# ---- Sections ------------------------------------------------------------------------------
last = CFG.get("sections_after_block_id") or after
for s in CFG["sections"]:
    key = s["key"]
    if DRY:
        print(f"[plan] section {key}: heading '{s['heading']['text']}' + tabs {[t['name'] + ':' + t['type'] for t in s['tabs']]}")
        continue
    if key in created and isinstance(created[key], dict):
        last = created[key]["block"]
        continue
    hid = append_after(last, [heading_block(s["heading"])])[0]
    first = s["tabs"][0]
    cfg, f, sorts = view_body(first)
    body = {"create_database": {"parent": {"type": "page_id", "page_id": MAIN_PAGE}, "position": {"type": "after_block", "block_id": hid}, "show_data_source_title": False},
            "data_source_id": DS, "name": first["name"], "type": cfg["type"], "configuration": cfg}
    if f:
        body["filter"] = f
    if sorts:
        body["sorts"] = sorts
    v = api_ok("POST", "/views", body, ver=V_NEW)
    block_id = v["parent"]["database_id"]
    views = [v["id"]]
    for tab in s["tabs"][1:]:
        cfg, f, sorts = view_body(tab)
        b2 = {"database_id": block_id, "data_source_id": DS, "name": tab["name"], "type": cfg["type"], "configuration": cfg}
        if f:
            b2["filter"] = f
        if sorts:
            b2["sorts"] = sorts
        views.append(api_ok("POST", "/views", b2, ver=V_NEW)["id"])
    created[key] = {"heading": hid, "block": block_id, "views": views}
    save_state(state)
    log(f"section {key}: {len(views)} tab(s)")
    last = block_id

if DRY:
    raise SystemExit(0)
total = 0
for s in CFG["sections"]:
    info = created.get(s["key"])
    if isinstance(info, dict):
        n = len(api_ok("GET", f"/views?database_id={info['block']}", ver=V_NEW)["results"])
        total += n
        log(f"  {s['key']}: {n} tabs (expected {len(s['tabs'])})")
log(f"total tabs: {total}")
if CLEANUP:
    for bid in CFG.get("cleanup_block_ids", []):
        r = api("DELETE", f"/blocks/{bid}")
        log(f"cleanup {bid}: {'ok' if 'error' not in r else r['body'][:120]}")
