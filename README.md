# Claude Skills — 코드·자료를 배우기 쉬운 형태로 바꾸는 모음

[Claude Code](https://docs.anthropic.com/claude-code) 에서 쓰는 **재사용 스킬(skill)** 저장소입니다.
강의자료(PDF/PPTX)·보고서 PDF·코드 노트북(.ipynb)·소스 코드베이스·강의 영상+자막·연구 논문을
**공부할 수 있는 형태**로 자동 변환하거나, 실제 GPU에서 돌려 **따라 하는 실습 교재**로 만드는 열 스킬을 폴더 단위로 담고 있어, 다른 컴퓨터에서도 그대로 내려받아 쓸 수 있습니다.

출력 대상은 네 갈래입니다.

- **Notion 페이지로** — 여섯 스킬 (`*-notion`). Notion 통합 토큰·rclone 등이 필요합니다.
- **로컬 HTML 파일로** — `notebook-explainer` 하나. **외부 서비스·API 키가 필요 없습니다.**
- **영상(mp4)과 대본으로** — `paper-to-manim-video`, `ai-concept-visualization-video` 둘. Manim으로 렌더하며 **Notion을 쓰지 않습니다.**
- **실습 교재 폴더(README)로** — `runpod-lesson-builder` 하나. RunPod GPU Pod에서 **실제로 실행·촬영한 결과**로 비개발자용 따라 하기 README를 만듭니다. Notion 대신 **RunPod 계정**이 필요합니다.

## 📦 포함된 스킬

| 폴더 | 스킬 | 한 줄 설명 |
|------|------|-----------|
| [`pdf-to-notion/`](./pdf-to-notion) | **pdf-to-notion** | PDF/PPTX 강의자료 폴더 → 페이지마다 **"PDF 이미지 \| 친근한 한국어 설명" 2단 레이아웃** 노션 페이지 |
| [`book-outline-notion/`](./book-outline-notion) | **book-outline-notion** | 목차 있는 긴 보고서·백서·단행본 PDF → **목차 계층 그대로 중첩 DB**(대분류 안에 하위 목차 DB). 원문 텍스트 + 진짜 표 + 그림 비전 OCR |
| [`code-guidebook-notion/`](./code-guidebook-notion) | **code-guidebook-notion** | Jupyter 노트북 폴더 → **코드 0 기초자용 가이드북**(코드 한 줄 풀이 + 실행결과 + 그림 + 실무팁) 노션 페이지 |
| [`code-callgraph-notion/`](./code-callgraph-notion) | **code-callgraph-notion** | Python 코드베이스 → **함수·메서드(원자단위) 호출그래프**를 계층형 Mermaid로(GitHub 소스 라인 딥링크) 노션 페이지 |
| [`video-transcript-notion/`](./video-transcript-notion) | **video-transcript-notion** | 강의 영상 폴더 + 자막 → **차시마다 "영상 1개 + 그 밑에 타임스탬프 대본"** 노션 페이지 (드라이브 대량 업로드·정체 워치독 포함) |
| [`curriculum-notion/`](./curriculum-notion) | **curriculum-notion** | 강의자료 묶음 → **기초 0인 사람이 from scratch로 따라가는 학습 커리큘럼**(주차 페이지 + 유닛 중첩 DB + **자동 채점되는 Colab 노트북**) |
| [`notebook-explainer/`](./notebook-explainer) | **notebook-explainer** | 노트북·스크립트 → **단일 HTML 인터랙티브 해설**. 코드 줄마다 클릭 설명 + **텐서 shape 변화·모델 구조 위젯**(층 클릭 ↔ 코드 줄 하이라이트). 모든 수치는 노트북 출력에서 읽은 실제 값. **Notion·API 키 불필요** |
| [`paper-to-manim-video/`](./paper-to-manim-video) | **paper-to-manim-video** | 논문 PDF·코드 → **3Blue1Brown 계열 한국어 교육 영상**. 나레이션 대본과 Manim 씬 코드를 `shots.json` 하나에서 함께 만들어 **낭독 시간과 영상 길이를 자동으로 일치**시키고, 1080p60 mp4 + `script.md` + `.srt` 까지 뽑습니다. **Notion 불필요** |
| [`ai-concept-visualization-video/`](./ai-concept-visualization-video) | **ai-concept-visualization-video** | 논문·모델·코드·주제 → **AI 개념 시각화 한국어 영상**(ManimGL + raenimgl). 자막 큐(약 2초)마다 연출이 있는 씬을 렌더하고 하단 자막(+ edge-tts 음성)을 구워 mp4까지. 검정 배경·토큰 디자인·흐름 문법, 린트와 박자·디자인 측정으로 검사. **Notion 불필요** |
| [`runpod-lesson-builder/`](./runpod-lesson-builder) | **runpod-lesson-builder** | 주제 → **RunPod Pod에서 실제로 실행한 결과로 만든 레슨별 독립형 실습 README**(STEP마다 실화면·모자이크, 🎙️ 해설 대본, 로그·기대 출력, 품질 검사). 시작할 때 범위·산출물·Pod·비용을 **먼저 대화형으로 묻고**, 여러 Pod로 병렬 제작한 뒤 내용 검토·REPORT까지 하고 **쓴 Pod를 Stop**합니다. **Notion 불필요** |

각 스킬 폴더 안의 `README.md` 에 상세 사용법이 있습니다.

```
Claude-skills/
├── README.md                     ← (이 파일)
├── pdf-to-notion/
│   ├── SKILL.md                  ← 스킬 본문(절차·규칙). Claude가 읽고 따라 함
│   ├── README.md                 ← 사람이 읽는 사용 설명
│   ├── scripts/                  ← 파이프라인 파이썬 스크립트
│   └── references/SCHEMA.md      ← 설명 JSON 스키마
├── book-outline-notion/
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/                  ← 00_preflight ~ 10_verify (구조 자동탐지·중첩DB 구축)
│   └── references/               ← GOTCHAS.md · SCHEMA.md
├── code-guidebook-notion/
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/
│   └── references/GUIDEBOOK_SCHEMA.md
├── code-callgraph-notion/
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/                  ← ast_graph·build_mermaid·validate_mermaid·publish_notion
│   └── references/               ← pipeline_guide.md · example_layout_nmfc.json
├── video-transcript-notion/
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/                  ← 01_scan·02_upload_videos·03_build_pages·04_sync_videos·06_verify·dashboard
│   └── references/               ← CONFIG.md · GOTCHAS.md
├── curriculum-notion/
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/                  ← curriculum·publish_skeleton·publish_all·build_unit_notebook·run_weeks·verify_*
│   └── references/               ← AUTHORING_CONTRACT.md · example_curriculum.json · example_unit_W04U05.py
├── notebook-explainer/           ← Notion을 쓰지 않는 스킬 (로컬 HTML 출력)
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/                  ← extract_notebook.py(base64·ANSI 제거) · verify_page.js(브라우저 검증)
│   └── references/               ← widget-recipes.md · architecture-recipes.md
├── paper-to-manim-video/         ← Notion을 쓰지 않는 스킬 (mp4 영상 + 대본 출력)
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/                  ← preflight·setup_env·parse_paper·estimate_narration·
│   │                                scaffold_video·crop_figure·gen_image·render·
│   │                                verify_output·export_script·deliver
│   ├── references/               ← imcommit-style-guide · raenim-api · narration ·
│   │                                generated-imagery · troubleshooting
│   └── assets/                   ← manim 프로젝트 템플릿 · noise 순수파이썬 shim
├── ai-concept-visualization-video/  ← Notion을 쓰지 않는 스킬 (ManimGL 영상 + 자막 mp4 출력)
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/                  ← scaffold·setup_env·preflight·fetch_examples·parse_paper·parse_code·
│   │                                crop_figure·tts·cues·lint·render·captions·assemble·
│   │                                measure_motion·measure_design·sweep_frames
│   ├── references/               ← shots-schema · narration-voice · captions · flow-grammar · design-system ·
│   │                                onscreen-text · raenimgl-api · example-corpus · troubleshooting
│   ├── assets/                   ← ManimGL 프로젝트 틀(pyproject · custom_config · vizkit · main 틀)
│   └── tests/                    ← pytest
└── runpod-lesson-builder/        ← Notion을 쓰지 않는 스킬 (RunPod 실습 README 폴더 출력)
    ├── SKILL.md
    ├── README.md
    ├── scripts/                  ← init_course·pod/pod_get·jlab·webshot·redact·annotate·
    │                                check_lesson·setup.sh·stackcheck.sh
    ├── references/               ← intake-interview(시작 인터뷰) · workflow · lesson-guide ·
    │                                runpod-jupyterlab-facts · pitfalls · verification · parallel-production
    └── assets/                   ← README·playbook·결정 기록·LESSON_GUIDE 틀, 워크플로 틀, 예시 레슨
```

## 🚀 다른 컴퓨터에서 설치하기

### 1) 저장소 클론
```bash
git clone https://github.com/HwaminCLaude/Claude-skills.git
```

### 2) 스킬 폴더를 Claude 스킬 디렉터리로 복사
Claude Code는 `~/.claude/skills/<스킬이름>/SKILL.md` 위치의 스킬을 인식합니다.

**Windows (PowerShell)**
```powershell
$dst = "$env:USERPROFILE\.claude\skills"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item -Recurse -Force .\pdf-to-notion          $dst\
Copy-Item -Recurse -Force .\book-outline-notion    $dst\
Copy-Item -Recurse -Force .\code-guidebook-notion  $dst\
Copy-Item -Recurse -Force .\code-callgraph-notion  $dst\
Copy-Item -Recurse -Force .\video-transcript-notion $dst\
Copy-Item -Recurse -Force .\curriculum-notion       $dst\
Copy-Item -Recurse -Force .\notebook-explainer      $dst\
Copy-Item -Recurse -Force .\paper-to-manim-video    $dst\
Copy-Item -Recurse -Force .\ai-concept-visualization-video $dst\
Copy-Item -Recurse -Force .\runpod-lesson-builder   $dst\
```

**macOS / Linux**
```bash
mkdir -p ~/.claude/skills
cp -r pdf-to-notion book-outline-notion code-guidebook-notion code-callgraph-notion \
      video-transcript-notion curriculum-notion notebook-explainer paper-to-manim-video \
      runpod-lesson-builder ai-concept-visualization-video \
      ~/.claude/skills/
```

> oh-my-claudecode(OMC)를 쓴다면 `/oh-my-claudecode:skill add <경로>` 로 등록할 수도 있습니다.

설치 후 Claude Code 세션에서 "이 폴더 PDF들 노션에 올려줘", "노트북 가이드북 만들어줘", "강의 영상이랑 대본 노션에 정리해줘", "RunPod 실습 교재 만들어줘", "이 논문으로 AI 개념 시각화 영상 만들어줘" 처럼 말하면 해당 스킬이 자동으로 호출됩니다.

## 🔧 사전 준비 (공통)

스킬을 실제로 돌리려면 아래가 필요합니다. **각 스킬은 작업 시작 시 `scripts/preflight.py` 로 이 항목들을 자동 점검**하고, 빠진 게 있으면 진행 전에 알려줍니다.

| 항목 | 용도 | 비고 |
|------|------|------|
| **Python 3.10+** | 파이프라인 실행 | |
| `pip install pymupdf pdfplumber` | PDF 분할·텍스트 추출 | pdf-to-notion 필수 |
| **rclone** + `gdrive` remote | 이미지를 Google Drive에 올려 노션에 임베드 | 인증은 사용자가 직접(`rclone config`) |
| **Notion MCP** 연결 | 노션 페이지 생성·블록 업로드 | 워크스페이스에 integration 연결 필요 |
| **LibreOffice** (선택) | PPTX → PDF 변환 | PPTX 자료가 있을 때만 |

> **`video-transcript-notion` 은 준비물이 다릅니다** — PDF 라이브러리 없이 **rclone**(영상 업로드)과 **Notion 통합 토큰**만 있으면 됩니다. 자막 길이 실측·화질 진단에 **ffprobe**(선택)를 씁니다. 표준 라이브러리만 쓰므로 별도 pip 설치가 필요 없습니다.

> **`book-outline-notion` 은 준비물이 다릅니다** — `pymupdf`·`pdfplumber`·**rclone**(그림 호스팅)과 **Notion 통합 토큰**이 필요하고, MCP 없이 REST 를 직접 호출합니다. 도식 OCR·요약은 **codex CLI**(선택)로 돌리며, 없으면 Claude 서브에이전트로 자동 폴백합니다.

> **`code-callgraph-notion` 은 준비물이 다릅니다** — rclone·PDF 라이브러리 대신 **mermaid-cli**(`npm i -g @mermaid-js/mermaid-cli`, 문법 검증)와 **notion-client**(`pip install notion-client`, 발행)만 있으면 됩니다. 표준 라이브러리 AST로 코드를 분석하므로 대상 코드의 의존성 설치는 불필요하고, 노드 딥링크를 쓰려면 대상 코드가 GitHub에 올라가 있으면 됩니다.

> **`paper-to-manim-video` 는 준비물이 완전히 다릅니다** — Notion·rclone을 쓰지 않는 대신
> **Python 3.11**, [**uv**](https://docs.astral.sh/uv/), **FFmpeg**, **LaTeX(MiKTeX)** 가 필요합니다.
> `manim==0.20.1` 과 [`raenim`](https://github.com/CodingVillainKor/raenim) 은 `scripts/setup_env.py` 가 전용 venv에 자동 설치합니다
> (`noise` 패키지는 cp311 휠이 없어 빌드가 실패하는 게 정상이며, 순수 파이썬 shim으로 자동 대체됩니다).
> **codex CLI** 가 있으면 은유 컷을 이미지 생성으로 채우고, 없으면 그 노드만 꺼진 채 전 구간 Manim 작도로 진행합니다.
> 작업 폴더는 **ASCII 경로**(`C:\manimwork\<slug>`)로 잡으세요 — MiKTeX가 한글 경로에서 실패합니다.

> **`ai-concept-visualization-video` 도 Notion·rclone을 쓰지 않습니다** — 대신
> [**uv**](https://docs.astral.sh/uv/)(프로젝트 venv, Python 3.10.18은 uv가 받음), **git**, **FFmpeg**(`subtitles` 필터·libass), **LaTeX(MiKTeX)**,
> 글꼴 **Noto Sans KR**(자막용 정적 `NotoSansKR-Medium.ttf` 포함)이 필요합니다. ManimGL 포크와 `raenimgl` 은 `scripts/setup_env.py` 의 `uv sync` 가 GitHub에서 받습니다.
> 연출 예시 코퍼스는 저장소에 넣지 않았습니다(원본에 라이선스 파일이 없음). 필요하면 `scripts/fetch_examples.py` 로 원본 공개 저장소에서 받습니다.
> 작업 폴더는 **ASCII 경로**(`C:\manimwork\<slug>`)로 잡으세요.

> **`runpod-lesson-builder` 는 준비물이 완전히 다릅니다** — Notion·rclone 대신
> **RunPod 계정**(크레딧, Credentials → SSH Public Keys의 **SSH 공개키 등록**), RunPod에 로그인한 **Claude in Chrome** 확장, **Git Bash**(Windows),
> **Python 3.10+** 와 `pip install pyyaml pillow playwright nbformat` + `playwright install chromium` 이 필요합니다.
> 여러 레슨을 병렬로 만들려면 Claude Code의 **Workflow** 도구를 씁니다(사용자가 요청할 때만, 없으면 차례로).
> 시작 인터뷰가 이 항목들을 먼저 조사하고, 사람이 직접 해야 하는 것(로그인·SSH 키·Deploy 승인)만 물어봅니다. Pod 비용은 사용자 계정에 청구됩니다.

> **`notebook-explainer` 는 위 준비물이 하나도 필요 없습니다** — Notion 토큰도, rclone도, PDF 라이브러리도 쓰지 않습니다.
> 결과물이 로컬 HTML 파일 하나이기 때문입니다. **Python 표준 라이브러리만으로 추출이 돌아가고**,
> 생성된 페이지를 실제 브라우저로 검증하려면 Node + playwright만 한 번 깔면 됩니다
> (`npm i -g playwright && npx playwright install chromium-headless-shell`). 검증은 생략해도 페이지는 만들어집니다.

### 환경변수 (폴더·계정만 바꿔 재사용)
| 변수 | 의미 | 기본값 |
|------|------|--------|
| `METACODE_ROOT` | 작업 폴더(자료가 든 곳) | 프로젝트 루트 |
| `METACODE_DB_ID` | 업로드 대상 Notion DB ID | (지정 권장) |
| `RCLONE_BIN` | rclone 실행 파일 경로 | `C:\Users\<you>\rclone\rclone.exe` |
| `RCLONE_REMOTE` | rclone remote 이름 | `gdrive` |

> 스크립트의 기본 경로는 개발 환경(Windows) 기준입니다. **다른 컴퓨터에서는 위 환경변수로 경로를 맞춰주세요.**
> 모든 파이썬 실행에는 한글/이모지 깨짐 방지를 위해 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 를 붙입니다.

## 🔁 작업 흐름 (Notion 계열 공통 6단계)

> `notebook-explainer` 는 이 흐름을 따르지 않습니다 —
> **추출 → 시각화 인벤토리 작성 → 단일 HTML 작성 → 브라우저 검증 → 원본 옆에 저장** 네 단계로 끝나고,
> 2·5단계(Drive 업로드·Notion 업로드)가 아예 없습니다.

> `paper-to-manim-video` 도 이 흐름을 따르지 않습니다 —
> **환경 검증 → 논문/코드 파싱 → 시리즈 편성(CP1) → 대본+shots.json(CP2) → 씬 코드 →
> 스모크 렌더 → 본번 렌더 → 길이 정합 검증(CP3)** 8단계이고, Drive·Notion 단계가 없습니다.
> 체크포인트 세 곳에서 사람의 승인을 받습니다.

> `ai-concept-visualization-video` 도 이 흐름을 따르지 않습니다 —
> **준비(scaffold·uv·preflight) → 입력 → 편성(사용자 확인) → 대본 shots.json(사용자 검토) → 음성(tts) → 씬 코드 →
> 린트·스모크 렌더 → 본번 렌더 → 합치기(자막·음성) → 측정·프레임 스윕·보고** 순서이고, Drive·Notion 단계가 없습니다.

> `runpod-lesson-builder` 도 이 흐름을 따르지 않습니다 —
> **시작 인터뷰 → 사전 점검·승인 → Pod 환경 → 파일럿 레슨(실행·실화면·README·품질 검사) → README만 보고 재현 검증 →
> 병렬 제작 → 끝난 뒤 내용 검토 → REPORT.md → 쓴 Pod Stop** 순서이고, Drive·Notion 단계가 없습니다.

0. **사전 점검**(`preflight.py`) — 폴더·자료·rclone·패키지·DB 확인. 빠진 건 사용자에게 요구하거나 자동 조치 후 재점검.
1. 자료 추출 (PDF 분할/텍스트, 노트북 코드·출력·그림)
2. 이미지 Google Drive 업로드 + 공개 임베드 URL 생성
3. 설명/가이드북 본문 작성 (친근한 한국어, 정해진 양식)
4. 노션 블록으로 직렬화 + 청크 분할
5. Notion MCP로 페이지 생성 후 청크 업로드
6. 업로드 결과 검증(블록 보존·개수)

## ⚠️ 핵심 주의사항 (실패 방지)
- **블록 변형 금지**: `mcp__notion__API-patch-block-children` 는 스키마에 paragraph만 보여도 code·image·equation·callout·column_list 등 **모든 블록을 처리**합니다. 읽은 청크를 변형 없이 그대로 올려야 합니다.
- **업로드 에이전트는 sonnet**(`executor`). opus(`executor-high`)는 Notion MCP가 노출 안 돼 업로드 불가.
- **청크 누적 버그**: 한 에이전트에 청크가 많으면(8개+) 합쳐 보내 거대 요청 에러가 날 수 있음 → 에이전트당 청크 ≤8, 순차 배치.
- 노션 **100블록/요청 제한** → 보수적으로 25~30블록 단위 청크.

자세한 절차·양식·예외 처리는 각 스킬의 `SKILL.md` 와 `references/` 를 참고하세요.

## 라이선스
개인 사용 목적. 자유롭게 가져다 쓰되 내부의 개인 경로/DB ID는 본인 환경에 맞게 바꿔 사용하세요.
