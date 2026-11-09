"""Restructure mode: move rows from the existing databases (portfolio.config.json: existing_databases)
into the master data source, then hand over to 03_upsert_pages.py for properties.
- Page ids, URLs, bodies and Notion-hosted files are preserved by the move.
- Non-empty legacy properties are copied into the master schema as new columns; after all pages are
  filled, 'cleanup_legacy' removes every column not in schema.json keep list.
- Internal links in legacy rich_text columns become 관련 항목 relations; labeled links are kept in the
  page body by 05_gen_specs.py (related section) from backup/full_backup.json.
Usage: python 02_move_and_fill.py [--cleanup-legacy]"""
import re
import sys
from notion_lib import *

state = load_state()
db_id, DS = master_ids(state)
items = load_json("items.json")
backup = load_json("backup/full_backup.json")
rows_by_id = {r["id"]: r for rows in backup["rows"].values() for r in rows}
page_ids = {it.get("page_id") for it in items.values() if it.get("page_id")}
moved, failed = 0, []
for key, it in items.items():
    pid = it.get("page_id")
    if not pid:
        continue
    page = api("GET", f"/pages/{pid}")
    if "error" in page:
        failed.append(key)
        log(f"GET failed {key}: {page['body'][:160]}")
        continue
    if page["parent"].get("data_source_id") == DS:
        continue
    r = api("POST", f"/pages/{pid}/move", {"parent": {"type": "data_source_id", "data_source_id": DS}}, ver=V_NEW)
    if "error" in r:
        failed.append(key)
        log(f"MOVE FAILED {key}: {r['body'][:200]}")
    else:
        moved += 1
log(f"moved {moved}, failed {len(failed)}: {failed}")

# relations from legacy internal links (hrefs that point at other portfolio pages)
hex32 = re.compile(r"([0-9a-f]{32})")
n_rel = 0
for key, it in items.items():
    pid = it.get("page_id")
    row = rows_by_id.get(pid)
    if not row:
        continue
    targets = []
    for p in row["properties"].values():
        if p["type"] == "rich_text":
            for seg in p["rich_text"]:
                href = seg.get("href") or ""
                m = hex32.search(href.replace("-", ""))
                if m and "notion" in href:
                    h = m.group(1)
                    tid = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
                    if tid in page_ids and tid != pid and tid not in targets:
                        targets.append(tid)
    if targets:
        r = api("PATCH", f"/pages/{pid}", {"properties": {"관련 항목": {"relation": [{"id": t} for t in targets]}}})
        n_rel += len(targets) if "error" not in r else 0
log(f"relations from legacy links: {n_rel}")

# files that arrived under a differently named legacy files column -> copy into 파일
for key, it in items.items():
    pid = it.get("page_id")
    if not pid:
        continue
    page = api("GET", f"/pages/{pid}")
    if "error" in page:
        continue
    have = list(page["properties"].get("파일", {}).get("files", []))
    extra = []
    for pname, p in page["properties"].items():
        if p["type"] == "files" and pname != "파일":
            extra += [f for f in p["files"] if f.get("name") not in {h.get("name") for h in have}]
    if extra:
        r = api("PATCH", f"/pages/{pid}", {"properties": {"파일": {"files": have + extra}}})
        log(f"files copied into 파일 on {it['title']}: {[f.get('name') for f in extra]} -> {'ok' if 'error' not in r else r['body'][:120]}")

for pid in CFG.get("delete_pages", []):
    r = api("PATCH", f"/pages/{pid}", {"in_trash": True})
    log(f"trash {pid}: {'ok' if 'error' not in r else r['body'][:100]}")

if "--cleanup-legacy" in sys.argv:
    ds = api_ok("GET", f"/data_sources/{DS}")
    keep = set(SCHEMA["keep_properties"])
    legacy = [n for n in ds["properties"] if n not in keep]
    if legacy:
        r = api("PATCH", f"/data_sources/{DS}", {"properties": {n: None for n in legacy}})
        log("legacy columns removed: " + (str(legacy) if "error" not in r else r["body"][:200]))
else:
    log("legacy columns kept; rerun with --cleanup-legacy after 03_upsert_pages.py")
