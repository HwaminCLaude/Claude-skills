# -*- coding: utf-8 -*-
"""fix_glyphs.py — 그림에서 깨지는 문자를 mathtext 로 바꾼다.

Malgun Gothic 에 `ŷ`(U+0177) 같은 글자가 없어서 그림에 네모(두부)로 찍힌다.
matplotlib 의 폰트 폴백은 이 조합에서 동작하지 않는 걸 실측으로 확인했다
(family 목록에 DejaVu Sans 를 넣어도 경고가 그대로 난다).

확실한 해결은 **mathtext**(`$\\hat{y}$`)다 — matplotlib 자체 수식 폰트로 그리므로
어떤 시스템에서도 렌더된다.

    python fix_glyphs.py            # 어떤 유닛이 문제인지만
    python fix_glyphs.py --apply
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
UNITS = HERE / "units"

# 깨지는 문자 → mathtext 대체
MAP = {
    "ŷ": r"$\hat{y}$",
    "x̂": r"$\hat{x}$",
    "θ̂": r"$\hat{\theta}$",
    "ȳ": r"$\bar{y}$",
    "x̄": r"$\bar{x}$",
    "μ̂": r"$\hat{\mu}$",
    "σ̂": r"$\hat{\sigma}$",
    "∑": r"$\sum$",
    "∂": r"$\partial$",
    "√": r"$\sqrt{\ }$",
    "≈": r"$\approx$",
    "≤": r"$\leq$",
    "≥": r"$\geq$",
    "≠": r"$\neq$",
    "∈": r"$\in$",
    "→": "->",
}


def main() -> int:
    apply = "--apply" in sys.argv
    hits: list[tuple[str, str, int]] = []
    for p in sorted(UNITS.glob("W*.py")):
        t = p.read_text(encoding="utf-8")
        # figs() 안에서만 바꾼다 (본문 설명 텍스트의 기호는 노션에서 잘 나온다)
        m = re.search(r"^def figs\(.*?\n(.*?)(?=^def |\Z)", t, re.S | re.M)
        if not m:
            continue
        body = m.group(0)
        new = body
        for ch, rep in MAP.items():
            if ch in new:
                hits.append((p.stem, ch, new.count(ch)))
                new = new.replace(ch, rep)
        if new != body and apply:
            p.write_text(t.replace(body, new), encoding="utf-8")

    if not hits:
        print("깨지는 문자 없음")
        return 0
    for stem, ch, n in hits:
        print(f"  {stem}: '{ch}' {n}곳 → {MAP[ch]}")
    print(f"\n{len({h[0] for h in hits})}개 유닛 / {sum(h[2] for h in hits)}곳")
    if not apply:
        print("미리보기입니다. 적용하려면 --apply")
    else:
        print("적용 완료 — preflight 를 다시 돌리세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
