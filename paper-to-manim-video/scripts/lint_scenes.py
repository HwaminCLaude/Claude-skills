#!/usr/bin/env python
"""씬 코드 정적 검사 — 렌더는 성공하는데 화면이 틀리는 것들만 본다.

여기 있는 규칙은 전부 실제로 밟아서 완성본에 들어갔던 것들이다. 공통점은
**렌더가 성공하고 길이도 맞는다**는 것 — verify_output.py로는 절대 안 잡힌다.

    python scripts/lint_scenes.py --root C:/manimwork/<slug>
    python scripts/lint_scenes.py --episode C:/manimwork/<slug>/ep01_x --json

종료 코드: 0 = 문제 없음, 1 = ERROR 있음. WARN만 있으면 0.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# 윈도우 콘솔 기본 코드페이지(cp949)로는 — 나 ✔ 를 못 찍는다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HANGUL = re.compile(r"[가-힣ㄱ-ㆎ]")

# 이모지·기호 — Malgun Gothic에 글립이 없어 점이 하나도 없는 mobject가 된다.
# ✔ ✕ 처럼 실제로 렌더되는 것이 있으므로 확인된 것만 화이트리스트에 둔다.
EMOJI = re.compile(
    "["
    "\U0001F000-\U0001FAFF"      # 이모지 전반
    "\u2190-\u21FF"               # 화살표
    "\u2600-\u27BF"               # 기타 기호·딩뱃
    "\uFE0F\u20E3"                # variation selector, keycap
    "]"
)
EMOJI_OK = set("→←↑↓↔⇒⇔✔✕✓✗①②③④⑤⑥⑦⑧⑨⑩")


class Finding:
    __slots__ = ("level", "rule", "file", "line", "msg", "fix")

    def __init__(self, level, rule, file, line, msg, fix):
        self.level, self.rule = level, rule
        self.file, self.line = file, line
        self.msg, self.fix = msg, fix

    def as_dict(self):
        return {"level": self.level, "rule": self.rule, "file": self.file,
                "line": self.line, "msg": self.msg, "fix": self.fix}


def _src(node, text):
    """노드의 원본 텍스트만 정확히 잘라낸다.

    줄 단위로 자르면 한 줄에 여러 인자가 있을 때 앞 인자까지 딸려와
    `x.animate...` 같은 패턴을 놓친다.
    """
    seg = ast.get_source_segment(text, node)
    if seg is not None:
        return seg
    ls = text.splitlines()
    return "\n".join(ls[node.lineno - 1:getattr(node, "end_lineno", node.lineno)])


def _str_args(node):
    """호출의 위치 인자 중 문자열 리터럴만."""
    out = []
    for a in node.args:
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            out.append(a.value)
    return out


def _callee(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _target_key(node):
    """애니메이션의 대상 mobject를 문자열 키로. `x`, `x[0]`, `x.y` 를 구분한다."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _target_key(node.value)
        return f"{base}.{node.attr}" if base else ""
    if isinstance(node, ast.Subscript):
        base = _target_key(node.value)
        idx = node.slice
        if isinstance(idx, ast.Constant):
            return f"{base}[{idx.value!r}]"
        return f"{base}[?]"
    if isinstance(node, ast.Call):
        # x.animate.scale(2) → x
        return _target_key(node.func)
    return ""


def lint_file(path: Path, mono_falls_back: bool = False):
    text = path.read_text(encoding="utf-8")
    rel = str(path)
    out: list[Finding] = []

    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        out.append(Finding("ERROR", "syntax", rel, e.lineno or 0,
                           f"문법 오류: {e.msg}", "먼저 문법을 고친다"))
        return out

    highlight_vars: dict[str, int] = {}   # disappear 변수명 -> 정의 줄
    played_names: set[str] = set()

    for node in ast.walk(tree):
        # ── R1  고정폭 폰트에 한글 → 두부(□)
        if isinstance(node, ast.Call) and _callee(node) == "mono":
            for s in _str_args(node):
                if HANGUL.search(s):
                    out.append(Finding(
                        "WARN" if mono_falls_back else "ERROR",
                        "mono-hangul", rel, node.lineno,
                        f'mono()에 한글이 들어갔다: "{s[:30]}"'
                        + (" (헬퍼에 한글 폴백이 있어 렌더는 된다 — 자간만 달라진다)"
                           if mono_falls_back else ""),
                        "kr()을 쓰거나, mono()가 한글을 만나면 KR 폰트로 넘어가게 고친다"))

        # ── R2  이모지 → 점 없는 mobject → move_to/next_to가 통째로 깨진다
        if isinstance(node, ast.Call) and _callee(node) in ("kr", "mono", "Text", "caption"):
            for s in _str_args(node):
                bad = {c for c in EMOJI.findall(s)} - EMOJI_OK
                if bad:
                    out.append(Finding(
                        "ERROR", "emoji", rel, node.lineno,
                        f"이모지 {''.join(sorted(bad))} 는 글립이 없어 빈 mobject가 된다",
                        "도형으로 직접 그리거나 뺀다. 빈 mobject에 next_to를 걸면 "
                        "옆 요소까지 원점으로 끌려간다"))

        # ── R3  MathTex/RaeTex 안 한글 → LaTeX가 죽는다
        if isinstance(node, ast.Call) and _callee(node) in ("MathTex", "Tex", "RaeTex"):
            for s in _str_args(node):
                if HANGUL.search(s):
                    out.append(Finding(
                        "ERROR", "latex-hangul", rel, node.lineno,
                        f'수식 안에 한글: "{s[:30]}"',
                        "수식은 영문으로 두고 한국어는 kr()로 옆에 붙인다"))

        # ── R4  path_arc가 걸린 Line에 set_opacity → 호 안쪽이 흰색으로 채워진다
        if isinstance(node, ast.Call) and _callee(node) == "set_opacity":
            block = _src(node, text)
            if "path_arc" in block:
                out.append(Finding(
                    "ERROR", "arc-fill", rel, node.lineno,
                    "path_arc가 걸린 선에 set_opacity를 쓰면 면(fill)까지 칠해져 "
                    "호가 흰 덩어리가 된다",
                    "set_stroke(opacity=...) 로 바꾼다"))

        # ── R5  VGroup에 이미지 → VGroup은 ImageMobject를 담지 못한다
        if isinstance(node, ast.Call) and _callee(node) == "VGroup":
            block = _src(node, text)
            if re.search(r"\bfig\(|ImageMobject\(", block):
                out.append(Finding(
                    "ERROR", "vgroup-image", rel, node.lineno,
                    "VGroup 안에 이미지가 들어 있다",
                    "Group(...)을 쓴다"))

        # ── R6  raenim SurroundingRect는 manim SurroundingRectangle과 다른 클래스
        if isinstance(node, ast.Call) and _callee(node) == "SurroundingRect":
            if node.args:
                out.append(Finding(
                    "ERROR", "surrounding-rect", rel, node.lineno,
                    "raenim의 SurroundingRect는 대상 mobject를 인자로 받지 않는다",
                    "manim의 SurroundingRectangle을 쓴다"))

        # ── R7  같은 playw 안에서 FadeIn과 Indicate/.animate가 같은 대상에 걸림
        if isinstance(node, ast.Call) and _callee(node) in ("playw", "playwl"):
            appearing, indicating, animating = {}, {}, {}
            for a in node.args:
                if not isinstance(a, ast.Call):
                    continue
                name = _callee(a)
                if name in ("FadeIn", "Write", "Create", "GrowFromCenter") and a.args:
                    k = _target_key(a.args[0])
                    if k:
                        appearing[k] = a.lineno
                elif name in ("Indicate", "Circumscribe", "Wiggle", "ApplyWave") and a.args:
                    k = _target_key(a.args[0])
                    if k:
                        indicating[k] = a.lineno
                # x.animate.scale(...) 형태
                if isinstance(a.func, ast.Attribute):
                    m = re.match(r"\s*([A-Za-z_][\w\.\[\]'\"]*)\.animate\b",
                                 _src(a, text))
                    if m:
                        animating[m.group(1)] = a.lineno

            for k in set(appearing) & set(indicating):
                out.append(Finding(
                    "ERROR", "fadein-plus-indicate", rel, node.lineno,
                    f"같은 playw에서 `{k}`에 등장과 Indicate를 동시에 걸었다 — "
                    "등장이 취소돼 화면에서 통째로 사라진다",
                    "샷을 나누거나, 대상을 건드리지 않는 Flash를 쓴다"))
            for k in (set(appearing) & set(animating)) - set(indicating):
                out.append(Finding(
                    "WARN", "fadein-plus-animate", rel, node.lineno,
                    f"같은 playw에서 `{k}`에 등장과 .animate를 동시에 걸었다 — "
                    "보통 끝 상태는 맞지만 등장 연출이 사라진다",
                    "프레임으로 확인한다. 연출이 필요하면 샷을 나눈다"))

        # ── R7b  강조 사각형을 playw 안에서 인라인으로 만들면 나중에 못 지운다
        #         self.playw(Create(row_box(tab, 2)))  ← 변수가 없어 FadeOut을 못 건다.
        #         표를 지워도 빈 사각형만 화면에 남는다. 손계산 편에서 3곳 밟았다.
        if isinstance(node, ast.Call) and _callee(node) in ("playw", "playwl"):
            for a in node.args:
                if not isinstance(a, ast.Call) or _callee(a) not in (
                        "Create", "FadeIn", "DrawBorderThenFill",
                        "GrowFromCenter", "ShowCreation"):
                    continue
                if not a.args or not isinstance(a.args[0], ast.Call):
                    continue
                inner = _callee(a.args[0])
                if inner in ("row_box", "col_box", "cell_box", "on_fig1",
                             "SurroundingRectangle", "SurroundingRect"):
                    out.append(Finding(
                        "WARN", "inline-highlight-rect", rel, a.lineno,
                        f"강조 사각형 `{inner}(...)`을 인라인으로 만들었다 — "
                        "변수가 없어 나중에 지울 수 없다",
                        "변수로 받아 두고 뒤에서 FadeOut 한다. "
                        "구간의 마지막 샷이라면 무시해도 된다"))

        # ── R8  code.highlight()의 disappear를 안 재생하면 강조 글자가 남는다
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if _callee(node.value) == "highlight" and len(node.targets) == 1:
                t = node.targets[0]
                if isinstance(t, ast.Tuple) and len(t.elts) == 2:
                    d = t.elts[1]
                    if isinstance(d, ast.Name):
                        highlight_vars[d.id] = node.lineno

        if isinstance(node, ast.Name):
            played_names.add(node.id)

    for var, ln in highlight_vars.items():
        # 정의 줄 이후에 다시 등장하는지 본다 (정의 자체도 Name으로 잡히므로 개수로 센다)
        uses = len(re.findall(rf"\b{re.escape(var)}\b", text))
        if uses <= 1:
            out.append(Finding(
                "ERROR", "highlight-leftover", rel, ln,
                f"highlight()가 준 `{var}`(사라짐)를 한 번도 재생하지 않았다",
                "코드를 지우는 playw에 함께 넣는다 — 안 그러면 빨간 강조 글자만 남는다"))

    # ── R9  타이밍 하드코딩 (shots.json을 안 읽음)
    if "load_shots(" in text:
        for m in re.finditer(r"playwl?\([^\n]*run_time\s*=\s*[\d.]+", text):
            ln = text[:m.start()].count("\n") + 1
            seg = text[m.start():m.end() + 60]
            if "wait=0.0" in seg or "wait=0" in seg:
                continue          # 전환 컷은 하드코딩이 정상
            out.append(Finding(
                "WARN", "hardcoded-timing", rel, ln,
                "run_time을 코드에 적었다",
                "**SHOTS[\"<id>\"] 로 shots.json에서 읽는다 — 대본을 고치면 영상이 따라와야 한다"))

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", help="프로젝트 루트 (ep*/main.py 전부 검사)")
    ap.add_argument("--episode", help="에피소드 폴더 하나만")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    targets: list[Path] = []
    if a.episode:
        targets = [Path(a.episode) / "main.py"]
    elif a.root:
        root = Path(a.root)
        targets = sorted(root.glob("ep*/main.py"))
        targets += [p for p in root.glob("*common.py")]
    else:
        ap.error("--root 또는 --episode 가 필요하다")

    # 헬퍼가 한글을 만나면 KR 폰트로 넘어가는지 — 그러면 mono-hangul은 치명적이지 않다
    fallback = False
    probe = Path(a.root) if a.root else Path(a.episode).parent
    for c in probe.glob("*common.py"):
        src = c.read_text(encoding="utf-8")
        if re.search(r"def mono\(", src) and re.search(r"KR if .*HANGUL", src):
            fallback = True

    findings: list[Finding] = []
    for t in targets:
        if t.exists():
            findings += lint_file(t, mono_falls_back=fallback)

    errors = [f for f in findings if f.level == "ERROR"]

    if a.json:
        print(json.dumps({"checked": [str(t) for t in targets],
                          "findings": [f.as_dict() for f in findings],
                          "errors": len(errors)},
                         ensure_ascii=False, indent=2))
    else:
        if not findings:
            print(f"[lint] {len(targets)}개 파일 — 문제 없음")
        for f in findings:
            head = "FAIL" if f.level == "ERROR" else "warn"
            print(f"  {head}  {Path(f.file).parent.name}/{Path(f.file).name}:{f.line}"
                  f"  [{f.rule}]")
            print(f"        {f.msg}")
            print(f"        → {f.fix}")
        if findings:
            print(f"[lint] ERROR {len(errors)} · WARN {len(findings) - len(errors)}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
