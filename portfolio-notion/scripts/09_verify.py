"""Verify the built portfolio: rows vs items, sections, periods, tabs and per-tab counts, files, URLs
(requests, redirects followed), summary quotes, and number provenance (config "number_checks":
{source_url: [numbers that must appear in that file]}). Writes logs/verify_report.json."""
from notion_lib import *

try:
    import requests
except ImportError:
    requests = None
state = load_state()
db_id, DS = master_ids(state)
items = load_json("items.json")
rep = {"checks": [], "missing_period": [], "url_status": {}, "numbers": {}}


def check(name, ok, detail=""):
    rep["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    log(f"[{'OK' if ok else 'FAIL'}] {name} {detail}")


rows = paginate("POST", f"/data_sources/{DS}/query", {"page_size": 100})
by_id = {r["id"]: r for r in rows}
check("master rows = items", len(rows) == len(items), f"{len(rows)} rows / {len(items)} items")
check("every item exists", all(it.get("page_id") in by_id for it in items.values()))
check("all rows have 섹션", all(r["properties"]["섹션"].get("select") for r in rows))
for r in rows:
    t = (r["properties"]["분류"].get("select") or {}).get("name")
    if t != "Tool" and not r["properties"]["기간"].get("date"):
        rep["missing_period"].append(title_of(r))
log(f"non-Tool rows without 기간 ({len(rep['missing_period'])}): {rep['missing_period']}")
expected = {}
for it in items.values():
    expected[it["section"]] = expected.get(it["section"], 0) + 1
total_tabs = 0
for key, info in state.get("created_blocks", {}).items():
    if not isinstance(info, dict) or "views" not in info:
        continue
    for vid in info["views"]:
        v = api_ok("GET", f"/views/{vid}", ver=V_NEW)
        total_tabs += 1
        q = api("POST", f"/views/{vid}/queries", {}, ver=V_NEW)
        if "error" in q:
            check(f"tab query {v['name']}", False, q["body"][:100])
            continue
        n = q.get("total_count", len(q.get("results", [])))
        api("DELETE", f"/views/{vid}/queries/{q.get('query_id')}", ver=V_NEW)
        sec = None
        f = v.get("filter") or {}
        for cond in ([f] + f.get("and", [])):
            if isinstance(cond, dict) and cond.get("property") == "섹션":
                sec = cond["select"]["equals"]
        exp = expected.get(sec) if sec else None
        check(f"tab {v['name']} ({v['type']})", exp is None or n == exp, f"{n} rows" + (f", section expects {exp}" if sec else ""))
log(f"tabs on main page: {total_tabs}")
no_quote = [it["title"] for it in items.values() if it.get("page_id") and not any(b["type"] == "quote" for b in children(it["page_id"])[:4])]
check("all pages have summary quote", not no_quote, str(no_quote))
urls = {r["properties"][k].get("url") for r in rows for k in ("GitHub", "배포 링크", "논문/자료 링크") if r["properties"].get(k, {}).get("url")}
if requests:
    for u in sorted(urls):
        try:
            rep["url_status"][u] = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=60, allow_redirects=True).status_code
        except Exception as e:
            rep["url_status"][u] = str(e)[:80]
    bad = {u: s for u, s in rep["url_status"].items() if s != 200}
    check("property URLs reachable", not bad, str(bad))
for url, nums in CFG.get("number_checks", {}).items():
    try:
        txt = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text if requests else ""
        missing = [n for n in nums if n not in txt]
        rep["numbers"][url] = missing
        check(f"numbers in {url.split('/')[-1]}", not missing, f"missing={missing}")
    except Exception as e:
        check(f"fetch {url}", False, str(e)[:100])
save_json(rep, "logs/verify_report.json")
fails = [c for c in rep["checks"] if not c["ok"]]
log(f"VERIFY DONE: {len(rep['checks'])} checks, {len(fails)} failed")
