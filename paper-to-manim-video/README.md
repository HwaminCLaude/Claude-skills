# paper-to-manim-video

**논문 PDF나 코드를 주면 → 나레이션 대본 + Manim 씬 코드 + 렌더된 mp4** 를 만들어 주는 Claude Code 스킬.
3Blue1Brown 계열 한국어 채널 [임커밋](https://www.youtube.com/@ImcommIT)의 [`manim-kor`](https://github.com/CodingVillainKor/manim-kor) 저장소를 분석해 그 제작 구조를 그대로 따릅니다.

이 스킬의 핵심은 Manim 코드를 대신 짜주는 게 아닙니다.
**대본과 애니메이션을 `shots.json` 하나에서 함께 만들어 길이를 일치시키는 것**입니다.
나레이션 낭독 시간을 계산해 `wait`을 역산하므로, 대본을 읽으면 영상이 정확히 그만큼 갑니다.

---

## 무엇이 나오나

에피소드 하나당:

| 파일 | 내용 |
|---|---|
| `<제목>.mp4` | 1080p60 완성 영상 (구간별 mp4도 따로) |
| `script.md` | 타임코드 붙은 **녹음용 대본** |
| `narration.srt` | 자막 |
| `shots.json` | 대본·타이밍·에셋의 단일 출처 |
| `main.py` | 구간별 Manim 씬 코드 |

기본값은 5~8분 단편 3~5편 시리즈입니다.

## 입력

논문과 코드는 **각각 독립적인 1급 입력**입니다. 하나만 줘도, 둘 다 줘도 됩니다.

| 입력 | 편성 |
|---|---|
| 논문만 | 문제제기 → 핵심 아이디어 → 방법(수식) → 결과 |
| 코드만 | 실행 흐름 → 핵심 함수 해부 → 텐서 shape 변화 |
| 둘 다 | 논문 편성 + "논문 수식이 코드 어디에 있는가" 대조 편 |

---

## 요구 환경

| 항목 | 비고 |
|---|---|
| Python 3.11 | `manim==0.20.1` 핀 (raenim이 0.20.x 시절에 멈춰 있음) |
| [uv](https://docs.astral.sh/uv/) | 프로젝트·venv 관리 |
| FFmpeg | `winget install Gyan.FFmpeg` |
| LaTeX (MiKTeX) | 수식 렌더용. preflight가 설치까지 안내 |
| 한글 폰트 | Windows는 Malgun Gothic 기본 탑재 |
| Codex CLI *(선택)* | 이미지 생성 노드. 없으면 자동으로 꺼지고 전 구간 Manim 작도 |

`scripts/preflight.py`가 13개 항목을 진단하고, 실패마다 구체적인 복구 명령을 알려줍니다.

```bash
python scripts/preflight.py --root C:\manimwork\my-paper
python scripts/setup_env.py  --root C:\manimwork\my-paper
```

> **프로젝트 루트는 ASCII 경로**로 잡으세요. MiKTeX가 한글 경로의 임시 파일에서 실패합니다.

---

## 쓰는 법

Claude Code에서 그냥 이렇게 말하면 됩니다.

```
논문으로 영상 만들어줘   (PDF 경로와 함께)
내 코드 설명 영상이랑 대본 써줘
임커밋처럼 만들어줘
```

체크포인트가 셋 있습니다 — **CP1 편성안 승인 → CP2 대본 검토 → CP3 최종 검수**.
CP3에는 생성 이미지를 쓴 컷과 논문 수치를 인용한 컷이 자동으로 올라옵니다.

---

## 파이프라인

```
Stage 0  환경 13항목 사전 검증 (실패 시 재검증 최대 3회)
Stage 1  입력 판정 → paper.json / codebase.json
Stage 2  시리즈 편성안                      [CP1]
Stage 3  나레이션 대본 + shots.json          [CP2]
Stage 4  에셋 확보 + 씬 코드 생성
Stage 5  480p15 스모크 렌더 + 오류 자동 수정
Stage 6  1080p60 본번 렌더 (구간 병렬)
Stage 7  길이 정합 검증 + 납품 폴더 구성      [CP3]
```

## 타이밍 계약

raenim의 `playw`는 **재생한 뒤 대기**합니다. 즉 한 샷의 길이는 `run_time + wait`입니다.

```python
wait = max(0.2, est_sec - run_time)
self.playw(Write(title), run_time=1.5, wait=wait)
```

`est_sec`을 그대로 `wait`에 넣으면 매 샷이 `run_time`만큼 초과됩니다.
`estimate_narration.py`가 한국어 5.5음절/초 + 문장부호 쉼을 기준으로 이 값을 계산해 채웁니다.

렌더 후 `verify_output.py`가 실제 mp4 길이와 비교해 **오차 15% 초과면 REWORK**로 표시합니다.
(전환 컷 때문에 +4~8%의 체계적 초과는 정상입니다.)

---

## 정확성 가드레일

자기 연구를 설명하는 영상이므로 다음을 강제합니다.

- **생성 이미지로 연구 산출물을 만들지 않습니다.** 데이터·성능 그래프·아키텍처 다이어그램·논문 figure 재현 요청은 `gen_image.py`가 거부(exit 2)합니다. 그런 건 논문 PDF에서 크롭(`crop_figure.py`)하거나 Manim으로 작도합니다.
- **생성 이미지 안에 글자를 넣지 않습니다.** 라벨·수식은 Manim `Text`/`MathTex`로 위에 얹습니다.
- **논문에 없는 주장을 대본에 쓰지 않습니다.** 수치는 논문 값 그대로, 비유는 비유라고 말합니다.
- 생성 이미지는 편당 1~3컷 상한. 영상의 뼈대는 항상 Manim 작도입니다.

---

## 스크립트

| 스크립트 | 용도 |
|---|---|
| `preflight.py` | 환경 13항목 진단 (읽기 전용) |
| `setup_env.py` | uv 프로젝트 + manim/raenim 설치 + `noise` shim 주입 |
| `parse_paper.py` | 논문 PDF → `paper.json` + `paper.txt` |
| `estimate_narration.py` | 낭독 시간 추정 → `est_sec` / `run_time` / `wait` |
| `scaffold_video.py` | 에피소드 폴더 + `main.py` 스텁 + `shots.json` |
| `crop_figure.py` | 논문 PDF에서 figure 추출 |
| `gen_image.py` | Codex 이미지 생성 (능력 게이트 + 가드레일) |
| `render.py` | 스모크→본번 렌더, 구간 병렬, 오류 분류, LaTeX 경합 자동 재시도 |
| `verify_output.py` | 길이 정합 + 해상도 + 프레임 샘플 |
| `export_script.py` | `shots.json` → `script.md` + `narration.srt` |
| `deliver.py` | 씬 합치기 + 납품 폴더 구성 |

전부 `--json`을 지원합니다.

## 참고 문서 (`references/`)

- `imcommit-style-guide.md` — 연출 어휘, 파일 구조, 관용구, 순정 manim에서의 회피 목록
- `raenim-api.md` — raenim 전체 API와 함정
- `narration.md` — 편성 규칙, 대본 톤, `shots.json` 스키마
- `generated-imagery.md` — 생성 이미지 정책과 사용법
- `troubleshooting.md` — preflight 복구, 렌더 오류 6종, 자주 밟는 함정

---

## 알아둘 함정

실제로 겪고 고친 것들입니다. 자세한 건 `references/troubleshooting.md`.

- **`noise` 빌드 실패는 정상입니다.** cp311 휠이 없어 MSVC를 요구합니다. `setup_env.py`가 순수 파이썬 Perlin shim을 넣습니다 (`RWiggle`만 쓰므로 지장 없음).
- **raenim은 `--no-deps`로 설치해야 합니다.** `[build-system]`이 없어 레거시 `setup.py`를 타고 `noise`를 끌어옵니다.
- **`manim.cfg`에 해상도를 넣으면 안 됩니다.** `-ql`/`-qh`를 덮어써 2단 렌더가 무력화됩니다.
- **`manim main.py`를 그냥 실행하면 멈춥니다.** 한 파일에 씬이 여러 개면 대화형으로 물어봅니다. `render.py`는 AST로 클래스를 찾아 항상 이름을 명시합니다.
- **병렬 렌더는 `media/Tex/`에서 경합합니다** (Windows `WinError 32`). `render.py`가 해당 씬만 직렬로 재시도합니다.
- **Codex 프롬프트는 stdin으로 넘겨야 합니다.** 명령행 인자로 주면 `cmd.exe`가 괄호를 재파싱해 깨집니다.

## 라이선스·출처

임커밋 채널의 **제작 방식**을 분석해 참고했고, 그 채널의 로고·브랜드 자산은 사용하지 않습니다.
의존하는 [`raenim`](https://github.com/CodingVillainKor/raenim)은 Apache-2.0, [ManimCE](https://github.com/ManimCommunity/manim)는 MIT입니다.
