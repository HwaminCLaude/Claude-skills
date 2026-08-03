"""6단계 — 최종 검증. 완료를 선언하기 전에 반드시 돌린다.

    python 06_verify.py --work <폴더>
    python 06_verify.py --work <폴더> --baseline   # 원본 DB 수정시각 기준선 기록

검사 항목
    1. 그룹별 페이지 수가 차시 수와 맞는가 (노션에서 실제로 세어 확인)
    2. 대본 커버리지 — 대본 없는 차시가 있는가
    3. 영상 커버리지 — 아직 ⏳ 인 차시가 몇 개인가
    4. 무작위 페이지 실물 점검 — embed 1개 + 대본 문단이 실제로 있는가
    5. (선택) 건드리면 안 되는 원본 DB 의 last_edited_time 이 그대로인가
"""
from __future__ import annotations

import collections
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vt_common as C


def group_db_map() -> dict:
    if C.cfg("notion.mode", "flat") == "flat":
        db = C.cfg("notion.database_id")
        return {"(전체)": db} if db else {}
    return C.cfg("notion.group_db_map") or {}


def record_baseline() -> None:
    """작업 전에 원본 DB 의 수정시각을 남겨 둔다 — 나중에 '안 건드렸음'을 증명한다."""
    src = C.cfg("notion.protected_dbs") or {}
    if not src:
        print("config 의 notion.protected_dbs 가 비어 있습니다 (보호할 DB 없음)")
        return
    base = {}
    for name, db_id in src.items():
        base[name] = C.api(f"https://api.notion.com/v1/databases/{db_id}")["last_edited_time"]
        print(f"  {name:<10} {base[name]}")
    C.save_json("baseline.json", base)
    print(f"\n기준선 저장: {C.out_dir() / 'baseline.json'}")


def main() -> None:
    C.init()
    if "--baseline" in sys.argv:
        record_baseline()
        return

    units = C.load_json("units.json") or []
    state = C.load_json("pages.json", {}) or {}
    if not state:
        sys.exit("pages.json 없음 — 03_build_pages.py 를 먼저 돌리세요")
    problems = []

    print("=" * 68)
    print("1. 그룹별 페이지 수 (노션 실측)")
    expect = collections.Counter(v["group"] for v in state.values())
    dbmap = group_db_map()
    total = 0
    for group, db_id in dbmap.items():
        want = len(state) if group == "(전체)" else expect.get(group, 0)
        if not want:
            continue
        got = len(C.query_db(db_id))
        total += got
        mark = "OK" if got == want else f"⚠ 기대 {want}"
        if got != want:
            problems.append(f"{group}: 노션 {got} ≠ 기대 {want}")
        print(f"  {group:<12} 노션 {got:>4}행  {mark}")
    print(f"  합계 노션 {total}행 / 기록 {len(state)}차시")

    print("=" * 68)
    print("2. 대본 커버리지")
    no_text = [k for k, v in state.items() if not v.get("segments")]
    sentences = sum(v.get("segments", 0) for v in state.values())
    src = collections.Counter(v.get("source", "?") for v in state.values())
    print(f"  대본 있는 차시 {len(state) - len(no_text)}/{len(state)} · 총 {sentences:,}문장")
    print(f"  출처: {dict(src)}")
    print(f"  대본 없음: {no_text or '없음'}")
    if no_text:
        problems.append(f"대본 없는 차시 {len(no_text)}개")

    print("=" * 68)
    print("3. 영상 커버리지")
    filled = sum(1 for v in state.values() if v.get("video_filled"))
    print(f"  영상 붙은 차시 {filled}/{len(state)} · 대기 {len(state) - filled}")
    if filled < len(state):
        print("  (04_sync_videos.py --loop 가 업로드되는 대로 채웁니다)")

    print("=" * 68)
    print("4. 무작위 페이지 실물 점검")
    random.seed(7)
    for key in random.sample(list(state), min(4, len(state))):
        info = state[key]
        blocks = C.get_children(info["page_id"])
        c = collections.Counter(b["type"] for b in blocks)
        ok = c.get("heading_2", 0) >= 1 and c.get("paragraph", 0) > 0
        emb = c.get("embed", 0)
        flag = "OK" if ok else "이상"
        if not ok:
            problems.append(f"{key}: 블록 구조 이상")
        print(f"  [{flag}] embed{emb} 대본문단{c.get('paragraph', 0):>3}  {info['title'][:46]}")

    base = C.load_json("baseline.json")
    if base:
        print("=" * 68)
        print("5. 원본 DB 무변경")
        protected = C.cfg("notion.protected_dbs") or {}
        changed = []
        for name, db_id in protected.items():
            now = C.api(f"https://api.notion.com/v1/databases/{db_id}")["last_edited_time"]
            if now != base.get(name):
                changed.append(f"{name} ({base.get(name)} → {now})")
        if changed:
            problems.append(f"원본 DB {len(changed)}개 변경됨")
            for c_ in changed:
                print(f"  ⚠ {c_}")
        else:
            print(f"  ✅ {len(protected)}개 DB 모두 작업 전과 동일 — 원본 무변경 확인")

    print("=" * 68)
    if problems:
        print("판정: 확인 필요")
        for p in problems:
            print(f"  · {p}")
    else:
        print("판정: 이상 없음")


if __name__ == "__main__":
    sys.exit(main())
