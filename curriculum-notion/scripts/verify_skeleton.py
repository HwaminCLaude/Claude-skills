# -*- coding: utf-8 -*-
"""verify_skeleton.py — 발행된 뼈대가 curriculum.json 과 정확히 일치하는지 검사.

부족(누락)뿐 아니라 **초과(중복)** 도 잡는다.
    python verify_skeleton.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent

def _need(name: str, hint: str):
    """없으면 트레이스백 대신 무엇을 먼저 하라고 알려 준다."""
    import json as _j
    import sys as _s
    p = HERE / name
    if not p.exists():
        print(f"[!] {name} 가 없습니다. 먼저 {hint} 를 실행하세요.", file=_s.stderr)
        _s.exit(2)
    return _j.loads(p.read_text(encoding="utf-8"))

import notion_api as N  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CUR = _need("curriculum.json", "curriculum.py --dump")
ST = _need("state.json", "publish_skeleton.py")


def title_of(page: dict) -> str:
    for v in (page.get("properties") or {}).values():
        if v.get("type") == "title":
            return "".join(x.get("plain_text", "") for x in v["title"])
    return ""


def main() -> int:
    errs: list[str] = []

    top = N.query_all(CUR["data_source_id"])
    names = [title_of(p) for p in top]
    print(f"코딩북 최상위 행: {len(top)}개 (기대 {len(CUR['weeks'])})")
    if len(top) != len(CUR["weeks"]):
        errs.append(f"최상위 행 수 {len(top)} ≠ {len(CUR['weeks'])}")
    if len(names) != len(set(names)):
        dup = {n for n in names if names.count(n) > 1}
        errs.append(f"최상위 중복 제목: {dup}")

    by_week = {}
    for u in CUR["units"]:
        by_week.setdefault(u["week"], []).append(u)

    print(f"\n{'주차':<6}{'유닛(노션)':>10}{'기대':>6}   판정")
    total = 0
    for wk in CUR["weeks"]:
        w = wk["week"]
        ent = ST["weeks"].get(str(w)) or {}
        ds = ent.get("unit_ds")
        if not ds:
            errs.append(f"{w}주차 유닛 DB 없음")
            continue
        rows = N.query_all(ds)
        got = [title_of(p) for p in rows]
        exp = [u["title"] for u in by_week[w]]
        total += len(rows)
        ok = sorted(got) == sorted(exp)
        print(f"{w:<6}{len(rows):>10}{len(exp):>6}   {'OK' if ok else '불일치'}")
        if not ok:
            miss = set(exp) - set(got)
            extra = set(got) - set(exp)
            if miss:
                errs.append(f"{w}주차 누락: {sorted(miss)}")
            if extra:
                errs.append(f"{w}주차 초과: {sorted(extra)}")
        if len(got) != len(set(got)):
            errs.append(f"{w}주차 중복 행 있음")

    print(f"\n유닛 합계 {total} / 기대 {len(CUR['units'])}")
    if total != len(CUR["units"]):
        errs.append(f"유닛 합계 {total} ≠ {len(CUR['units'])}")

    if errs:
        print("\n[검증 실패]")
        for e in errs:
            print("  -", e)
        return 1
    print("\n검증 통과 — 뼈대가 커리큘럼과 정확히 일치합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
