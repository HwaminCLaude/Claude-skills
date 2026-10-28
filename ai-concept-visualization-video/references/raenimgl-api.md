# raenimgl API 요약

raenimgl 커밋 `089d4ffec3cae45877cecd68ab143a5ab47190b3` 소스(설치된 raenimgl 패키지, 또는 `scripts/fetch_examples.py`로 받은 `example_corpus/raenimgl/`)에서 옮긴 실제 시그니처다. `from raenimgl import *`로 쓰며, 키트 `vizkit.py`가 다시 내보낸다.

## 씬

### `class Scene2D(LiveSound, Scene, RaenimScene)` — `scene.py`

참고 코퍼스 씬 기본형은 `class X(InteractiveScene, Scene2D)`다. 키트의 `CueScene`도 이 둘을 상속한다.

| 멤버 | 시그니처 | 동작 |
|---|---|---|
| `cf` | property → `self.frame` | 카메라 프레임. `self.cf.animate.shift/move_to/scale/reorient(...)`, `self.cf.save_state()` → `Restore(self.cf)` |
| `playw` | `playw(self, *args, wait=1, **kwargs)` | `self.play(*args, **kwargs)` 다음 `self.wait(wait)`. 인자가 제너레이터 하나면 풀어서 재생 |
| `playwl` | `playwl(self, *args, lag_ratio=0.05, wait=1, **kwargs)` | `playw(LaggedStart(*args, lag_ratio=lag_ratio), wait=wait)` |
| `playwlfin` | `playwlfin(self, *mobjects, **kwargs)` | 객체마다 `FadeIn`을 만들어 `playwl` |
| `addw` | `addw(self, *args, wait=1, **kwargs)` | `self.add` 다음 `self.wait(wait)` |
| `playw_return` | `playw_return(self, *args, **kwargs)` | `rate_func=there_and_back`으로 `playw`(갔다가 돌아옴) |
| `play_camera` | `play_camera(self, to=ORIGIN, scale=1, **play_kwargs)` | `self.frame.animate.move_to(to).scale(scale)` |
| `clear` | `clear(self)` | 모든 객체 updater 제거 후 한 박자에 전부 FadeOut(`playw`라 1초 대기 포함) |
| `overlay` | property → `Overlay` | 현재 객체 전체를 buff 0.5로 덮는 막(처음 부를 때 만든다). 앞에 둘 대상은 `set_z_index(ol.z_index + 1)` |
| `all_but` | `all_but(self, *mobjects)` | 주어진 것을 뺀 화면 객체 목록(VGroup은 펼친다) |
| `mobjects_` | property | 빈 `Mobject`를 뺀 화면 객체 목록 |
| `to_front` | `to_front(self, *mobjects)` | `bring_to_front` |
| `mouse`, `point_mouse_to` | — | 마우스 SVG 소품(에셋 `assets/mouse.svg` 필요) |

**큐 블록 안에서 주의**: `playw`, `playwl`, `addw`, `clear`는 기본으로 1초를 더 기다린다. `with self.cue(id):` 안에서는 `self.play(...)`를 쓰거나 `wait=0`을 준다. 남는 시간은 `CueScene`이 큐 끝에서 채운다. 그렇지 않으면 `CUE_OVERRUN`이 난다.

`playw`, `playwl`, `playwlfin`, `clear`, `play_camera`는 안에서 `self.play`를 부른다. 그래서 `CueScene`이 큐마다 세는 박자 수(cuelog `plays`)에 들어간다. `addw`와 `wait`는 박자가 아니다(`plays` 0인 큐는 `render.py`가 `WARN CUE_NO_BEAT`).

### `class Scene3D(LiveSound, ThreeDScene, RaenimScene)`

`set_camera(theta, phi, gamma, zoom)`, `tilt_camera_horizontal(degree, zoom=1.0)` 등이 있다. 이 스킬은 쓰지 않는다. GL에서는 `Scene2D`의 `self.frame`도 `reorient`로 3D 기울이기가 된다(`structure`).

### 사운드 `LiveSound.add_sound(self, sound_file, time_offset=0, gain=None, gain_to_background=None)`

`-w` 렌더에서는 ManimGL 기본 동작대로 파일에 넣는다. 이 스킬의 TTS 모드는 씬 안 `add_sound`를 쓰지 않고 `assemble.py`가 cuelog 시각에 음성을 놓는다.

## 글자 — `text.py`

| 클래스 | 시그니처 | 메모 |
|---|---|---|
| `Words(Text)` | `Words(text: str, **kwargs)` | `.words` → 공백으로 나눈 낱말별 `VGroup`. 설명 카드에서 `self.playwl(*[FadeIn(w) for w in t.words], lag_ratio=0.5)` |
| `TextBox(VGroup)` | `TextBox(text, text_kwargs={"font_size": 24, "color": WHITE}, box_kwargs={"color": WHITE, "fill_color": BLACK, "fill_opacity": 0.75, "buff": 0.1}, **kwargs)` | `.text`, `.box`. 기본이 흰 테두리 상자라 테두리 상자 수(`T10`)에 들어간다 |
| `TexBox(VGroup)` | `TexBox(*text, tex_kwargs=..., box_kwargs=..., **kwargs)` | `.tex`, `.box` |
| `CodeText(Text)` | `CodeText(text, font_size=24, font=MONO_FONT)` | 한 줄 코드 |
| `ListText(VGroup)` | `ListText(*texts, font_size=48, color=WHITE, arrange=RIGHT, no_bracket=False, **kwargs)` | `[a b c]` 모양 |

`MONO_FONT`(`utils.py`)는 Windows에서 `"Consolas"`다. `MOCK = int(interactive())`는 `-w` 렌더에서 0이다.

## 코드 소품 — `script.py`

| 클래스 | 시그니처 | 메모 |
|---|---|---|
| `PythonCode(VGroup)` | `PythonCode(filename: str, font_size=24, font=None, language="python", code_style="monokai", lsh=None, **kwargs)` | 파일을 읽어 그린다. `.frame`(GREY_E 0.3 면, 테두리 0), `.code`, `get_lines()`, `find_text(line_no, text, nth=1)`, `text_slice(...)`, `highlight(line_no, text=None, nth=1, anim=Write, color="#FFFF00", anim_out=FadeOut)` → (들어올 애니, 나갈 애니) |
| `rCode(VGroup)` | `rCode(code=None, filename=None, font_size=24, font=None, language=None, code_style="monokai", lsh=1.25, frame_buff=0.3, **kwargs)` | 문자열로도 만든다. `rc.ls[i]`(0부터 줄), `rc.ls[i][j]`(공백 뺀 글자), `get_lines(start, end)`, `find_text(line, text, nth)`, `find_all_text(text)`, `text_slice(...)`, `all_text_slices(text)`, `highlight(line, text=None, ...)` |

- `highlight`의 기본 색 `#FFFF00`은 노랑이다. 노랑은 자막 전용이므로 `color=OBJ[0]` 같은 토큰을 넘긴다.
- 코드 소품의 글자는 `prop`으로 보고 화면 글자 셈(§밀도)에서 뺀다.

## 도형과 소품 — `mobject.py`, `matrix.py`, `nn.py`, `coordinates.py`, `filesystem.py`, `git.py`

| 이름 | 시그니처 | 메모 |
|---|---|---|
| `Overlay(Rectangle)` | `Overlay(*args, stroke_width=0, color=BLACK, fill_opacity=0.7, **kwargs)` | `.surround_mobjects(mobjects, buff=0.5)`, `.to_front(mobjects)`, `.update_coverage(mobjects, buff=0.5)`. 이 스킬은 0.75를 쓴다(`OVERLAY_OPACITY`) |
| `Chainer(VGroup)` | `Chainer(*args, chain_type="plain", chain_kwargs={"buff": 0}, **kwargs)` | 객체를 차례로 선(`plain`/`dashedline`/`arrow`)으로 잇는다 |
| `Joiner(VGroup)` | `Joiner(*args, join: callable, **kwargs)` | 사이에 `join()` 객체를 끼운다 |
| `PixelImage(VGroup)` | — | 픽셀 격자 |
| `zeros/ones/eye/randn(DecimalMatrix)` | `randn(*shape, **kwargs)` 등 | `.val`로 numpy 값. lora1에서 `randn(7, 7)`로 가중치 행렬을 그렸다 |
| `Mat` | `Mat.zeros(*shape)`, `Mat.ones`, `Mat.eye(n)`, `Mat.randn(*shape)` | 위 클래스의 정적 생성기 |
| `Tensor(VGroup)` | `Tensor(dim: int, shape="square", arrange=DOWN, buff=MED_SMALL_BUFF*0.4, ellipsis=False)` | 칸 벡터. `.to_numbers(numbers=None, font_size=18)` |
| `Linear` | `Linear(in_channels: int, out_channels: int)` → `VGroup(in_layer, weights, out_layer)` | 완전연결 층 그림 |
| `MLP` | `MLP(*dims, layer_distance=3)` | 여러 층. 층 색이 `random_color()`라 `seed(41)`을 반드시 둔다 |
| `forward_prop/backward_prop` | `forward_prop(mlp, scene_instance=None, run_time=0.3)` | 신호 흐름 애니메이션 |
| `RaenimPlane(NumberPlane)` | `RaenimPlane(x_range=(-5, 5, 1), y_range=(-4, 4, 1), ...)` | `.markc(x, y, tick=True, line=True)` 좌표 표시 |
| `RaenimLine(NumberLine)` | `RaenimLine(**kwargs)` | 수직선 |
| `FileSystem`, `Folder`, `File`, `FileIcon`, `FolderIcon` | — | 파일 트리 소품 |
| `new_commit`, `branch` | `branch(start=None, *, direction=RIGHT, n_commits=3, buff=1)` | git 그래프 소품 |

## 애니메이션 — `animation.py`

| 이름 | 시그니처 | 메모 |
|---|---|---|
| `RWiggle(Animation)` | `RWiggle(mobject, amp=None, speed=None, phase=None, pow=8, ...)` | 펄린 노이즈로 흔들고 제자리로 |
| `AMove(Transform)` | `AMove(mobject, target_point, anticipation_amount=0.1, anticipation_ratio=0.4, run_time=1.5, **kwargs)` | 살짝 뒤로 갔다가 이동. 큐 안에서는 `run_time=1.0` 이하로 |
| `Transformr(Transform)` | `Transformr(mobject, target)` | 끝나면 장면 안 객체를 target으로 바꿔 둔다 |
| `AnchorToPoint` | `AnchorToPoint(group, dest, anchor)` → `group.animate.shift(...)` | 묶음 안 한 점을 목적지에 맞춘다 |
| `SkewedAnimations(list)` | `SkewedAnimations(*animations)` | 여러 애니메이션 열을 어긋나게 겹친다 |
| `Marking(AnimationGroup)` | `Marking(mobject, buff=MED_SMALL_BUFF, color=YELLOW, run_time=1, ...)` | 빛나는 테두리가 나타났다 사라짐. 노랑 기본이니 color 토큰을 넘긴다 |
| `Create` | `Create(mobject)` | `ShowCreation` 별칭 |
| `Circumscribe` | `FlashAround` 별칭 | 순간 강조 |

## 기타

- `align(source, target, direction, buff=...)`(`functions.py`): `source`를 `target` 안쪽 `direction` 변에 붙인다. 모든 Mobject에 `.align(...)` 메서드로 붙어 있어 `.animate.align(...)`도 된다.
- `raenim_colors(nums, hue_spread=45)`(`colors.py`): PEACH/COBALT 두 극 사이 색 목록. hex 색이라 이 스킬에서는 쓰지 않는다(OBJ 토큰 사용).
- `MINT`, `X_STRING "✘"`, `CHECK_STRING "✔"`(`constant.py`): `✘ ✔`는 Noto Sans KR에 없다. 쓰지 않는다.
- `Logo`: 원작 채널 로고. 쓰지 않는다(린트 `T9` ERROR).
- `__init__.py`는 MiKTeX 호환을 위해 ManimGL의 `full_tex_to_svg`를 고쳐 끼운다(`latex`에는 `-no-pdf`를 주지 않는다). raenimgl을 import하지 않고 Tex를 쓰면 MiKTeX에서 실패할 수 있다.

## 키트 `vizkit.py`가 더하는 것(raenimgl 아님)

씬 코드는 `from vizkit import *` 하나로 위 raenimgl 이름과 아래 키트 이름을 함께 쓴다. 자세한 동작은 키트 docstring을 본다.

| 이름 | 시그니처 | 동작 |
|---|---|---|
| `FS`, `TEXT_SCALE`, `TEX_FS` | `FS = {"S": 20, "M": 24, "T": 26, "L": 32, "XL": 40}`, `TEXT_SCALE = 1.44`, `TEX_FS = FS × 1.5` | FS는 설계 크기. Text는 `FS × TEXT_SCALE`, Tex는 `TEX_FS`로 그린다(`design-system.md`) |
| `label` | `label(text, size="M", color=TEXT, *, prop=False)` | Noto Sans KR. `prop=True`는 극 안 문장(채팅, 화면 속 UI) 린트 표지, 화면 효과 없음 |
| `title`, `source`, `mono` | `title(text)`, `source(text)`, `mono(text, size="M")` | 좌상단 제목(T), 출처(Noto Serif KR S, TEXT_2), 코드 글자(Consolas) |
| `tex` | `tex(*parts, size="L", color=TEXT, **kwargs)` | `Tex(*parts, font_size=TEX_FS[size])`. 조각 고르기 `m["BA"].set_color(OBJ[1])`. `t2c={"BA": OBJ[1]}`도 된다(color를 칠한 뒤 다시 입힌다). `size`는 키워드 전용이다: `tex("W_0", "L")`은 `W_0L`을 그린다 |
| `tint` | `tint(mob, color, opacity=0.3)` | 테두리 없는 반투명 면 |
| `dim_others`, `undim` | `dim_others(scene, keep, opacity=DIM) -> list`, `undim(scene) -> list` | 애니메이션 목록 → `self.play(*...)`. `undim`은 장면에 남은 객체만 되돌린다 |
| `dimmed` | `dimmed(mob, k=DIM, scene=None) -> mob` | 바로 k배로 흐림(애니메이션 아님). `scene=`이면 `undim`이 되돌린다 |
| `focus_cover` | `focus_cover(card, keep) -> VGroup` | 카드에서 keep 밖을 덮는 BLACK 띠 4개(재생 안 함) |
| `stand_up`, `lay_down` | `stand_up(mob, phi=60)`, `lay_down(mob, phi=60)` | RIGHT축 ±phi° 회전. 객체면 바로, `mob.animate`면 애니메이션 빌더 |
| `CueScene.cue` | `with self.cue(id):` | 큐 길이까지 기다림, cuelog에 `start`, `dur`, `elapsed`, `plays`. id가 timing.json에 없으면 `CueNotFound`(원인과 있는 큐 id를 적음) |
| `CueScene` 카메라 | `zoom_in(target, scale=0.4, run_time=1.0)`, `zoom_out(run_time=1.0)`, `pan_to(target, run_time=1.0)`, `tilt(center, phi=60, height=None, run_time=1.0)`, `untilt(run_time=1.0)` | 직접 재생. zoom_in/tilt는 카메라 상태 스택에 쌓고 zoom_out/untilt가 꺼낸다 |
| `CueScene.orbit` | `orbit(degrees) -> 애니메이션` | `tilt` 안에서 카메라 `increment_theta`. 재생하지 않고 돌려주므로 다른 애니메이션과 한 `play`에 넣는다 |
| `CueScene` 흐름 | `carry(group, edge=LEFT, scale=0.6, run_time=1.0)`, `aside(group, angle_deg=80, direction=LEFT, run_time=1.0)`, `clear_to(keep, run_time=0.6)` | 직접 재생 |
| `CueScene.quote_card` | `quote_card(image_path, run_time=1.0) -> Group(덮개, 카드)` | 뒤를 BLACK 0.75로 덮고 카드를 오른쪽에서 들인다 |
| `CueScene.quote_focus` | `quote_focus(card, keep=None, cover=None, run_time=0.6) -> VGroup` 또는 `None` | 카드 나머지를 덮개로 가림(직접 재생). `cover`를 주면 그 덮개를 Transform, `keep=None`이면 FadeOut |
