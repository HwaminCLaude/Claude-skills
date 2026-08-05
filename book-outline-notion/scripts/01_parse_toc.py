"""
01_parse_toc.py — PDF 목차 페이지를 파싱해 725노드 트리를 만든다.

이 PDF는 내장 북마크가 0개라 목차 페이지(기본 3~23쪽)의 텍스트를 직접 읽는다.
목차는 `제목` 다음 줄에 `쪽번호` 가 오는 2줄 구조이며, 들여쓰기는 신뢰할 수 없어
번호 체계(Ⅰ. / 1. / 1) / (1) / 1.1) / 4.2.1) / a))로 레벨을 판정한다.

산출: _output/toc.json
게이트: 노드 수가 EXPECTED_NODES(725)와 다르거나 쪽번호 없는 노드가 있으면 중단.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).parent))
import config as C

PAGE_ONLY = re.compile(r"^\d{1,3}$")


def toc_lines() -> list[str]:
    """목차 페이지들의 비어있지 않은 줄을 순서대로 모은다."""
    doc = fitz.open(C.PDF_PATH)
    out: list[str] = []
    for pno in range(C.TOC_PAGE_FIRST, C.TOC_PAGE_LAST + 1):
        for raw in doc[pno - 1].get_text("text").splitlines():
            s = raw.strip()
            if s:
                out.append(s)
    doc.close()
    return out


def parse_nodes(lines: list[str]) -> tuple[list[dict], list[str]]:
    """(노드 목록, 무시된 줄) — `제목` + `쪽번호` 쌍을 훑는다."""
    nodes: list[dict] = []
    skipped: list[str] = []
    i = 0
    while i < len(lines):
        s = lines[i]
        if PAGE_ONLY.fullmatch(s):        # 짝을 잃은 쪽번호
            i += 1
            continue
        hit = C.match_level(s)
        if not hit:                        # '목   차' 같은 머리글
            skipped.append(s)
            i += 1
            continue
        level, num, title = hit
        page = None
        if i + 1 < len(lines) and PAGE_ONLY.fullmatch(lines[i + 1]):
            page = int(lines[i + 1])
        nodes.append({"level": level, "num": num, "title": title, "page": page})
        i += 2 if page is not None else 1
    return nodes, skipped


def build_tree(nodes: list[dict]) -> list[dict]:
    """레벨 스택으로 부모를 붙이고 경로·순번·부(Part)·끝쪽을 채운다."""
    stack: dict[int, dict] = {}
    for idx, n in enumerate(nodes):
        n["id"] = f"n{idx + 1:04d}"
        n["seq"] = idx + 1
        n["display"] = C.display_title(n["level"], n["num"], n["title"])
        n["prefix"] = C.prefix_for(n["level"], n["num"])
        n["children"] = []

        parent = None
        for lv in range(n["level"] - 1, 0, -1):
            if lv in stack:
                parent = stack[lv]
                break
        n["parent"] = parent["id"] if parent else None
        n["path"] = (parent["path"] + " > " + n["prefix"]) if parent else n["prefix"]
        n["part"] = parent["part"] if parent else n["num"]
        if parent:
            parent["children"].append(n["id"])

        stack[n["level"]] = n
        for lv in [k for k in stack if k > n["level"]]:
            del stack[lv]

    # 끝쪽 = 자기 서브트리에 속하지 않는 다음 노드의 시작쪽 (없으면 본문 끝)
    for i, n in enumerate(nodes):
        end = C.BODY_LAST
        for j in range(i + 1, len(nodes)):
            if nodes[j]["level"] <= n["level"]:
                end = nodes[j]["page"]
                break
        n["end_page"] = max(n["page"], end)
        n["pages"] = n["end_page"] - n["page"] + 1
    return nodes


def main():
    lines = toc_lines()
    nodes, skipped = parse_nodes(lines)

    print(f"목차 줄 {len(lines)}개 → 노드 {len(nodes)}개 (무시 {len(skipped)}줄: {skipped[:5]})")

    missing_page = [n for n in nodes if n["page"] is None]
    if missing_page:
        print(f"[ERROR] 쪽번호 없는 노드 {len(missing_page)}개:", file=sys.stderr)
        for n in missing_page[:10]:
            print(f"   L{n['level']} {n['num']} | {n['title']}", file=sys.stderr)
        sys.exit(1)

    if len(nodes) != C.EXPECTED_NODES:
        print(f"[ERROR] 노드 수 {len(nodes)} != 기대값 {C.EXPECTED_NODES}. "
              f"목차 범위(BOOK_TOC_FIRST/LAST)나 번호 패턴을 확인하세요.", file=sys.stderr)
        sys.exit(1)

    nodes = build_tree(nodes)

    # 요약 리포트
    from collections import Counter
    lv = Counter(n["level"] for n in nodes)
    parents = sum(1 for n in nodes if n["children"])
    print("레벨별:", " ".join(f"L{k}={lv[k]}" for k in sorted(lv)))
    print(f"부모 {parents}개 / 말단 {len(nodes) - parents}개")
    print("부(Part)별:", dict(Counter(n["part"] for n in nodes)))

    C.TOC_JSON.write_text(json.dumps(nodes, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[DONE] {C.TOC_JSON}")

    print("\n샘플 (앞 6개):")
    for n in nodes[:6]:
        print(f"  #{n['seq']:3d} L{n['level']} {n['display'][:45]:47s} p{n['page']}-{n['end_page']}  {n['path']}")


if __name__ == "__main__":
    main()
