---
name: book-outline-notion
description: 보고서·백서·단행본 PDF를 **목차 계층 그대로** Notion 중첩 데이터베이스로 변환하는 스킬. 목차 페이지를 파싱해 트리를 만들고, 대분류 DB 안에 하위 목차 DB를 중첩해 폴더처럼 파고들게 한다. 본문은 원문 텍스트를 그대로 블록화하고(표는 진짜 Notion 표, 그림은 크롭 이미지+비전 OCR), 절마다 한 줄 요약을 붙인다. 사용자가 "PDF 목차 구조 그대로 노션에", "보고서를 노션 DB로", "목차랑 하위목차를 데이터베이스로 만들어줘", "대주제 안에 또 데이터베이스 넣어서", "책/백서 노션에 정리", "PDF를 폴더 계층처럼 노션에" 라고 할 때 사용한다. 페이지마다 스캔 이미지+해설 2단으로 만드는 강의자료 변환은 pdf-to-notion 스킬을 쓴다.
---

# PDF 목차 → Notion 중첩 DB

목차가 있는 긴 PDF(시장조사 보고서·백서·단행본)를 **목차 계층 그대로** Notion으로 옮긴다.
497쪽 보고서(목차 725항목·표 310개·그림 234개)를 실제로 완주한 파이프라인이다.

## 결과물 구조

```
📚 최상위 DB (대분류만)
   Ⅰ. AI 산업 시장동향…      ← 행을 열면
     └ 📂 하위 목차 DB
          1. AI 산업 개요…     ← 행을 열면
            └ 📂 하위 목차 DB
                 1) AI 산업 개요 및 분류   ← 이 행을 열면 본문 전체
```

말단 행 페이지 = 💡 한 줄 요약 → 📑 접이식 상세 목차 → 본문
(그 아래 목차는 **H2/H3 소제목**으로 흡수. 원문 텍스트·진짜 표·그림+`🔍 도식 내용` 토글·원문 쪽 링크)

## 핵심 설계 판단 (그대로 따를 것)

1. **DB 행은 3단계까지만**(`BOOK_MAX_DB_LEVEL=3`). 문서의 논리적 계층을 그대로 옮기면
   수백 행이 평평하게 펼쳐져 **사람이 훑을 수 없다.** 그 아래는 페이지 본문의 소제목이 맞다.
2. **계층은 인라인 DB 중첩으로 만든다.** relation 속성만으로는 화면에 계층이 안 보이고,
   Notion '하위 항목(Sub-items)'은 **공개 API로 켤 수 없다**(권한 문제 아님).
3. **텍스트→블록 변환에 LLM을 쓰지 않는다.** 규칙으로 전 라인이 분류되며(실측 100%),
   LLM을 넣으면 원문이 왜곡될 뿐이다. LLM은 **OCR·요약·검수**에만 쓴다.

자세한 근거와 함정은 반드시 [`references/GOTCHAS.md`](references/GOTCHAS.md) 를 읽을 것.
산출물 구조는 [`references/SCHEMA.md`](references/SCHEMA.md).

## 사전 준비

- **Python 3.10+** + `PyMuPDF`, `pdfplumber`
- **Notion 통합 토큰** — 대상 DB가 통합앱과 **연결(Connections)** 돼 있어야 함.
  `NOTION_TOKEN` 환경변수 또는 작업 폴더의 `.env`(토큰 값만 적어도 됨)
- **rclone** + Google Drive remote — 그림을 공개 URL로 호스팅 (노션 image 블록은 외부 URL만 받음)
- **codex CLI**(선택) — 없으면 Claude 서브에이전트로 자동 폴백

## 워크플로우

작업 폴더에 PDF를 두고 환경변수 2개만 정한 뒤 번호 순서대로 실행한다.
**cp949 이모지 에러 방지를 위해 항상 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 을 붙인다.**
모든 단계는 **멱등**이라 중단 후 같은 명령을 다시 실행하면 남은 것만 처리한다.

```bash
export BOOK_ROOT="/path/to/작업폴더"
export BOOK_DB_ID="<대상 Notion DB URL 또는 ID>"
```

### Step 0. 사전 점검 + 구조 자동 탐지 ★먼저 실행
```
python scripts/00_preflight.py
```
목차 쪽 범위·본문 범위·인쇄 쪽번호 오프셋·머리말 y위치·목차 항목 수를 **스스로 찾아**
그대로 복사해 쓸 환경변수를 출력한다. 출력된 값을 `export` 한 뒤 다음 단계로 간다.

`MISS` 가 있으면 그대로 진행하지 말 것:
- `ASK>` → **`AskUserQuestion` 으로 사용자에게 확인** (대상 DB, 기존 행 덮어쓰기, rclone 인증 등)
- `FIX>` → 자동 조치 후 preflight 재실행 (최대 3회)

### Step 1~2. 목차 파싱 → 본문 분해 (게이트 2개)
```
python scripts/01_parse_toc.py        # → toc.json
python scripts/02_extract_sections.py # → sections.json, figures.json
```
- 01은 **노드 수가 기대값과 다르면 중단**한다.
- 02는 **헤딩을 하나라도 못 찾거나 본문 줄 커버리지가 100%가 아니면 중단**한다.
- 여기서 막히면 번호 체계가 다른 문서다. `config.LEVEL_PATTERNS` 를 문서에 맞게 고친다.

### Step 3~5. 그림 추출 → 판독 → 호스팅
```
python scripts/03_render_figures.py   # 크롭 PNG (그림 + 이미지로 그려진 표)
python scripts/04_ocr_figures.py      # 비전 판독 → figocr.json
python scripts/05_upload_drive.py     # Drive 업로드 + 공개 URL → drive_urls.json
```
그림은 텍스트 레이어가 비어 있어(실측 0자) **OCR을 하지 않으면 검색도 요약도 안 된다.**

### Step 6. 절별 한 줄 요약
```
python scripts/06_summaries.py        # → summaries.json
```
그림 판독 결과를 입력으로 넣어 도식 내용을 아는 상태로 요약한다.

### Step 7~8. 직렬화 → 검수
```
python scripts/07_serialize.py        # → page_blocks.json (DB 행이 될 노드만)
python scripts/08_qa.py --sample 30   # 원문 vs 변환 결과 대조 → qa.json
```
08이 지적한 것은 **원본 PDF를 직접 열어 확인한 뒤** 판단한다. LLM 지적이 오탐인 경우가 있다
(줄바꿈에 가려 띄어쓰기를 단정할 수 없는 경우 등). 실제 결함이면 02를 고치고 02→07을 다시 돌린다.

### Step 9~10. Notion 구축 → 검증
```
python -u scripts/09_build_notion.py  # 중첩 DB 생성 + 행 생성 + 본문 append
python scripts/10_verify.py           # 트리를 실제로 타고 내려가며 실측 검증
```
09는 **기존 행을 먼저 보관처리(archive)** 하고 새로 만든다. `--skip-purge` 로 건너뛸 수 있다.
10은 최상위부터 트리를 순회하며 행 수·제목·image/table 블록 수·소제목 수·원문 표본을 센다.
**여기서 전부 통과하기 전에는 완료라고 말하지 않는다.**

## LLM 백엔드

`BOOK_LLM_BACKEND` = `auto`(기본) / `codex` / `agent`

- **codex**: `codex exec` 로 배치 실행. 프롬프트는 stdin, 결과는 `-o` 파일로 받는다
  (자세한 이유는 GOTCHAS 8번).
- **agent**: codex가 없으면 자동 전환. 04·06·08 단계가 `_output/prompts/*.md` 에 프롬프트를 남긴다.
  → **Claude가 각 프롬프트를 `executor` 서브에이전트에 맡기고**, 결과 JSON을
  `_output/gen/<프롬프트와 같은 이름>.json` 으로 저장한 뒤 해당 스크립트를 다시 실행하면 이어진다.
  프롬프트 파일 상단 주석에 저장 경로와 첨부 이미지 경로가 적혀 있다.
  한 에이전트당 **프롬프트 1개**씩 맡기고, 이미지가 있으면 `Read` 로 직접 보게 한다.

## 재사용 체크리스트 (새 PDF)

1. 작업 폴더에 PDF 하나를 두고 `BOOK_ROOT`·`BOOK_DB_ID` 설정
2. `00_preflight.py` 실행 → 출력된 환경변수 `export`
3. 01·02 게이트 통과 확인 (실패하면 `LEVEL_PATTERNS` 조정)
4. 03~10 순서대로 실행
5. 목차 깊이가 안 맞으면 `BOOK_MAX_DB_LEVEL` 을 바꿔 **07 → 09 만** 다시 실행

## 주의

- **되돌리기**: `_output/notion_state.json` 에 모든 page_id가 남는다. 잘못되면 그 목록으로 archive.
- **진행률**: `python -u` 로 실행하거나 상태 파일을 본다. 버퍼링 때문에 로그가 한참 비어 보인다.
- 표·그림 개수, 소제목 개수는 **추측하지 말고 10단계로 실측**한다.
