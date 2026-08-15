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
| `<이름>_FINAL.mp4` | 1080p60 완성 영상 — **나레이션 음성 + 자막 포함** |
| `narration.mp3` | TTS 나레이션 트랙 (영상 길이와 일치) |
| `narration.srt` | 자막 (실측 음성 길이 기준) |
| `script.md` | 타임코드 붙은 **녹음용 대본** (직접 녹음할 경우) |
| `shots.json` | 대본·타이밍·에셋의 단일 출처 |
| `main.py` | 구간별 Manim 씬 코드 |
| `scenes/` | 구간별 mp4 (따로 편집할 때) |

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
| edge-tts | 나레이션 음성. `uv pip install edge-tts` — **API 키 불필요**, 인터넷만 필요 |
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

체크포인트가 넷 있습니다 — **CP0 제작 사양 → CP1 편성안 승인 → CP2 대본 검토 → CP3 최종 검수**.

CP0에서는 편성 템플릿을 고릅니다. 논문·코드 분량을 보고 권장안이 맨 위에 오지만
선택은 사용자가 하고, "직접 지정"으로 원하는 구성을 적어도 됩니다.
한 번 정한 문항은 다시 묻지 않습니다.

```bash
python scripts/list_templates.py        # 현재 편성 템플릿 목록
```

| 템플릿 | 편수 | 언제 |
|---|---|---|
| `series-5` 표준 | 5편 · 30~35분 | 논문과 코드가 둘 다 충실할 때 |
| `series-3` 압축 | 3편 · 18~21분 | 코드가 작거나 논문이 짧을 때 |
| `single` 단편 | 1편 · 6~8분 | 개념 하나만 짧게 |
| `code-first` | 4편 · 24~30분 | 코드가 주인공이고 논문은 근거일 때 |
| `results-first` | 3편 · 18~22분 | 재현·벤치마크가 목적일 때 |

새 템플릿은 `assets/series_templates.local.json`에 넣으면 선택지에 자동으로 뜹니다.
이 파일은 스킬을 업데이트해도 지워지지 않습니다.

---

## 파이프라인

```
Stage 0    환경 13항목 사전 검증 (실패 시 재검증 최대 3회)
Stage 1    입력 판정 → paper.json / codebase.json
Stage 1.5  제작 사양 (편성 템플릿 등)        [CP0]
Stage 2    시리즈 편성안                     [CP1]
Stage 3    나레이션 대본 + shots.json         [CP2]
Stage 4    에셋 확보 + 씬 코드 생성
Stage 5    480p15 스모크 렌더 + 오류 자동 수정
Stage 5.5  정적 린트 — 렌더는 되는데 화면이 틀리는 조합 10종
Stage 6    1080p60 본번 렌더 (구간 병렬)
Stage 7    나레이션 음성(TTS) + 자막 + 최종 mux
Stage 8    길이 정합 + 프레임 스윕 + 납품 폴더  [CP3]
```

## 음성과 자막이 자동으로 맞는 이유

영상 타임라인이 `shots.json`의 `run_time + wait`로 만들어져 있으므로, 각 문장의 시작 시각은 **이미 알고 있다**. 음성은 정렬(align)할 필요 없이 그 시각에 **배치**하면 된다.

한 가지만 보정하면 된다 — 대본에 없는 전환 컷 때문에 씬이 예상보다 4~8% 길다. `tts_narrate.py`가 렌더된 씬을 ffprobe로 재서 **씬 단위로 스케일**하므로 오차가 뒤로 누적되지 않는다. 씬 안에서의 잔차는 수백 밀리초 수준이다.

```bash
python scripts/tts_narrate.py --episode <ep> --quality qh --fit
python scripts/mux_av.py     --episode <ep> --quality qh          # 자막 트랙
python scripts/mux_av.py     --episode <ep> --quality qh --burn   # 자막 태움
```

기본 음성은 `ko-KR-HyunsuMultilingualNeural` — 대본이 한영 혼용이라 multilingual이 맞다. 다른 선택지는 `ko-KR-InJoonNeural`(남), `ko-KR-SunHiNeural`(여). `--fit`은 배정된 슬롯을 넘치는 줄만 말하기 속도를 올려 다시 합성한다. `tts/`에 줄별 mp3가 남으므로 마음에 안 드는 한 줄만 다시 녹음할 수 있다.

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
| `parse_code.py` | 노트북·소스 → `codebase.json` (섹션·정의·shape 흐름 지점) |
| `estimate_narration.py` | 낭독 시간 추정 → `est_sec` / `run_time` / `wait` |
| `scaffold_video.py` | 에피소드 폴더 + `main.py` 스텁 + `shots.json` |
| `crop_figure.py` | 논문 PDF에서 figure 추출 |
| `gen_image.py` | Codex 이미지 생성 (능력 게이트 + 가드레일) |
| `list_templates.py` | 편성 템플릿 목록 → CP0 선택지 (`.local.json` 추가분 자동 병합) |
| `lint_scenes.py` | **렌더 전** 정적 검사 10종 — 렌더는 되는데 화면이 틀리는 조합 |
| `render.py` | 스모크→본번 렌더, 구간 병렬, 오류 분류, LaTeX 경합 자동 재시도 |
| `verify_output.py` | 길이 정합 + 해상도 + 프레임 샘플 |
| `sweep_frames.py` | **렌더 후** 구간당 35%/70%/마지막 프레임 추출 (눈으로 볼 것) |
| `export_script.py` | `shots.json` → `script.md` + `narration.srt` |
| `tts_narrate.py` | 대본 → 나레이션 음성 + 실측 자막 (씬 단위 스케일 보정) |
| `mux_av.py` | 씬 결합 + 음성 + 자막(트랙/태움) → `<ep>_FINAL.mp4` |
| `deliver.py` | 씬 합치기 + 납품 폴더 구성 |

전부 `--json`을 지원합니다.

## 참고 문서 (`references/`)

- `production-spec.md` — CP0 문항과 답이 뒤 단계에 미치는 영향, 템플릿 추가법
- `scene-templates.md` — 검증된 씬 배치 8종 (좌표 포함)
- `visual-qa.md` — 린트 규칙 10종 + 프레임 스윕 절차
- `imcommit-style-guide.md` — 연출 어휘, 파일 구조, 관용구, 순정 manim에서의 회피 목록
- `raenim-api.md` — raenim 전체 API와 함정
- `narration.md` — 편성 규칙, 대본 톤, `shots.json` 스키마
- `computed-facts.md` — 계산 노드, 불변량, 결과표 3장면 세트
- `generated-imagery.md` — 생성 이미지 정책과 사용법
- `troubleshooting.md` — preflight 복구, 렌더 오류 6종, 자주 밟는 함정

---

## 렌더가 성공해도 화면은 틀릴 수 있습니다

두 시리즈(79구간)를 만들며 **길이·해상도 검증을 전부 통과하고도 화면이 틀린 결함이 19건**
나왔습니다. 예외도 경고도 나지 않아 `verify_output.py`로는 한 건도 못 잡습니다.

그래서 방어선을 둘로 나눴습니다.

**렌더 전 — `lint_scenes.py`** (특정 API 조합은 항상 틀린다)

| 잡는 것 | 왜 조용한가 |
|---|---|
| 고정폭 헬퍼에 한글 | 글립이 없어 **두부(□)**만 그려진다 |
| 이모지 `🔍 🔒 ⚡` | **점이 하나도 없는 mobject**가 되어 `move_to`가 무효화되고, `next_to`로 붙인 이웃까지 원점으로 끌려간다 |
| `Line(path_arc=x).set_opacity()` | `set_opacity`가 면(fill)까지 칠해 호가 **흰 덩어리**가 된다 |
| 같은 `playw`에 `FadeIn` + `Indicate` | 등장이 취소돼 **값이 사라진다** |
| `highlight()`의 `disappear` 미재생 | 코드가 사라진 뒤 **빨간 강조 글자만 남는다** |

**렌더 후 — `sweep_frames.py` + 눈** (자리 다툼은 정적으로 못 잡는다)

구간마다 35%·70%·마지막 세 지점을 뽑습니다. 41구간이면 123장입니다.
글자 겹침, 화면 밖 잘림, 사라졌어야 할 찌꺼기는 이 단계에서만 보입니다.

```bash
python scripts/lint_scenes.py  --root C:/manimwork/my-paper     # ERROR 0이 될 때까지
python scripts/sweep_frames.py --root C:/manimwork/my-paper     # 그리고 눈으로 본다
```

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
