# pdf-to-notion

PDF/PPTX 강의자료 폴더를 **Notion 데이터베이스 페이지**로 변환하는 Claude Code 스킬입니다.
페이지마다 **왼쪽=PDF 페이지 이미지 / 오른쪽=친근한 한국어 설명** 의 2단(column) 레이아웃을 만듭니다.

## 결과물 모양 (페이지 1개)
```
H1: 강의자료 제목 (파란 배경)
── PDF 페이지마다 반복 ──
  H2: 섹션 제목 또는 p001
  column_list
    ├─ 왼쪽: image (Google Drive 임베드 — 그 페이지 스캔)
    └─ 오른쪽: 그 페이지를 풀어쓴 설명 블록들 (요약 callout + 본문)
  divider
```

## 언제 자동 호출되나
"PDF를 노션에 올려줘", "강의자료 노션 변환", "이 폴더 자료들 노션 DB에 같은 작업" 등.

## 설치
저장소 루트 README의 "다른 컴퓨터에서 설치하기"를 따라 이 폴더를 `~/.claude/skills/pdf-to-notion/` 에 복사하세요.

## 사전 준비
- Python 3.10+, `pip install pymupdf pdfplumber`
- rclone + `gdrive` remote(사용자 인증), Notion MCP 연결
- PPTX가 있으면 LibreOffice(`soffice`)
- 환경변수: `METACODE_ROOT`(작업 폴더), `METACODE_DB_ID`(대상 DB)

## 사용 절차 (`scripts/`)
모든 실행에 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 를 붙입니다.

| 단계 | 스크립트 | 하는 일 |
|------|----------|---------|
| **0. 사전점검** | `preflight.py pdf "<폴더>" --db "<DB>"` | 폴더·PDF/PPTX·rclone·패키지·DB 확인. 빠지면 `ASK>`/`FIX>` 안내 |
| 1. 분할·추출 | `01_split_and_extract.py` | PDF → 페이지별 PNG + 텍스트(`content_cache.json`) |
| 2. Drive 업로드 | `02_upload_to_drive.py` | PNG → Google Drive + 공개 임베드 URL(`drive_urls.json`) |
| 3. 설명 작성 | (수기/에이전트) `explanations_*.json` | 페이지별 설명 블록. 스키마: [`references/SCHEMA.md`](./references/SCHEMA.md) |
| 3b. 병합 | `merge_explanations.py` | 여러 설명 파일 → `explanations.json` (같은 deck deep merge) |
| 4. 직렬화 | `04_serialize_blocks.py` | → `page_blocks.json` (완성 블록 시퀀스) |
| 5. 업로드 | Notion MCP | 페이지 생성 후 청크 append |

> **새 강사 자료**라면 `01_split_and_extract.py` 의 instructor 분기에 식별 키워드를 한 줄 추가하세요(없으면 `unknown`으로 분류).

## 텍스트 양식 (고정)
- 친근한 어투(~예요/~입니다), 전문용어 쉬운 말 병기
- 각 페이지 맨 위 **한 줄 요약 callout(주황 💡)**, 팁=파랑 ⚙️, 주의=빨강 ⚠️
- 핵심 **굵게**, 코드 `백틱`, 자료에 없는 내용 날조 금지

## ⚠️ 업로드 불변 규칙
- 읽은 청크를 **변형 없이 그대로** 업로드(code/image/column_list 유지). `patch-block-children`는 모든 블록 타입을 처리함.
- 업로드 에이전트는 **`executor`(sonnet)**. 25~30블록 청크, 에이전트당 청크 ≤8.

자세한 내용은 [`SKILL.md`](./SKILL.md) 참고.
