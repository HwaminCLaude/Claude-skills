"""손계산 워크스루 씬이 함께 쓰는 헬퍼 (템플릿).

프로젝트 루트에 복사해 쓴다.

    cp <skill>/assets/walkthrough_template/wtcommon.py .

    # 각 에피소드의 main.py
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    from wtcommon import *

이 시리즈는 화면의 대부분이 **숫자 표**와 **계산 줄**이다. 그래서 자리 다툼이
가장 흔한 결함이 된다(프레임 x ∈ [−7.11, 7.11], y ∈ [−4, 4]).
그 둘을 만드는 함수를 한곳에 모아, 크기를 미리 재고 배치할 수 있게 했다.

프로젝트에 이미 `<slug>common.py`(kr·mono·box·token_row 등)가 있다면
아래 "기본 헬퍼" 절을 지우고 `from <slug>common import *` 로 바꾼다.

읽을 것: references/hand-calc-walkthrough.md §8 (배치 함정)
"""

from __future__ import annotations

import json
import math
import re as _re
from pathlib import Path as PPath

from manim import *          # noqa: F401,F403
from raenim import *         # noqa: F401,F403
from random import seed

seed(41)
np.random.seed(41)           # noqa: F405 — 렌더할 때마다 화면이 같아야 한다

# ─────────────────────────────────────────────────── 기본 헬퍼
# (프로젝트 공용 모듈이 이미 있으면 이 절을 지우고 import로 바꾼다)

KR = "Malgun Gothic"          # 한글 폰트. Pango가 알아서 고르지 않는다
MONO = "Consolas"

MINT_ = ManimColor("#00DDAA")    # noqa: F405 — 긍정·성립
RIVAL = ManimColor("#FF7A59")    # noqa: F405 — 문제·경고
ACCENT = ManimColor("#FFD166")   # noqa: F405 — 주목
COOL = ManimColor("#5AA9E6")     # noqa: F405 — 중립 도식

_HANGUL = _re.compile(r"[가-힣ㄱ-ㆎ]")


def kr(text: str, **kwargs) -> "Text":                              # noqa: F405
    """한글 텍스트."""
    kwargs.setdefault("font", KR)
    return Text(text, **kwargs)                                     # noqa: F405


def mono(text: str, **kwargs) -> "Text":                            # noqa: F405
    """수치·코드 조각용 고정폭.

    고정폭 폰트에는 한글 글립이 없어 두부(□)가 된다. 표 라벨처럼 한글이 섞여
    들어오는 자리가 있어서, 한글이 보이면 조용히 한글 폰트로 바꾼다.
    """
    kwargs.setdefault("font", KR if _HANGUL.search(text) else MONO)
    kwargs.setdefault("font_size", 24)
    return Text(text, **kwargs)                                     # noqa: F405


def box(label: str, color=COOL, w=2.2, h=1.0, fs=22) -> "VGroup":   # noqa: F405
    rect = RoundedRectangle(width=w, height=h, corner_radius=0.12,  # noqa: F405
                            stroke_color=color, stroke_width=2.5,
                            fill_color=BLACK, fill_opacity=1)       # noqa: F405
    return VGroup(rect, kr(label, font_size=fs).move_to(rect))      # noqa: F405


def token_row(words, w=1.15, h=0.55, buff=0.18, fs=17,
              color=COOL) -> "VGroup":                              # noqa: F405
    """토큰 상자를 가로로. 예시 문장은 시리즈 내내 이 모양으로 나온다."""
    return VGroup(*[box(t, color, w=w, h=h, fs=fs)                  # noqa: F405
                    for t in words]).arrange(RIGHT, buff=buff)      # noqa: F405


def slot(title: str, w=3.4, h=1.1) -> "VGroup":                     # noqa: F405
    rect = Rectangle(width=w, height=h, stroke_color=GREY_D,        # noqa: F405
                     stroke_width=2, fill_opacity=0)
    return VGroup(rect, kr(title, font_size=20).move_to(rect))      # noqa: F405


def check(color=MINT_, fs=34) -> "Text":                            # noqa: F405
    return Text("✔", font=KR, font_size=fs, color=color)            # noqa: F405


def cross_mark(color=RIVAL, fs=34) -> "Text":                       # noqa: F405
    """이름이 `cross`가 아닌 이유: 크로스어텐션 씬 클래스와 부딪힌다."""
    return Text("✕", font=KR, font_size=fs, color=color)            # noqa: F405


def title_card(text: str, sub: str | None = None) -> "VGroup":      # noqa: F405
    parts = [kr(text, font_size=42)]
    if sub:
        parts.append(kr(sub, font_size=22, color=GREY_B))           # noqa: F405
    return VGroup(*parts).arrange(DOWN, buff=0.45)                  # noqa: F405


def next_card(text: str) -> "VGroup":                               # noqa: F405
    return VGroup(                                                  # noqa: F405
        kr("다음 편", font_size=22, color=GREY_B),                  # noqa: F405
        kr(text, font_size=30),
    ).arrange(DOWN, buff=0.3)


def load_shots(main_file: str) -> dict[str, dict]:
    """에피소드의 shots.json에서 샷별 타이밍을 읽어온다."""
    path = PPath(main_file).resolve().parent / "shots.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        shot["id"]: {"run_time": shot["run_time"], "wait": shot["wait"]}
        for body in data["scenes"].values()
        for shot in body["shots"]
    }


# ─────────────────────────────────────────────── 워크스루 수치 로딩

_PROJECT = PPath(__file__).resolve().parent
WT = json.loads((_PROJECT / "analysis" / "walkthrough_facts.json")
                .read_text(encoding="utf-8"))

CFG = WT["config"]
VOCAB = WT.get("vocab", {})
WEIGHTS = WT["weights"]
# 아래 두 줄은 모델에 맞춰 이름을 바꾼다 (인코더/디코더가 없는 모델도 있다)
ENC = WT.get("encoder", {})
DEC = WT.get("decoder", {})


def fmt(v, dp=2):
    """표에 넣을 숫자 문자열. −0.00 표기를 없앤다."""
    s = f"{float(v):.{dp}f}"
    return "0.00" if s in ("-0.00", "0.00") and dp == 2 else s


# ─────────────────────────────────────────────────────── 표와 계산 줄

def numtab(rows, row_labels=None, col_labels=None, cell_w=1.30, cell_h=0.52,
           fs=22, color=COOL, dp=2, label_fs=18, label_color=None):
    """숫자 표. 이 시리즈의 주력 화면.

    `.cells[r][c]`로 숫자 mobject에, `.bg[r][c]`로 칸 사각형에 닿는다.
    `.width`/`.height`가 라벨까지 포함한 실제 크기라, 옆에 무언가를 둘 때
    이 값을 재고 두면 겹치지 않는다.

    빈 문자열을 넣어 두었다가 나중에 값을 덮어쓰면 "표를 한 줄씩 채우는" 연출이 된다.
    """
    label_color = GREY_B if label_color is None else label_color    # noqa: F405
    grid, bgs, cells = VGroup(), [], []                             # noqa: F405
    n_r, n_c = len(rows), len(rows[0])
    for r in range(n_r):
        bg_row, cell_row = [], []
        for c in range(n_c):
            rect = Rectangle(width=cell_w, height=cell_h,            # noqa: F405
                             stroke_color=GREY_D, stroke_width=1.2,  # noqa: F405
                             fill_opacity=0)
            rect.move_to([(c - (n_c - 1) / 2) * cell_w,
                          ((n_r - 1) / 2 - r) * cell_h, 0])
            txt = mono(fmt(rows[r][c], dp) if not isinstance(rows[r][c], str)
                       else rows[r][c], font_size=fs, color=color)
            txt.move_to(rect)
            grid.add(rect, txt)
            bg_row.append(rect)
            cell_row.append(txt)
        bgs.append(bg_row)
        cells.append(cell_row)
    grid.bg, grid.cells = bgs, cells

    whole = VGroup(grid)                                            # noqa: F405
    whole.grid = grid
    whole.bg, whole.cells = bgs, cells
    whole.cell_w, whole.cell_h = cell_w, cell_h

    if row_labels:
        labs = VGroup()                                             # noqa: F405
        for r, name in enumerate(row_labels):
            t = kr(name, font_size=label_fs, color=label_color)
            t.next_to(bgs[r][0], LEFT, buff=0.18)                   # noqa: F405
            labs.add(t)
        whole.add(labs)
        whole.row_labels = labs
    if col_labels:
        labs = VGroup()                                             # noqa: F405
        for c, name in enumerate(col_labels):
            t = kr(name, font_size=label_fs, color=label_color)
            t.next_to(bgs[0][c], UP, buff=0.16)                     # noqa: F405
            labs.add(t)
        whole.add(labs)
        whole.col_labels = labs
    return whole


def cell_box(tab, r, c, color=ACCENT, width=3.5, pad=0.0):
    """표의 한 칸을 감싼다. **반드시 변수로 받아 두고 나중에 지운다.**"""
    rect = tab.bg[r][c]
    return Rectangle(width=rect.width + pad, height=rect.height + pad,  # noqa: F405
                     stroke_color=color, stroke_width=width).move_to(rect)


def row_box(tab, r, color=ACCENT, width=3.5, pad=0.06):
    cells = tab.bg[r]
    w = cells[-1].get_right()[0] - cells[0].get_left()[0]
    return Rectangle(width=w + pad, height=cells[0].height + pad,    # noqa: F405
                     stroke_color=color, stroke_width=width).move_to(
        [(cells[0].get_left()[0] + cells[-1].get_right()[0]) / 2,
         cells[0].get_center()[1], 0])


def col_box(tab, c, color=ACCENT, width=3.5, pad=0.06):
    cells = [row[c] for row in tab.bg]
    h = cells[0].get_top()[1] - cells[-1].get_bottom()[1]
    return Rectangle(width=cells[0].width + pad, height=h + pad,     # noqa: F405
                     stroke_color=color, stroke_width=width).move_to(
        [cells[0].get_center()[0],
         (cells[0].get_top()[1] + cells[-1].get_bottom()[1]) / 2, 0])


def fit(m, max_w=13.0, max_h=7.4):
    """프레임 안으로 줄인다.

    벡터 셋이 한 줄에 들어가면 쉽게 화면 밖으로 나간다. 만들 때 재서 줄인다.
    """
    if m.width > max_w:
        m.scale(max_w / m.width)
    if m.height > max_h:
        m.scale(max_h / m.height)
    return m


def calc(*lines, fs=26, buff=0.30, color=WHITE, align=LEFT):        # noqa: F405
    """계산 줄 묶음. 한 줄이 곧 손으로 적는 한 줄이다."""
    g = VGroup(*[mono(t, font_size=fs, color=color) for t in lines])  # noqa: F405
    g.arrange(DOWN, buff=buff, aligned_edge=align)                  # noqa: F405
    return fit(g)


def vecrow(values, dp=2, fs=28, color=WHITE, prefix=""):            # noqa: F405
    """[a, b, c, d] 한 줄짜리 벡터 표기. `.plain`에 문자열이 남는다."""
    body = ", ".join(fmt(v, dp) if not isinstance(v, str) else v for v in values)
    t = mono(f"{prefix}[{body}]", font_size=fs, color=color)
    t.plain = f"{prefix}[{body}]"
    return fit(t)


def eq(tex, fs=40, color=WHITE):                                    # noqa: F405
    """수식. 한글을 절대 넣지 않는다(LaTeX 유니코드 오류)."""
    return MathTex(tex, font_size=fs, color=color)                  # noqa: F405


def titled(title, body, buff=0.35, fs=24, color=GREY_B):            # noqa: F405
    t = kr(title, font_size=fs, color=color)
    g = VGroup(t, body).arrange(DOWN, buff=buff)                    # noqa: F405
    g.title, g.body = t, body
    return g


def scene_title(text):
    """구간 좌상단에 남는 작은 제목.

    본문 제목과 **같은 문구를 쓰지 않는다** — 화면에 두 번 뜬다.
    위쪽에 캡션을 둘 일이 있으면 이걸 먼저 FadeOut 한다.
    """
    t = kr(text, font_size=26, color=GREY_B)                        # noqa: F405
    t.to_corner(UL, buff=0.42)                                      # noqa: F405
    return t


def note(text, color=GREY_B, fs=22, width=None):
    t = kr(text, font_size=fs, color=color)
    if width and t.width > width:
        t.scale(width / t.width)
    t.to_edge(DOWN, buff=0.55)                                      # noqa: F405
    return t


def warn_card(text, w=8.6, h=1.25, color=RIVAL, fs=24):
    """주의 카드. 이 시리즈는 '우리가 정한 값'을 자주 밝혀야 한다."""
    rect = RoundedRectangle(width=w, height=h, corner_radius=0.14,  # noqa: F405
                            stroke_color=color, stroke_width=2.5,
                            fill_color=BLACK, fill_opacity=1)       # noqa: F405
    t = kr(text, font_size=fs, color=color)
    if t.width > w - 0.5:
        t.scale((w - 0.5) / t.width)
    return VGroup(rect, t.move_to(rect))                            # noqa: F405


def arrow(a, b, color=None, width=3, buff=0.12):
    return Arrow(a, b, buff=buff, stroke_width=width,               # noqa: F405
                 color=GREY_B if color is None else color,          # noqa: F405
                 max_tip_length_to_length_ratio=0.22)


def flow(labels, w=2.5, h=0.85, buff=0.55, color=COOL, fs=20,
         direction=None):
    """상자 체인 + 화살표. 파이프라인 도식용."""
    direction = RIGHT if direction is None else direction           # noqa: F405
    boxes = VGroup(*[box(t, color, w=w, h=h, fs=fs)                 # noqa: F405
                     for t in labels]).arrange(direction, buff=buff)
    links = VGroup()                                                # noqa: F405
    for a, b in zip(boxes[:-1], boxes[1:]):
        links.add(arrow(a.get_edge_center(direction),
                        b.get_edge_center(-direction), buff=0.08))
    g = VGroup(boxes, links)                                        # noqa: F405
    g.boxes, g.links = boxes, links
    return g


def bar_chart(values, labels, unit=2.0, width=0.5, buff=0.5, color=COOL,
              top_label=True, fs=20, hi=None, hi_color=ACCENT, floor=0.0):
    """막대 + 값 라벨 + 이름표. 음수도 된다(0선 아래로 내려간다).

    이름표는 막대·값라벨을 통틀어 **가장 아래**보다 더 아래에 둔다.
    0선 바로 아래에 고정하면 음수 막대의 값 라벨과 겹친다.
    """
    group, tops, names = VGroup(), VGroup(), VGroup()               # noqa: F405
    for i, v in enumerate(values):
        h = max(abs(float(v)) * unit, 0.04)
        col = hi_color if (hi is not None and i in hi) else color
        rect = Rectangle(width=width, height=h, fill_color=col,      # noqa: F405
                         fill_opacity=0.9, stroke_width=0)
        x = (i - (len(values) - 1) / 2) * (width + buff)
        rect.move_to([x, (h / 2) if float(v) >= floor else (-h / 2), 0])
        group.add(rect)
        if top_label:
            t = mono(fmt(v), font_size=fs, color=col)
            t.next_to(rect, UP if float(v) >= floor else DOWN, buff=0.12)  # noqa: F405
            tops.add(t)
        names.add(kr(labels[i], font_size=fs - 2, color=GREY_B)     # noqa: F405
                  .move_to([x, 0, 0]))
    bottom = min([m.get_bottom()[1] for m in list(group) + list(tops)])
    for n in names:
        n.move_to([n.get_center()[0], bottom - 0.34, 0])
    whole = VGroup(group, tops, names)                              # noqa: F405
    whole.bars, whole.tops, whole.names = group, tops, names
    return whole


def softmax_lines(scaled, attn, dp=2):
    """softmax를 손으로 계산하는 세 줄 묶음의 문자열들.

        exps, total, ratios = softmax_lines(h["scaled"][r], h["attn"][r])
        self.playw(FadeIn(calc(*exps)), ...)
    """
    exps = [math.exp(v) for v in scaled]
    total = sum(exps)
    return (
        [f"e^{fmt(v)} = {fmt(e)}" for v, e in zip(scaled, exps)],
        f"합 = {fmt(total)}",
        [f"{fmt(e)} / {fmt(total)} = {fmt(a)}" for e, a in zip(exps, attn)],
    )
