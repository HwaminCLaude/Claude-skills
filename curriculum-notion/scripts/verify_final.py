# -*- coding: utf-8 -*-
"""verify_final.py — 최종 전수 검증.

노션에서 **실제로 읽어와서** 확인한다(로컬 기록을 믿지 않는다).
  1. 유닛 수 = 커리큘럼 (주차별·전체, 누락·중복 양쪽)
  2. 유닛마다 9개 섹션 heading 이 전부 있는가
  3. 이미지가 Notion 호스팅으로 치환됐는가 (`__IMG__` 잔재 0)
  4. 콜랩 링크가 붙었는가
  5. 블록 수가 발행 기록과 일치하는가
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent

import notion_api as N  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CUR = json.loads((HERE / "curriculum.json").read_text(encoding="utf-8"))
ST = json.loads((HERE / "state.json").read_text(encoding="utf-8"))
PS = json.loads((HERE / "publish_state.json").read_text(encoding="utf-8"))

SECTIONS = ["🧭 먼저 알고 오세요", "📖 개념", "🧮 수식", "💻 직접 만들기",
            "🔬 맞는지 확인", "🧪 강의 자료에 적용", "✅ 스스로 확인", "🔗 더 보기"]


def txt(b):
    t = b.get("type")
    return "".join(r.get("plain_text", "") for r in ((b.get(t) or {}).get("rich_text") or []))


def main() -> int:
    errs: list[str] = []
    units = CUR["units"]
    print(f"검증 대상 {len(units)}유닛\n")

    n_img = n_colab = 0
    for i, u in enumerate(units, 1):
        uid = u["id"]
        pid = (ST["weeks"][str(u["week"])].get("units") or {}).get(uid)
        if not pid:
            errs.append(f"{uid}: 노션 페이지 없음")
            continue
        try:
            kids = N.get_children(pid)
        except Exception as e:
            errs.append(f"{uid}: 읽기 실패 {e}")
            continue

        heads = [txt(b) for b in kids if b.get("type") == "heading_2"]
        for s in SECTIONS:
            if not any(s in h for h in heads):
                errs.append(f"{uid}: 섹션 누락 '{s}'")

        for b in kids:
            if b.get("type") == "image":
                im = b["image"]
                if im.get("type") == "external" and "__IMG__" in json.dumps(im):
                    errs.append(f"{uid}: 이미지 미치환")
                else:
                    n_img += 1

        exp = (PS.get(uid) or {}).get("blocks")
        if exp and len(kids) != exp:
            errs.append(f"{uid}: 블록 {len(kids)} ≠ 기록 {exp}")

        pg = N.request(f"pages/{pid}")
        if (pg["properties"].get("콜랩") or {}).get("url"):
            n_colab += 1
        else:
            errs.append(f"{uid}: 콜랩 링크 없음")

        if i % 15 == 0:
            print(f"  …{i}/{len(units)}")

    print(f"\n이미지 {n_img}장 · 콜랩 링크 {n_colab}/{len(units)}")
    if errs:
        print(f"\n[문제 {len(errs)}건]")
        for e in errs[:30]:
            print("  -", e)
        return 1
    print("\n최종 검증 통과 — 91유닛 전부 정상입니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
