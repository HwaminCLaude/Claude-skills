"""Back up the main page (blocks, recursive), every existing database listed in portfolio.config.json
(schema, rows, views) and all Notion-hosted files/images (signed URLs expire in 1 hour).
Run before any mutation. Output: backup/full_backup.json, backup/files/."""
import re
from notion_lib import *

out = {"databases": {}, "data_sources": {}, "rows": {}, "views": {}, "page_blocks": {}, "files": []}
existing = CFG.get("existing_databases", {})
for name, dbid in existing.items():
    db = api_ok("GET", f"/databases/{dbid}", ver=V_NEW)
    db["_name"] = name
    out["databases"][dbid] = db
    for ds in db["data_sources"]:
        out["data_sources"][ds["id"]] = api_ok("GET", f"/data_sources/{ds['id']}")
        out["rows"][ds["id"]] = paginate("POST", f"/data_sources/{ds['id']}/query", {"page_size": 100})
    vs = paginate("GET", f"/views?database_id={dbid}", ver=V_NEW)
    out["views"][dbid] = [api_ok("GET", f"/views/{v['id']}", ver=V_NEW) for v in vs]
    log(f"DB {name}: sources={len(db['data_sources'])} rows={[len(out['rows'][d['id']]) for d in db['data_sources']]} views={len(vs)}")
state = load_state()
if "ds_id" in state:
    ds = state["ds_id"]
    out["data_sources"][ds] = api_ok("GET", f"/data_sources/{ds}")
    out["rows"][ds] = paginate("POST", f"/data_sources/{ds}/query", {"page_size": 100})
    log(f"master data source: rows={len(out['rows'][ds])}")
out["main_page"] = api_ok("GET", f"/pages/{MAIN_PAGE}")
out["main_page_blocks"] = walk_blocks(MAIN_PAGE)
n = 0
for dsid, rows in out["rows"].items():
    for r in rows:
        out["page_blocks"][r["id"]] = walk_blocks(r["id"])
        n += 1
log(f"page bodies backed up: {n}")


def safe(s):
    return re.sub(r"[^\w.\- ]+", "_", s)[:80]


def grab(url, dest, kind, page_id, name):
    try:
        size = download(url, dest)
        out["files"].append({"page": page_id, "kind": kind, "name": name, "path": dest, "size": size})
    except Exception as e:
        out["files"].append({"page": page_id, "kind": kind, "name": name, "error": str(e)})


for dsid, rows in out["rows"].items():
    for r in rows:
        for pname, p in r["properties"].items():
            if p["type"] == "files":
                for i, f in enumerate(p["files"]):
                    url = (f.get("file") or {}).get("url") or (f.get("external") or {}).get("url")
                    if url:
                        grab(url, os.path.join(ROOT, "backup", "files", f"{r['id']}__prop__{safe(f.get('name') or str(i))}"), "property", r["id"], f.get("name"))


def walk_media(blocks, page_id):
    for b in blocks:
        t = b["type"]
        if t in ("image", "file", "pdf", "video") and (b[t].get("type") == "file"):
            url = b[t]["file"]["url"]
            ext = url.split("?")[0].rsplit(".", 1)[-1][:5]
            grab(url, os.path.join(ROOT, "backup", "files", f"{page_id}__{t}__{b['id']}.{ext}"), t, page_id, b["id"])
        if b.get("children"):
            walk_media(b["children"], page_id)


for pid, blocks in out["page_blocks"].items():
    walk_media(blocks, pid)
walk_media(out["main_page_blocks"], MAIN_PAGE)
p = save_json(out, "backup/full_backup.json")
ok = [f for f in out["files"] if "path" in f]
log(f"saved {p}; files downloaded={len(ok)} failed={len(out['files']) - len(ok)}")
