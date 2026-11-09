"""Create or update every item in items.json inside the master data source.
- Entries with page_id are updated (properties only).
- Entries without page_id are created (first block = external image when "image" is given, so the
  gallery card gets a thumbnail); the new id is written back into items.json.
- Second pass writes 관련 항목 relations from "related" (keys or page ids)."""
from notion_lib import *

state = load_state()
db_id, DS = master_ids(state)
items = load_json("items.json")
ids, ds = prop_ids(state)
status_names = {o["name"] for o in ds["properties"]["상태"]["status"]["options"]}
STATUS_ALIASES = {"완료": ["완료", "Done", "Complete"], "진행 중": ["진행 중", "In progress"], "예정": ["시작 전", "Not started", "To-do"]}


def status_name(k):
    for c in STATUS_ALIASES.get(k, [k]):
        if c in status_names:
            return c
    return None


def props_for(it):
    props = {
        "이름": {"title": [{"type": "text", "text": {"content": it["title"]}}]},
        "섹션": {"select": {"name": it["section"]}},
        "분류": {"select": {"name": it["type"]}},
        "한줄 성과": text_prop(it.get("result", "")),
        "역할": text_prop(it.get("role", "")),
        "기관·주최": text_prop(it.get("org", "")),
        "기술 스택": {"multi_select": [{"name": s} for s in it.get("stack", [])]},
        "정렬": {"number": it.get("sort", 99)},
        "GitHub": {"url": it.get("github") or None},
        "배포 링크": {"url": it.get("deploy") or None},
        "논문/자료 링크": {"url": it.get("paper") or None},
        "기간": {"date": it["period"]} if it.get("period") else {"date": None},
    }
    sn = status_name(it["status"]) if it.get("status") else None
    props["상태"] = {"status": {"name": sn}} if sn else {"status": None}
    for extra_name in SCHEMA.get("extra_properties", {}):
        if it.get(extra_name) is not None:
            props[extra_name] = {"select": {"name": it[extra_name]}}
    return props


created, updated, failed = 0, 0, []
for key, it in items.items():
    if it.get("page_id"):
        r = api("PATCH", f"/pages/{it['page_id']}", {"properties": props_for(it)})
        if "error" in r:
            failed.append(key)
            log(f"UPDATE FAILED {key}: {r['body'][:200]}")
        else:
            updated += 1
    else:
        kids = []
        if it.get("image"):
            kids.append(blk("image", {"type": "external", "external": {"url": it["image"]}}))
        r = api("POST", "/pages", {"parent": {"type": "data_source_id", "data_source_id": DS}, "properties": props_for(it), "children": kids})
        if "error" in r:
            failed.append(key)
            log(f"CREATE FAILED {key}: {r['body'][:200]}")
        else:
            it["page_id"] = r["id"]
            created += 1
            log(f"created {key}: {r.get('url')}")
save_json(items, "items.json")
key_to_id = {k: v["page_id"] for k, v in items.items() if v.get("page_id")}
n_rel = 0
for key, it in items.items():
    rel = [key_to_id.get(x, x) for x in it.get("related", [])]
    rel = [x for x in rel if x and x != it.get("page_id")]
    if rel and it.get("page_id"):
        r = api("PATCH", f"/pages/{it['page_id']}", {"properties": {"관련 항목": {"relation": [{"id": x} for x in rel]}}})
        n_rel += len(rel) if "error" not in r else 0
log(f"created {created}, updated {updated}, failed {failed}, relations {n_rel}")
