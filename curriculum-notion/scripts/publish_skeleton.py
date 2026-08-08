# -*- coding: utf-8 -*-
"""publish_skeleton.py — curriculum.json → 코딩북 뼈대 발행.

만드는 것
  1. 코딩북 DB 스키마 확장 (주차·유닛수·상태)
  2. `00 · 학습 지도` + 17개 주차 페이지
  3. 각 주차 페이지 본문(목표·흐름·완료기준·강의자료) + 인라인 `📂 유닛` DB
  4. 유닛 행 86개 (제목·속성만. 본문은 Step 4에서 채움)

멱등: state.json 에 생성한 page_id/ds_id 를 기록해 이어서 재개한다.
같은 제목이 이미 있으면 재사용한다(중복 생성 안 함).

    python publish_skeleton.py --dry     # 무엇을 만들지만 출력
    python publish_skeleton.py           # 실제 발행
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


import notion_api as N          # noqa: E402
import blocks as B              # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CUR = _need("curriculum.json", "curriculum.py --dump")
STATE = HERE / "state.json"
UNIT_DB_TITLE = "📂 유닛"
DRIVE_BASE = "https://drive.google.com/drive/search?q="

TOP_PROPS = {
    "이름": {"title": {}},
    "주차": {"number": {"format": "number"}},
    "유닛수": {"number": {"format": "number"}},
    "상태": {"select": {"options": [{"name": "안함", "color": "default"},
                                   {"name": "공부중", "color": "yellow"},
                                   {"name": "완료", "color": "green"}]}},
}

UNIT_PROPS = {
    "이름": {"title": {}},
    "순서": {"number": {"format": "number"}},
    "유형": {"select": {"options": [{"name": "개념", "color": "blue"},
                                   {"name": "실습", "color": "green"},
                                   {"name": "보충", "color": "orange"},
                                   {"name": "프로젝트", "color": "purple"}]}},
    "난이도": {"select": {"options": [{"name": "입문", "color": "green"},
                                    {"name": "기본", "color": "blue"},
                                    {"name": "심화", "color": "red"}]}},
    "상태": {"select": {"options": [{"name": "안함", "color": "default"},
                                   {"name": "공부중", "color": "yellow"},
                                   {"name": "완료", "color": "green"}]}},
    "콜랩": {"url": {}},
    "예상시간": {"number": {"format": "number"}},
}


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def title_of(page: dict) -> str:
    for v in (page.get("properties") or {}).values():
        if v.get("type") == "title":
            return "".join(x.get("plain_text", "") for x in v["title"])
    return ""


def week_body(wk: dict, units: list[dict]) -> list:
    """주차 페이지 본문 — 목표·흐름·완료기준·자료 위치."""
    bs = [
        B.h1(f"{wk['week']}주차 · {wk['folder'].split('_', 1)[1]}"),
        B.callout(wk["intro"], "🎯", "orange_background"),
        B.p(f"이 주차는 **{len(units)}개 유닛**이고, 다 하면 대략 "
            f"**{sum(u['minutes'] for u in units) / 60:.1f}시간**이에요. "
            "아래 유닛을 **위에서부터 순서대로** 하나씩 열어서 따라가면 됩니다."),
        B.divider(),
        B.h2("이번 주에 할 수 있게 되는 것"),
    ]
    for u in units:
        bs.append(B.bullet(f"**{u['raw_title']}** — {u['goal']}"))
    bs += [
        B.divider(),
        B.h2("공부하는 방법"),
        B.callout(
            "유닛 페이지는 항상 같은 순서예요. **개념 → 수식(숫자 대입) → 직접 구현 → "
            "라이브러리 대조 검산 → 강의자료 적용 → 스스로 확인**. "
            "특히 **대조 검산**이 핵심이에요 — 내가 짠 코드가 맞는지 스스로 판정할 수 있게 "
            "`np.allclose(내구현, 라이브러리답)` 로 채점되게 만들어 뒀어요.", "🧭", "blue_background"),
        B.callout(
            "막히면 건너뛰지 말고 **바로 앞 유닛**으로 돌아가세요. "
            "각 유닛의 '선수지식' 칸에 무엇을 알고 와야 하는지 적어 뒀어요.", "⚠️", "red_background"),
        B.divider(),
        B.h2("원본 강의자료"),
        B.p(f"구글드라이브 `메타코드 실습프로젝트/{wk['folder']}/` 안에 "
            f"`{wk['week']}주차 실습`(코드·데이터)과 `{wk['week']}주차 강의자료`(슬라이드)가 있어요."),
        B.divider(),
        B.h2("유닛"),
    ]
    return bs


def ensure_top_schema() -> None:
    ds = N.get_data_source(CUR["data_source_id"])
    have = set((ds.get("properties") or {}).keys())
    add = {k: v for k, v in TOP_PROPS.items() if k not in have and v.get("title") is None}
    if add:
        N.update_data_source(CUR["data_source_id"], add)
        print(f"  코딩북 속성 추가: {', '.join(add)}")
    else:
        print("  코딩북 속성 이미 준비됨")


def existing_pages() -> dict[str, str]:
    rows = N.query_all(CUR["data_source_id"])
    return {title_of(p): p["id"] for p in rows}


def main() -> int:
    dry = "--dry" in sys.argv
    st = load_state()
    st.setdefault("weeks", {})

    weeks = CUR["weeks"]
    units_by_week = {}
    for u in CUR["units"]:
        units_by_week.setdefault(u["week"], []).append(u)

    print(f"발행 대상: 주차 {len(weeks)}개 / 유닛 {len(CUR['units'])}개"
          + ("   [미리보기]" if dry else ""))
    if dry:
        for wk in weeks:
            us = units_by_week[wk["week"]]
            print(f"  {wk['week']:>2}주차 ({len(us)}유닛)  {wk['folder']}")
            for u in us:
                print(f"        {u['title']}  [{u['type']}/{u['level']}/{u['minutes']}분]")
        return 0

    print("\n[1/3] 코딩북 스키마")
    ensure_top_schema()

    print("\n[2/3] 주차 페이지 + 유닛 DB")
    have = existing_pages()
    for wk in weeks:
        w = wk["week"]
        key = str(w)
        ent = st["weeks"].setdefault(key, {})
        name = f"{w:02d}주차 · {wk['folder'].split('_', 1)[1]}"
        us = units_by_week[w]

        # 주차 페이지
        if not ent.get("page_id"):
            if name in have:
                ent["page_id"] = have[name]
                print(f"  {name} — 기존 재사용")
            else:
                pg = N.create_page(
                    {"type": "data_source_id", "data_source_id": CUR["data_source_id"]},
                    {"이름": {"title": [{"text": {"content": name}}]},
                     "주차": {"number": w},
                     "유닛수": {"number": len(us)},
                     "상태": {"select": {"name": "안함"}}})
                ent["page_id"] = pg["id"]
                print(f"  {name} — 생성")
            save_state(st)

        # 본문
        if not ent.get("body_done"):
            N.chunked_append(ent["page_id"], week_body(wk, us))
            ent["body_done"] = True
            save_state(st)

        # 인라인 유닛 DB
        if not ent.get("unit_ds"):
            db = N.request("databases", "POST", {
                "parent": {"type": "page_id", "page_id": ent["page_id"]},
                "title": [{"type": "text", "text": {"content": UNIT_DB_TITLE}}],
                "is_inline": True,
                "initial_data_source": {"properties": UNIT_PROPS},
            })
            ent["unit_db"] = db["id"]
            ent["unit_ds"] = db["data_sources"][0]["id"]
            ent["units"] = {}
            save_state(st)
            print(f"      └ 유닛 DB 생성")

    print("\n[3/3] 유닛 행")
    made = skipped = 0
    for wk in weeks:
        ent = st["weeks"][str(wk["week"])]
        ent.setdefault("units", {})
        for u in units_by_week[wk["week"]]:
            if u["id"] in ent["units"]:
                skipped += 1
                continue
            pg = N.create_page(
                {"type": "data_source_id", "data_source_id": ent["unit_ds"]},
                {"이름": {"title": [{"text": {"content": u["title"]}}]},
                 "순서": {"number": u["order"]},
                 "유형": {"select": {"name": u["type"]}},
                 "난이도": {"select": {"name": u["level"]}},
                 "상태": {"select": {"name": "안함"}},
                 "예상시간": {"number": u["minutes"]}})
            ent["units"][u["id"]] = pg["id"]
            made += 1
            if made % 10 == 0:
                save_state(st)
                print(f"    …{made}개")
    save_state(st)
    print(f"  생성 {made} / 기존 {skipped}")
    print(f"\n상태: {STATE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
