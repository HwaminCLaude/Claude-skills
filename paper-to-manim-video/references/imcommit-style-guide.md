# 임커밋 스타일 연출 가이드

임커밋(Imcommit / GitHub `CodingVillainKor`) 채널의 `manim-kor` 저장소를 원문 분석해 뽑아낸 규약이다. 이 스킬이 만드는 영상은 이 구조를 따른다.

출처: [manim-kor](https://github.com/CodingVillainKor/manim-kor), [raenim](https://github.com/CodingVillainKor/raenim). 저자 포크(`CodingVillainKor/manim`)는 **쓰지 않는다** — 우리는 순정 ManimCE + raenim 조합이다. 아래 "회피 목록" 참조.

---

## 1. 무엇이 이 스타일을 만드는가

세 가지다.

1. **한 영상 = 한 아이디어.** 5~8분 단편을 여러 편으로 나눈다. `attention1/2/3`, `dino1~5`, `dit1~4`처럼 번호를 붙여 시리즈로 간다. 한 편에 논문 전체를 밀어넣지 않는다.
2. **나레이션 호흡이 코드에 박혀 있다.** `self.play` 대신 `self.playw(..., wait=N)`을 쓴다. `wait`이 곧 "여기서 N초 동안 말한다"는 뜻이다. 대본과 영상이 어긋나지 않는 이유가 이것 하나다.
3. **헬퍼가 영상에서 태어난다.** 새 연출이 필요하면 영상 파일 안에 함수를 정의하고, 재사용 가치가 생기면 라이브러리로 승격한다. (증거: `src/gitmerge1/main.py`의 로컬 `get_commit`과 `raenim/git.py`의 것이 글자까지 동일하고, `new_commit`만 인자가 일반화됐다.)

---

## 2. 파일 구조 규약

```python
from manim import *
from raenim import *
from random import seed

seed(41)
np.random.seed(41)      # 렌더할 때마다 화면이 같아야 편집·나레이션이 맞는다

KR = "Malgun Gothic"    # Pango는 한글 폰트를 알아서 고르지 않는다


class intro(Scene2D):   # 구간 하나 = 클래스 하나
    def construct(self):
        ...
```

- **클래스 = 영상 구간**, 클래스 이름이 곧 CLI 렌더 타깃이다. 짧고 소문자 ASCII로 짓는다 (`intro`, `problem`, `method`, `result`, `kvCache`, `woKVcache`). PEP8 PascalCase를 따르지 않는 건 의도적이다 — 터미널에 타이핑하기 쉬워야 한다.
- 한 파일에 클래스 3~6개가 보통이다. 2D/3D를 한 파일에서 섞어도 된다 (`lm/main.py`는 6개 중 하나만 `Scene3D`).
- **`manim main.py`를 그냥 실행하면 안 된다.** 클래스가 여러 개면 Manim이 대화형으로 물어보며 멈춘다. 항상 클래스명을 명시한다.
- 에셋은 에피소드 폴더 안에 두고 상대 경로로 참조한다 (`ImageMobject("assets/figures/fig2.png")`). Manim은 작업 디렉터리 기준으로 경로를 푼다.

---

## 3. 타이밍 계약 (가장 중요)

`playw`는 **재생한 뒤 기다린다.** 즉 한 샷의 길이는 `run_time + wait`다.

```python
wait = max(0.2, est_sec - run_time)
self.playw(Write(title), run_time=1.5, wait=wait)
```

`est_sec`을 그냥 `wait`에 넣으면 매 샷이 `run_time`만큼 길어진다. 게다가 `Write()`의 기본 `run_time`은 텍스트 길이에 비례하므로 오차가 일정하지도 않다. **샷마다 `run_time`을 명시**하고 `wait`은 위 식으로 계산한다. `scripts/estimate_narration.py`가 이걸 자동으로 채운다.

기본 `run_time`: 일반 등장 1.0~1.5초, 강조 2.0초, 화면 전환 0.8초.

---

## 4. 샷 유형별 도구 선택

| 보여줄 것 | 쓸 것 |
|---|---|
| 제목·설명 문장 | `kr("...")` = `Text(..., font="Malgun Gothic")` |
| 수식 전체 | `MathTex` 또는 `RaeTex` |
| 수식의 **한 조각만 강조** | `RaeTex("J(W)", "=", r"\frac{...}")["\\frac{...}"]` — 문자열로 꺼낸다 |
| 코드 한 줄씩 설명 | `PythonCode` + `highlight(line, text)` |
| 코드 실행 순서 | `PythonCode.exec()` |
| 텐서·레이어 도식 | `Tensor(5, shape="square")`, `Linear(3, 4)`, `MLP(3, 5, 2)` |
| 순전파·역전파 흐름 | `forward_prop(mlp, self)` / `backward_prop(mlp, self)` |
| 폴더·파일 트리 | `Folder("/home/user/")`, `FileSystem(folders=[...], files=[...])` |
| 커밋 그래프 | `get_commit()`, `new_commit(c, direction=RIGHT)`, `branch(...)` |
| 논문의 실제 그림·데이터 | `ImageMobject(...)` + `crop_figure.py` — **생성 이미지 금지** |
| 은유·분위기 컷 | `ImageMobject(...)` + `gen_image.py` (편당 1~3컷 상한) |

---

## 5. 반복되는 연출 관용구

```python
# 재생 후 나레이션 호흡
self.playw(FadeIn(box), run_time=1.0, wait=1.8)

# 여러 요소 순차 등장 (LaggedStart 자동 래핑)
self.playwl(FadeIn(item) for item in group)     # 제너레이터 식 그대로 됨

# 텍스트를 도형·수식으로 바꿔치기 (원본을 씬에서 치움)
self.playw(Transform(label, formula, replace_mobject_with_target_in_scene=True),
           run_time=1.2, wait=1.0)

# 수식 변형
self.playw(TransformMatchingTex(eq_before, eq_after), run_time=1.5, wait=2.0)

# 이동 예약 후 한꺼번에
for m in (a, b, c):
    m.generate_target()
a.target.shift(LEFT * 2)
self.playw(*[MoveToTarget(m) for m in (a, b, c)], run_time=1.0, wait=0.5)

# 카메라 훑고 원복
self.cf.save_state()
self.playw(self.cf.animate.scale(0.6).move_to(detail), run_time=1.2, wait=2.5)
self.playw(Restore(self.cf), run_time=1.0, wait=0.3)

# 3D로 기울이되 글자는 정면으로
tilt = 65
self.tilt_camera_horizontal(tilt)
label = kr("[B, L, D]").rotate(-tilt * DEGREES, UP)
```

**긴 순차 애니메이션**은 리스트를 먼저 만들고 루프에서 재생한다. `layernorm.py`는 들어오는 선/정규화/나가는 선 세 리스트를 `None`으로 한 칸씩 밀어 겹치게 만든 뒤 `AnimationGroup`으로 묶어 파이프라인 효과를 낸다.

---

## 6. 순정 ManimCE에서의 회피 목록

우리는 저자 포크를 쓰지 않으므로 다음은 **쓸 수 없다** (또는 애초에 깨져 있다):

| 대상 | 이유 |
|---|---|
| `SkewedAnimations` | 포크에만 있는 `_AnimationBuilder.method_names`를 읽는다. 게다가 포크에서도 `methods`가 `MethodWithArgs` dataclass라 첨자 접근이 `TypeError`로 깨진다 — 양쪽 다 동작 안 함 |
| `raenim.imcommit.Logo` | 채널 로고다. 남의 채널 아이덴티티이므로 쓰지 않는다. (`__init__.py`가 export하지도 않는다) |
| `--parallel` / `--multithread` | 포크 전용 CLI 플래그. 대신 `render.py --jobs N`으로 구간별 프로세스를 병렬로 띄운다 |
| `Chainer(chain_type=<미지값>)` | 폴백이 클래스가 아니라 문자열 `"plain"`이라 `TypeError` |
| `PixelImage` (480px 초과 이미지) | 리사이즈 전 `h, w`로 `arrange_in_grid`를 호출해 그리드와 픽셀 수가 어긋난다 |
| `Tensor(shape=<"circle"/"square" 외>)` | else 분기가 없어 `NameError` |

또 하나: **`clear()`는 순정 `Scene.clear()`가 아니다.** raenim이 덮어써서 updater를 떼고 전부 `FadeOut`하는 애니메이션이 된다(1초 대기 포함). 즉시 제거를 원하면 `self.remove(*self.mobjects)`를 쓴다.

---

## 7. manim.cfg에 해상도를 넣지 말 것

`pixel_width` / `pixel_height` / `frame_rate`를 `manim.cfg`에 쓰면 **`-ql`/`-qh` 플래그를 덮어쓴다.** 스모크(480p15) → 본번(1080p60) 2단 렌더가 통째로 무력화되므로 절대 넣지 않는다. 품질은 `render.py`가 호출할 때마다 정한다.

(임커밋 포크의 `default.cfg`에는 실제로 `# These now override the --quality option` 주석과 함께 박혀 있다. 그래서 그 저장소의 모든 영상이 1080p60 고정이다.)

---

## 8. 나레이션 톤

- 구어체 존댓말. "~합니다", "~죠", "~볼까요".
- **질문으로 연다.** "왜 이게 문제일까요?" → 답을 화면으로 보여준다.
- 한 문장은 짧게. 화면에 한 가지 변화가 일어나는 동안 한 문장.
- 수식을 읽어주지 말고 **의미를 말한다.** "분자는 클래스 간 분산입니다"가 "W 트랜스포즈 S b W"보다 낫다.
- 전문용어는 한국어 + 영어 병기 첫 등장 시 1회. "국소 이웃(local neighborhood)".
