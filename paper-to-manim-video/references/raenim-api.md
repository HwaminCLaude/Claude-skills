# raenim API 레퍼런스 (순정 ManimCE 기준)

`raenim` 0.5.3 (Apache-2.0), 14개 모듈 약 1,625줄. `from manim import *` 위에 `from raenim import *`를 덮어쓰는 설계다. 아래는 소스를 직접 읽고 정리한 것으로, **순정 ManimCE 0.20.1에서 동작 확인된 것만** 표시했다.

> 설치 주의: raenim은 `[build-system]`이 없어 레거시 `setup.py`를 타고 `install_requires`의 `noise`(cp311 휠 없음)를 끌어온다. `uv pip install --no-deps`로 넣고 `addict`/`opencv-python`은 따로 선언하며, `noise`는 `assets/noise_shim/noise.py`를 주입해 대체한다. `setup_env.py`가 전부 처리한다.

---

## scene.py — 씬 계층

```python
class RaenimScene:                              # 순수 믹스인, export 안 됨
class Scene2D(MovingCameraScene, RaenimScene)
class Scene3D(ThreeDScene, RaenimScene)
```

| 메서드 | 하는 일 |
|---|---|
| `playw(*anims, wait=1, **kw)` | `play` 후 `wait`초 대기. 제너레이터 식을 인자로 주면 자동 언팩 |
| `playwl(*anims, lag_ratio=0.05, wait=1)` | `LaggedStart`로 감싼 `playw` |
| `playwlfin(*mobs)` | 전부 `FadeIn`으로 감싸 `playwl` |
| `addw(*mobs, wait=1)` | `add` 후 대기 |
| `playw_return(...)` | `rate_func=there_and_back` 고정 (갔다 돌아오기) |
| `clear()` | **순정과 다름** — updater 제거 후 전체 `FadeOut` 애니메이션 |
| `to_front(*mobs)` | `add_foreground_mobjects` 별칭 |
| `all_but(*mobs)` | VGroup 한 겹 평탄화 후 지정 mobject 제외한 나머지 |
| `organize(locals())` | 지역변수 중 `Mobject`만 골라 `addict.Dict`로 — `m.circle` 점 표기 접근 |
| `cf` (property) | 2D: `camera.frame` / 3D: `renderer.camera._frame_center` |
| `mouse`, `overlay` (property) | 마우스 커서 이미지, 검정 반투명 오버레이 (lazy) |

`Scene3D` 전용:

| 메서드 | 하는 일 |
|---|---|
| `tilt_camera_horizontal(degree, zoom=1.0)` | phi/theta/gamma를 각도 하나로 계산해 `set_camera_orientation` |
| `tilt_camera_vertical(degree, zoom=1.0)` | phi만 변경 |
| `move_camera_horizontally/vertically(...)` | `move_camera` + 내부에서 `wait`까지 수행 |
| `set_camera(...)` | `set_camera_orientation`의 얇은 별칭 |

주의: `play_camera(to, scale)`는 `self.camera.frame`을 직접 참조하므로 **`Scene2D` 전용**이다. `Scene3D`의 `ThreeDCamera`에는 `frame`이 없다. `Scene2D.point_mouse_to()`는 return이 없는 미완성 코드다.

---

## text.py — 텍스트·수식

```python
RaeTex(*tex_strings, items=None)     # MathTex 서브클래스
```
정수 인덱스 대신 **원문 문자열로** 조각을 꺼낸다. 이 스킬에서 수식 강조의 기본 도구다.

```python
eq = RaeTex("J(W)", "=", r"\frac{W^\top S_b W}{W^\top S_w W}")
self.playw(Indicate(eq[r"\frac{W^\top S_b W}{W^\top S_w W}"], color=YELLOW),
           run_time=1.0, wait=1.5)
```

- `items=`는 `MathTex`의 `substrings_to_isolate`로 넘어간다.
- 같은 문자열을 두 번 넘기면 같은 키의 VGroup에 합쳐진다.
- `items`를 지정하면 서브모브젝트 분할 개수가 인자 개수와 달라져 매핑이 어긋날 수 있다. 강조가 엉뚱한 곳에 걸리면 `items`를 빼고 조각을 더 잘게 나눠 넘길 것.
- README의 백틱 예제(``RaeTex(r"x`+`y")``)는 **구버전 API**다. 지금은 위 형태가 맞다.

| 클래스 | 설명 |
|---|---|
| `Words(text)` | 공백 기준 단어 구간을 미리 계산. `w.words[0]`로 단어 단위 접근 |
| `CodeText(text)` | `font_size=24` + 고정폭 폰트를 주입한 `Text` |
| `TextBox` / `TexBox` | `Text`/`MathTex`를 반투명 검정 `SurroundingRectangle`로 감쌈. `.text`/`.tex`, `.box` 접근. z_index 자동 관리 |
| `ListText("a","b","c")` | 대괄호로 감싼 목록. `no_bracket=True`로 끌 수 있음 |

`MONO_FONT`는 플랫폼별로 결정된다(Windows → Consolas). **한글 폰트는 아니다** — 한글은 반드시 `Text(..., font="Malgun Gothic")`으로 직접 지정한다.

---

## script.py — 코드 시각화 (이 스킬의 주력)

```python
code = PythonCode("snippet.py")     # 파일 경로를 받는다
```

`ManimCE`의 `Code`를 상속하되 원본 소스를 보관하고 `ast.parse`까지 해 둔다. 핵심은 **소스 좌표 → mobject 매핑**이다.

| 호출 | 반환 |
|---|---|
| `code(12)` | 12번째 줄 mobject |
| `code(3, 9)` | 3~9번째 줄 슬라이스 |
| `code.find_text(12, "range", nth=1)` | 그 줄에서 n번째 `range`의 `(start, end)` 문자 인덱스 |
| `code.text_slice(12, "range", exclusive=False)` | 그 글자들의 VMobject (`exclusive=True`면 그 부분을 뺀 나머지) |
| `code.highlight(12, "range", color="#FFFF00")` | `(등장 애니메이션, 사라짐 애니메이션)` 튜플 |
| `code.exec()` | 실행 순서대로 줄 하이라이트 애니메이션 리스트 |
| `code.exec(with_line_no=True)` | `(FadeOut(box), line_no)` 튜플 리스트 |

`exec()`의 백엔드는 둘이다.
- 기본 `ASTExecutionSimulator` — AST를 순회하며 If/For/While/With/Try를 해석. **루프는 3회만** 시뮬레이션한다.
- `use_tracer=True` → `compile` + `sys.settrace`로 **코드를 실제로 실행**해 line 이벤트를 수집. 신뢰할 수 없는 코드에는 쓰지 말 것.

또한 `frame`/`script`/`code`는 raenim이 재정의한 프로퍼티다 (`frame = self[:-1]`, `script`와 `code`는 `code_lines` 별칭). 생성자가 `background` 인자를 조용히 버리는 점도 알아둘 것.

---

## nn.py — 신경망 도식

`Linear`와 `MLP`는 **클래스가 아니라 함수**이고 `VGroup`을 돌려준다.

```python
Linear(3, 4)                         # 입력층(파랑) + 전결합선 + 출력층(초록)
MLP(3, 5, 5, 2, layer_distance=3)    # [층, 가중치, 층, ..., 층] 인터리브 VGroup
Tensor(5, shape="square", arrange=RIGHT, buff=0.1)
Activation("relu")                   # 원 안에 활성함수 그래프 (원+그래프만 반환)
forward_prop(mlp, self)              # scene을 주면 직접 play, None이면 애니메이션 리스트 반환
backward_prop(mlp, self)
```

- `Tensor.to_numbers(numbers=None)`은 mobject가 아니라 **애니메이션**(`Transform`)을 반환한다.
- `Conv1d`/`Conv2d`/`RNN`은 빈 스텁이다 (미구현, `__all__`에도 없음).
- `propagation`은 `run_time=0.3`을 하드코딩한 뒤 다시 `play(run_time=...)`을 호출해 이중 적용된다 — 타이밍이 이상하면 이걸 의심할 것.

---

## 그 외 모듈

| 모듈 | 제공 |
|---|---|
| `git.py` | `get_commit()`, `chash(text)`, `new_commit(c, *, direction=RIGHT, buff=1)`, `branch(...)` — direction·buff는 **키워드 전용** |
| `filesystem.py` | `FileIcon`, `FolderIcon`, `File`, `Folder`, `FileSystem(folders=[], files=[], tag=None)` |
| `matrix.py` | `Mat.zeros/ones/eye/randn(...)` — `DecimalMatrix` 위의 numpy 스타일 팩토리, `.val`로 원본 배열 |
| `coordinates.py` | `RaenimPlane` (격자 끔, 축만 남기고 0.6배), `markc(x, y)` (좌표 점 + tick + 보조선, updater 포함) |
| `animation.py` | `RWiggle` (Perlin 떨림), `AMove` (반동 이동), `Transformr` (replace 고정 Transform), `Marking` (노란 강조), `AnchorToPoint` |
| `mobject.py` | `SurroundingRect`, `Chainer`, `BrokenLine`, `Joiner`, `Pixel`, `PixelImage`, `Overlay`, `Mouse` |
| `constant.py` | `MINT = #00DDAA`, `X_STRING = ✘`, `CHECK_STRING = ✔` |

---

## 네임스페이스 오염 주의

`animation.py`, `matrix.py`, `git.py`, `coordinates.py`, `mobject.py`에 `__all__`이 없다. 따라서 `from raenim import *`는 다음까지 쏟아낸다:

`zeros`, `ones`, `eye`, `randn` (numpy 동명 함수와 혼동), `random`, `pnoise1`, `imread`, `resize`, `Path`, `Union`, `Any`, `Sequence`, `_AnimationBuilder`, `wiggle_shift`, `anticipation_rate`

특히 `Path`가 덮어씌워지므로, 씬 파일에서 `pathlib.Path`가 필요하면 `from pathlib import Path`를 **raenim import 뒤에** 다시 쓴다. `randn` 같은 이름도 numpy 것을 기대하고 쓰면 다른 게 나온다 — `np.random.randn`으로 명시할 것.
