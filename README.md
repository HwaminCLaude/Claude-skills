# Claude Skills — 코드·자료 → Notion 변환 모음

[Claude Code](https://docs.anthropic.com/claude-code) 에서 쓰는 **재사용 스킬(skill)** 저장소입니다.
강의자료(PDF/PPTX)·코드 노트북(.ipynb)·소스 코드베이스를 **Notion 데이터베이스 페이지**로 자동 변환하는 세 스킬을 폴더 단위로 담고 있어, 다른 컴퓨터에서도 그대로 내려받아 쓸 수 있습니다.

## 📦 포함된 스킬

| 폴더 | 스킬 | 한 줄 설명 |
|------|------|-----------|
| [`pdf-to-notion/`](./pdf-to-notion) | **pdf-to-notion** | PDF/PPTX 강의자료 폴더 → 페이지마다 **"PDF 이미지 \| 친근한 한국어 설명" 2단 레이아웃** 노션 페이지 |
| [`code-guidebook-notion/`](./code-guidebook-notion) | **code-guidebook-notion** | Jupyter 노트북 폴더 → **코드 0 기초자용 가이드북**(코드 한 줄 풀이 + 실행결과 + 그림 + 실무팁) 노션 페이지 |
| [`code-callgraph-notion/`](./code-callgraph-notion) | **code-callgraph-notion** | Python 코드베이스 → **함수·메서드(원자단위) 호출그래프**를 계층형 Mermaid로(GitHub 소스 라인 딥링크) 노션 페이지 |

각 스킬 폴더 안의 `README.md` 에 상세 사용법이 있습니다.

```
Claude-skills/
├── README.md                     ← (이 파일)
├── pdf-to-notion/
│   ├── SKILL.md                  ← 스킬 본문(절차·규칙). Claude가 읽고 따라 함
│   ├── README.md                 ← 사람이 읽는 사용 설명
│   ├── scripts/                  ← 파이프라인 파이썬 스크립트
│   └── references/SCHEMA.md      ← 설명 JSON 스키마
├── code-guidebook-notion/
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/
│   └── references/GUIDEBOOK_SCHEMA.md
└── code-callgraph-notion/
    ├── SKILL.md
    ├── README.md
    ├── scripts/                  ← ast_graph·build_mermaid·validate_mermaid·publish_notion
    └── references/               ← pipeline_guide.md · example_layout_nmfc.json
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
Copy-Item -Recurse -Force .\code-guidebook-notion  $dst\
Copy-Item -Recurse -Force .\code-callgraph-notion  $dst\
```

**macOS / Linux**
```bash
mkdir -p ~/.claude/skills
cp -r pdf-to-notion code-guidebook-notion code-callgraph-notion ~/.claude/skills/
```

> oh-my-claudecode(OMC)를 쓴다면 `/oh-my-claudecode:skill add <경로>` 로 등록할 수도 있습니다.

설치 후 Claude Code 세션에서 "이 폴더 PDF들 노션에 올려줘", "노트북 가이드북 만들어줘" 처럼 말하면 해당 스킬이 자동으로 호출됩니다.

## 🔧 사전 준비 (공통)

스킬을 실제로 돌리려면 아래가 필요합니다. **각 스킬은 작업 시작 시 `scripts/preflight.py` 로 이 항목들을 자동 점검**하고, 빠진 게 있으면 진행 전에 알려줍니다.

| 항목 | 용도 | 비고 |
|------|------|------|
| **Python 3.10+** | 파이프라인 실행 | |
| `pip install pymupdf pdfplumber` | PDF 분할·텍스트 추출 | pdf-to-notion 필수 |
| **rclone** + `gdrive` remote | 이미지를 Google Drive에 올려 노션에 임베드 | 인증은 사용자가 직접(`rclone config`) |
| **Notion MCP** 연결 | 노션 페이지 생성·블록 업로드 | 워크스페이스에 integration 연결 필요 |
| **LibreOffice** (선택) | PPTX → PDF 변환 | PPTX 자료가 있을 때만 |

> **`code-callgraph-notion` 은 준비물이 다릅니다** — rclone·PDF 라이브러리 대신 **mermaid-cli**(`npm i -g @mermaid-js/mermaid-cli`, 문법 검증)와 **notion-client**(`pip install notion-client`, 발행)만 있으면 됩니다. 표준 라이브러리 AST로 코드를 분석하므로 대상 코드의 의존성 설치는 불필요하고, 노드 딥링크를 쓰려면 대상 코드가 GitHub에 올라가 있으면 됩니다.

### 환경변수 (폴더·계정만 바꿔 재사용)
| 변수 | 의미 | 기본값 |
|------|------|--------|
| `METACODE_ROOT` | 작업 폴더(자료가 든 곳) | 프로젝트 루트 |
| `METACODE_DB_ID` | 업로드 대상 Notion DB ID | (지정 권장) |
| `RCLONE_BIN` | rclone 실행 파일 경로 | `C:\Users\<you>\rclone\rclone.exe` |
| `RCLONE_REMOTE` | rclone remote 이름 | `gdrive` |

> 스크립트의 기본 경로는 개발 환경(Windows) 기준입니다. **다른 컴퓨터에서는 위 환경변수로 경로를 맞춰주세요.**
> 모든 파이썬 실행에는 한글/이모지 깨짐 방지를 위해 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 를 붙입니다.

## 🔁 작업 흐름 (공통 6단계)
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
