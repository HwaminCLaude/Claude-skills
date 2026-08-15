# 씬 레이아웃 템플릿

두 시리즈(79구간)에서 **실제로 렌더해 눈으로 확인한** 배치들이다. 좌표가 붙어 있는 이유는
자리 다툼이 이 스택에서 가장 흔한 결함이기 때문이다 — 새로 짜기 전에 여기서 고른다.

프레임: **x ∈ [−7.11, 7.11], y ∈ [−4, 4]**. 아래 좌표는 전부 이 기준이다.

---

## 고르는 법

| 화면에 올릴 것 | 템플릿 |
|---|---|
| 논문 표를 그대로 | **T1 표 + 아래 주석** |
| 코드와 설명을 나란히 | **T2 좌 코드 · 우 설명** |
| 논문 그림에 표시 | **T3 그림 + 바깥 라벨** |
| 수식 하나를 뜯기 | **T4 수식 + 아래 해설** |
| 값 몇 개를 대조 | **T5 검산 스택** |
| 흐름·구조 | **T6 좌 도식 · 우 목록** |
| 막대·분포 | **T7 차트 + 위 라벨** |
| 전환·다음 편 예고 | **T8 카드** |

---

## T1 — 표 + 아래 주석

논문 표를 옮길 때. **주석·비교 블록은 표 오른쪽이 아니라 표 아래**에 둔다.
오른쪽에 두면 마지막 열 위에 올라탄다(실제로 3번 밟았다).

```python
COLS = [-4.6, -0.6, 1.6, 4.4]           # 라벨열 + 값 3열
ROWS = [2.35, 1.75, 1.15, 0.55, -0.15, -0.75, -1.45, -2.05]

head = VGroup(*[mono(h, font_size=18, color=GREY_B).move_to([x, 3.0, 0])
                for x, h in zip(COLS, HEAD) if h])
rule = Line([-6.0, 2.7, 0], [5.8, 2.7, 0], stroke_color=GREY_D, stroke_width=2)
# 값 셀: kr()은 0열(한글 라벨), mono()는 나머지(숫자)
```

- 표가 차지하는 범위: **x −6.0 ~ 5.5, y 2.7 ~ −2.3**
- 주석·대조 블록: `move_to([0.0, -3.0, 0])` — 표 아래 빈 자리
- 좌우 판정 화살표: `move_to([4.0, -3.05, 0])` — 막대(좌하)·캡션(중앙 최하단)과 안 겹친다
- 출처 캡션: `caption(...).to_edge(DOWN, buff=0.35)`

**강조는 새로 그리지 않는다.** 이미 화면에 있는 셀을 참조해 키운다:

```python
base_row = t2_row(6, MINT_, fs=22)      # 변수로 잡아둔다
...
self.playw(Flash(base_row[3], color=MINT_, line_length=0.3),
           base_row[3].animate.scale(1.35), **SHOTS["..."])
```

같은 자리에 같은 값을 다시 `FadeIn` 하면 글자가 포개진다.

---

## T2 — 좌 코드 · 우 설명

코드 대조편의 기본형. 코드는 왼쪽 고정, 설명은 오른쪽 세로 스택.

```python
code = code_at("sdpa.py", scale=0.5).to_edge(LEFT, buff=0.4)
# 코드 상자 오른쪽 끝은 대략 x ≈ 1.5 (scale·줄길이에 따라 다르다 — 프레임으로 확인)

notes = VGroup(
    kr("입력 [2, 7, 512]", font_size=22),
    kr("사영 후 [2, 7, 512]", font_size=22),
).arrange(DOWN, buff=0.5).to_edge(RIGHT, buff=0.8)
```

- 오른쪽 설명이 길면 **줄을 접는다**(`"앞줄\n뒷줄"`). 코드 상자 위로 올라타는 것보다 낫다.
- `code.highlight(...)`는 **(appear, disappear) 두 개**를 준다.
  `disappear`를 코드 지우는 `playw`에 반드시 넣는다 — 안 넣으면 강조 글자만 남는다.

```python
a1, d1 = code.highlight(8, "'prj'", color="#FFD166")
self.playw(FadeIn(code), a1, **SHOTS["s01"])
...
self.playw(FadeOut(code), d1, **SHOTS["s09"])      # d1을 빠뜨리지 않는다
```

---

## T3 — 논문 그림 + 바깥 라벨

```python
f = fig("fig3.png", height=4.4).shift(UP * 0.5)
cap = caption("논문 Figure 3 (arXiv:xxxx, p.13)", fs=16).next_to(f, DOWN, buff=0.2)
```

- **라벨을 그림 위에 얹지 않는다.** 논문 그림은 흰 배경이라 회색·민트 글씨가 안 읽힌다.
  `next_to(f, RIGHT, buff=0.3)` 처럼 **바깥**에 둔다.
- 그림 안 특정 위치를 가리킬 때만 사각형을 얹는다. 좌표는 **렌더 프레임에서 실측한 비율**로:

```python
box = Rectangle(width=f.width * 0.045, height=f.height * 0.30,
                stroke_color=ACCENT, stroke_width=3)
box.move_to(f.get_center() + RIGHT * f.width * 0.045 + UP * f.height * 0.24)
```

- 그림이 섞인 그룹은 `VGroup`이 아니라 **`Group`**이다.
- 축 라벨과 설명 라벨을 둘 다 그림 아래 두면 부딪힌다. 축은 `buff=0.05`,
  설명은 **`buff=0.62`** 처럼 확실히 벌린다.

---

## T4 — 수식 + 아래 해설

```python
eq = MathTex(r"\mathrm{Attention}(Q,K,V) = "
             r"\mathrm{softmax}\!\left(\frac{QK^T}{\sqrt{d_k}}\right)V",
             font_size=40).to_edge(DOWN, buff=0.8)
```

- **수식 안에 한글을 넣지 않는다.** LaTeX가 죽는다. 한국어는 `kr()`로 옆·아래에.
- 수식을 화면 아래에 두면 위쪽 도형(행렬 그리드 등)과 세로로 겹치기 쉽다.
  도형을 먼저 `FadeOut` 하거나 도형을 위로 올린다.
- 수식 일부만 강조: `RaeTex(...)`로 조각을 나눠 만들고 조각에 색을 준다.

---

## T5 — 검산 스택

"논문에 적힌 값 ↔ 코드를 돌려 얻은 값"을 대조하는 세로 스택. 계산 노드가 있는 편의 마무리형.

```python
rows = VGroup(
    fact_row("논문 Table 3 · big", "213M", COOL, 34),
    fact_row("세어보니", f"{FACTS['params']['big_m']}M", MINT_, 34),
    fact_row("상대 오차", f"{FACTS['params']['big_rel']}%", MINT_, 30),
).arrange(DOWN, buff=0.45).shift(DOWN * 0.2)
```

- 값은 **`FACTS[...]`에서 읽는다.** 숫자를 코드에 적으면 분석을 다시 돌려도 영상이 안 바뀐다.
- `fact_row`의 값 자리에 **한글을 넣지 않는다**(고정폭 폰트 → 두부). 한글 값이면 `kr()`로 짠다.
- 통과 표시는 `check(fs=26)` — `✔`는 KR 폰트에 있어 안전하다. 이모지는 안 된다.

---

## T6 — 좌 도식 · 우 목록

```python
diagram = ...                                  # 왼쪽 절반, x −6 ~ 0
items = VGroup(*[kr(t, font_size=24) for t in TITLES]) \
    .arrange(DOWN, buff=0.4, aligned_edge=LEFT)   # ← 반드시 aligned_edge=LEFT
items.to_edge(RIGHT, buff=1.2)
```

- 목록은 **`aligned_edge=LEFT`**. 빼먹으면 가운데 정렬이 되어 줄마다 들쭉날쭉해진다.
- 목록이 오른쪽 끝에 붙었으면 그 왼쪽 끝(x)을 재고, 항목보다 긴 줄은 **접는다**:

```python
long = kr("④ 어텐션 드롭아웃\n    — 이 목록엔 없다", font_size=21, color=ACCENT)
long.next_to(items, DOWN, buff=0.3).align_to(items, LEFT)
```

---

## T7 — 차트 + 위 라벨

```python
bar_g = bars(values, unit=0.62, width=0.34, buff=0.14)
bar_g.to_edge(RIGHT, buff=1.2).shift(DOWN * 1.0)
```

- **높이를 두 번 곱하지 않는다.** `bars(..., unit=U)`와 `set_bar_heights(..., unit=2.4)`의
  기본값이 다르다. `set_bar_heights(g, [v * k for v in vals])`의 실제 높이는 `v·k·2.4`다.
  가장 큰 값으로 **미리 계산해** 프레임 안(위 여유 ≥ 1.0)에 들어오는지 확인한다.
- 값 라벨은 막대 위(`buff=0.12`)에 붙으므로 **막대 top + 0.3**까지가 실제 차지 범위다.
- 기준선(threshold) 라벨은 선 바로 위에 두면 막대 위에 올라탄다.
  **막대 그룹 위 빈 자리**(`next_to(bar_g, UP, buff=0.3)`)에 두고 색으로 구분한다.
- 흩어진 점 강조는 `VGroup.scale()`이 아니라 점마다:
  `*[d.animate.set_color(MINT_).scale(1.6) for d in few]`

---

## T8 — 카드 (도입·전환·예고)

```python
title = title_card("이 논문이 풀려는 문제", "문제 정의 · 1편")
self.playw(Write(title[0]), FadeIn(title[1]), run_time=1.2, wait=0.0)
...
nxt = VGroup(caption("다음 편"), kr(NEXT_TITLE, font_size=30)) \
    .arrange(DOWN, buff=0.2)
```

- 전환 컷은 `run_time` 짧게, `wait=0.0`. 나레이션이 없는 컷이므로 `shots.json`에 넣지 않아도 된다.
- 예고 카드는 화면 중앙 아래(`shift(DOWN * 0.5)`)가 안전하다.

---

## 색과 헬퍼 (두 시리즈 공통)

| 이름 | 쓰임 |
|---|---|
| `MINT_` | 제안 방법 · 좋아지는 값 |
| `COOL` | 중립 · 입력·구조 |
| `ACCENT` | 주의 · 논문 인용 · 강조 |
| `RIVAL` | 비교 대상 · 나빠지는 값 |
| `GREY_B` / `GREY_D` | 보조 라벨 / 선 |

| 헬퍼 | 주의 |
|---|---|
| `kr(text)` | 한글 전용. `font="Malgun Gothic"` 고정 |
| `mono(text)` | ASCII 전용. **한글이 들어오면 KR 폰트로 넘어가게** 만들어 둔다 |
| `box(label, color, w, h, fs)` | 색을 바꿀 땐 `recolor()` — `set_color()`는 배경까지 칠한다 |
| `fig(name, height)` | `Group`에 담는다 (`VGroup` 아님) |
| `check(fs)` / `cross(fs)` | `✔`/`✕`는 KR 폰트에 있다. **다른 이모지는 쓰지 않는다** |
| `caption(text, fs)` | 출처 표기. `to_edge(DOWN, buff=0.35)` |
| `load_shots(__file__)` | 타이밍의 유일한 출처 |

이모지가 필요하면 도형으로 그린다. 예:

<!-- 새 템플릿 추가 지점 — 아래 "T9 이후" 참고 -->


```python
def padlock(size=0.34, color=GREY_B):
    body = RoundedRectangle(width=size, height=size * 0.78,
                            corner_radius=size * 0.1, stroke_color=color,
                            stroke_width=3, fill_color=BLACK, fill_opacity=1)
    shackle = Arc(radius=size * 0.27, start_angle=0, angle=PI,
                  stroke_color=color, stroke_width=3)
    shackle.next_to(body, UP, buff=0)
    return VGroup(body, shackle)
```

---

## T9 이후 — 새 템플릿을 추가하려면

이 파일에 절을 하나 더 붙인다. 쓸모 있는 템플릿이 되려면 **세 가지가 다 있어야** 한다:

1. **언제 고르나** — 맨 위 "고르는 법" 표에 한 줄 추가
2. **좌표** — "대충 오른쪽"이 아니라 실제 숫자.
   프레임은 x ∈ [−7.11, 7.11], y ∈ [−4, 4]. 차지하는 범위를 x·y로 적는다
3. **밟았던 함정** — 그 배치에서 실제로 부딪혔던 것. 이게 이 문서의 핵심이다

좌표를 재는 법: 한 번 렌더한 뒤 프레임에서 픽셀을 읽고 환산한다(1920×1080 기준).

```
x = -7.11 + (x_px / 1920) * 14.22
y =  4.00 - (y_px / 1080) *  8.00
```

`sweep_frames.py --width 0` 로 원본 해상도 프레임을 뽑으면 재기 쉽다.

템플릿을 추가했으면 **`references/visual-qa.md`의 검수 항목에 걸리는지** 한 번 생각해본다 —
새 배치는 새 자리 다툼을 만든다.
