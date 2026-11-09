"""Apply short titles and one-line results from concise.json ({key: {"title": ..., "result": ...}}).
Gallery cards show the title and 한줄 성과, so keep titles <= ~20 chars and results <= ~28 chars,
numbers first. The previous long result is kept in items.json as long_result for the page quote."""
from notion_lib import *

items = load_json("items.json")
concise = load_json("concise.json")
changed = 0
for key, c in concise.items():
    it = items.get(key)
    if not it or not it.get("page_id"):
        log(f"skip {key}: not in items.json or no page_id")
        continue
    props = {}
    if c.get("title") and c["title"] != it["title"]:
        props["이름"] = {"title": [{"type": "text", "text": {"content": c["title"]}}]}
    if c.get("result"):
        props["한줄 성과"] = text_prop(c["result"])
    if props:
        r = api("PATCH", f"/pages/{it['page_id']}", {"properties": props})
        if "error" in r:
            log(f"FAIL {key}: {r['body'][:160]}")
            continue
        changed += 1
    it["long_result"] = it.get("long_result") or it["result"]
    if c.get("result"):
        it["result"] = c["result"]
    if c.get("title"):
        it["title"] = c["title"]
save_json(items, "items.json")
longest = max((len(it["result"]), it["title"]) for it in items.values())
log(f"updated {changed} pages; longest 한줄 성과: {longest}")
