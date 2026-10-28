"""lint.py 규칙마다 걸리는 입력 1개, 통과하는 입력 1개. 편 통계(E1~E8)와 stats 줄도 본다."""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SK = Path(__file__).resolve().parents[1]
LINT = SK / "scripts" / "lint.py"
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def _load():
    spec = importlib.util.spec_from_file_location("viz_lint", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cue(cid, t="좋은 자막", key=None, rel="build"):
    return {"id": cid, "t": t, "say": None, "key": key, "rel": rel, "move": "fade", "hold": False}


def _main(body, cue_ids=("c001",)):
    cues = "".join(f'        with self.cue("{c}"):\n            pass\n' for c in cue_ids)
    lines = "\n".join("        " + ln for ln in body.strip("\n").splitlines()) if body.strip() else "        pass"
    return ("from vizkit import *\n\n\nclass A(CueScene):\n    def construct(self):\n"
            f"{lines}\n{cues}")


def _episode(tmp_path, body="", cues=None, raw_main=None):
    cues = cues or [_cue("c001")]
    ep = tmp_path / "ep"
    ep.mkdir(parents=True)
    (ep / "shots.json").write_text(json.dumps(
        {"episode": "ep", "mode": "silent", "scenes": [{"name": "A", "cues": cues}]},
        ensure_ascii=False), encoding="utf-8")
    src = raw_main if raw_main is not None else _main(body, [c["id"] for c in cues])
    (ep / "main.py").write_text(src, encoding="utf-8")
    return ep


def _rules(tmp_path, **kw):
    ep = _episode(tmp_path, **kw)
    return [(lv, rule) for lv, rule, _w, _m in _load().lint_episode(ep)]


# (rule, level, 걸리는 씬 코드, 통과하는 씬 코드)
CODE_CASES = [
    ("T1", "ERROR", 'x = label("분산이 커진다")', 'x = label("분산")'),
    ("T1", "ERROR", 'x = label("왜 그럴까?")', 'x = label("왜 그럴까?", prop=True)'),
    ("T1", "ERROR", 'x = Text("정답입니다.")', 'x = label("정답입니다", prop=True)'),
    ("T1", "ERROR", 'x = explain_card(label("정답입니다"))', 'x = explain_card(label("정답"))'),
    ("T1", "ERROR", 'x = label(f"{n}개입니다")', 'x = label(f"{n}개")'),
    ("T1", "ERROR", 'x = label("값이 " + v + "입니다")', 'x = label("값 " + v)'),
    ("T2", "ERROR", 'x = label("평균·분산")', 'x = label("평균 분산")'),
    ("T2", "ERROR", 'x = label("입력 → 출력")', 'x = Tex(r"x \\to y")'),
    ("T3", "ERROR", 'x = title("1-1 도입")', 'x = title("도입")'),
    ("T3", "ERROR", 'x = label("(1) 가정")', 'x = label("가정")'),
    ("T4", "ERROR", 'x = source("논문 3쪽")', 'x = source("Hu et al., 2021")'),
    ("T4", "ERROR", 'x = label("핵심 정리")', 'x = label("핵심")'),
    ("T5", "WARN", 'x = label("저랭크 행렬 두 개를 곱함")', 'x = label("저랭크 행렬")'),
    ("T6", "WARN",
     'a = label("W 행렬")\nb = label("A 행렬")\nc = label("B 행렬")\n'
     'd = label("r 랭크")\ne = label("x 입력")\nf = label("h 출력")',
     'a = label("W 행렬")\nb = label("A 행렬")\nc = label("B")'),
    ("T7", "WARN", 'x = Text("가", font_size=30)', 'x = label("가", "M")'),
    ("T7", "WARN", 'x = Text("가", font_size=24)', 'x = label("가", "S")'),
    ("T7", "WARN", 'x = Tex("+", font_size=TEX_FS["L"] * 1.5)', 'x = tex("+", size="XL")'),
    ("T7", "WARN", 'x = rCode(c, font_size=FS["M"] * 1.44)', 'x = rCode(c, font_size=24)'),
    ("T4", "ERROR", 'x = tex(r"\\text{정리}")', 'x = tex("W_0")'),
    ("T8", "WARN", 'x = Square().set_fill("#FF0000")', 'x = Square().set_fill(RED)'),
    ("T9", "ERROR", 'x = Logo()', 'x = Square()'),
    ("T10", "WARN",
     'a = SurroundingRectangle(x)\nb = SurroundingRectangle(y)\nc = SurroundingRectangle(z)',
     'a = SurroundingRectangle(x).set_opacity(0.3)\nb = SurroundingRectangle(y, fill_opacity=0.3)\n'
     'c = SurroundingRectangle(z, buff=0).set_stroke(width=0).set_fill(BLUE, 0.3)\nd = SurroundingRectangle(w)'),
]


@pytest.mark.parametrize("rule,level,bad,good", CODE_CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CODE_CASES)])
def test_code_rules(tmp_path, rule, level, bad, good):
    assert (level, rule) in _rules(tmp_path / "bad", body=bad)
    assert all(r != rule for _lv, r in _rules(tmp_path / "good", body=good))


def _structure_cues(n_struct, total):
    return [_cue(f"c{i:03d}", rel="structure" if i < n_struct else ("next" if i % 2 else "build"))
            for i in range(total)]


# (rule, level, 걸리는 큐 목록, 통과하는 큐 목록)
CUE_CASES = [
    ("C1", "ERROR", [_cue("c001", "가" * 27)], [_cue("c001", "가" * 26)]),
    ("C2", "ERROR", [_cue("c001", "이렇게 끝납니다.")], [_cue("c001", "이렇게 끝나죠?")]),
    ("C3", "ERROR", [_cue("c001", "원래 W·A")], [_cue("c001", "원래 W와 A")]),
    ("C3", "ERROR", [_cue("c001", "랭크 r(작은 값)")], [_cue("c001", "랭크 r은 작은 값")]),
    ("C3", "ERROR", [_cue("c001", "핵심: 랭크")], [_cue("c001", "핵심은 랭크")]),
    ("C4", "ERROR", [_cue("c001", "원래 W를 그대로 얼려 둡니다", key="얼린다")],
     [_cue("c001", "원래 W를 그대로 얼려 둡니다", key="그대로 얼려")]),
    ("C5", "WARN", [_cue(f"c{i:03d}", rel="build") for i in range(5)],
     [_cue(f"c{i:03d}", rel="build") for i in range(4)] + [_cue("c004", rel="point")]),
    ("C7", "ERROR", [_cue("c001", "W₀ 고정")], [_cue("c001", "W 고정 ✓")]),
    ("C8", "WARN", _structure_cues(2, 40), _structure_cues(1, 40)),
]


@pytest.mark.parametrize("rule,level,bad,good", CUE_CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CUE_CASES)])
def test_cue_rules(tmp_path, rule, level, bad, good):
    assert (level, rule) in _rules(tmp_path / "bad", cues=bad)
    assert all(r != rule for _lv, r in _rules(tmp_path / "good", cues=good))


T1_CAUGHT = ["분산이 커진다", "정답입니다", "여기만 바뀌어요", "학습합니다", "이것이 핵심이다",
             "왜 그럴까?", "커진다", "있다", "돼요", "알죠", "고정됨", "없음", "LoRA는 핵심임"]
T1_PASSED = ["다음", "중요", "필요", "처음", "마음", "고정", "저장", "메모리",
             "수요", "주요", "포함", "프레임", "게임", "아까", "LoRA"]


@pytest.mark.parametrize("txt", T1_CAUGHT)
def test_t1_catches_sentence_endings(txt):
    assert _load().is_sentence_end(txt)


@pytest.mark.parametrize("txt", T1_PASSED)
def test_t1_passes_nouns(txt):
    assert not _load().is_sentence_end(txt)


def test_t1_nouns_pass_whole_lint(tmp_path):
    body = "\n".join(f'x{i} = label("{w}")' for i, w in enumerate(T1_PASSED))
    assert all(r != "T1" for _lv, r in _rules(tmp_path, body=body))


SUP, Q, JYO, YO = "값이 바뀝니다", "이건 왜 그럴까요?", "여기가 핵심이죠", "평범한 자막이에요"


def _cues_from(texts, key=0):
    """문구 목록을 큐로. key는 뒤에서 key개 큐에 칠한다."""
    n = len(texts)
    return [_cue(f"c{i:03d}", t, key=t[:2] if i >= n - key else None, rel=["build", "next", "point"][i % 3])
            for i, t in enumerate(texts)]


def _cues_with(n=20, key=0, q=0, jyo=0, supnida=0):
    """n큐(모두 문장 끝): 질문 q개, '~죠' jyo개, 습니다체 supnida개, 나머지는 해요체.
    습니다체는 다른 큐 사이에 고르게 끼워 넣어 5연속(E8)이 생기지 않게 한다."""
    others = [Q] * q + [JYO] * jyo + [YO] * (n - q - jyo - supnida)
    gaps = len(others) + 1
    texts = []
    for g in range(gaps):
        texts += [SUP] * ((g + 1) * supnida // gaps - g * supnida // gaps)
        if g < len(others):
            texts.append(others[g])
    return _cues_from(texts, key)


GOOD_STATS = dict(key=4, q=4, jyo=3, supnida=10)  # 20문장: key 20%, 질문 20%, 죠 15%, 습니다체 50%

# (rule, 걸리는 통계 인자, 통과하는 통계 인자)
STAT_CASES = [
    ("E1", dict(GOOD_STATS, key=1), GOOD_STATS),       # key 5%
    ("E1", dict(GOOD_STATS, key=8), GOOD_STATS),       # key 40%
    ("E2", dict(GOOD_STATS, q=2), GOOD_STATS),         # 질문 10%
    ("E3", dict(GOOD_STATS, jyo=1), GOOD_STATS),       # 죠 5%
    ("E3", dict(GOOD_STATS, jyo=5), GOOD_STATS),       # 죠 25%
    ("E4", dict(GOOD_STATS, supnida=6), GOOD_STATS),   # 습니다체 30%(해요체 쏠림)
    ("E4", dict(key=4, q=3, jyo=2, supnida=14), GOOD_STATS),  # 습니다체 70%
]


@pytest.mark.parametrize("rule,bad,good", STAT_CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(STAT_CASES)])
def test_episode_ratio_rules(tmp_path, rule, bad, good):
    assert ("WARN", rule) in _rules(tmp_path / "bad", cues=_cues_with(**bad))
    assert all(r[:1] != "E" for _lv, r in _rules(tmp_path / "good", cues=_cues_with(**good)))


def test_episode_ratio_rules_skip_tiny_episode(tmp_path):
    assert all(r[:1] != "E" or r == "E5" for _lv, r in _rules(tmp_path, cues=[_cue("c001")]))


def test_e8_supnida_run(tmp_path):
    """습니다체 문장이 5개 이어지면 WARN E8(다섯 번째 큐). 비율은 같고 4개까지만 이으면 통과."""
    rest = [Q, SUP, JYO, SUP, Q, SUP, YO, SUP, JYO, SUP, Q, YO, Q, JYO, YO]
    bad = _cues_from([SUP] * 5 + rest, key=4)
    assert ("WARN", "E8") in _rules(tmp_path / "bad", cues=bad)
    good = _cues_from([SUP] * 4 + [Q, SUP] + rest[1:], key=4)
    rules = _rules(tmp_path / "good", cues=good)
    assert ("WARN", "E8") not in rules and ("WARN", "E4") not in rules


def test_tone_ratios_count_sentences_not_cues():
    """말투 비율은 문장 끝 큐로 센다. 쉼표나 어미 없이 끊긴 큐는 문장 수에 넣지 않는다."""
    mod = _load()
    assert mod.is_sentence_final(SUP) and mod.is_sentence_final(Q) and mod.is_sentence_final("안 바뀌죠")
    assert not mod.is_sentence_final("LoRA는요,") and not mod.is_sentence_final("입력이 지나가는 이 길은")
    split = []
    for c in _cues_with(**GOOD_STATS):
        split += [_cue(c["id"] + "a", "그래서 이 부분은,", rel=c["rel"]), c]
    _w, st = mod.episode_stats({"scenes": [{"name": "A", "cues": split}]}, None, None)
    assert st["cues"] == 40 and st["sentences"] == 20
    assert st["supnida"] == 0.5 and st["question"] == 0.2 and st["jyo"] == 0.15


def test_e5_first_person(tmp_path):
    bad = [_cue("c001", "제가 해 볼게요"), _cue("c002", "우리 모델은요,")]
    rules = _rules(tmp_path / "bad", cues=bad)
    assert rules.count(("WARN", "E5")) == 2
    good = [_cue("c001", "문제가 남아요"), _cue("c002", "숙제가 생기죠")]
    assert ("WARN", "E5") not in _rules(tmp_path / "good", cues=good)


def test_e6_canvas_hangul_per_minute(tmp_path):
    body = 'a = label("고정")\nb = label("저장")\nc = label("메모리")\nd = label("번역")'  # 9자
    bad = _episode(tmp_path / "bad", body=body)
    (bad / "timing.json").write_text(json.dumps({"c001": {"scene": "A", "dur": 20.0}}), encoding="utf-8")
    assert ("WARN", "E6") in [(lv, r) for lv, r, _w, _m in _load().lint_episode(bad)]  # 27자/분
    good = _episode(tmp_path / "good", body=body)
    (good / "scene_durs.json").write_text(json.dumps({"A": 60.0}), encoding="utf-8")
    assert all(r != "E6" for _lv, r, _w, _m in _load().lint_episode(good))  # 9자/분
    prop = _episode(tmp_path / "prop", body=body.replace(")", ", prop=True)"))
    (prop / "timing.json").write_text(json.dumps({"c001": {"scene": "A", "dur": 20.0}}), encoding="utf-8")
    assert all(r != "E6" for _lv, r, _w, _m in _load().lint_episode(prop))


def test_e7_caption_overlap(tmp_path):
    cues = [_cue("c001", "원래 W는 그대로 두고 옆길만 배워요")]
    bad = _main('pass', ["c001"]).replace(
        '        with self.cue("c001"):\n            pass\n',
        '        with self.cue("c001"):\n            x = label("W는 그대로 두고 옆길만", prop=True)\n')
    assert ("WARN", "E7") in _rules(tmp_path / "bad", cues=cues, raw_main=bad)
    good = bad.replace("W는 그대로 두고 옆길만", "고정")
    assert ("WARN", "E7") not in _rules(tmp_path / "good", cues=cues, raw_main=good)


def test_cli_stats_line(tmp_path):
    ep = _episode(tmp_path, cues=_cues_with(**GOOD_STATS), body='x = label("고정")')
    (ep / "scene_durs.json").write_text(json.dumps({"A": 60.0}), encoding="utf-8")
    r = subprocess.run([sys.executable, str(LINT), "--episode", str(ep)],
                       capture_output=True, text=True, encoding="utf-8", env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    last = r.stderr.strip().splitlines()[-1]
    assert last.startswith("stats: "), r.stderr
    kv = dict(p.split("=", 1) for p in last[len("stats: "):].split())
    assert kv["cues"] == "20" and kv["sentences"] == "20" and kv["len_max"] == "10" and kv["len_median"] == "7.5"
    assert kv["key"] == "20.0%" and kv["question"] == "20.0%" and kv["jyo"] == "15.0%"
    assert kv["supnida"] == "50.0%" and kv["supnida_run"] == "1" and kv["canvas_hangul_per_min"] == "2.0"


def test_c8_long_episode_allows_two(tmp_path):
    assert all(r != "C8" for _lv, r in _rules(tmp_path, cues=_structure_cues(2, 80)))


def test_c6_cue_without_self_cue(tmp_path):
    cues = [_cue("c001"), _cue("c002")]
    only_first = _main("", ["c001"])
    assert ("ERROR", "C6") in _rules(tmp_path / "bad", cues=cues, raw_main=only_first)
    assert all(r != "C6" for _lv, r in _rules(tmp_path / "good", cues=cues))


def test_docstring_exempt_from_t8(tmp_path):
    doc = '"""ai-concept-visualization-video 템플릿, 배경 #000000"""\n'
    src = doc + _main("").replace("    def construct", '    """설명 씬, 배경 #000000"""\n    def construct')
    rules = [r for _lv, r in _rules(tmp_path / "good", raw_main=src)]
    assert "T8" not in rules
    assert ("ERROR", "T9") in _rules(tmp_path / "bad", body='x = Logo()')


def test_cli_format_and_exit(tmp_path):
    ep = _episode(tmp_path / "bad", body='x = label("분산이 커진다")')
    r = subprocess.run([sys.executable, str(LINT), "--episode", str(ep)],
                       capture_output=True, text=True, encoding="utf-8", env=ENV)
    assert r.returncode == 1, r.stdout + r.stderr
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert lines and all(ln.split(" ", 1)[0] in ("ERROR", "WARN") for ln in lines)
    t1 = [ln for ln in lines if ln.startswith("ERROR T1 ")]
    assert t1 and t1[0].split(" ")[2].startswith("main.py:")

    ok = _episode(tmp_path / "good", body='x = label("분산")')
    r = subprocess.run([sys.executable, str(LINT), "--episode", str(ok)],
                       capture_output=True, text=True, encoding="utf-8", env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
