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

`resume`은 별도 상태 파일을 쓰지 않고 **산출물의 존재로 판단**한다: `paper.json` 있으면 Stage 1 통과, `spec.json` 있으면 CP0 통과(다시 묻지 않는다), 에피소드 폴더의 `shots.json`에 `narration`이 차 있으면 Stage 3 통과, `main.py`에 스텁이 아닌 본문이 있으면 Stage 4 통과, `media/videos/main/1080p60/*.mp4`가 있으면 Stage 6 통과. 파일이 곧 체크포인트라 중간에 사람이 손으로 고쳐도 그대로 이어진다.

사용자가 처음부터 방식을 지정했으면(예: "3편으로", "노트북은 됐고", "자막만") **CP0을 묻지 않고**
그 값으로 `spec.json`을 채운 뒤 진행한다. 인터랙티브는 정보가 없을 때만 쓴다.

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

### Stage 1.5 — 제작 사양  → **CP0 인터랙티브 선택**

파싱이 끝나면 **바로 대본을 쓰지 않는다.** 사양을 먼저 확정한다 — 나중에 바꾸면 대본부터 다시 써야 한다.

**한 번 정해진 문항은 다시 묻지 않는다.** 확정값은 `references/production-spec.md`의
표에 적어두고, CP0에서는 아직 안 정해진 것만 올린다.

| 문항 | 선택지 | 현재 확정값 |
|---|---|---|
| **편성** | `list_templates.py`가 JSON에서 읽어온다 (현재 5종) | **매번 묻는다** (논문 분량에 따라 다르다고 함) |
| **실습** | 노트북 3권 / 1권 / 없음 | 3권 — 묻지 않는다 |
| **나레이션** | 음성+자막 트랙 / 음성+태운 자막 / 자막만(직접 녹음) | 음성+자막 트랙 — 묻지 않는다 |
| **검수** | 표준 / 정밀 / 빠름 | 표준 — 묻지 않는다 |

그래서 실제 CP0은 **`AskUserQuestion`으로 편성 한 문항만** 올린다.
선택지는 **문서에 적지 말고 스크립트로 뽑는다** — 템플릿이 늘어나도 고칠 곳이 없다:

```bash
python scripts/list_templates.py --json      # options 형태로 그대로 쓴다
```

논문·코드 분량을 보고 권장안을 첫 번째에 놓는다(`AskUserQuestion`은 최대 4개까지만
받으므로 템플릿이 4종을 넘으면 이번 논문에 맞는 것만 추린다. 나머지는 "직접 지정"으로 받는다).
나머지 세 문항은 기본값으로 `spec.json`에 채우고 편성안 제시 때 한 줄로 알린다.

새 템플릿은 `assets/series_templates.local.json`에 넣는다 — 스킬을 업데이트해도 남고
선택지에 자동으로 뜬다. 형식과 필수 필드: `references/production-spec.md`

"직접 지정"(Other)은 자동으로 붙는다. **사용자가 직접 적으면 템플릿을 버리고 그 말을 따른다.**
답은 `<root>/spec.json`에 적어 뒤 단계가 읽게 한다.

템플릿 내용: `assets/series_templates.json` · 문항 문구와 영향: `references/production-spec.md`

### Stage 2 — 시리즈 편성  → **CP1 사용자 승인**

고른 템플릿을 뼈대로, **논문의 실제 절 구성에 맞춰** 편별 제목·구간을 다시 짠다.
한 편 = 한 아이디어, 5~8분, 구간 4~11개, 구간 하나 90초 이하.
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

**새로 짜기 전에 `references/scene-templates.md`에서 고른다.** 표·코드·논문그림·수식·검산·
도식·차트·카드 8종의 검증된 배치가 좌표까지 적혀 있다. 자리 다툼이 이 스택에서 가장 흔한 결함이다.

연출 어휘와 관용구: `references/imcommit-style-guide.md`
raenim API: `references/raenim-api.md`

### Stage 5 — 스모크 렌더 + 자동 수정

```bash
python scripts/render.py --episode <ep> --quality ql
```

480p15로 전 구간을 먼저 통과시킨다. 오류는 `error_kind`로 분류되어 조치가 함께 나온다. **자동 수정 최대 3회**, 초과하면 연출을 낮추거나 사용자에게 올린다.

### Stage 5.5 — 정적 린트  (검수 강도와 무관하게 **항상**)

```bash
python scripts/lint_scenes.py --root C:/manimwork/<slug>
```

**렌더가 성공하는데 화면이 틀리는** 조합 10종을 잡는다 — 고정폭 폰트에 한글(두부),
이모지(점 없는 mobject → `move_to` 무효), `Line(path_arc).set_opacity()`(호가 흰 덩어리),
등장+`Indicate` 동시(값이 사라짐), `highlight()`의 `disappear` 미재생(강조 찌꺼기) 등.

ERROR가 있으면 본번 렌더로 넘어가지 않는다. 규칙별 설명: `references/visual-qa.md` §1

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
python scripts/verify_output.py --episode <ep> --quality qh --frames 3   # 길이·해상도
python scripts/sweep_frames.py  --root <root>  --quality qh              # 구간당 3장
```

`verify_output.py`는 실제 mp4 길이와 `sum(run_time + wait)`를 비교해 **오차 15% 초과면 REWORK**.

**여기서 끝내지 않는다.** 길이가 맞아도 화면은 틀릴 수 있다 — 글자 겹침, 화면 밖 잘림,
사라졌어야 할 찌꺼기, 두부(□). 실제 두 시리즈(79구간)에서 이런 결함이 **19건** 나왔고
전부 프레임을 눈으로 보고서야 발견했다. 자동 검증은 한 건도 못 잡았다.

`sweep_frames.py`가 구간마다 **35% · 70% · 마지막** 세 지점을 뽑는다. 41구간이면 123장이다.
한 번에 6~8장씩 `Read`로 본다. 무엇을 찾고 무엇이 정상인지: `references/visual-qa.md` §2

고친 구간은 **다시 렌더하고 다시 스윕**한다. 납품용 검수 프레임도 재렌더 이후에 다시 뽑는다.

CP3에는 다음을 올린다:
- 생성 이미지를 쓴 컷 전부 (0개면 0개라고 명시)
- REWORK 판정 구간
- 논문 수치를 인용한 컷 — png로 뽑아 `SendUserFile`로 보낸다
- 스윕에서 고친 결함 목록 (몇 장 봤고 몇 건 고쳤는지)

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
   특히 "논문에 없다", "A라서 B다" 류의 단정은 원문에서 다시 확인한다 —
   서로 다른 모델의 수치를 한 문장으로 잇는 실수가 실제로 나왔다(12시간=base 27.3 ↔ 28.4=big 3.5일).
7. **임커밋 채널 로고(`raenim.imcommit.Logo`)를 쓰지 않는다.** 남의 채널 아이덴티티다. 스타일을 배우는 것과 브랜드를 가져다 쓰는 것은 다르다.
8. **이모지를 쓰지 않는다.** 🔍 🔒 ⚡ 는 Malgun Gothic에 글립이 없어 **점이 하나도 없는 mobject**가 된다.
   그러면 `move_to`가 무효가 되고 `next_to`로 붙인 이웃까지 원점으로 끌려간다. 도형으로 그린다.
   (`✔ ✕ → ← ①②③`은 KR 폰트에 있어 안전하다.)
9. **배치 전에 이미 화면에 있는 것의 범위를 센다.** 프레임은 x ∈ [−7.11, 7.11], y ∈ [−4, 4].
   `next_to`는 기준물 **가운데**에 맞추므로, 좁은 기준물 옆의 긴 한글 라벨은 화면 밖으로 나간다.
10. **렌더가 성공했다고 끝이 아니다.** Stage 5.5 린트와 Stage 8 프레임 스윕을 건너뛰지 않는다.
    길이·해상도 검증을 전부 통과하고도 화면이 틀린 결함이 두 시리즈에서 19건 나왔다.

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
| `list_templates.py` | 편성 템플릿 목록 → CP0 선택지 (`--json`). `.local.json` 추가분 자동 병합 |
| `lint_scenes.py` | **렌더 전** 정적 검사 10종 — 렌더는 되는데 화면이 틀리는 조합 |
| `render.py` | 스모크→본번 렌더, 씬 병렬, 오류 분류, LaTeX 경합 자동 재시도 |
| `verify_output.py` | 길이 정합 + 해상도 + 프레임 샘플 |
| `sweep_frames.py` | **렌더 후** 구간당 N지점 프레임 추출 (눈으로 볼 것) |
| `export_script.py` | `shots.json` → `script.md`(녹음용) + `narration.srt` |
| `tts_narrate.py` | 대본 → 나레이션 음성(edge-tts) + 실측 자막, 씬 단위 스케일 보정 |
| `mux_av.py` | 씬 결합 + 음성 + 자막(트랙 또는 태움) → `<ep>_FINAL.mp4` |
| `deliver.py` | 씬 합치기 + 납품 폴더 구성 (편별 폴더 + README) |

전부 `--json`을 지원해 기계적으로 결과를 읽을 수 있다.

## 참고 문서

- `references/production-spec.md` — **CP0 인터랙티브 문항**과 답이 뒤 단계에 미치는 영향
- `references/scene-templates.md` — **검증된 씬 배치 8종** (좌표 포함). 새로 짜기 전에 여기서 고른다
- `references/visual-qa.md` — **린트 규칙 10종 + 프레임 스윕 절차**. 조용히 틀리는 결함의 방어선
- `references/imcommit-style-guide.md` — 연출 어휘, 파일 구조, 관용구, 순정 manim 회피 목록
- `references/raenim-api.md` — raenim 전체 API와 함정
- `references/narration.md` — 편성 규칙, 대본 톤, shots.json 스키마
- `references/computed-facts.md` — 계산 노드, 불변량, 개인정보 절차, 결과표 3장면 세트
- `references/generated-imagery.md` — 생성 이미지 정책과 사용법
- `references/troubleshooting.md` — preflight 복구, 렌더 오류 6종, 자주 밟는 함정

## 템플릿

- `assets/series_templates.json` — 편성 5종 (`series-5` / `series-3` / `single` / `code-first` / `results-first`)
- `assets/project_template/` — `main.py` 스텁 + `manim.cfg`

관련 스킬: 짧은 개념 클립 하나만 필요하면 `paper-to-obsidian-notion`의 `ref/visualization-manim.md`(10초~1분 클립용)를 보라. 이 스킬은 완결된 편성 영상을 만든다.
