"""
07_serialize.py — 3단계 목차 구조용 블록 직렬화.

DB 행은 **Ⅰ → 1. → 1) 3단계까지만** 만든다(36행).
그 아래 (1)/1.1)/4.2.1)/a) 689개 항목은 해당 L3 페이지 **본문 안의 소제목**으로 흡수한다.
  L4 → H2(파란 배경) + 요약 한 줄
  L5 → H3
  L6·L7 → 굵은 문단

산출: _output/page_blocks.json {node_id: [block, ...]}  (L1·L2·L3 36개만)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as C
import notion_blocks as NB
from notion_api import count_blocks

MAX_DB_LEVEL = int(__import__("os").environ.get("BOOK_MAX_DB_LEVEL", 3))


def load(p: Path, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def descendants_of(sec: dict, order: list[dict], s: dict) -> list[dict]:
    """목차 순서상 s 다음부터, s보다 얕거나 같은 레벨이 나오기 전까지 = s의 서브트리."""
    out = []
    for t in order:
        if t["seq"] <= s["seq"]:
            continue
        if t["level"] <= s["level"]:
            break
        out.append(t)
    return out


def main():
    sec = json.loads(C.SECTIONS_JSON.read_text(encoding="utf-8"))
    summaries = load(C.SUMMARIES_JSON, {})
    ocr = load(C.FIGOCR_JSON, {})
    urls = load(C.DRIVE_URLS, {})
    files = load(C.DRIVE_FILES, [])
    pdf_url = files[0]["url"] if files else None

    figs = load(C.FIGURES_JSON, [])
    exp_img, exp_tbl = len(figs), sum(
        1 for s in sec.values() for b in s["blocks"] if b["type"] == "table")
    for name, obj, exp in [("summaries.json", summaries, len(sec)),
                           ("figocr.json", ocr, exp_img),
                           ("drive_urls.json", urls, exp_img)]:
        print(f"  {name:18s} {len(obj):5d}개  "
              f"{'OK' if len(obj) >= exp else f'부족 ({len(obj)}/{exp})'}")

    order = sorted(sec.values(), key=lambda s: s["seq"])
    rows = [s for s in order if s["level"] <= MAX_DB_LEVEL]
    print(f"\nDB 행: {len(rows)}개 (레벨 {MAX_DB_LEVEL}까지) / "
          f"본문 흡수: {len(order) - len(rows)}개")

    pages: dict[str, list] = {}
    tot_img = tot_tbl = 0
    for s in rows:
        if s["level"] < MAX_DB_LEVEL and s["children"]:
            blocks = NB.build_branch_page(s, summaries, pdf_url)
        else:
            desc = descendants_of(sec, order, s)
            blocks = NB.build_leaf_page(s, desc, summaries, ocr, urls, pdf_url)
        pages[s["id"]] = blocks
        tot_img += sum(1 for b in blocks if b["type"] == "image")
        tot_tbl += sum(1 for b in blocks if b["type"] == "table")

    counts = {k: sum(count_blocks(b) for b in v) for k, v in pages.items()}
    big = max(counts.items(), key=lambda kv: kv[1])
    est = sum(-(-v // 85) for v in counts.values())

    C.PAGE_BLOCKS.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    print(f"image 블록 {tot_img}개 / table 블록 {tot_tbl}개")
    print(f"총 블록 {sum(counts.values())}개, 최대 {big[1]}개 ({sec[big[0]]['display'][:38]})")
    print(f"예상 append {est}회 → 약 {est * 0.34 / 60:.1f}분")
    print(f"[DONE] {C.PAGE_BLOCKS} ({C.PAGE_BLOCKS.stat().st_size / 1024 / 1024:.1f}MB)")

    if tot_img != exp_img or tot_tbl != exp_tbl:
        print(f"[WARN] 기대치와 다름 (image {exp_img} / table {exp_tbl})", file=sys.stderr)


if __name__ == "__main__":
    main()
