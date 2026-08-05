"""
14_rebuild_depth3.py — Notion DB를 **3단계 목차 구조**로 다시 만든다.

  📚 최상위 DB (4행)  Ⅰ / Ⅱ / Ⅲ / Ⅳ
     └ 행을 열면 📂 하위 목차 DB (2행)  1. / 2.
          └ 행을 열면 📂 하위 목차 DB (2~7행)  1) / 2) …
               └ 이 행을 열면 **본문 전체** — (1)/1.1) 등 689개 항목이 소제목으로 들어있다

DB 행은 36개(4+8+24)뿐이고, 그 아래 목차는 페이지 본문의 H2/H3 소제목이 된다.
기존에 만든 725행 구조는 전부 보관처리(archive)하고 새로 만든다.

멱등: _output/depth3_state.json 에 기록해 중단 후 이어서 재개한다.
사용: python scripts/14_rebuild_depth3.py [--purge-only] [--skip-purge]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as C
import notion_api as N

STATE = C.OUT_DIR / "depth3_state.json"
CHILD_DB_TITLE = "📂 하위 목차"
# 07_serialize.py 와 반드시 같은 값이어야 한다(같은 환경변수를 읽는다).
MAX_DB_LEVEL = int(__import__("os").environ.get("BOOK_MAX_DB_LEVEL", 3))


def schema_from(ds: dict) -> dict:
    """부모 DB 스키마 복제(relation 제외). move/create 시 값 보존에 필요."""
    props = {}
    for k, v in (ds.get("properties") or {}).items():
        t = v["type"]
        if t == "relation":
            continue
        if t == "title":
            props[k] = {"title": {}}
        elif t == "select":
            props[k] = {"select": {"options": [{"name": o["name"]}
                                               for o in v["select"]["options"]]}}
        elif t == "number":
            props[k] = {"number": {"format": v["number"].get("format", "number")}}
        else:
            props[k] = {t: {}}
    return props


def row_props(s: dict, summary: str) -> dict:
    p = {
        C.TITLE_PROP: {"title": [{"text": {"content": s["display"][:2000]}}]},
        "순번": {"number": s["seq"]},
        "레벨": {"select": {"name": f"L{s['level']}"}},
        "번호": {"rich_text": [{"text": {"content": str(s["num"])[:2000]}}]},
        "경로": {"rich_text": [{"text": {"content": s["path"][:2000]}}]},
        "부": {"select": {"name": s["part"]}},
        "시작쪽": {"number": s["page_start"]},
        "끝쪽": {"number": s["page_end"]},
        "쪽수": {"number": s["page_end"] - s["page_start"] + 1},
        "표": {"number": s["n_table"]},
        "그림": {"number": s["n_figure"]},
        "상태": {"select": {"name": "본문완료"}},
    }
    if summary:
        p["요약"] = {"rich_text": [{"text": {"content": summary[:2000]}}]}
    return p


def subtree_counts(order: list[dict], s: dict) -> tuple[int, int]:
    """서브트리 전체의 표·그림 합계 (L3 행 속성에 실제 포함량을 반영)."""
    nt, nf = s["n_table"], s["n_figure"]
    for d in order:
        if d["seq"] <= s["seq"]:
            continue
        if d["level"] <= s["level"]:
            break
        nt += d["n_table"]
        nf += d["n_figure"]
    return nt, nf


def purge(state: dict):
    """이전 725행 구조를 전부 보관처리한다."""
    old = C.STATE_JSON
    ids = []
    if old.exists():
        ids = [v["page_id"] for v in json.loads(old.read_text(encoding="utf-8")).values()
               if v.get("page_id")]
    done = set(state.get("purged") or [])
    todo = [i for i in ids if i not in done]
    print(f"이전 구조 정리: {len(todo)}개 보관처리 (완료 {len(done)})")
    for i, pid in enumerate(todo, 1):
        try:
            N.archive_block(pid)
        except N.NotionError as e:
            if e.status not in (400, 404):     # 이미 지워진 경우는 무시
                print(f"  [WARN] {pid}: {e}", file=sys.stderr)
        done.add(pid)
        if i % 100 == 0:
            print(f"  {i}/{len(todo)}")
            state["purged"] = sorted(done)
            STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    state["purged"] = sorted(done)
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    left = N.query_all(C.NOTION_DS_ID)
    print(f"  최상위 DB 남은 행: {len(left)}개")
    for r in left:
        try:
            N.archive_block(r["id"])
        except N.NotionError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--purge-only", action="store_true")
    ap.add_argument("--skip-purge", action="store_true")
    args = ap.parse_args()

    sec = json.loads(C.SECTIONS_JSON.read_text(encoding="utf-8"))
    pages = json.loads(C.PAGE_BLOCKS.read_text(encoding="utf-8"))
    summaries = json.loads(C.SUMMARIES_JSON.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    state.setdefault("rows", {})
    state.setdefault("dbs", {})

    order = sorted(sec.values(), key=lambda s: s["seq"])
    schema = schema_from(N.get_data_source(C.NOTION_DS_ID))

    if not args.skip_purge:
        purge(state)
    if args.purge_only:
        return

    def save():
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    def make_row(ds_id: str, s: dict) -> str:
        """행 생성 + 본문 append (멱등)."""
        rec = state["rows"].get(s["id"])
        if rec and rec.get("done"):
            return rec["page_id"]
        props = row_props(s, summaries.get(s["id"], ""))
        if s["level"] == MAX_DB_LEVEL:
            nt, nf = subtree_counts(order, s)
            props["표"] = {"number": nt}
            props["그림"] = {"number": nf}
        if not rec or not rec.get("page_id"):
            page = N.create_page({"type": "data_source_id", "data_source_id": ds_id},
                                 props)
            rec = {"page_id": page["id"]}
            state["rows"][s["id"]] = rec
            save()
        blocks = pages.get(s["id"])
        if blocks is None:
            print(f"  [WARN] page_blocks 에 {s['id']}({s['display'][:30]}) 없음 — "
                  f"07_serialize.py 를 같은 BOOK_MAX_DB_LEVEL 로 다시 실행하세요.",
                  file=sys.stderr)
            blocks = []
        N.chunked_append(rec["page_id"], blocks, limit=85)
        rec["done"] = True
        save()
        return rec["page_id"]

    def make_child_db(page_id: str, key: str) -> str:
        if key in state["dbs"]:
            return state["dbs"][key]
        db = N.request("databases", "POST", {
            "parent": {"type": "page_id", "page_id": page_id},
            "title": [{"type": "text", "text": {"content": CHILD_DB_TITLE}}],
            "is_inline": True,
            "initial_data_source": {"properties": schema},
        })
        state["dbs"][key] = db["data_sources"][0]["id"]
        save()
        return state["dbs"][key]

    roots = [s for s in order if s["level"] == 1]
    n_rows = n_dbs = 0
    for s1 in roots:
        p1 = make_row(C.NOTION_DS_ID, s1)
        n_rows += 1
        kids2 = [sec[k] for k in s1["children"]]
        if not kids2:
            continue
        ds1 = make_child_db(p1, s1["id"])
        n_dbs += 1
        for s2 in sorted(kids2, key=lambda x: x["seq"]):
            p2 = make_row(ds1, s2)
            n_rows += 1
            kids3 = [sec[k] for k in s2["children"]]
            if not kids3:
                continue
            ds2 = make_child_db(p2, s2["id"])
            n_dbs += 1
            for s3 in sorted(kids3, key=lambda x: x["seq"]):
                make_row(ds2, s3)
                n_rows += 1
                print(f"  [{n_rows:2d}/36] {s3['display'][:46]}")

    save()
    top = N.query_all(C.NOTION_DS_ID)
    print(f"\n행 {n_rows}개 / 하위 DB {n_dbs}개")
    print(f"최상위 DB: {len(top)}행")
    for r in top:
        print("    · " + "".join(x["plain_text"]
                                 for x in r["properties"][C.TITLE_PROP]["title"]))
    print(f"[DONE] {STATE}")


if __name__ == "__main__":
    main()
