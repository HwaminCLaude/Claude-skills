#!/usr/bin/env python
"""에피소드의 씬 코드(main.py)와 대본(shots.json)을 정적 검사한다.

    python lint.py --episode <dir>

출력은 `ERROR|WARN <rule> <where> <msg>` 줄이다. ERROR가 하나라도 있으면 exit 1.
where는 씬 코드 규칙이면 `main.py:<줄>`(T10은 `main.py:<씬 이름>`), 큐 규칙이면 큐 id다.
편 통계 규칙은 편 전체면 `-`(E1~E4, E6), 큐면 큐 id(E5, E8), 화면 글자면 `main.py:<줄>`(E7)이다.
stdout에는 이 줄들만 찍고, 요약 두 줄(lint:, stats:)은 stderr로 낸다.

씬 코드 규칙(T1~T10)은 label/title/source/mono/Text/Tex 호출의 문자열 인자를 본다.
문자열 상수, f-string의 상수 조각, "가" + "나" 같은 상수 더하기까지 본다. 변수로 넘긴
문자열(label(name))은 값을 알 수 없어 검사하지 못한다.
`prop=True`를 준 호출은 극 안 소품(채팅 프롬프트, 화면 속 UI)으로 보고 T1(종결형)과
T5(해설 길이), E6(분당 글자 수)에서 뺀다.

큐 규칙은 C1~C8, 편 통계 규칙은 E1~E8(모두 WARN)이다. 말투 비율(E2~E4, E8)은 큐가 아니라
문장 끝 큐(is_sentence_final)로 센다. 표준 오류 끝에
`lint: ERROR n, WARN n` 줄과 `stats: ...` 편 통계 한 줄을 찍는다.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

TEXT_FUNCS = {"label", "title", "source", "mono", "Text", "Tex", "tex"}
TEX_FUNCS = {"Tex", "tex"}
FONT_TOKENS = {20, 24, 26, 32, 40}
HANGUL = re.compile(r"[\uac00-\ud7a3\u3131-\u318e]")
LATIN = re.compile(r"[A-Za-z]")

END_PUNCT = ".?!~…,"
T1_SPACED = re.compile(r"(다|요|죠|함|음|임|됨|까)$")
# 띄어쓰기 없는 한 낱말에서 종결형으로 보는 어미. ㄴ다·ㅆ다·요·까는 is_sentence_end가 앞 글자 받침으로 더 본다.
T1_WORD = re.compile(r"(니다|니까|는다|이다|였다|했다|었다|았다|겠다|없다|어요|아요|해요|에요|예요|"
                     r"워요|와요|봐요|돼요|줘요|세요|네요|군요|든요|데요|고요|지요|까요|래요|대요|게요|걸요|죠|됨|"
                     r"(있|없|같|많|적|작|높|낮|좋|싫|넓|좁|짧|깊|얕|늦)음)$")
YO_VOWELS = {0, 1, 3, 4, 5, 6, 7, 9, 10, 11, 14, 15}  # ㅏㅐㅒㅓㅔㅕㅖㅘㅙㅚㅝㅞ (받침 없는 앞 글자 + 요 = 해요체)
T2_CHARS = re.compile(r"[·—→⇒“”‘’\u2460-\u2469]")
T3_RE = re.compile(r"^([0-9]+-[0-9]+|\([0-9]+\)|H[0-9]+|[0-9]+편|특강|[0-9]+장)\s")
T4_RE = re.compile(r"쪽|p\.\d|PDF|노트|해설|정리")
HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?\b")
FILL_HINT = re.compile(r"opacity|fill")

C3_CHARS = re.compile(r"[·—→:()（）]")
SHORT_EPISODE_MAX_CUES = 70  # 짧은 편(1분 30초~2분 30초) 큐 수 상한. 넘으면 structure 상한 2

# 편 통계(설계 §5.5-9, §5.6, §5.7, §7 A4, §2.1 G4). E1은 큐가 STAT_MIN_CUES개 이상,
# 말투 비율(E2~E4)은 문장 끝 큐가 STAT_MIN_SENTENCES개 이상일 때만 낸다.
STAT_MIN_CUES = 10
STAT_MIN_SENTENCES = 8
KEY_RANGE = (0.10, 0.30)        # §5.6, A4: 노랑 칠한 큐 10~30%
# §5.7 말투(2026-10-28 사용자 결정): 습니다체가 기본이고 2~3문장마다 '~죠?'·'~까요?'로 끊는다.
QUESTION_MIN = 0.15             # 질문 15% 이상(참고 영상 약 22%)
JYO_RANGE = (0.10, 0.20)        # '~죠' 10~20%(참고 영상 12.1%)
SUPNIDA_RANGE = (0.45, 0.65)    # 습니다·ㅂ니다 45~65%(참고 영상 60.5%)
SUPNIDA_RUN_MAX = 4             # 습니다로 끝나는 문장은 4개까지만 잇는다(E8)
SENT_END = re.compile(r"(니다|니까|요|죠|다|까|네|군|지)$")
CANVAS_HANGUL_PER_MIN = 20      # §2.1 G4, A3: 캔버스 해설용 한글 분당 20자 이하
OVERLAP_WORDS = 4               # §5.5-9: 자막과 캔버스 문구 4낱말 이상 겹침
FIRST_PERSON = re.compile(r"(?<![가-힣])(저는|제가|저도|저를|저희|제게|내가|우리)")
PLACEHOLDER = "\u25a1"          # f-string의 {식} 자리. 한글도 라틴도 아니다.


def _name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _static_text(node: ast.AST) -> str | None:
    """문자열 상수, f-string(상수 조각 + {식} 자리표), 상수 더하기를 글자로 푼다. 못 풀면 None."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else PLACEHOLDER
                       for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _static_text(node.left), _static_text(node.right)
        if left is None and right is None:
            return None
        return (PLACEHOLDER if left is None else left) + (PLACEHOLDER if right is None else right)
    return None


def _str_args(call: ast.Call) -> list[str]:
    return [t for t in (_static_text(a) for a in call.args) if t is not None]


def _syl(ch: str) -> tuple[int, int] | None:
    """한글 음절이면 (중성 번호, 종성 번호)."""
    if "가" <= ch <= "힣":
        k = ord(ch) - 0xAC00
        return (k // 28) % 21, k % 28
    return None


def is_sentence_end(txt: str) -> bool:
    """T1: 문장 종결형인가. 띄어 쓴 문장은 넓게, 한 낱말은 서술어 어미만 본다."""
    t = txt.strip().rstrip(END_PUNCT + " ")
    if not t or not HANGUL.search(t):
        return False
    if re.search(r"\s", t):
        return bool(T1_SPACED.search(t))
    if len(t) < 2:
        return False
    if T1_WORD.search(t):
        return True
    prev = _syl(t[-2])
    if prev is None:
        return False
    vowel, jong = prev
    last = t[-1]
    if last == "다":
        return jong in (4, 20)            # ㄴ다(커진다, 된다), ㅆ다(있다, 썼다)
    if last == "요":
        return jong == 0 and vowel in YO_VOWELS   # 커요, 가요. 중요·필요·수요는 통과
    if last == "까":
        return jong == 8                  # ㄹ까(할까, 그럴까)
    return False


def _has_prop(call: ast.Call) -> bool:
    return any(k.arg == "prop" and isinstance(k.value, ast.Constant) and k.value.value is True
               for k in call.keywords)


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    par = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            par[ch] = node
    return par


def _enclosing_cue(node, par) -> str | None:
    """node를 감싼 `with self.cue("id"):` 블록의 큐 id."""
    cur = par.get(node)
    while cur is not None:
        if isinstance(cur, ast.With):
            for it in cur.items:
                c = it.context_expr
                if isinstance(c, ast.Call) and _name(c.func) == "cue" and c.args \
                        and isinstance(c.args[0], ast.Constant) and isinstance(c.args[0].value, str):
                    return c.args[0].value
        cur = par.get(cur)
    return None


def canvas_strings(src: str) -> list[dict]:
    """씬 코드의 화면 글자 목록. 항목: text, line, func, prop, tex, cue(감싼 큐 id 또는 None)."""
    tree = ast.parse(src)
    par = _parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _name(node.func) in TEXT_FUNCS:
            fn = _name(node.func)
            for s in _str_args(node):
                out.append({"text": s, "line": node.lineno, "func": fn, "prop": _has_prop(node),
                            "tex": fn in TEX_FUNCS, "cue": _enclosing_cue(node, par)})
    return sorted(out, key=lambda d: d["line"])


def _rect_is_filled(call: ast.Call, par) -> bool:
    """SurroundingRectangle(...)에 fill/opacity가 있는가(kwargs나 이어 붙인 메서드)."""
    if any(k.arg and FILL_HINT.search(k.arg) for k in call.keywords):
        return True
    cur = call
    while True:  # SurroundingRectangle(x).set_stroke(...).set_opacity(0.3) 같은 체인을 따라 올라간다
        attr = par.get(cur)
        if not isinstance(attr, ast.Attribute) or attr.value is not cur:
            return False
        if FILL_HINT.search(attr.attr):
            return True
        nxt = par.get(attr)
        if not isinstance(nxt, ast.Call) or nxt.func is not attr:
            return False
        if any(k.arg and FILL_HINT.search(k.arg) for k in nxt.keywords):
            return True
        cur = nxt


def lint_code(src: str, fname: str = "main.py") -> list[tuple[str, str, str, str]]:
    out: list[tuple[str, str, str, str]] = []
    tree = ast.parse(src)
    par = _parents(tree)
    mixed = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = _name(node.func)
        where = f"{fname}:{node.lineno}"

        if fn == "Logo":
            out.append(("ERROR", "T9", where, "Logo 클래스는 쓰지 않는다"))

        for k in node.keywords:
            if k.arg != "font_size":
                continue
            v = k.value
            if fn in ("Text", "Tex"):
                # 키트 보정(TEXT_SCALE, TEX_FS)을 건너뛰므로 숫자가 토큰이어도 글자가 작게 나온다
                out.append(("WARN", "T7", where, "Text/Tex에 font_size를 직접 주지 않는다. label(.., size)·tex(.., size=)를 쓴다"))
            elif isinstance(v, ast.Constant) and isinstance(v.value, (int, float)) and v.value not in FONT_TOKENS:
                out.append(("WARN", "T7", where, f"font_size {v.value}는 토큰(20/24/26/32/40) 밖"))
            elif isinstance(v, ast.BinOp):
                out.append(("WARN", "T7", where, "font_size에 배율을 곱하지 않는다. 크기는 토큰 이름으로 고른다"))

        if fn not in TEXT_FUNCS:
            continue
        exempt = _has_prop(node)
        is_tex = fn in TEX_FUNCS
        for s in _str_args(node):
            txt = s.strip()
            if not exempt and is_sentence_end(txt):
                out.append(("ERROR", "T1", where, f"종결형 문장: {txt!r}"))
            if not is_tex and HANGUL.search(txt) and T2_CHARS.search(txt):
                out.append(("ERROR", "T2", where, f"한글 구절을 기호로 이음: {txt!r}"))
            if T3_RE.search(txt):
                out.append(("ERROR", "T3", where, f"번호 머리: {txt!r}"))
            if T4_RE.search(txt):
                out.append(("ERROR", "T4", where, f"문서 메타: {txt!r}"))
            if not is_tex and not exempt and HANGUL.search(txt) \
                    and len(re.sub(r"\s", "", txt.replace(PLACEHOLDER, ""))) > 8:
                out.append(("WARN", "T5", where, f"해설 글자가 8자 넘음: {txt!r}"))
            if not is_tex and HANGUL.search(txt) and LATIN.search(txt):
                mixed.append((where, txt))

    docstrings = {id(b.body[0].value) for b in ast.walk(tree)
                  if isinstance(b, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                  and b.body and isinstance(b.body[0], ast.Expr)
                  and isinstance(b.body[0].value, ast.Constant)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            where = f"{fname}:{getattr(node, 'lineno', '?')}"
            if HEX_RE.search(node.value):
                out.append(("WARN", "T8", where, f"hex 리터럴 대신 토큰을 쓴다: {node.value!r}"))

    if len(mixed) > 5:
        out.append(("WARN", "T6", f"{fname}:{mixed[5][0].split(':')[-1]}",
                    f"한글·라틴 혼합 문자열 {len(mixed)}개(편당 5개 이하)"))

    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        outline = [n for n in ast.walk(cls) if isinstance(n, ast.Call)
                   and _name(n.func) == "SurroundingRectangle" and not _rect_is_filled(n, par)]
        if len(outline) > 2:
            out.append(("WARN", "T10", f"{fname}:{cls.name}",
                        f"테두리만 있는 상자 {len(outline)}개(씬당 2개 이하, 줄 "
                        f"{','.join(str(n.lineno) for n in outline)})"))
    return out


def cue_ids_in_code(src: str) -> set[str]:
    ids = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and _name(node.func) == "cue" and node.args \
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            ids.add(node.args[0].value)
    return ids


def _font_files() -> list[Path]:
    dirs = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"]
    if os.environ.get("LOCALAPPDATA"):
        dirs.append(Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts")
    found = []
    for d in dirs:
        if d.is_dir():
            found += [p for p in d.iterdir() if p.suffix.lower() in (".ttf", ".otf")
                      and p.name.lower().startswith("notosanskr")]
    return found


def noto_sans_kr_cmap() -> set[int] | None:
    """Noto Sans KR 글꼴 파일들의 cmap 합집합. 글꼴이나 fontTools가 없으면 None."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    cmap: set[int] = set()
    for p in _font_files():
        try:
            cmap |= set(TTFont(str(p), fontNumber=0, lazy=True).getBestCmap())
        except Exception:
            continue
    return cmap or None


def lint_cues(shots: dict, code_src: str | None) -> list[tuple[str, str, str, str]]:
    out: list[tuple[str, str, str, str]] = []
    cues = [c for sc in shots.get("scenes", []) for c in sc.get("cues", [])]
    code_ids = cue_ids_in_code(code_src) if code_src is not None else None
    cmap = noto_sans_kr_cmap()
    if cmap is None:
        out.append(("WARN", "C7", "-", "Noto Sans KR 글꼴 파일이나 fontTools가 없어 글리프 검사를 건너뜀"))

    for c in cues:
        cid, t, key = str(c.get("id")), c.get("t") or "", c.get("key")
        if len(t) > 26:
            out.append(("ERROR", "C1", cid, f"{len(t)}자(26자 이하): {t!r}"))
        if t.rstrip().endswith((".", "。")):
            out.append(("ERROR", "C2", cid, f"끝 마침표: {t!r}"))
        bad = sorted(set(C3_CHARS.findall(t)))
        if bad:
            out.append(("ERROR", "C3", cid, f"금지 기호 {''.join(bad)}: {t!r}"))
        if key and key not in t:
            out.append(("ERROR", "C4", cid, f"key {key!r}가 t의 부분 문자열이 아님"))
        if code_ids is not None and cid not in code_ids:
            out.append(("ERROR", "C6", cid, f'씬 코드에 self.cue("{cid}")가 없음'))
        if cmap is not None:
            miss = sorted({ch for ch in t if not ch.isspace() and ord(ch) not in cmap})
            if miss:
                out.append(("ERROR", "C7", cid, "Noto Sans KR에 없는 글자 "
                            + " ".join(f"{ch}(U+{ord(ch):04X})" for ch in miss)))

    run_rel, run_len, run_start = None, 0, None
    for c in cues + [{"rel": None, "id": None}]:
        rel = c.get("rel")
        if rel == run_rel and rel is not None:
            run_len += 1
            continue
        if run_rel is not None and run_len > 4:
            out.append(("WARN", "C5", str(run_start), f"rel {run_rel!r}가 {run_len}큐 이어짐(4큐 이하)"))
        run_rel, run_len, run_start = rel, 1, c.get("id")

    n_struct = sum(1 for c in cues if c.get("rel") == "structure")
    cap = 1 if len(cues) <= SHORT_EPISODE_MAX_CUES else 2
    if n_struct > cap:
        out.append(("WARN", "C8", "-", f"structure {n_struct}회(이 길이에서는 {cap}회 이하)"))
    return out


def _bare(t: str) -> str:
    return (t or "").strip().rstrip(END_PUNCT + " ")


def is_sentence_final(t: str) -> bool:
    """자막 큐가 문장을 끝내는가. 쉼표로 끝나거나('LoRA는요,') 어미 없이 끊기면('이 길은') 문장 중간이다."""
    s = (t or "").strip()
    if not s or s.endswith(","):
        return False
    if s.endswith(("?", "!")):
        return True
    return bool(SENT_END.search(_bare(s)))


def _words(t: str) -> list[str]:
    return [w for w in (re.sub(r"[.,?!~…\"'()]", "", x) for x in t.split()) if w]


def _overlap(a: str, b: str, n: int = OVERLAP_WORDS) -> str | None:
    """a와 b가 연속 n낱말 이상 겹치면 겹친 구절."""
    wa, wb = _words(a), _words(b)
    grams = {tuple(wb[i:i + n]) for i in range(len(wb) - n + 1)}
    for i in range(len(wa) - n + 1):
        if tuple(wa[i:i + n]) in grams:
            return " ".join(wa[i:i + n])
    return None


def episode_stats(shots: dict | None, code_src: str | None, duration_s: float | None):
    """편 통계 WARN(E1~E8)과 통계 사전. 기준값은 모듈 상단 상수(설계 §5.5-9, §5.6, §5.7, A4, G4)."""
    out: list[tuple[str, str, str, str]] = []
    cues = [c for sc in (shots or {}).get("scenes", []) for c in sc.get("cues", [])]
    n = len(cues)
    texts = [c.get("t") or "" for c in cues]
    lens = sorted(len(t) for t in texts)
    st = {"cues": n, "len_max": lens[-1] if lens else 0,
          "len_median": (lens[n // 2] if n % 2 else (lens[n // 2 - 1] + lens[n // 2]) / 2) if n else 0}
    st["key"] = sum(1 for c in cues if c.get("key")) / n if n else 0.0
    finals = [c for c in cues if is_sentence_final(c.get("t"))]
    ns = len(finals)
    ends = [c.get("t") or "" for c in finals]
    st["sentences"] = ns
    st["question"] = sum(1 for t in ends if t.strip().endswith("?")) / ns if ns else 0.0
    st["jyo"] = sum(1 for t in ends if _bare(t).endswith("죠")) / ns if ns else 0.0
    st["supnida"] = sum(1 for t in ends if _bare(t).endswith("니다")) / ns if ns else 0.0

    if n >= STAT_MIN_CUES:
        lo, hi = KEY_RANGE
        if not lo <= st["key"] <= hi:
            out.append(("WARN", "E1", "-", f"key 칠한 큐 {st['key']:.1%}({lo:.0%}~{hi:.0%})"))
    if ns >= STAT_MIN_SENTENCES:
        if st["question"] < QUESTION_MIN:
            out.append(("WARN", "E2", "-", f"질문 문장 {st['question']:.1%}({QUESTION_MIN:.0%} 이상)"))
        lo, hi = JYO_RANGE
        if not lo <= st["jyo"] <= hi:
            out.append(("WARN", "E3", "-", f"'~죠' 문장 {st['jyo']:.1%}({lo:.0%}~{hi:.0%})"))
        lo, hi = SUPNIDA_RANGE
        if not lo <= st["supnida"] <= hi:
            out.append(("WARN", "E4", "-", f"습니다체 문장 {st['supnida']:.1%}({lo:.0%}~{hi:.0%}, 습니다체가 기본)"))

    run = st["supnida_run"] = 0
    for c in finals:
        run = run + 1 if _bare(c.get("t")).endswith("니다") else 0
        st["supnida_run"] = max(st["supnida_run"], run)
        if run == SUPNIDA_RUN_MAX + 1:
            out.append(("WARN", "E8", str(c.get("id")),
                        f"습니다체 문장이 {SUPNIDA_RUN_MAX}개 넘게 이어짐. '~죠?'·'~까요?'로 끊는다: {c.get('t')!r}"))

    for c in cues:
        hits = sorted({m.group(1) for f in ("t", "say") for m in FIRST_PERSON.finditer(c.get(f) or "")})
        if hits:
            out.append(("WARN", "E5", str(c.get("id")), f"1인칭 {', '.join(hits)}: {c.get('t')!r}"))

    canvas = canvas_strings(code_src) if code_src is not None else []
    hangul = sum(len(HANGUL.findall(d["text"])) for d in canvas if not d["tex"] and not d["prop"])
    st["canvas_hangul"] = hangul
    st["canvas_hangul_per_min"] = hangul / (duration_s / 60) if duration_s else None
    if st["canvas_hangul_per_min"] is not None and st["canvas_hangul_per_min"] > CANVAS_HANGUL_PER_MIN:
        out.append(("WARN", "E6", "-", f"화면 해설 한글 분당 {st['canvas_hangul_per_min']:.1f}자"
                    f"({hangul}자/{duration_s:.1f}초, 분당 {CANVAS_HANGUL_PER_MIN}자 이하)"))

    by_id = {str(c.get("id")): c.get("t") or "" for c in cues}
    for d in canvas:
        if d["tex"]:
            continue
        pool = [(d["cue"], by_id[d["cue"]])] if d["cue"] in by_id else list(by_id.items())
        for cid, t in pool:
            hit = _overlap(d["text"], t)
            if hit:
                out.append(("WARN", "E7", f"main.py:{d['line']}",
                            f"자막 {cid}와 {OVERLAP_WORDS}낱말 이상 겹침 {hit!r}: {d['text']!r}"))
                break
    return out, st


def stats_line(st: dict) -> str:
    per_min = st.get("canvas_hangul_per_min")
    return (f"stats: cues={st['cues']} sentences={st['sentences']} len_max={st['len_max']} "
            f"len_median={st['len_median']:g} key={st['key']:.1%} question={st['question']:.1%} "
            f"jyo={st['jyo']:.1%} supnida={st['supnida']:.1%} supnida_run={st['supnida_run']} "
            "canvas_hangul_per_min="
            + ("-" if per_min is None else f"{per_min:.1f}"))


def episode_duration(ep: Path) -> float | None:
    """편 길이(초): timing.json의 dur 합, 없으면 scene_durs.json 합."""
    for name, pick in (("timing.json", lambda d: [v.get("dur", 0) for v in d.values()]),
                       ("scene_durs.json", lambda d: list(d.values()))):
        f = Path(ep) / name
        if f.is_file():
            try:
                total = float(sum(pick(json.loads(f.read_text(encoding="utf-8")))))
            except Exception:
                continue
            if total > 0:
                return total
    return None


def _read(ep: Path):
    main_py, shots_json = ep / "main.py", ep / "shots.json"
    src = main_py.read_text(encoding="utf-8") if main_py.is_file() else None
    shots = json.loads(shots_json.read_text(encoding="utf-8")) if shots_json.is_file() else None
    return src, shots


def lint_episode(ep: Path) -> list[tuple[str, str, str, str]]:
    ep = Path(ep)
    src, shots = _read(ep)
    out = []
    if src is not None:
        out += lint_code(src)
    if shots is not None:
        out += lint_cues(shots, src)
    out += episode_stats(shots, src, episode_duration(ep))[0]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--episode", required=True)
    a = ap.parse_args(argv)
    ep = Path(a.episode)
    if not (ep / "main.py").is_file() and not (ep / "shots.json").is_file():
        print(f"ERROR L0 {ep} main.py와 shots.json이 없다")
        return 1
    findings = lint_episode(ep)
    for lv, rule, where, msg in findings:
        print(f"{lv} {rule} {where} {msg}")
    n_err = sum(1 for f in findings if f[0] == "ERROR")
    n_warn = len(findings) - n_err
    print(f"lint: ERROR {n_err}, WARN {n_warn}", file=sys.stderr)
    src, shots = _read(ep)
    print(stats_line(episode_stats(shots, src, episode_duration(ep))[1]), file=sys.stderr)
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
