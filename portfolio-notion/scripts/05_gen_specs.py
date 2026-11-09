"""Generate pages/<key>.json body specs for every item: a summary quote (long_result, 기간, 역할, 기관, 기술,
링크) + custom sections from pages_custom/<key>.json + a related-links section built from legacy
labeled links found in backup/full_backup.json (restructure mode). No provenance/meta sentences."""
import glob
from notion_lib import *

items = load_json("items.json")
try:
    backup = load_json("backup/full_backup.json")
    rows_by_id = {r["id"]: r for rows in backup["rows"].values() for r in rows}
except FileNotFoundError:
    rows_by_id = {}
custom = {}
for f in glob.glob(os.path.join(ROOT, "pages_custom", "*.json")):
    c = load_json(f)
    custom[c.get("key") or c.get("page_id")] = c
REMOVE = CFG.get("remove_text_contains", [])


def legacy_links(row):
    out = []
    for pname, p in row.get("properties", {}).items():
        if p["type"] == "rich_text":
            for seg in p["rich_text"]:
                if seg.get("href"):
                    out.append((seg.get("plain_text", "").strip() or pname, seg["href"]))
        elif p["type"] == "url" and p.get("url"):
            out.append((pname, p["url"]))
    return out


os.makedirs(os.path.join(ROOT, "pages"), exist_ok=True)
n = 0
for key, it in items.items():
    pid = it.get("page_id")
    if not pid:
        continue
    lines = [f"**{it.get('long_result') or it['result']}**"]
    per = it.get("period")
    if per:
        s, e = per["start"], per.get("end")
        lines.append(f"기간: {s} ~ {e}" if e else (f"기간: {s} ~ 진행 중" if it.get("status") == "진행 중" else f"기간: {s}"))
    if it.get("role"):
        lines.append(f"역할: {it['role']}")
    if it.get("org"):
        lines.append(f"기관·주최: {it['org']}")
    if it.get("stack"):
        lines.append("기술: " + ", ".join(it["stack"]))
    links = [f"[GitHub]({it['github']})" if it.get("github") else None,
             f"[배포 사이트]({it['deploy']})" if it.get("deploy") else None,
             f"[논문·자료]({it['paper']})" if it.get("paper") else None]
    links = [x for x in links if x]
    if links:
        lines.append("링크: " + " · ".join(links))
    spec = {"page_id": pid, "key": key, "title": it["title"], "top_summary": {"lines": lines},
            "remove_text_contains": REMOVE, "append": []}
    c = custom.get(key) or custom.get(pid)
    if c:
        spec["append"] += c.get("append", [])
    known = {it.get("github"), it.get("deploy"), it.get("paper")}
    rel, seen = [], set()
    for label, url in legacy_links(rows_by_id.get(pid, {})):
        if url in known or url in seen:
            continue
        seen.add(url)
        rel.append(f"[{label}]({url})")
    if rel:
        spec["append"] += [{"h2": "관련 자료"}, {"bullets": rel}]
    save_json(spec, os.path.join("pages", f"{key}.json"))
    n += 1
log(f"generated {n} specs ({len(custom)} with custom sections)")
