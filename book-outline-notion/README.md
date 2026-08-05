# book-outline-notion

목차가 있는 긴 PDF(**시장조사 보고서·백서·단행본**)를 **목차 계층 그대로** Notion 중첩
데이터베이스로 옮기는 Claude Code 스킬입니다.
**497쪽 보고서(목차 725항목 · 표 310개 · 그림 234개)를 실제로 완주한 파이프라인**을 그대로 담았습니다.

## 결과물 모양

```
📚 최상위 DB (대분류 4행)
   Ⅰ. AI 산업 시장동향과 국가별 경쟁력 및 전망      ← 행을 열면
     └ 📂 하위 목차 DB (8행)
          1. AI 산업 개요 및 시장동향               ← 행을 열면
            └ 📂 하위 목차 DB (24행)
                 1) AI 산업 개요 및 분류            ← 이 행을 열면 본문 전체
```

말단 행 페이지 안:
```
💡 AI 개념·범위·가치사슬·생태계와 패러다임 변화를 다룬다     ← 한 줄 요약
📑 이 절의 상세 목차 (47항목)                               ← 접이식
─────────
H2  (1) 개요                                    ← 하위 목차가 소제목으로 흡수
    AI 발전과정, 산업 범위, 가치사슬을 다룬다
H3  1.1) AI 개념 및 발전과정
    • 인공지능(AI)은 인간의 학습, 추론, 판단…      ← 원문 그대로
    [그림Ⅰ-1] AI 기술 발전과정
    ┌────────────────┐
    │  (크롭된 도식 이미지) │
    └────────────────┘
    🔍 도식 내용 (검색용)                          ← 비전 OCR. 도식 안 글자까지 검색됨
    자료: Stanford AI Index, Gartner
    [표Ⅰ-1] AI 기술 발전단계
    ┌──────┬──────┬──────┐
    │ 단계 │ 시기 │ 특징 │                       ← 진짜 Notion 표
    └──────┴──────┴──────┘
─────────
📄 원문 43–47쪽
```

## 자매 스킬과의 차이

| | 이 스킬 | `pdf-to-notion` |
|---|---|---|
| 대상 | 목차가 있는 긴 보고서·단행본 | 강의자료 PDF/PPTX 폴더 |
| 구조 | 목차 계층 = 중첩 DB (폴더처럼) | 자료 1개 = 페이지 1개 |
| 본문 | 원문 텍스트 + 진짜 표 + 그림만 이미지 | 페이지 전체 스캔 이미지 + AI 해설 2단 |
| 검색 | 본문·표·도식 OCR까지 전부 검색됨 | 이미지라 검색 안 됨 |

## 언제 자동 호출되나

"PDF 목차 구조 그대로 노션에", "보고서를 노션 DB로", "목차랑 하위목차를 데이터베이스로 만들어줘",
"대주제 안에 또 데이터베이스 넣어서", "책/백서 노션에 정리", "PDF를 폴더 계층처럼 노션에" 등.

## 설치

저장소 루트 README의 설치 안내를 따라 이 폴더를 `~/.claude/skills/book-outline-notion/` 에 복사하세요.

## 사전 준비

- **Python 3.10+** + `PyMuPDF`, `pdfplumber`
- **Notion 통합 토큰** — 대상 DB가 통합앱과 **연결(Connections)** 돼 있어야 함.
  `NOTION_TOKEN` 환경변수 또는 작업 폴더의 `.env`(토큰 값만 적어도 됨)
- **rclone** + Google Drive remote — 그림 호스팅 (노션 image 블록은 외부 URL만 받음)
- **codex CLI**(선택) — 없으면 Claude 서브에이전트로 자동 폴백

## 사용법

```bash
export BOOK_ROOT="/path/to/작업폴더"        # PDF 가 들어있는 폴더
export BOOK_DB_ID="<대상 Notion DB URL>"    # URL 그대로 넣어도 됨

python scripts/00_preflight.py              # 구조 자동 탐지 → 환경변수 출력
# 출력된 export 줄을 그대로 실행한 뒤

python scripts/01_parse_toc.py              # 목차 트리        (게이트)
python scripts/02_extract_sections.py       # 본문 분해        (게이트)
python scripts/03_render_figures.py         # 그림 크롭
python scripts/04_ocr_figures.py            # 도식 비전 판독
python scripts/05_upload_drive.py           # Drive 업로드
python scripts/06_summaries.py              # 절별 한 줄 요약
python scripts/07_serialize.py              # 노션 블록 직렬화
python scripts/08_qa.py --sample 30         # 원문 대조 검수
python -u scripts/09_build_notion.py        # 중첩 DB 구축
python scripts/10_verify.py                 # 실측 검증
```

Windows PowerShell에서는 `$env:BOOK_ROOT = "..."` 형식을 쓰고,
모든 python 실행 앞에 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 을 붙이세요(cp949 이모지 에러 방지).

**모든 단계가 멱등**입니다. 중단해도 같은 명령을 다시 실행하면 남은 것만 처리합니다.

## 주요 설정

| 환경변수 | 기본값 | 의미 |
|---|---|---|
| `BOOK_ROOT` | 현재 폴더 | PDF가 있는 작업 폴더 |
| `BOOK_DB_ID` | (필수) | 대상 Notion DB (URL 가능) |
| `BOOK_MAX_DB_LEVEL` | `3` | **DB 행으로 만들 목차 깊이.** 그 아래는 본문 소제목 |
| `BOOK_TOC_FIRST/LAST` | 자동 탐지 | 목차 쪽 범위 |
| `BOOK_BODY_FIRST/LAST` | 자동 탐지 | 본문 쪽 범위 |
| `BOOK_EXPECTED_NODES` | 자동 탐지 | 목차 항목 수 (게이트) |
| `BOOK_LLM_BACKEND` | `auto` | `codex` / `agent` 강제 |
| `BOOK_FIG_DPI` | `200` | 그림 크롭 해상도 |

깊이가 안 맞으면 `BOOK_MAX_DB_LEVEL` 만 바꿔 **07 → 09** 만 다시 돌리면 됩니다.

## 검증

`10_verify.py` 는 추측하지 않고 **최상위 DB부터 트리를 실제로 타고 내려가며** 셉니다.

- 최상위 행 수·제목이 목차 대분류와 일치하는가
- 트리 순회로 DB 행 전부에 도달하는가 (누락·초과 0)
- image 블록 수 = 크롭한 그림 수, table 블록 수 = 추출한 표 수
- H2/H3 소제목 수 = 흡수된 하위 목차 수
- 무작위 표본의 본문이 원문과 일치하는가

## 문서

- [`references/GOTCHAS.md`](./references/GOTCHAS.md) — **실패에서 배운 13가지.** 처음 쓰기 전에 읽으세요
- [`references/SCHEMA.md`](./references/SCHEMA.md) — `_output/` 산출물 JSON 스키마

## 알아둘 것

- Notion **'하위 항목(Sub-items)'은 공개 API로 못 켭니다**(권한 문제 아님). 그래서 이 스킬은
  **인라인 DB 중첩**으로 계층을 만듭니다. UI 조작이 필요 없고 결과도 더 낫습니다.
- **텍스트→블록 변환에는 LLM을 쓰지 않습니다.** 규칙으로 전 라인이 분류되며(실측 100%),
  LLM을 넣으면 원문이 왜곡될 뿐입니다. LLM은 OCR·요약·검수에만 씁니다.
- 그림은 텍스트 레이어가 비어 있어(실측 0자) **OCR을 안 하면 검색도 요약도 안 됩니다.**
