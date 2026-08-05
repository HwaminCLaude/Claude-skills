"""
13_verify_nested.py — 중첩 DB 구조를 최상위부터 실제로 타고 내려가며 검증한다.

기본은 3단계(Ⅰ → 1. → 1))이며 BOOK_MAX_DB_LEVEL 로 바꿀 수 있다.
말단(L3) 페이지에는 그 아래 목차(L4~L7)가 소제목으로 흡수돼 있어야 하므로,
행 구조뿐 아니라 **본문 안 소제목·이미지·표 개수까지** 실제로 센다.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as C
import notion_api as N

MAX_DB_LEVEL = int(os.environ.get("BOOK_MAX_DB_LEVEL", 3))
OK, FAIL = [], []


def check(name: str, cond: bool, detail: str = ""):
    (OK if cond else FAIL).append((name, detail))
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def title_of(row: dict) -> str:
    return "".join(x.get("plain_text", "")
                   for x in row["properties"][C.TITLE_PROP]["title"])


def child_ds(page_id: str) -> str | None:
    for b in N.get_children(page_id):
        if b["type"] == "child_database":
            srcs = (N.get_database(b["id"]).get("data_sources") or [])
            if srcs:
                return srcs[0]["id"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spot", type=int, default=6)
    args = ap.parse_args()

    sec = json.loads(C.SECTIONS_JSON.read_text(encoding="utf-8"))
    order = sorted(sec.values(), key=lambda s: s["seq"])
    print("=" * 64)
    print(f" 중첩 DB 구조 검증 (DB 깊이 {MAX_DB_LEVEL}단계)")
    print("=" * 64)

    print("\n== 1. 최상위 DB ==")
    top = N.query_all(C.NOTION_DS_ID)
    names = sorted(title_of(r) for r in top)
    expect = sorted(s["display"] for s in sec.values() if s["level"] == 1)
    check("최상위 4행", len(top) == 4, f"실제 {len(top)}개")
    check("최상위가 Ⅰ~Ⅳ", names == expect, "" if names == expect else f"{names}")

    print("\n== 2. 트리 순회 ==")
    seen: dict[int, str] = {}
    problems: list[str] = []

    def walk(ds_id: str, expect_ids: list[str], depth: int):
        rows = N.query_all(ds_id)
        got = {}
        for r in rows:
            seq = (r["properties"].get("순번") or {}).get("number")
            if seq is None:
                problems.append(f"순번 없는 행: {title_of(r)}")
                continue
            got[seq] = r
            seen[seq] = r["id"]
        want = {sec[i]["seq"] for i in expect_ids}
        if set(got) != want:
            problems.append(f"depth{depth} 누락{sorted(want - set(got))[:4]} "
                            f"초과{sorted(set(got) - want)[:4]}")
        for i in expect_ids:
            s = sec[i]
            r = got.get(s["seq"])
            if not r:
                continue
            if title_of(r) != s["display"]:
                problems.append(f"제목 불일치 {title_of(r)!r}")
            if s["level"] < MAX_DB_LEVEL and s["children"]:
                cds = child_ds(r["id"])
                if not cds:
                    problems.append(f"하위 DB 없음: {s['display']}")
                else:
                    walk(cds, s["children"], depth + 1)

    roots = [s["id"] for s in order if s["level"] == 1]
    walk(C.NOTION_DS_ID, roots, 1)

    n_rows = sum(1 for s in order if s["level"] <= MAX_DB_LEVEL)
    check(f"DB 행 {n_rows}개 도달", len(seen) == n_rows, f"실제 {len(seen)}개")
    check("구조 불일치 없음", not problems, f"{len(problems)}건 {problems[:3]}")

    print("\n== 3. 말단 페이지 본문 (하위 목차 흡수 확인) ==")
    leaves = [s for s in order if s["level"] == MAX_DB_LEVEL]
    exp_img = sum(1 for s in order for b in s["blocks"] if b["type"] == "figure")
    exp_tbl = sum(1 for s in order for b in s["blocks"] if b["type"] == "table")
    n_img = n_tbl = n_h2 = n_h3 = 0
    for i, s in enumerate(leaves, 1):
        pid = seen.get(s["seq"])
        if not pid:
            continue
        kids = N.get_children(pid)
        n_img += sum(1 for b in kids if b["type"] == "image")
        n_tbl += sum(1 for b in kids if b["type"] == "table")
        n_h2 += sum(1 for b in kids if b["type"] == "heading_2")
        n_h3 += sum(1 for b in kids if b["type"] == "heading_3")
        if i % 8 == 0:
            print(f"     {i}/{len(leaves)} (img {n_img}, tbl {n_tbl})")
    exp_h2 = sum(1 for s in order if s["level"] == 4)
    exp_h3 = sum(1 for s in order if s["level"] == 5)
    check(f"image 블록 {exp_img}개", n_img == exp_img, f"실제 {n_img}개")
    check(f"table 블록 {exp_tbl}개", n_tbl == exp_tbl, f"실제 {n_tbl}개")
    check(f"H2(=L4 소제목) {exp_h2}개", n_h2 == exp_h2, f"실제 {n_h2}개")
    check(f"H3(=L5 소제목) {exp_h3}개", n_h3 == exp_h3, f"실제 {n_h3}개")

    print("\n== 4. 원문 대조 표본 ==")
    rng = random.Random(20260805)
    bad = 0
    pool = [s for s in order if s["level"] > MAX_DB_LEVEL and s["blocks"]]
    for s in rng.sample(pool, min(args.spot, len(pool))):
        anc = next((a for a in reversed(order)
                    if a["level"] == MAX_DB_LEVEL and a["seq"] < s["seq"]), None)
        pid = seen.get(anc["seq"]) if anc else None
        if not pid:
            bad += 1
            continue
        txt = " ".join("".join(x.get("plain_text", "")
                               for x in (b.get(b["type"]) or {}).get("rich_text", []))
                       for b in N.get_children(pid))
        first = next((b["text"] for b in s["blocks"]
                      if b["type"] in ("bul", "p") and b.get("text")), "")
        if first and re.sub(r"\s+", "", first[:50]) not in re.sub(r"\s+", "", txt):
            bad += 1
            print(f"     ✗ {s['display'][:40]} (상위 {anc['display'][:24]})")
    check(f"표본 {args.spot}개 본문 보존", bad == 0, f"불일치 {bad}개")

    print("\n" + "=" * 64)
    if FAIL:
        print(f"실패 {len(FAIL)}건 ❌")
        for n, d in FAIL:
            print(f"  - {n} {d}")
        sys.exit(1)
    print(f"전체 통과 ✅ ({len(OK)}개 항목)")
    print(f"\n확인: {N.get_database(C.NOTION_DB_ID).get('url')}")


if __name__ == "__main__":
    main()
