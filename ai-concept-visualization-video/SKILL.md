---
name: ai-concept-visualization-video
description: AI 개념 시각화 스타일(ManimGL + raenimgl)의 한국어 AI 설명 영상을 만든다. 논문, 모델, 코드, 주제 설명을 받아 자막 큐 대본(shots.json)을 쓰고, 큐마다 박자가 있는 ManimGL 씬을 렌더한 뒤 하단 자막을 구워 mp4까지 뽑는다. 검정 배경, 토큰 디자인, 흐름 문법(확대, 카메라 이동, 3D 기울이기, 이어받기, 논문 인용 카드)을 쓴다. 사용자가 "AI 개념 시각화 영상 만들어줘", "AI concept visualization video", "AI 설명 영상 만들어줘", "논문을 manim 영상으로", "이 모델 구조를 manim 영상으로", "코드를 manim 영상으로 설명", "ManimGL 영상"이라고 할 때 사용한다. 시험 대비용 손계산 영상이 아니다. 손계산, 숫자 대입 워크스루, ManimCE 교육 영상은 paper-to-manim-video를 쓴다.
---

# ai-concept-visualization-video

ManimGL 포크와 raenimgl을 바탕으로, AI 관련 설명 영상(논문, 모델, 코드)을 AI 개념 시각화 스타일로 만든다. 산출물은 **대본(`shots.json`) + 씬 코드(`main.py`) + 자막이 박힌 `<episode>_FINAL.mp4`** 한 벌이다.

핵심은 두 가지다.
1. **자막 큐가 박자 단위다.** 큐(1줄, 약 2초)마다 연출(`move`)이 1개 이상 있어 화면이 약 2초마다 움직인다. 슬라이드처럼 멈춰 있지 않는다.
2. **디자인이 깔끔하다.** 검정 배경, 토큰 색·크기, 면으로 칠하는 강조, 짧은 명사 라벨. 화면 글자가 AI가 쓴 문서처럼 보이지 않는다.

사용자에게는 한국어로 답한다. 코드 식별자는 영어, 자막·라벨은 한국어.

## 스킬 폴더

`SK` = 이 SKILL.md가 있는 폴더(`C:\Users\<user>\.claude\skills\ai-concept-visualization-video`).

| 경로 | 내용 |
|---|---|
| `scripts/scaffold.py` | 프로젝트·에피소드 폴더 만들기(`--mode` 기본 `tts`, 무음은 `silent`) |
| `scripts/setup_env.py` | `uv sync`로 환경 만들기(PATH에 `uv` 필요) |
| `scripts/fetch_examples.py` | (선택) 연출 예시 코퍼스를 원본 공개 저장소의 고정 커밋에서 받아 `references/example_corpus/`에 둔다(git 필요) |
| `scripts/preflight.py` | 파이썬, import, ffmpeg libass, LaTeX, 캔버스 글꼴, 자막 글꼴(`capfont`) 검사 |
| `scripts/parse_paper.py` | 논문 PDF → `--out` 폴더에 `paper.json`(+`paper.txt`) |
| `scripts/parse_code.py` | 노트북(.ipynb)·.py 파일·소스 폴더 → `--out` 폴더에 `codebase.json`(+`code.txt`) |
| `scripts/crop_figure.py` | 논문 그림을 PNG로 자르기 |
| `scripts/tts.py` | 큐마다 edge-tts 음성 합성 → `tts\<id>.mp3`, `tts\durs.json`(tts 모드) |
| `scripts/cues.py` | 큐 길이 계산 → `timing.json` |
| `scripts/lint.py` | 씬 코드·큐 규칙 검사 + 편 통계(`stats:` 줄) |
| `scripts/render.py` | 씬 렌더(병렬, 오류 분류, 큐 초과·박자 없는 큐 보고) |
| `scripts/captions.py` | ASS 자막 만들기(`assemble.py`가 부른다) |
| `scripts/assemble.py` | 씬 이어 붙이기 + 자막 굽기(+ tts 모드 음성 배치) |
| `scripts/measure_motion.py` | 박자 측정(A1) |
| `scripts/measure_design.py` | 디자인 측정(A2) |
| `scripts/sweep_frames.py` | 3×3 프레임 시트 |
| `assets/project_template/` | `pyproject.toml`, `custom_config.yml`, `vizkit.py`(키트), `main_template.py` |
| `references/` | 아래 표 |

| 참고 문서 | 언제 읽나 |
|---|---|
| `references/shots-schema.md` | 3단계 대본을 쓰기 전 |
| `references/narration-voice.md` | 3단계 자막 문장을 쓸 때 |
| `references/captions.md` | 3단계, 7단계 자막 모양과 핵심어 |
| `references/flow-grammar.md` | 3단계 `rel`·`move`를 달 때, 4단계 씬을 짤 때(코퍼스 `파일:줄` 색인) |
| `references/design-system.md` | 4단계 색·크기·배치·강조 |
| `references/onscreen-text.md` | 4단계 캔버스 글자 쓰기(고쳐 쓰기 예시) |
| `references/raenimgl-api.md` | 4단계 raenimgl API 시그니처 |
| `references/troubleshooting.md` | 렌더·환경 오류가 날 때 |
| `references/example-corpus.md` | 예시 코퍼스(장면 코드 33편 + raenimgl 소스) 받는 법·출처·찾아보는 법. 받기 전에는 `references/example_corpus/`가 없다 |

## 실행 파이썬

- 0단계의 `scaffold.py`, `setup_env.py`는 아무 파이썬(`python`)으로 돌린다.
- 그 뒤 모든 스크립트는 **프로젝트 venv 파이썬**(`<proj>\.venv\Scripts\python.exe`, 이하 `PY`)으로 돌린다. PyMuPDF, fontTools, OpenCV가 거기 있다.
- 프로젝트 루트는 ASCII 경로(`C:\manimwork\<slug>`)로 둔다. 에피소드 폴더는 `<proj>\<episode>`다.
- 아래 명령의 경로는 모두 따옴표로 감싼다(사용자 폴더에 한글이 있다).

---

## 작업 흐름

### 0. 준비

준비물(없으면 사용자에게 설치를 부탁한다):
- **`uv`**: PATH에 있어야 한다. `setup_env.py`가 PATH의 `uv`로 `uv sync`를 돌리고, 없으면 `FAIL uv not found on PATH`로 멈춘다. 설치: https://docs.astral.sh/uv/ . Python 3.10.18은 uv가 내려받는다. tts 모드에서 `tts.py`도 uv 임시 환경을 쓸 수 있다.
- **git**: `uv sync`가 ManimGL 포크·raenimgl을 GitHub에서 받을 때, `fetch_examples.py`가 예시 코퍼스를 받을 때 필요하다.
- ffmpeg·ffprobe(libass `subtitles` 필터 포함), LaTeX(MiKTeX: `latex`, `dvisvgm`, Tex 수식용).
- 글꼴: Noto Sans KR(캔버스), 정적 Noto Sans KR Medium(`NotoSansKR-Medium.ttf`, 자막). Noto Serif KR, Consolas는 있으면 좋다.

```powershell
python "SK\scripts\scaffold.py" --root C:\manimwork\<slug> --episode <ep>                 # tts 모드(기본)
python "SK\scripts\scaffold.py" --root C:\manimwork\<slug> --episode <ep> --mode silent   # 무음 영상
python "SK\scripts\setup_env.py" --root C:\manimwork\<slug>
C:\manimwork\<slug>\.venv\Scripts\python.exe "SK\scripts\preflight.py" --root C:\manimwork\<slug>
```

- `scaffold.py`: 루트에 `pyproject.toml`, `custom_config.yml`, 에피소드 폴더에 `main.py`, `shots.json`(빈 스키마), `vizkit.py`를 만든다. 이미 있는 파일은 건너뛴다(`shots.json`이 이미 있으면 `--mode`도 반영되지 않는다).
- **모드 고르기**: 기본은 `tts`(edge-tts 음성 + 박힌 자막)다. 사용자가 무음 영상(자막만)을 원하면 `--mode silent`로 만든다. 나중에 바꾸려면 `shots.json`의 `"mode"`를 고치고 3단계부터 다시 한다.
- `setup_env.py`: `uv sync`(Python 3.10.18, manimgl 포크, raenimgl, av 등) 후 import를 확인한다.
- `preflight.py`: `PASS/WARN/FAIL` 줄을 찍는다. **FAIL이 0건이어야 다음으로 간다.** FAIL이면 `references/troubleshooting.md`를 보고 고친 뒤 다시 돌린다. `capfont` 줄은 자막 헤더 그대로 한 줄을 ffmpeg로 구워 libass가 `NotoSansKR-Medium`을 골랐는지 본다(가는 VF Thin이나 Arial로 바뀌면 FAIL).
- (선택) 연출 예시 코퍼스: `python "SK\scripts\fetch_examples.py"` — 원본 공개 저장소의 고정 커밋에서 장면 코드 33편과 raenimgl 소스를 `references/example_corpus/`로 받는다(git 필요, 이미 있으면 건너뜀). 4단계에서 `flow-grammar.md`의 `파일:줄`을 열어 볼 때 쓴다.

### 1. 입력

논문 PDF, 코드, 주제 설명 중 하나 이상을 받는다. 논문이면:

```powershell
PY "SK\scripts\parse_paper.py" --pdf <proj>\paper\<name>.pdf --out <proj> --dump-text
PY "SK\scripts\crop_figure.py" --pdf <proj>\paper\<name>.pdf --list --pages 1-8
PY "SK\scripts\crop_figure.py" --pdf <proj>\paper\<name>.pdf --page <n> --bbox x0,y0,x1,y1 --out <proj>\<ep>\assets\fig1.png
```

- `parse_paper.py`의 `--out`은 프로젝트 루트다. 그 폴더에 `paper.json`(절 목록 등)이 생기고, `--dump-text`면 `paper.txt`(쪽별 본문)도 생긴다. 폴더가 없으면 만든다.
- 그림은 논문의 실제 그림만 쓴다. 이미지 생성은 쓰지 않는다.
- 벡터 그림은 `--list`에 안 나온다. `--bbox`로 영역을 렌더한다(PDF 포인트, 좌상단 원점).

코드(노트북, .py 파일, 소스 폴더)면:

```powershell
PY "SK\scripts\parse_code.py" --input <proj>\code\<name>.ipynb --out <proj> --dump-text
PY "SK\scripts\parse_code.py" --input <proj>\code\src --out <proj>          # .py 소스 폴더
```

- `--input`은 `.ipynb` 파일, `.py` 파일, 소스 폴더 중 하나다. `--out`(프로젝트 루트)에 `codebase.json`이 생긴다. 노트북 마크다운 제목(구간 경계), 함수·클래스 정의, import, 데이터 흐름 지점(셀 출력의 `torch.Size`, `# (B, T, D)` 같은 shape 주석, `reshape`·`view`·`cat` 등 shape가 바뀌는 호출)이 들어 있다. `--dump-text`면 셀 원문과 출력 앞부분을 `code.txt`로도 쓴다.
- 표준 라이브러리만 쓰므로 아무 파이썬으로 돌려도 된다.
- 코드 영상은 shape가 바뀌는 지점을 씬 경계 후보로 삼고, 화면의 코드는 `mono()`로 짧게 보여 준다(소품).

### 2. 편성 — 사용자 확인 1회

- 기본은 3~6분 1편이다. 사용자가 "짧은 영상"이라 하면 1분 30초~2분 30초.
- 씬(구간) 목록을 정한다. 씬 하나 = `CueScene` 클래스 하나 = 이야기 한 덩어리.
- 첫 60초(짧은 편은 30초) 안에 `hook`. `structure`(3D)는 편당 1~2회(짧은 편 1회).
- 씬 이름, 구간마다 보여 줄 그림, 예상 길이를 표로 보여 주고 확인을 받는다.

### 3. 대본 `shots.json` — 사용자 검토 1회

`references/shots-schema.md`대로 쓴다. 큐마다 `id`, `t`, `say`, `key`, `rel`, `move`, `hold`.

- 말투는 `references/narration-voice.md`: **습니다체가 기본**(문장 끝의 45~65%)이고, 2~3문장마다 확인 '~죠?'나 질문 '~까요?'로 끊는다. 습니다체는 4문장까지만 잇는다. 질문 15% 이상, '~죠' 10~20%. 해요체('~요')는 '~고요', '~거든요'처럼 짧게 섞을 때만 쓴다. 1인칭 없음, 문어 연결어미 금지.
- `rel`은 12개 중 하나(`detail next structure carry aside change build point new hook quote chapter`). 같은 `rel`이 4큐 넘게 이어지지 않게 한다. 뜻은 `references/flow-grammar.md`.
- 대본 비율은 린트의 편 통계로 확인한다. 요약 두 줄은 stderr로 나오므로 `2>&1`로 함께 받는다.

```powershell
PY "SK\scripts\lint.py" --episode <proj>\<ep> 2>&1
```

- 마지막 줄 `stats: cues=<n> sentences=<n> len_max=<자> len_median=<자> key=<%> question=<%> jyo=<%> supnida=<%> supnida_run=<n> canvas_hangul_per_min=<자|->`를 본다. 목표는 `key` 10~30%, `question` 15% 이상, `jyo` 10~20%, `supnida` 45~65%, `supnida_run` 4 이하, `len_median` 15~20자, `len_max` 26 이하. `key`는 큐 단위, `question`·`jyo`·`supnida`는 문장 끝 큐(쉼표 없이 어미나 물음표로 끝나는 큐) 단위로 센다.
- 벗어나면 `WARN E1`(key)·`E2`(질문)·`E3`(죠)·`E4`(습니다체)·`E8`(습니다체 5연속)이 나온다. E1은 큐가 10개 이상, E2~E4는 문장 끝 큐가 8개 이상일 때만 낸다. `WARN E5`는 1인칭(저는, 제가, 우리 등)이 든 큐다. `len_median`은 WARN 없이 통계로만 나온다.
- 이 단계에서는 씬 코드가 아직 없어서 큐마다 `ERROR C6 <id> 씬 코드에 self.cue(...)가 없음`이 나오고 exit 1이다. 정상이다(4단계에서 씬 코드를 쓰면 사라진다). C6 말고 C1~C4, C7 ERROR와 C5(같은 `rel` 4큐 초과) WARN은 지금 고친다.
- 그다음 큐 길이를 계산한다. **모드에 따라 순서가 다르다.**
  - tts 모드(기본): 3.6의 `tts.py`를 먼저 돌리고 `cues.py`를 돌린다(`tts\durs.json`이 없으면 `cues.py`가 FAIL).
  - silent 모드: 바로 `cues.py`를 돌린다(글자 수 공식).

```powershell
PY "SK\scripts\cues.py" --episode <proj>\<ep>
```

- `timing.json`이 생기고 씬별 길이와 총길이가 찍힌다. 총길이가 2단계 목표 안인지 본다.
- `WARN rate`가 찍힌 큐는 쪼갠다.
- 큐 목록(씬, `t`, `key`, `rel`, 길이)을 사용자에게 보여 주고 검토를 받는다.

### 3.6 음성(tts 모드, 기본)

- `mode: "tts"`가 스킬 기본값이다(`scaffold.py`가 이 값으로 `shots.json`을 만든다). 큐마다 `say`(없으면 `t`)를 edge-tts로 합성해 실측 길이를 큐 길이로 쓴다. silent 모드면 이 단계를 건너뛴다.
- 순서: 대본 확정 → **음성 합성** → **그다음** `cues.py`(실측 길이로 `timing.json`) → 4단계 씬 작성·렌더.

```powershell
PY "SK\scripts\tts.py" --episode <proj>\<ep>
PY "SK\scripts\cues.py" --episode <proj>\<ep>
```

- `scripts/tts.py`: `tts\<id>.mp3`와 `tts\durs.json`(`{id: 초}`)을 만든다. 목소리 기본값은 `ko-KR-HyunsuMultilingualNeural`(`--voice`로 바꾼다). 네트워크가 필요하다(키는 필요 없다).
- 대본을 고친 뒤 다시 돌리면 **문장이 바뀐 큐만** 다시 합성한다(`tts\.cache.json`에 합성 입력을 적어 둔다). 전부 다시 만들려면 `--force`.
- 프로젝트 venv에 edge-tts가 없으면 `tts.py`가 uv 임시 환경(`uv run --no-project --with edge-tts`)으로 스스로 다시 실행한다. venv에 넣고 싶으면 `uv pip install --python PY edge-tts`.
- 자막에는 `t`, 음성에는 `say`가 쓰인다. 발음 표기('로라')는 `say`에만 적는다.

### 4. 씬 코드 `main.py`

`main.py`는 시작 틀(`from vizkit import *`, `seed(41)`, `np.random.seed(41)`)을 그대로 두고 씬 클래스를 `shots.json` 씬 이름으로 쓴다.

```python
class Freeze(CueScene):
    def construct(self):
        with self.cue("c010"):            # rel=build
            w = Square(2.0).set_fill(OBJ[0], 0.7).set_stroke(width=0)
            self.play(FadeIn(w, shift=UP * 0.25), run_time=0.8)
        with self.cue("c011"):            # rel=point
            self.play(*dim_others(self, [w]), run_time=0.6)
        with self.cue("c012"):            # rel=detail
            self.zoom_in(w, scale=0.4)
        with self.cue("c013"):
            self.zoom_out()
```

- **키트(`vizkit.py`)만 쓴다.**
  - 토큰: `BG`, `PANEL`, `OVERLAY_OPACITY`, `TEXT`, `TEXT_2`, `LINE`, `ARROW`, `DIM`, `OBJ[0..3]`, `FS`, `TEXT_SCALE`, `TEX_FS`, `BUFF`, `CAPTION_SAFE_Y`, `CONTENT_X`, `CONTENT_X_WIDE`, `CUE_OVERRUN_TOL`.
  - **글자 크기**: `FS = {S:20, M:24, T:26, L:32, XL:40}`는 설계 크기다. 키트가 Text에 `TEXT_SCALE`(1.44)을 곱해 그리고, Tex는 `TEX_FS`(= FS×1.5, S 30 · M 36 · T 39 · L 48 · XL 60)로 그린다. **`main.py`에서 `.scale(1.44)`나 `font_size=FS[..]*k`처럼 배율을 또 곱하지 않는다**(글자가 두 번 커진다). 크기는 토큰 이름(`"S"`~`"XL"`)으로만 고른다.
  - 글자: `label(text, size="M", color=TEXT, *, prop=False)`, `title(text)`, `source(text)`, `mono(text, size="M")`.
    - `prop=True`는 화면 효과 없는 린트 표지다. 채팅 프롬프트, 화면 속 UI처럼 일부러 넣은 극 안 문장(`label("요약해 줘", "S", prop=True)`)에만 쓴다. T1(종결형), T5(8자), E6(분당 글자)에서 빠진다.
  - 수식: `tex(*parts, size="L", color=TEXT, **kw)` → `Tex(*parts, font_size=TEX_FS[size])`. `Tex(..., font_size=...)`를 직접 쓰지 않는다.
    - 예: `tex("W_0")`, `tex(r"35\,\text{MB}", size="M", color=OBJ[2])`, `m = tex("W_0", "+", "BA"); m["BA"].set_color(OBJ[1])`.
    - **`size`는 키워드 전용이다.** `tex("W_0", "L")`은 `W_0L`을 그린다.
  - 강조(애니메이션 목록을 돌려준다 → `self.play(*...)`): `dim_others(self, keep)`, `undim(self)`. `tint(mob, color)`는 틴트 객체를 돌려준다.
    - `undim(self)`는 지금 장면에 남은 객체만 되돌린다. 그 사이 FadeOut한 객체를 되살리지 않는다.
    - `dimmed(mob, k=DIM, scene=None)`: 애니메이션 없이 바로 흐린다(앞 씬 끝 화면을 흐린 채 이어받을 때). `self.add(dimmed(ctx, scene=self))`처럼 `scene=self`를 주면 나중 `undim(self)`가 되돌린다.
  - 흐름 헬퍼(직접 재생): `zoom_in`/`zoom_out`(detail), `pan_to`(next), `tilt`/`untilt`(structure), `carry`(carry), `aside`(aside), `quote_card`(quote, hook), `quote_focus`(quote, point), `clear_to`(new, chapter).
  - 세우기·궤도(재생하지 않고 돌려준다 → `self.play(...)`): `stand_up(m.animate)`, `lay_down(m.animate)`(반대로 눕히기), `self.orbit(degrees)`(카메라 θ 돌리기, `tilt` 안에서만, `untilt()`가 되돌린다). 예: `self.play(*[lay_down(m.animate) for m in front], self.orbit(-14), run_time=0.9)`.
  - **인용 카드 강조는 `quote_focus`로 한다.** 밝은 논문 그림 카드는 `zoom_in`으로 확대하지 않는다(확대하면 카드가 자막 띠를 덮는다). `quote_focus`는 keep 밖을 검정 덮개(`OVERLAY_OPACITY`)로 가리고 덮개를 돌려준다.
    - `keep`은 카드 안 비율 상자 `(x0, y0, x1, y1)`(`(0, 0)` = 왼쪽 위)나 Mobject다.
    - 돌려받은 덮개를 다시 넘기면 초점을 옮긴다. 덮개는 장면에 따로 올라가므로 카드를 치울 때 함께 FadeOut한다(`clear_to`는 함께 치운다).

    ```python
    q = self.quote_card("assets/fig1.png"); card = q[1]
    cov = self.quote_focus(card, (0, 0, 0.53, 1), run_time=0.6)   # 왼쪽만 남김
    cov = self.quote_focus(card, (0.5, 0, 1, 1), cov, run_time=0.8)  # 오른쪽으로 옮김
    self.play(FadeOut(q), FadeOut(cov))
    ```
  - `with self.cue(id)`의 id가 `timing.json`에 없으면 `CueNotFound`(원인과 있는 큐 id를 적음)가 난다. `shots.json`을 고친 뒤 `cues.py`를 다시 돌린다.
- `rel`별 연출과 참고 예시는 `references/flow-grammar.md`, 디자인은 `references/design-system.md`, 캔버스 글자는 `references/onscreen-text.md`, raenimgl API는 `references/raenimgl-api.md`. 원본 장면은 `references/example_corpus/`에서 `파일:줄`로 찾아 본다(없으면 `scripts/fetch_examples.py`로 먼저 받는다).
- 논문 그림은 `self.quote_card("assets/fig1.png")`(에피소드 폴더 기준 상대 경로).

### 5. 린트 + 스모크 렌더

```powershell
PY "SK\scripts\lint.py" --episode <proj>\<ep>
PY "SK\scripts\render.py" --episode <proj>\<ep> --quality l
```

- `lint.py`: stdout에 `ERROR|WARN <rule> <where> <msg>` 줄만 찍는다. **ERROR 0건(exit 0)이어야 렌더로 간다.**
  - 규칙: T1~T10(씬 글자), C1~C8(큐), E1~E8(편 통계, 모두 WARN: E1 key 비율, E2 질문, E3 '~죠', E4 습니다체 45~65%, E5 1인칭, E6 캔버스 해설 한글 분당 20자 초과, E7 자막과 캔버스 글자 4낱말 겹침, E8 습니다체 5연속).
  - 요약 두 줄 `lint: ERROR n, WARN n`과 `stats: ...`는 stderr로 나온다(3단계 참고).
  - 한계: 변수로 넘긴 문자열(`label(name)`)과 키워드로 넘긴 문자열(`Text(text=...)`)은 검사하지 못한다. 화면 글자는 위치 인자 문자열로 쓴다.
- `render.py`: 씬마다 `-m manimlib main.py <S> -w -l`을 `--jobs 2`로 돌린다. 로그는 `<ep>\logs\render_<S>.log`. 보고 줄:
  - `OK <S> <렌더초>s video=<길이>s`
  - `FAIL <S> kind=<latex|font|attribute|import|other> <마지막 오류 줄>`
  - `WARN CUE_OVERRUN <S> <cue_id> <초과초>`
  - `WARN CUE_NO_BEAT <S> <cue_id>`: 큐 블록 안에서 `self.play`가 0번인 큐(박자 없는 큐). `wait`, `add`는 박자로 세지 않고, `playw`·키트 흐름 헬퍼는 센다.
  - `SUMMARY ok=<n> fail=<n> overrun=<n> no_beat=<n> logs=<경로>`
- `CUE_OVERRUN`이 나오면 그 큐의 `run_time`을 줄이거나 박자를 다음 큐로 옮긴다. `CUE_NO_BEAT`이 나오면 그 큐 블록에 박자(`self.play`)를 하나 넣는다. **둘 다 0건(`overrun=0 no_beat=0`)이 될 때까지 고친다.**
- 특정 씬만: `--scenes A,B`.

### 6. 본번 렌더

```powershell
PY "SK\scripts\render.py" --episode <proj>\<ep> --quality hd
```

1920×1080, 60fps(`custom_config.yml`). 렌더 전에 그 씬의 옛 mp4를 지우므로, 실패한 씬이 옛 영상으로 섞이지 않는다.

### 7. 합치기

```powershell
PY "SK\scripts\assemble.py" --episode <proj>\<ep>            # tts 모드: 음성 + 박힌 자막
PY "SK\scripts\assemble.py" --episode <proj>\<ep> --silent   # 무음 모드(또는 tts 모드 미리 보기)
```

- `shots.json` 씬 순서로 `videos\*.mp4`를 이어 `_scenes.mp4`, 씬 실제 길이를 `scene_durs.json`에 적는다.
- `scripts/captions.py`로 cuelog 실제 시각에 맞춘 `captions.ass`를 만들고 구워 `<episode>_FINAL.mp4`를 만든다.
- 굽기 로그로 자막 글꼴을 검사한다. libass가 `Noto Sans KR Medium`이 아닌 글꼴을 고르면 `FAIL`로 멈춘다(`preflight.py`의 `capfont`를 보고 고친다). Medium에 없는 글자를 대체 글꼴로 그리면 `WARN caption glyph ...`, 길이 0인 자막이 생기면 `WARN caption zero-length ...`가 찍힌다. 둘 다 고친다.
- 무음 모드는 `--silent`(음성 트랙 없음).
- tts 모드는 `--silent` 없이 부른다. 큐마다 `tts\<id>.mp3`를 cuelog 실제 시작 시각(자막과 같은 시각)에 놓아 `narration.wav`를 만들고(영상 길이에 맞춰 늘이거나 자른다), AAC 음성 트랙으로 넣는다. 자막은 `<episode>.srt`로도 따로 나온다.
- `WARN audio overrun <id>`가 찍히면 그 큐의 음성이 자기 자리보다 길다. 다음 큐 음성과 겹치므로 문장을 줄이거나 큐를 쪼개고, `tts.py` → `cues.py` → 렌더부터 다시 한다. mp3가 빠진 큐가 있으면 FAIL이다.

### 8. 측정, 프레임 스윕, 보고

```powershell
PY "SK\scripts\measure_motion.py" --video <proj>\<ep>\<ep>_FINAL.mp4
PY "SK\scripts\measure_design.py" --video <proj>\<ep>\_scenes.mp4
PY "SK\scripts\sweep_frames.py" --video <proj>\<ep>\<ep>_FINAL.mp4 --every 4 --out <proj>\<ep>\review
```

- `A1 PASS`(멈춤 중앙값 3초 이하, 5초 미만 멈춤 18% 이상), `A2 PASS`(배경 `#000000`, 자막 띠 침범 0, 테두리 상자 중앙값 0, 내용 폭·초점 덩어리 기준)를 확인한다. `measure_design.py`는 자막 없는 `_scenes.mp4`로 잰다.
- 시트를 **전부 눈으로 본다.** 두부(□), 겹침, 화면 밖 잘림, 자막 띠 침범을 찾는다.
- FAIL이나 결함이 있으면 고치고 5단계부터 다시 한다(최대 3회, 넘으면 남은 FAIL을 보고).
- 사용자에게 보고한다: FINAL 경로, 길이, 해상도·fps, 린트·측정 결과, 시트 경로, 남은 문제.

---

## 반드시 지킬 것

**박자 계약(`self.cue`)**
- `shots.json`의 모든 큐는 씬 코드에 `with self.cue("<id>"):` 블록이 하나씩 있다(없으면 린트 C6 ERROR).
- 블록마다 박자(`move`)가 1개 이상 있다. 박자 `run_time`은 0.5~1.0초, 남는 시간은 `CueScene`이 기다린다. 블록 밖에서 `self.wait`으로 시간을 채우지 않는다.
- 블록 안 애니메이션이 큐 길이보다 0.3초(`CUE_OVERRUN_TOL`) 넘게 길면 `CUE_OVERRUN`이다. 0건으로 만든다.
- 블록 안에 `self.play`가 없는 큐는 `CUE_NO_BEAT`이다. 0건으로 만든다.
- 대본을 고치면 `cues.py`를 다시 돌려 `timing.json`을 새로 만든다(tts 모드면 `tts.py`부터).

**화면**
- 배경 `#000000`. 코드에 hex를 쓰지 않고 토큰만 쓴다(린트 T8).
- 캔버스 글꼴 Noto Sans KR(`label`). Consolas는 코드 소품(`mono`), Noto Serif KR은 출처·문서 소품(`source`)에만.
- 글자 크기 토큰 `S/M/T/L/XL = 20/24/26/32/40`(설계 크기)만 쓰고, 이름으로 고른다(`label(.., "L")`, `tex(.., size="M")`). 키트가 Text는 ×1.44(`TEXT_SCALE`), Tex는 `TEX_FS`(×1.5)로 그리므로 `main.py`에서 배율을 곱하거나 `font_size`를 직접 쓰지 않는다(`Text`/`Tex`에 `font_size`를 주거나 `font_size`에 배율을 곱하면 린트 T7 WARN. `.scale()`로 키운 크기는 린트가 못 잡는다). 간격(buff)은 0.25, 0.5, 1.0만.
- 내용 하단 y ≥ −2.7(아래 15%는 자막 띠). 내용 |x| ≤ 4.3(비교 장면만 5.7).
- 제목은 좌상단 한 곳(`title()`)만. 번호 머리, 대시, 가운뎃점 금지.
- 강조는 면으로(틴트, 흐리기 0.25). 인용 카드는 확대하지 않고 `quote_focus` 덮개로 강조한다. 테두리만 있는 상자는 한 화면에 1개까지(린트 T10은 씬에 3개 이상이면 WARN).
- 캔버스 해설 한글은 한 줄 명사구, 공백 빼고 8자 이하(T5), 종결형(`~다/요/죠/함/음/임/됨/까`) 금지(T1). `·—→⇒` 따옴표 `①~⑩`으로 구절을 잇지 않는다(T2). 문서 메타('쪽', 'PDF', '노트', '해설', '정리') 금지(T4). 예외는 `prop=True`를 준 극 안 소품 글자뿐이다(T1·T5·E6에서만 빠지고 나머지 규칙은 그대로 받는다).

**자막 큐(`t`)**
- 1줄, 공백 포함 26자 이하(C1), 끝 마침표 없음(C2). 편 중앙값 15~20자(`stats:` 줄의 `len_median`).
- `·—→:`와 괄호를 쓰지 않는다(C3).
- `key`는 `t`의 부분 문자열(C4), 큐당 1개 이하. 칠한 큐는 편의 10~30%(E1).
- Noto Sans KR에 없는 글자를 쓰지 않는다(린트 C7). 없는 글자: 아래 첨자 숫자(`₀`~`₉`), `ⁿ`, 위 첨자 `⁰`·`⁵`~`⁹`, 이모지, `✔✕✗`. 그리스 문자(`α`, `Δ`, `θ`, `λ` 등)와 `¹²³⁴`는 있다. `W₀`는 자막에서 `원래 W`처럼 말로 푼다.
- 자막 ASS 값(PlayRes 1920×1080, `Noto Sans KR Medium` 64, Bold 0, `#DCDCDC`, 핵심어 `#EACF25`, 외곽선·그림자 0, MarginV 103)은 `captions.py`가 넣는다. 바꾸지 않는다. 특히 가족 이름 `Noto Sans KR` + Bold로 되돌리면 libass가 가는 VF Thin을 고른다.

**브랜드 금지**
- raenimgl의 `Logo` 클래스(원작 채널 로고)와 예시 코퍼스에 나오는 채널 이름 같은 브랜드 요소는 화면과 자막에 쓰지 않는다(`Logo`는 린트 T9가 막는다). 예시 코퍼스 코드는 참고·차용만 한다.

**하지 않는 것**
- 이미지 생성, 다른 AI 호출. 그림은 논문의 실제 그림만.
- 렌더할 때 창 띄우기(`-w` 없이 실행), `self.embed()`.
- 측정·스윕을 건너뛰고 완료라고 말하기.
