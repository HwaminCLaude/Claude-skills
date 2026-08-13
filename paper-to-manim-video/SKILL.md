---
name: paper-to-manim-video
description: 논문 PDF나 코드(둘 중 하나 또는 둘 다)를 받아 임커밋(3Blue1Brown 계열) 스타일의 한국어 교육 영상을 만든다. 나레이션 대본과 Manim 씬 코드를 하나의 shot list에서 함께 생성해 대본 낭독 시간과 영상 길이를 자동으로 맞추고, 실제로 렌더해 mp4까지 뽑는다. 5~8분 단편 3~5편 시리즈가 기본. 사용자가 "논문으로 영상 만들어줘", "내 논문 유튜브 영상", "임커밋처럼 만들어줘", "manim으로 논문 설명 영상", "코드 설명 영상이랑 대본", "논문 영상 대본 써줘"라고 할 때 사용한다. 노션 정리는 pdf-to-notion, 코드 가이드북은 code-guidebook-notion을 쓴다.
---

# Paper to Manim Video

논문·코드를 임커밋 스타일 한국어 교육 영상으로 만든다. 산출물은 **대본 + Manim 코드 + 렌더된 mp4** 한 벌이다.

이 스킬의 핵심은 Manim 코드를 짜주는 게 아니다. **대본과 애니메이션을 `shots.json` 하나에서 함께 만들어 길이를 맞추는 것**이다. 나레이션 낭독 시간을 계산해 `playw`의 `wait`을 역산하므로, 대본을 읽으면 영상이 정확히 그만큼 간다.

사용자에게는 한국어로 답한다. 코드 식별자는 영어, 주석·나레이션은 한국어.

---

## 스택

**순정 ManimCE 0.20.1 + raenim** (Apache-2.0). 임커밋의 manim 포크는 쓰지 않는다 — 포크의 ffmpeg 재인코딩이 경로에 한글이 있으면 깨지고, 우리에게 필요한 연출 어휘는 raenim에 다 있다.

- `manim`은 **0.20.1로 핀**한다. raenim이 0.20.x 시절에 멈춰 있어(마지막 커밋 2026-03) 0.21.0은 미검증이다.
- `noise`는 cp311 휠이 없어 빌드가 **실패하는 게 정상**이다. `setup_env.py`가 순수 파이썬 shim을 넣는다.
- 프로젝트 루트는 **ASCII 경로**(`C:\manimwork\<slug>`)로 만든다. MiKTeX가 한글 경로에서 사고를 낸다.
- 나레이션 음성은 **edge-tts**(`uv pip install edge-tts`). API 키가 필요 없고 한국어 음성 3종이 있다. 인터넷은 필요하다.

---

## 모드

| 모드 | 하는 일 | 트리거 예 |
|---|---|---|
| `init` (기본) | Stage 0~7 전체. 시리즈 3~5편 | "논문으로 영상 만들어줘" |
| `one` | 단편 1편만 | "이 개념만 짧게" |
| `script-only` | 대본·콘티까지만 (코드·렌더 없음) | "대본만 먼저" |
| `render` | 기존 프로젝트 재렌더 | "다시 렌더해줘" |
| `resume` | 이미 만들어진 산출물을 보고 이어서 | "이어서" |

`resume`은 별도 상태 파일을 쓰지 않고 **산출물의 존재로 판단**한다: `paper.json` 있으면 Stage 1 통과, 에피소드 폴더의 `shots.json`에 `narration`이 차 있으면 Stage 3 통과, `main.py`에 스텁이 아닌 본문이 있으면 Stage 4 통과, `media/videos/main/1080p60/*.mp4`가 있으면 Stage 6 통과. 파일이 곧 체크포인트라 중간에 사람이 손으로 고쳐도 그대로 이어진다.

---

## 워크플로우

### Stage 0 — 사전 검증

```bash
python scripts/preflight.py --root C:\manimwork\<slug>
```

13개 항목. `FAIL`은 차단, `WARN`은 기능 축소(codex 없음 → 이미지 생성 노드 off). 실패하면 안내대로 조치 후 **재검증, 최대 3회**. 그래도 안 되면 사용자에게 보고하고 멈춘다.

환경이 없으면:
```bash
python scripts/setup_env.py --root C:\manimwork\<slug>
```

LaTeX가 없으면 `winget install --id MiKTeX.MiKTeX --silent --accept-package-agreements --accept-source-agreements` 후 **반드시** `initexmf --set-config-value "[MPM]AutoInstall=1"`. 안 켜면 첫 `MathTex` 렌더가 GUI 대화상자에서 멈춘다(실패가 아니라 정지).

자세히: `references/troubleshooting.md`

### Stage 1 — 입력 판정 및 파싱

논문·코드는 각각 독립적인 1급 입력이다. 어느 쪽도 없으면 중단하고 요구한다.

- **논문** → `paper.json` (섹션, 핵심 주장, 수식, figure 목록, 한계)
  - figure 목록은 `python scripts/crop_figure.py --pdf <pdf> --list`로 뽑는다
- **코드** → `codebase.json` — `python scripts/parse_code.py --input <ipynb|py|dir> --out <root> --dump-text`
  - 섹션(마크다운 헤딩)·정의·**shape 흐름 지점**을 뽑는다. shape 증거는 두 종류다: 셀 출력의 `torch.Size([...])`(실측)와 코드 주석의 `# (B, T, D)`(저자 표기). 데이터 흐름 편성은 이 지점들을 뼈대로 삼는다.

### Stage 2 — 시리즈 편성  → **CP1 사용자 승인**

한 편 = 한 아이디어, 5~8분, 구간 4~7개. 편성안을 제시하고 승인을 받은 뒤 진행한다.
규칙과 승인 양식: `references/narration.md` §1

### Stage 3 — 대본 + shots.json  → **CP2 대본 검토**

편별로 `shots.json`을 쓴다. `narration`만 먼저 채우고:

```bash
python scripts/estimate_narration.py --shots shots.json --write
```

`est_sec`·`run_time`·`wait`이 자동으로 채워진다. `run_time >= est_sec` 경고가 뜨면 문장을 쪼개거나 `run_time`을 줄인다.

스키마와 톤 규칙: `references/narration.md` §2~3

### Stage 3.5 — 계산 (수치를 다루는 영상만)

영상이 상관계수·적합도·p값 같은 **수치를 말한다면**, 그 숫자는 계산 결과여야 한다. 그럴듯한 자릿수를 쓰는 순간 영상 전체가 무너진다.

```bash
python scripts/compute_facts.py --root <root>          # 분석 실행 + 검증
python scripts/compute_facts.py --root <root> --check  # 검증만
```

규약 한 줄: **`analysis/`가 계산하고, `facts.json`이 기록하고, 씬은 `facts.json`에서만 읽는다.** 손으로 옮겨 적는 경로는 없다.

- `facts.json` 필수 키: `source`(데이터 출처) · `criteria`(연구자가 정한 판정 기준 — 계산값과 분리) · `invariants`(수학적 검산, 하나라도 false면 실패)
- 씬 코드는 `FACTS["efa"]["kmo"]` 처럼 읽어 쓴다. **하드코딩 금지** — 분석을 다시 돌려도 영상이 안 바뀐다
- 라이브러리 호출 한 줄은 화면에 못 올린다. `numpy`/`scipy`로 **직접 구현**하고 라이브러리는 교차검증 보조로만
- 연구 데이터에는 식별정보가 들어 있을 수 있다. **원본은 읽기만** 하고 비식별 사본으로 작업한다

자세히: `references/computed-facts.md` (불변량 목록, 개인정보 절차, **결과표 3장면 세트**)

### Stage 4 — 에셋 + 씬 코드

```bash
python scripts/scaffold_video.py --root <root> --name ep01_problem \
    --title "이 논문이 풀려는 문제" --scenes intro problem why
```

에셋을 먼저 확보한다.
- 논문 그림·데이터 → `crop_figure.py` (**생성 이미지 절대 금지**)
- 은유·분위기 컷 → `gen_image.py` (편당 1~3컷 상한, `references/generated-imagery.md`)

그다음 `shots.json`을 보고 `main.py`의 각 구간 클래스를 채운다. 샷 하나 = `self.playw(...)` 하나:

```python
self.playw(<anim>, run_time=<shot.run_time>, wait=<shot.wait>)
```

연출 어휘와 관용구: `references/imcommit-style-guide.md`
raenim API: `references/raenim-api.md`

### Stage 5 — 스모크 렌더 + 자동 수정

```bash
python scripts/render.py --episode <ep> --quality ql
```

480p15로 전 구간을 먼저 통과시킨다. 오류는 `error_kind`로 분류되어 조치가 함께 나온다. **자동 수정 최대 3회**, 초과하면 연출을 낮추거나 사용자에게 올린다.

### Stage 6 — 본번 렌더

```bash
python scripts/render.py --episode <ep> --quality qh --jobs 3
```

구간별로 프로세스를 병렬로 띄운다(포크의 `--parallel` 없이 같은 효과). 캐시는 켜 둔다 — 고친 구간만 다시 그려진다. 오래 걸리므로 백그라운드로 돌린다.

### Stage 7 — 나레이션 음성 + 자막

```bash
python scripts/tts_narrate.py --episode <ep> --quality qh --fit
python scripts/mux_av.py     --episode <ep> --quality qh          # 자막을 트랙으로
python scripts/mux_av.py     --episode <ep> --quality qh --burn   # 자막을 화면에 태움
```

`shots.json`의 타임라인이 곧 음성의 배치 시각이다 — 정렬이 아니라 **배치**다. 다만 대본에 없는 전환 컷 때문에 씬이 예상보다 4~8% 길므로, `tts_narrate.py`가 렌더된 씬 길이를 ffprobe로 재서 **씬 단위로 스케일 보정**한다. 그래서 드리프트가 뒤로 누적되지 않는다.

음성은 **edge-tts**(무료, API 키 불필요). 기본 음성은 `ko-KR-HyunsuMultilingualNeural` — 대본이 한영 혼용("토큰", "RNN")이라 multilingual이 맞다. `--fit`은 슬롯을 넘치는 줄만 속도를 올려 다시 합성한다.

산출: `narration.mp3`(영상 길이와 일치), `narration.srt`(실측 음성 길이 기준), `tts/`(줄별 mp3 — 한 줄만 다시 녹음 가능), `<ep>_FINAL.mp4`.

### Stage 8 — 검증  → **CP3 최종 검수**

```bash
python scripts/verify_output.py --episode <ep> --quality qh --frames 3
```

실제 mp4 길이와 `sum(run_time + wait)`를 비교해 **오차 15% 초과면 REWORK**. 프레임 샘플을 뽑아 실제로 눈으로 본다(한글이 □□□로 나와도 길이·해상도는 멀쩡할 수 있다).

CP3에는 다음을 올린다: 생성 이미지를 쓴 컷 전부, REWORK 판정 구간, 논문 수치를 인용한 컷.

---

## 산출물 배치

```
C:\manimwork\<slug>\
├─ pyproject.toml / uv.lock / .venv        # 프로젝트 공용 환경
├─ paper.json  |  codebase.json  |  paper.txt
└─ ep01_problem\
   ├─ main.py            # 구간 클래스들
   ├─ manim.cfg          # 해상도는 넣지 않는다 (아래 참조)
   ├─ shots.json         # 대본 + 타이밍 + 에셋의 단일 출처
   ├─ script.md          # 사람이 읽는 대본 (녹음용)
   ├─ assets/figures/    # crop_figure.py 산출물
   ├─ assets/generated/  # gen_image.py 산출물 + prompts.json
   ├─ media/             # 렌더 결과 (gitignore)
   └─ verify_frames/     # 검수용 프레임
```

---

## 반드시 지킬 것

1. **`manim main.py`를 그냥 실행하지 않는다.** 한 파일에 클래스가 여러 개면 Manim이 대화형으로 물으며 멈춘다. `render.py`는 AST로 클래스를 찾아 항상 이름을 명시한다.
2. **`manim.cfg`에 `pixel_width`/`pixel_height`/`frame_rate`를 넣지 않는다.** `-ql`/`-qh`를 덮어써 2단 렌더가 무력화된다.
3. **한글은 `Text(..., font="Malgun Gothic")`.** Pango가 알아서 고르지 않는다. `kr()` 헬퍼를 쓴다.
4. **타이밍은 `wait = max(0.2, est_sec - run_time)`.** `playw`는 재생 *후* 대기라 `est_sec`을 그대로 `wait`에 넣으면 매 컷이 `run_time`만큼 길어진다.
5. **생성 이미지로 연구 산출물을 만들지 않는다.** 데이터·결과·아키텍처는 논문 크롭이나 Manim 작도로만. `gen_image.py`가 1차로 거부하지만 판단 책임은 이쪽에 있다.
6. **논문에 없는 주장을 대본에 쓰지 않는다.** 비유는 비유라고 말하고, 수치는 논문 값만 쓴다.
7. **임커밋 채널 로고(`raenim.imcommit.Logo`)를 쓰지 않는다.** 남의 채널 아이덴티티다. 스타일을 배우는 것과 브랜드를 가져다 쓰는 것은 다르다.

---

## 스크립트

| 스크립트 | 용도 |
|---|---|
| `preflight.py` | 환경 13항목 진단 (읽기 전용) |
| `setup_env.py` | uv 프로젝트 + manim/raenim 설치 + noise shim |
| `parse_paper.py` | 논문 PDF → `paper.json` + `paper.txt` (섹션·수식·캡션·그림) |
| `parse_code.py` | 노트북·소스 → `codebase.json` (섹션·정의·**shape 흐름 지점**) |
| `compute_facts.py` | `analysis/` 실행 → `facts.json` 검증 (수치 영상의 유일한 숫자 출처) |
| `estimate_narration.py` | 낭독 시간 추정 → `est_sec`/`run_time`/`wait` |
| `scaffold_video.py` | 에피소드 폴더 + main.py 스텁 + shots.json |
| `crop_figure.py` | 논문 PDF에서 figure 추출 (임베드 이미지 / 영역 렌더) |
| `gen_image.py` | Codex 이미지 생성 (능력 게이트 + 가드레일) |
| `render.py` | 스모크→본번 렌더, 씬 병렬, 오류 분류, LaTeX 경합 자동 재시도 |
| `verify_output.py` | 길이 정합 + 해상도 + 프레임 샘플 |
| `export_script.py` | `shots.json` → `script.md`(녹음용) + `narration.srt` |
| `tts_narrate.py` | 대본 → 나레이션 음성(edge-tts) + 실측 자막, 씬 단위 스케일 보정 |
| `mux_av.py` | 씬 결합 + 음성 + 자막(트랙 또는 태움) → `<ep>_FINAL.mp4` |
| `deliver.py` | 씬 합치기 + 납품 폴더 구성 (편별 폴더 + README) |

전부 `--json`을 지원해 기계적으로 결과를 읽을 수 있다.

## 참고 문서

- `references/imcommit-style-guide.md` — 연출 어휘, 파일 구조, 관용구, 순정 manim 회피 목록
- `references/raenim-api.md` — raenim 전체 API와 함정
- `references/narration.md` — 편성 규칙, 대본 톤, shots.json 스키마
- `references/computed-facts.md` — 계산 노드, 불변량, 개인정보 절차, 결과표 3장면 세트
- `references/generated-imagery.md` — 생성 이미지 정책과 사용법
- `references/troubleshooting.md` — preflight 복구, 렌더 오류 6종, 자주 밟는 함정

관련 스킬: 짧은 개념 클립 하나만 필요하면 `paper-to-obsidian-notion`의 `ref/visualization-manim.md`(10초~1분 클립용)를 보라. 이 스킬은 완결된 편성 영상을 만든다.
