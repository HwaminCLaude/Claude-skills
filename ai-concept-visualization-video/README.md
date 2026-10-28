# ai-concept-visualization-video

**논문·모델·코드·주제 설명을 주면 → 자막 큐 대본(`shots.json`) + ManimGL 씬 코드 + 자막이 박힌 mp4** 를 만드는 Claude Code 스킬.
검정 배경 위에서 개념을 그림으로 풀어 가는 **한국어 AI 개념 시각화 영상**을 만듭니다.

핵심은 두 가지입니다.

1. **자막 큐가 박자 단위입니다.** 큐(한 줄, 약 2초)마다 연출이 하나 이상 있어서 화면이 약 2초마다 움직입니다. 슬라이드처럼 멈춰 있지 않습니다.
2. **디자인이 깔끔합니다.** 검정 배경, 토큰으로 정한 색·크기, 면으로 칠하는 강조, 짧은 명사 라벨을 씁니다. 린트(`scripts/lint.py`)와 측정 스크립트가 규칙을 검사합니다.

---

## 무엇이 나오나

에피소드 하나당:

| 파일 | 내용 |
|---|---|
| `<episode>_FINAL.mp4` | 완성 영상. 하단 자막을 구워 넣고, 기본 `tts` 모드면 음성도 들어갑니다(`silent` 모드는 자막만) |
| `shots.json` | 자막 큐 대본. 큐마다 문장, 직전 큐와의 관계(`rel`), 연출(`move`) |
| `main.py` | 큐 블록(`with self.cue(id):`)으로 짠 ManimGL 씬 코드 |
| `timing.json`, `tts/` | 큐 길이와 큐마다 합성한 음성(`tts` 모드) |

## 작업 흐름

**준비 → 입력 → 편성(사용자 확인 1회) → 대본 `shots.json`(사용자 검토 1회) → 음성 → 씬 코드 → 린트·스모크 렌더 → 본번 렌더 → 합치기 → 측정·프레임 스윕·보고**

- 입력은 논문 PDF(`parse_paper.py`), 노트북·`.py`·소스 폴더(`parse_code.py`), 주제 설명 중 아무것이나 됩니다.
- 연출은 `references/flow-grammar.md`의 흐름 문법(확대, 카메라 이동, 3D 기울이기, 이어받기, 논문 인용 카드 등)을 따릅니다.
- 손계산·숫자 대입 워크스루, ManimCE 교육 영상은 이 스킬이 아니라 [`paper-to-manim-video`](../paper-to-manim-video)를 씁니다.

## 요구 환경

| 항목 | 비고 |
|---|---|
| [uv](https://docs.astral.sh/uv/) | 프로젝트 venv를 만듭니다. Python 3.10.18은 uv가 내려받습니다 |
| git | uv가 ManimGL 포크·raenimgl을 GitHub에서 받을 때, 예시 코퍼스를 받을 때 |
| FFmpeg | `ffmpeg`·`ffprobe`, 자막을 굽는 `subtitles` 필터(libass)가 있어야 합니다 |
| LaTeX (MiKTeX) | `latex`, `dvisvgm` — 수식(Tex)을 쓸 때 |
| 글꼴 | Noto Sans KR(필수), 자막용 정적 `NotoSansKR-Medium.ttf`(필수), Noto Serif KR·Consolas(있으면 좋음) |
| edge-tts | `tts` 모드 음성. API 키는 필요 없고 인터넷만 있으면 됩니다 |

```powershell
python "SK\scripts\scaffold.py" --root C:\manimwork\<slug> --episode <ep>
python "SK\scripts\setup_env.py" --root C:\manimwork\<slug>
C:\manimwork\<slug>\.venv\Scripts\python.exe "SK\scripts\preflight.py" --root C:\manimwork\<slug>
```

`SK`는 이 스킬 폴더입니다. `preflight.py`가 venv(Python 3.10.18, manimlib·raenimgl·av), FFmpeg(libass), LaTeX, 캔버스·자막 글꼴을 PASS/WARN/FAIL로 진단하며, FAIL이 0이어야 다음 단계로 갑니다. uv는 `setup_env.py`가 확인하고, edge-tts가 venv에 없으면 `tts.py`가 uv 임시 환경으로 다시 실행합니다.

> **프로젝트 루트는 ASCII 경로**(`C:\manimwork\<slug>`)로 잡으세요. MiKTeX가 한글 경로에서 실패합니다.

## 설치

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force .\ai-concept-visualization-video "$env:USERPROFILE\.claude\skills\"
```

## 쓰는 법

Claude Code에서 이렇게 말하면 됩니다.

```text
이 논문으로 AI 개념 시각화 영상 만들어줘
이 모델 구조를 manim 영상으로 설명해줘
이 코드를 AI 설명 영상으로 만들어줘
```

편성과 대본, 두 곳에서 사용자에게 확인을 받은 뒤 렌더합니다.

## 폴더 구성

```
ai-concept-visualization-video/
├── SKILL.md            ← 스킬 본문(절차·규칙). Claude가 읽고 따라 함
├── README.md           ← (이 파일)
├── scripts/            ← scaffold · setup_env · preflight · fetch_examples · parse_paper · parse_code ·
│                          crop_figure · tts · cues · lint · render · captions · assemble ·
│                          measure_motion · measure_design · sweep_frames
├── references/         ← shots-schema · narration-voice · captions · flow-grammar · design-system ·
│                          onscreen-text · raenimgl-api · example-corpus · troubleshooting
├── assets/             ← 프로젝트 틀(pyproject.toml · custom_config.yml · vizkit.py · main 틀)
└── tests/              ← pytest
```

## 출처와 의존성

- 렌더에 쓰는 **ManimGL 포크**(`CodingVillainKor/manimgl`)와 **raenimgl**(`CodingVillainKor/raenimgl`)은 이 스킬에 들어 있지 않습니다. 프로젝트를 만들 때 `uv sync`가 GitHub에서 받습니다(`assets/project_template/pyproject.toml`).
- 연출 예시 코퍼스(장면 코드 33편 + raenimgl 소스)도 넣지 않았습니다. 원본 저장소에 라이선스 파일이 없어 다시 배포하지 않습니다. 필요하면 `python "SK\scripts\fetch_examples.py"`로 원본 공개 저장소의 고정 커밋에서 받습니다(`references/example-corpus.md`).
- 문서에 나오는 '참고 영상'·'참고 코퍼스'가 무엇인지, 받은 코드를 빌려 쓸 때의 주의는 `references/example-corpus.md`에 적었습니다.
- 원작 채널의 로고와 이름 같은 브랜드 요소는 영상에 쓰지 않습니다. 린트 `T9`가 raenimgl의 `Logo` 클래스를 막습니다.

## 주의

- edge-tts는 비공식 엔드포인트라 공개·상업용 음성 라이선스가 분명하지 않습니다. 영상을 공개하기 전에 라이선스가 있는 TTS나 직접 녹음으로 바꿀지 정하세요.
- 테스트는 프로젝트 venv 파이썬으로 돌립니다: `C:\manimwork\<slug>\.venv\Scripts\python.exe -m pytest tests`. 예시 코퍼스를 받기 전에는 코퍼스를 여는 검사를 건너뜁니다.
