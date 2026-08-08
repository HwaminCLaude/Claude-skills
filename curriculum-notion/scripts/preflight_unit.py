# -*- coding: utf-8 -*-
"""preflight_unit.py — 유닛 모듈이 AUTHORING_CONTRACT 를 지켰는지 발행 전 검사.

노션에 올리기 전에 **여기서 다 걸러낸다**. 청크 하나에 무효 블록이 있으면
그 청크(85블록)가 통째로 실패하기 때문에, 사전 검사가 재발행 비용을 없앤다.

    python preflight_unit.py units/W04U05.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import blocks as B                       # noqa: E402
import unitkit as K                      # noqa: E402
from build_unit_notebook import load     # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VALID_LANG = {"python", "bash", "json", "mermaid", "plain text", "yaml", "shell",
              "markdown", "sql", "javascript", "typescript", "docker"}

SECTIONS = ["🧭 먼저 알고 오세요", "📖 개념", "🧮 수식", "💻 직접 만들기",
            "🔬 맞는지 확인", "🧪 강의 자료에 적용", "✅ 스스로 확인", "🔗 더 보기"]


def text_of(b: dict) -> str:
    t = b.get("type")
    o = b.get(t) or {}
    return "".join(r.get("plain_text", r.get("text", {}).get("content", ""))
                   for r in (o.get("rich_text") or []))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    p = Path(sys.argv[1])
    mod = load(p)
    errs: list[str] = []

    for attr in ("UNIT", "TITLE", "GOAL", "build", "NB"):
        if not hasattr(mod, attr):
            errs.append(f"필수 항목 없음: {attr}")
    if errs:
        for e in errs:
            print("  -", e)
        return 1

    # 그림 먼저 생성 (이미지 존재 확인을 위해)
    if hasattr(mod, "figs"):
        plt = K.setup_mpl()
        try:
            glyph = K.figs_with_glyph_check(mod, plt)
            for g in glyph[:3]:
                errs.append(f"그림 한글 깨짐(폰트에 글자 없음): {g[:90]}")
        except Exception as e:
            errs.append(f"figs() 실행 실패: {e}")

    def IM(key, caption=None):
        return B.image(key, caption)

    try:
        bs = mod.build(B, IM)
    except Exception as e:
        print(f"  - build() 실행 실패: {e}")
        return 1

    if not isinstance(bs, list) or not bs:
        errs.append("build() 가 블록 리스트를 반환하지 않음")
        bs = []

    # 1) 섹션 순서
    heads = [text_of(b) for b in bs if b.get("type") == "heading_2"]
    idx, order_ok = -1, True
    for s in SECTIONS:
        try:
            j = next(i for i, h in enumerate(heads) if s in h)
        except StopIteration:
            errs.append(f"섹션 누락: {s}")
            continue
        if j < idx:
            order_ok = False
        idx = j
    if not order_ok:
        errs.append(f"섹션 순서 어긋남: {heads}")

    # 2) 목표 콜아웃이 맨 앞
    if bs and bs[0].get("type") != "callout":
        errs.append("첫 블록이 목표 콜아웃이 아님")

    # 3) 블록별 규칙
    n_img = n_eq = n_code = 0
    for i, b in enumerate(bs):
        t = b.get("type")
        if t == "code":
            n_code += 1
            lang = (b.get("code") or {}).get("language")
            if lang not in VALID_LANG:
                errs.append(f"[{i}] 잘못된 code language: {lang!r}")
            for r in (b["code"].get("rich_text") or []):
                if len(r.get("text", {}).get("content", "")) > 2000:
                    errs.append(f"[{i}] 코드 2000자 초과")
        elif t == "equation":
            n_eq += 1
            ex = (b.get("equation") or {}).get("expression", "")
            if "$" in ex:
                errs.append(f"[{i}] 블록 수식에 $ 포함: {ex[:40]}")
            if ex.count("{") != ex.count("}"):
                errs.append(f"[{i}] 수식 중괄호 불균형: {ex[:40]}")
        elif t == "image":
            n_img += 1
            url = ((b.get("image") or {}).get("external") or {}).get("url", "")
            if not url.startswith("__IMG__:"):
                errs.append(f"[{i}] 이미지가 __IMG__ 자리표시자가 아님: {url[:40]}")
            else:
                key = url.split(":", 1)[1]
                if not (K.IMG / f"{key}.png").exists():
                    errs.append(f"[{i}] 이미지 파일 없음: {key}.png")
                if not key.startswith(mod.UNIT.lower()):
                    errs.append(f"[{i}] 이미지 key 접두사 규칙 위반: {key}")
        for r in ((b.get(t) or {}).get("rich_text") or []):
            c = r.get("text", {}).get("content", "")
            if len(c) > 2000:
                errs.append(f"[{i}] rich_text 2000자 초과")

    if n_img < 1:
        errs.append("그림이 한 장도 없음 (개념 섹션에 최소 1장)")
    if n_eq < 1:
        errs.append("수식 블록이 없음")
    if n_code < 2:
        errs.append("코드 블록이 2개 미만 (직접 구현 + 대조 검산)")

    # 4) 어투
    body = " ".join(text_of(b) for b in bs)
    hard = len(re.findall(r"(?<![가-힣])(한다|이다|된다|있다)\.", body))
    if hard > 3:
        errs.append(f"문어체('~한다') {hard}회 — 친근한 존댓말로 바꿀 것")

    # 5) 노트북 규약
    nb = getattr(mod, "NB", {})
    for must in ("setup", "explore", "todo", "check"):
        if not nb.get(must):
            errs.append(f"NB 필수 장 없음: {must}")
    todo_src = "\n".join(b for k, b in nb.get("todo", []) if k == "code")
    if "TODO" not in todo_src:
        errs.append("NB todo 장에 TODO 빈칸 없음")
    chk_src = "\n".join(b for k, b in nb.get("check", []) if k == "code")
    if not any(t in chk_src for t in ("allclose", "assert", "np.testing")):
        errs.append("NB check 장에 자동 채점(allclose/assert) 없음")

    # 정답 누출 검사 — TODO 위쪽(setup/explore)에 답이 있으면 연습이 무의미해진다.
    # `sigmoid_ref` 처럼 이름만 바꾼 것도 잡으려고 **본문 줄**을 비교한다.
    upper = "\n".join(b for key in ("setup", "explore")
                      for k, b in nb.get(key, []) if k == "code")
    sol = getattr(mod, "SOLUTION", "") or ""
    if not sol:
        errs.append("SOLUTION 없음 (검산 실행 검증에 필요)")
    # 인자 조각(`columns="channel",`)까지 잡으면 오탐이 난다 — 2장이 같은 API를 작은 예로
    # 보여주는 건 규약대로 정상이다. **계산의 알맹이**만 본다:
    #   ① return 문 (가장 강한 신호)  ② 30자 이상의 실제 계산 줄
    KWARG = re.compile(r'^[\w\s]*=\s*[^=]+,?$')
    for line in sol.splitlines():
        s = line.strip().rstrip(",")
        if s.startswith(("def ", "#", "import", "from", "@")) or len(s) < 15:
            continue
        is_return = s.startswith("return ") and len(s) > 12
        if not is_return:
            if len(s) < 30 or KWARG.match(s):
                continue
        if s in upper or (is_return and s in upper):
            errs.append(f"정답 누출: setup/explore 에 정답 본문이 있음 → {s[:60]}")
    for name in re.findall(r"def\s+(\w+)\s*\(",
                           "\n".join(b for k, b in nb.get("todo", []) if k == "code")):
        if re.search(rf"def\s+_?{re.escape(name)}_?\w*\s*\(", upper):
            errs.append(f"정답 누출: setup/explore 에 `{name}` 유사 함수 정의가 있음")

    print(f"{mod.UNIT}  블록 {len(bs)} (그림 {n_img} · 수식 {n_eq} · 코드 {n_code})")
    if errs:
        print("[preflight 실패]")
        for e in errs:
            print("  -", e)
        return 1
    print("preflight 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
