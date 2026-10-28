# 흐름 문법: 직전과의 관계(`rel`) → 연출(`move`)

대본(`shots.json`)의 자막 큐마다 **직전 큐와의 관계** `rel`을 하나 붙인다. 씬 코드는 그 `rel`에 맞는 연출을 큐 블록(`with self.cue(id):`) 안에서 1개 이상 재생한다. 근거는 참고 코퍼스 33편 코드에서 각 연출이 쓰인 상황이다.

- 예시의 `파일:줄`은 `references/example_corpus/` 기준이다(`scripts/fetch_examples.py`로 받는다. 원본 `src/<topic>/main.py` → `<topic>.py`, 줄 번호 동일). 모두 실제 줄을 열어 확인했다.
- 키트 헬퍼는 `vizkit.py`의 `CueScene` 메서드와 함수다. 시그니처는 `SKILL.md`와 키트 docstring을 본다.
- 박자 하나의 `run_time`은 기본 1초(0.5~1.0)다. 남는 시간은 큐 블록이 끝날 때 `CueScene`이 기다린다.
- `CueScene`은 큐 블록 안의 `self.play` 횟수를 cuelog의 `plays`로 남긴다(`playw`, `playwl`, 키트 카메라 헬퍼도 센다. `wait`, `add`는 세지 않는다). `plays`가 0인 큐는 `render.py`가 `WARN CUE_NO_BEAT <Scene> <cue_id>`로 알린다(설계 A5 '박자 없는 큐 0개').
- 글자와 수식은 `label(text, size)`, `tex(*parts, size=...)`로만 만든다. 키트가 1080p 잉크 높이에 맞춰 크기를 보정하므로 `.scale()`로 키우지 않는다(`design-system.md` 글자 크기 토큰).

## 요약 표

| rel | 이야기 흐름 | move | 키트 헬퍼 | 참고 코퍼스 근거(빈도) |
|---|---|---|---|---|
| `detail` | 같은 그림의 작은 부분을 자세히 | 2D 카메라 확대 → 복귀 | `zoom_in`, `zoom_out` | save_state 31회 |
| `next` | 다음 볼 것이 같은 그림 옆에 있음 | 2D 카메라 이동(핵심 객체를 실어 같이 옮길 수도 있음) | `pan_to` | 이동·확대 체인 69회(19편) |
| `structure` | 여러 개를 한 판으로 보고 그중 하나를 설명 | 3D 기울이기(phi 50~70°, 1초) → 대상만 세우기 → `Restore` | `tilt`, `stand_up`/`lay_down`, `orbit`, `untilt` | 48회/18편 |
| `carry` | 앞 결과를 써서 다음 단계로 | 줄여서 옆으로 밀고 빈자리에 새 내용, 또는 Transform | `carry` | Transform 계열 253회, 이동+등장 동시 40회 |
| `aside` | 앞 내용은 남기고 새 설명 시작 | 앞 묶음을 옆으로 돌려 치움(`rotate(axis=UP)` 60~100° + `shift`) | `aside` | 4회 |
| `change` | 값이나 모양만 바뀜 | 같은 자리 변환(Transform, 점→숫자, 값 갱신) | (직접 `Transform`) | — |
| `build` | 지금 그림에 다음 조각을 더함 | 그 자리 등장(Write, FadeIn(shift), GrowArrow) | (직접 재생) | FadeIn(shift) 158회 |
| `point` | 한 항이나 한 칸을 가리킴 | 나머지 흐리기(0.25) + 대상 색, 반투명 틴트, Indicate/Flash/Circumscribe | `dim_others`, `undim`, `dimmed`, `tint`, (카드) `quote_focus` | 흐리기 65회, 강조 325회 |
| `new` | 새 생각 시작 | 제목만 남기고 비운 뒤 새 구성 | `clear_to` | 빈 화면 비율 2.5~16% |
| `hook` | 편의 도입(첫 60초) | 빠른 컷 몽타주: 논문 그림, 결과, 예고 장면 | `quote_card`, `clear_to` | 큰 전환 18/38개가 첫 60초 |
| `quote` | 논문 인용 | 크롭 카드가 옆에서 들어오고 뒤는 BLACK 0.75, 카드 안 강조는 덮개 | `quote_card`, `quote_focus` | 편집층 33/38개 |
| `chapter` | 주제 전환 | 컷(씬 경계) 또는 밀어내기 | 새 `CueScene` 클래스, `clear_to` | 편집층 |

규칙
- 같은 `rel`이 4큐 넘게 이어지면 린트 `C5` WARN이다. `build`만 반복하면 슬라이드처럼 된다.
- `structure`(3D)는 편당 1~2회(짧은 편 1회)다. 린트 `C8`이 센다.
- `hook`, `quote`, `chapter`는 참고 영상에서는 편집 프로그램이 한 일이다. 우리는 Manim 안에서 만든다. 그래서 코드 근거는 '도입 씬', '그림 띄우기', '씬 경계'에서 가져왔다.
- 표에 `rel`을 더하면 반드시 참고 코퍼스 근거 `파일:줄`을 함께 적는다.

---

## `detail`

같은 그림 안의 작은 부분을 자세히 볼 때. 카메라 상태를 저장하고 대상으로 확대한 다음, 설명이 끝나면 `Restore`로 돌아온다.

- 키트: `self.zoom_in(target, scale=0.4)` → (설명 박자들) → `self.zoom_out()`
- 예시
  - floatingpoint.py:422-423 — `self.cf.save_state()` 다음 `self.cf.animate.move_to(numl.n2p(0.5)).scale(0.3)`로 수직선 한 구간 확대.
  - CFMvsDiffusion.py:368 — 설명이 끝나면 `Restore(self.cf)`를 FadeOut과 함께 재생해 원래 화면으로 복귀.
  - floatingpoint.py:1516 — `self.playw(Restore(self.cf))` 단독 복귀.

## `next`

다음 볼 것이 같은 그림의 옆에 있을 때. 카메라를 옮긴다. 핵심 객체를 카메라와 같이 옮기면 '실어 나르는' 느낌이 난다.

- 키트: `self.pan_to(target)`
- 예시
  - lora1.py:264-268 — `self.cf.animate.shift(LEFT*12)`와 함께 `ab`, `at`, `bt`도 `shift(LEFT * 12)`로 실어 옮긴다.
  - clco2.py:111 — `self.cf.animate.shift(RIGHT * ...)`로 옆 패널에 초점을 옮긴다.
  - CLIP.py:55 — `self.cf.animate.shift(RIGHT * 1.5)`로 옆 설명 자리를 연다.

## `structure`

여러 개를 한 판으로 늘어놓고 그중 하나를 설명할 때. 판을 3D로 눕히고, 설명할 대상만 같은 각도로 세운 뒤, 끝나면 `Restore`.

- 키트: `self.tilt(center, phi=60)` → `self.play(stand_up(mob.animate))`(세우기 애니메이션) → `self.play(lay_down(mob.animate))`(다시 눕히기) → `self.untilt()`
  - `stand_up(mob, phi=60)`은 `mob.rotate(phi°, axis=RIGHT)`를 그대로 부른다. 객체를 넘기면 **바로** 돌리고 그 객체를 돌려준다(`self.add(stand_up(m))`, 애니메이션 아님). `mob.animate`를 넘겨야 애니메이션이 된다. `self.play(stand_up(mob))`는 틀린 쓰임이다.
  - 기울인 판을 조금 돌려 깊이를 보여 줄 때는 `self.orbit(degrees)`(카메라 `increment_theta` 애니메이션을 돌려준다, `tilt` 안에서만): `self.play(lay_down(m.animate), self.orbit(-14), run_time=0.9)`. `untilt()`가 tilt 전 카메라로 되돌린다.
- 예시
  - linearAttn.py:340-344 — `self.cf.save_state()` 뒤 `self.cf.animate.reorient(0, 74, 0, (...), 1.83)`로 판을 눕힌다.
  - bondinterest.py:127-132 — `reorient(0, 56, 0, ...)`와 동시에 `fpy.animate.rotate(56 * DEGREES, axis=RIGHT)`로 대상만 세운다.
  - bondinterest.py:244-247 — 세웠던 것을 `rotate(-56 * DEGREES, axis=RIGHT)`로 눕히며 `Restore(self.cf)`.
  - floatingpoint.py:1512-1516 — 기울이기 → `Indicate` → `Restore(self.cf)` 한 묶음.

## `carry`

앞 결과를 가지고 다음 단계로 갈 때. 앞 묶음을 줄여 옆으로 밀고 빈자리에 새 내용을 놓거나, 앞 결과를 다음 모양으로 Transform한다.

- 키트: `self.carry(group, edge=LEFT, scale=0.6)`
- 예시
  - jev1.py:271 — `VGroup(q1, cns, q1_tag).animate.scale(0.8).shift(LEFT * 3)`로 질문을 왼쪽으로 밀고, 이어서 답을 오른쪽에 놓는다.
  - clco2.py:107 — `Transformr(bot2.copy(), done2)`로 앞 결과를 다음 칸으로 옮겨 변환.
  - CLIP.py:718-721 — 카메라 복귀와 `MoveToTarget(img_encoding)`, `MoveToTarget(text_encoding)`을 한 박자에.

## `aside`

앞 내용은 버리지 않고 남겨 둔 채 새 설명을 시작할 때. 앞 묶음 전체를 세로축(UP) 기준으로 60~100° 돌려 옆으로 치운다.

- 키트: `self.aside(group, angle_deg=80, direction=LEFT)`
- 예시
  - CLIP.py:436-438 — `all_things.save_state()` 뒤 `rotate(-angle, axis=UP).shift(RIGHT * 4)`(angle 71°).
  - linearAttn3.py:435 — `scale(0.7).rotate(PI / 3, axis=UP).shift(LEFT * 5)`.
  - curseofknowledge.py:630 — `rotate(PI / 1.8, axis=UP).shift(IN * 4 + LEFT * 6.5)`.

## `change`

자리는 그대로이고 값이나 모양만 바뀔 때. 같은 위치에서 변환한다.

- 키트 헬퍼 없음. `Transform`, `ReplacementTransform`, `ValueTracker` 갱신을 직접 쓴다.
- 예시
  - lora1.py:256-258 — 같은 자리에 새 `Tex("16 \\times 1024")`를 만들어 `Transform(at, at_), Transform(bt, bt_)`.
  - floatingpoint.py:429 — 눈금 32개를 64개로 `Transform(ticks01, ticks01_new)`.
  - floatingpoint.py:125 — `val2.animate.set_value(2147483647)`로 숫자만 갱신.

## `build`

지금 그림에 다음 조각을 더할 때. 그 자리에서 등장시킨다. 이것만 이어지지 않게 한다.

- 키트 헬퍼 없음. `FadeIn(shift=...)`, `Write`, `GrowArrow`를 직접 쓴다.
- 예시
  - CFMvsDiffusion.py:158 — `FadeIn(model_output, shift=UP, scale=2)`.
  - gqa.py:152 — `self.playwl(FadeIn(arrow_text), GrowArrow(arrow_q), lag_ratio=0.5)`.
  - justgrpo.py:34 — `FadeIn(model_ar), Write(modelt_ar)`.

## `point`

문장 안의 한 항이나 한 칸을 가리킬 때. 우선순위는 (1) 나머지 흐리기 + 대상 색, (2) 반투명 틴트, (3) 순간 강조다.

- 키트: `self.play(*dim_others(self, [target]))` → `self.play(*undim(self))`, `tint(mob, BLUE)`
  - `undim(self)`은 지금 장면에 남은 객체만 되돌린다. 흐린 뒤 `FadeOut`으로 뺀 객체는 되살리지 않는다.
  - 앞 씬 끝 화면을 흐린 채 이어받을 때: `self.add(dimmed(ctx, scene=self))`(바로 0.25배, 애니메이션 아님). `scene=`을 주면 나중 `undim(self)`이 되돌린다.
  - 인용 카드 안의 한 부분을 가리킬 때는 흐리기 대신 `self.quote_focus(card, keep)`(아래 `quote`).
- 예시
  - CLIP.py:817-820 — 대상 막대만 GREEN으로 칠하고 나머지는 `set_opacity(0.2)`, 라벨은 GREY_B.
  - lora1.py:127 — `SurroundingRectangle(weight, color=BLUE, buff=0.0).set_opacity(0.3)` 반투명 틴트.
  - bondinterest.py:327 — `Circumscribe(explain.words[-2], color=YELLOW_B)` 순간 강조.
  - clco_autohistory.py:320 — `Flash(...)` 두 개 동시.

## `new`

새 생각을 시작할 때. 제목만 남기고 비운 뒤 새로 구성한다.

- 키트: `self.clear_to([title])`
- 예시
  - clco2.py:119 — 채팅 묶음 전체를 `FadeOut(VGroup(...))`하고 다음 줄부터 새 구성(시각 라벨)을 쌓는다.
  - floatingpoint.py:68 — 설명 묶음을 한 번에 `FadeOut(VGroup(brace_text, bit_brace, eq, numc))`.
  - raenimgl/scene.py:153-156 — `clear()`: 모든 객체의 updater를 떼고 한 박자에 전부 FadeOut.

## `hook`

편의 도입(첫 60초). 논문 그림, 결과, 예고 장면을 빠르게 넘긴다. 참고 영상은 편집으로 했지만 우리는 첫 씬 안에서 컷 대신 짧은 FadeIn/FadeOut과 `quote_card`를 1초 간격으로 이어 만든다.

- 키트: `self.quote_card(path)`, `self.clear_to([])`
- 예시
  - CFMvsDiffusion.py:1009-1010 — 씬 첫 박자로 논문 그림 `ImageMobject("cfm_fig.png")`을 바로 띄운다.
  - CLIP.py:26-36 — 도입 씬 `intro`: 모델 상자 하나를 띄우고 바로 입력 예시를 넣는다(첫 박자부터 그림).
  - lora1.py:9-21 — 도입 씬 `whatisLoRA`: 층 묶음을 한 번에 그려 바로 보여 준다.

## `quote`

논문을 인용할 때. 뒤를 BLACK 0.75로 어둡게 덮고, 크롭 카드가 옆에서 들어온다. 핵심 부분만 남기고 나머지를 덮는다(`quote_focus`). 출처는 카드 옆에 Noto Serif KR S 크기로 보이는 동안만 둔다.

- 키트: `q = self.quote_card("assets/fig1.png"); card = q[1]` → 강조 `cov = self.quote_focus(card, keep)` → 초점 옮기기 `cov = self.quote_focus(card, keep2, cov)` → 치우기 `self.play(FadeOut(q), FadeOut(cov))`
  - `keep`은 카드 안 비율 상자 `(x0, y0, x1, y1)`(왼쪽 위가 `(0, 0)`, 오른쪽 아래가 `(1, 1)`) 또는 카드 위에 놓은 Mobject다. 나머지 부분을 BLACK `OVERLAY_OPACITY` 띠 4개로 덮는다. 예: 왼쪽 53%만 남김 `(0, 0, 0.53, 1)`, 오른쪽 절반으로 옮김 `(0.5, 0, 1, 1)`.
  - `keep=None`에 `cover`를 주면 덮개만 FadeOut한다. 덮개는 장면에 따로 올라가므로 카드를 치울 때 함께 FadeOut한다(`clear_to`도 치운다).
- **밝은 카드는 확대하지 않는다.** 흰 논문 그림을 카메라로 키우면 카드가 자막 띠(y < −2.7)를 덮어 A2가 FAIL이 되고 자막을 읽을 수 없다. 강조는 카메라 확대 대신 `quote_focus` 덮개로 한다. `quote_card` 카드는 화면 높이 0.6배, 아래 끝 약 −2.4라서 그대로 두면 자막 띠에 닿지 않는다.
- 예시
  - floatingpoint.py:131-133 — `ol = self.overlay`, 대상만 `set_z_index(ol.z_index + 1)`로 올리고 `FadeIn(ol)`.
  - bondinterest.py:122-124 — 같은 방식으로 한 줄만 위로 올리고 나머지를 덮는다.
  - CFMvsDiffusion.py:1288-1289 — 논문 그림 `ImageMobject("cfm_fig.png")`을 FadeIn.

## `chapter`

주제를 바꿀 때. 씬 경계(클래스 하나가 끝나고 다음 클래스 시작)가 곧 컷이다. 씬 안에서 바꿀 때는 밀어내기(`FadeOut(shift=...)` + `FadeIn(shift=...)`)를 쓴다.

- 키트: `shots.json`에서 새 씬을 시작하고 `class Next(CueScene)`를 만든다. 씬 안이면 `self.clear_to([])`.
- 예시
  - lora1.py:277 — `class comparisonLora(InteractiveScene, Scene2D)`: 앞 씬 `whatisLoRA` 다음 주제(파라미터 수 비교)로 컷.
  - CLIP.py:85 — `class naiveApproach(...)`: 도입 다음 장으로 컷.
  - CLIP.py:671 — `FadeOut(VGroup(...), shift=RIGHT)`로 밀어내며 바꾼다.
