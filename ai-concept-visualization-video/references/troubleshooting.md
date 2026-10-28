# 문제 해결

환경: Windows 11, `uv` + Python 3.10.18, ManimGL 1.7.2 포크(CodingVillainKor), raenimgl, MiKTeX, ffmpeg 8.1.2 full_build(libass·fontconfig). 2026-10-27 `C:\manimwork\_spike_manimgl\`에서 시험한 결과다. 먼저 `python scripts/preflight.py --root <proj>`를 돌려 FAIL 줄을 본다.

## `av` 누락

- 증상: 렌더 시작 직후 `ModuleNotFoundError: No module named 'av'`.
- 원인: 포크가 `av`를 import하지만 의존성 목록에 없다.
- 해결: `pyproject.toml` 의존성에 `av`를 둔다(템플릿에 들어 있다). 그다음 `python scripts/setup_env.py --root <proj>`(= `uv sync`).

## 창이 뜨거나 렌더가 멈춤(`-w`)

- 증상: 창이 열리고 대화형 셸(`embed`)에서 멈춘다. 자동 실행이 끝나지 않는다.
- 해결: 항상 `-w`를 준다. `manimgl main.py <Scene> -w -l`(스모크), `--hd`(본번). `-w`면 창 없이 파일로 쓰고 `self.embed()`는 건너뛴다. `render.py`가 이 플래그를 붙인다.
- 씬 코드에 `self.embed()`를 넣지 않는다.
- 출력은 cwd의 `videos/<Scene>.mp4`다(`custom_config.yml`의 `directories.subdirs.output: videos`). 에피소드 폴더를 cwd로 두고 실행한다.

## 글꼴

- 증상: 한글이 두부(□)로 나오거나 다른 글꼴로 바뀜. 자막의 `₀` 같은 문자가 두부로 나옴.
- 확인: `preflight.py`가 manimpango 글꼴 목록에서 Noto Sans KR, Noto Serif KR, Consolas를 찾는다. 자막 글자는 `lint.py`의 `C7`이 Noto Sans KR cmap으로 검사한다.
- 2026-10-27 확인: `C:\Windows\Fonts\NotoSansKR-*.ttf`에 `₀`(U+2080), `✔ ✕ ✗ ✘`가 없다. `α`, `Δ`, `✓`, `−`는 있다. 아래첨자는 화면에서 Tex로(`W_0`), 자막에서는 빼고 쓴다.
- 글꼴을 새로 깔았으면 manimpango가 다시 읽도록 터미널을 새로 연다. `Text` 캐시가 옛 글꼴을 쥐고 있으면 `<venv>` 밖 ManimGL 캐시 폴더(Tex·Text SVG 캐시)를 지운다.
- `Text(..., weight=BOLD)`처럼 굵기를 지정하지 않는다(디자인 규칙). 한글 굵은 글꼴 매칭이 어긋나 다른 글꼴로 바뀌는 원인도 된다.

## 자막이 가늘다: VF Thin 함정

- 증상: 구운 자막의 획이 약 2px로, 참고 영상(약 4px)보다 눈에 띄게 가늘다. ASS Bold를 `-1`로 줘도 굵어지지 않는다. 굽기 로그(`-loglevel info`)에 `fontselect: (Noto Sans KR, 700, 0) -> NotoSansKR-Thin`이 찍힌다.
- 원인: `C:\Windows\Fonts\NotoSansKR-VF.ttf`(가변 글꼴)가 가족 이름 'Noto Sans KR'로 등록되고 기본 인스턴스가 Thin(굵기 100)이다. 정적 `NotoSansKR-Regular.ttf`, `NotoSansKR-Bold.ttf`도 가족 이름이 같은 'Noto Sans KR'이라, libass(ffmpeg 8.1.2의 글꼴 공급자는 DirectWrite)는 VF를 고르고 Thin 윤곽을 그린다. 가변 축은 적용되지 않고 Bold 플래그도 듣지 않는다.
- 해결: 자막 Fontname을 `Noto Sans KR Medium`, Bold `0`으로 둔다(`captions.py`가 넣는다). 정적 `NotoSansKR-Medium.ttf`만 legacy 가족 이름이 'Noto Sans KR Medium'이라 그 파일로 정확히 떨어진다. 획 4px, 잉크 40px, 줄 중심 947.5px로 참고 영상과 맞는다.
- 함께 피할 것: 'Noto Sans KR Bold'(전체 이름)나 'NotoSansKR-Bold'(PostScript 이름)는 DirectWrite에서 찾지 못해 **Arial로 조용히 바뀐다**. 정적 Bold 파일만 든 폴더를 `fontsdir`로 넘기면 Bold가 되지만 획 6px로 너무 무겁다.
- 확인: `preflight.py`의 `capfont` 줄. 자막 헤더 그대로 한 줄을 구워 libass가 `NotoSansKR-Medium`을 골랐는지 보고, 아니면 FAIL이다. `assemble.py`도 굽기 로그로 같은 검사를 해서 다른 글꼴이면 `FAIL caption font ... resolved to ...`로 멈춘다.
- Medium 파일이 없는 PC(예: Google Fonts의 가변 글꼴만 깐 경우): Noto Sans KR 정적 글꼴 묶음에서 `NotoSansKR-Medium.ttf`를 설치하고 터미널을 새로 연 뒤 `preflight.py`를 다시 돌린다.

## MiKTeX(Tex 수식)

- 증상: `LatexError` 또는 `latex.exe`가 `-no-pdf`를 거부.
- 원인: ManimGL 기본 `full_tex_to_svg`가 `latex`에도 `-no-pdf`를 붙인다. MiKTeX `latex.exe`는 이를 거부한다.
- 해결: `from raenimgl import *`(키트가 해 준다)를 먼저 해야 한다. raenimgl `__init__.py`가 이 함수를 고쳐 끼운다.
- 패키지 설치 창이 뜨면 렌더가 멈춘다. MiKTeX Console에서 'Install missing packages on-the-fly'를 'Yes'로 둔다. `latex`와 `dvisvgm`이 PATH에 있어야 한다(`preflight.py`가 검사).
- TEMP 경로에 한글(사용자 이름)이 있어도 LaTeX는 동작했다.

## 한글·공백 경로

- 프로젝트 루트는 ASCII 경로로 둔다(`C:\manimwork\<slug>`). 사용자 폴더(`C:\Users\<한글 이름>\...`)에 프로젝트를 만들지 않는다.
- 스킬 스크립트는 한글 경로에 있다. Git Bash에서는 경로를 따옴표로 감싼다. PowerShell에서는 `& "C:\Users\<user>\...\python.exe" ...`.
- ffmpeg `subtitles=` 필터는 경로의 `:`, `\`, 공백, 작은따옴표에 약하다. `assemble.py`는 에피소드 폴더를 cwd로 두고 `subtitles=captions.ass` 상대 경로로 굽는다. 직접 ffmpeg를 부를 때도 같은 방식을 쓴다.
- Python에서 파일을 열 때는 `encoding="utf-8"`을 준다(cp949 기본값 때문에 `UnicodeEncodeError`가 난다). 콘솔 출력이 깨지면 `PYTHONIOENCODING=utf-8`.

## fps와 해상도

- 포크 기본은 1920×1080, 배경 `#000000`, **30fps**다. `custom_config.yml`에서 `camera.fps: 60`을 준다. 명령줄 `--fps 60`도 된다.
- `-l`은 저해상도 스모크 렌더다. 본번은 `--hd`(1080p).
- 확인: `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -of csv=p=0 <mp4>` → `1920,1080,60/1`.
- 속도 참고(1080p60): 56초 영상 약 112초, 3D 기울이기 33.5초 영상 약 36초. `render.py --jobs` 기본 2(GPU 컨텍스트 경합 방지).

## 큐 시간 초과(`CUE_OVERRUN`)

- 증상: `render.py` 보고에 `CUE_OVERRUN <id> <초>` 경고.
- 원인: 큐 블록 안 애니메이션 합이 큐 길이보다 길다. 흔한 원인은 `playw`의 기본 `wait=1`이다.
- 해결: 큐 안에서는 `self.play`를 쓰거나 `wait=0`. 박자를 다음 큐로 옮기거나 `run_time`을 줄인다. 자막은 cuelog 실제 시각을 쓰므로 어긋나지는 않지만, 뒤 큐들이 밀린다.

## 박자 없는 큐(`CUE_NO_BEAT`)

- 증상: `render.py` 보고에 `WARN CUE_NO_BEAT <Scene> <cue_id>`, `SUMMARY ... no_beat=<n>`이 1 이상.
- 원인: 그 큐 블록 안에서 `self.play`가 한 번도 불리지 않았다(`wait`, `add`만 있음). cuelog 항목의 `plays`가 0이다. 자막만 바뀌고 화면은 멈춘다.
- 해결: 그 큐에 박자를 하나 넣는다(흐름 문법의 `point` 강조, 작은 이동, 값 바꾸기 등). 앞 큐의 애니메이션을 이 큐로 옮겨도 된다. `no_beat=0`까지 고친다.
- 한계: `plays`는 play 횟수만 센다. 어두운 칸끼리 바뀌거나 가는 선만 움직이는 박자는 `measure_motion.py`에서 정지로 잡힐 수 있다. 렌더 뒤 `hold_max_s`도 본다.

## 큐 id를 못 찾음(`CueNotFound`)

- 증상: 렌더가 `vizkit.CueNotFound: 큐 id '<id>'가 ...`로 실패한다(`kind=other`).
- 원인: 씬 코드의 `self.cue("<id>")`가 `timing.json`에 없다. shots.json을 고친 뒤 `cues.py`를 다시 돌리지 않았거나, 템플릿 예시 큐가 남아 있다.
- 해결: `cues.py --episode <ep>`로 `timing.json`을 다시 만들고, 씬 코드의 큐 id를 shots.json과 맞춘다. 오류 메시지에 지금 있는 큐 id 목록이 나온다.

## 자막 띠가 덮임(A2 `caption_band`)

- 증상: `measure_design.py`가 `A2 FAIL (caption_band)`. 자막 뒤에 그림이 비친다.
- 원인: 내용이 y < −2.7로 내려왔다. 흔한 경우는 흰 논문 카드를 카메라로 확대한 것이다.
- 해결: 인용 카드는 확대하지 않고 `quote_focus` 덮개로 강조한다. 다른 그림은 `CONTENT` 범위 안으로 올리거나 줄인다.

## 렌더 실패와 옛 파일

- `render.py`는 렌더 전에 `videos/<Scene>.mp4`를 지운다. 실패하면 exit 1과 함께 stderr 분류(`kind=latex|font|attribute|import|other`)를 찍는다. 옛 파일로 이어 붙이지 않는다.
- `AttributeError`는 ManimCE 문법을 GL에 쓴 경우가 많다(예: `MathTex` 대신 `Tex`, `self.camera.frame` 대신 `self.frame`/`self.cf`). `Create`는 raenimgl이 `ShowCreation` 별칭으로 넣어 두어 GL에서도 된다.
