# portfolio-notion

GitHub 저장소, Google Drive 자료, 기존 Notion 페이지, 링크드인 소개에서 **확인 가능한 수치**를 모아
Notion 포트폴리오를 만들거나 재구성하는 Claude Code 스킬입니다. 겉모습(갤러리 카드)은 유지하면서 카드를 열면
"무엇을, 어떻게, 결과가 얼마나"가 수치와 근거 링크로 보이게 만드는 것이 목표입니다.

## 결과물 모양

```
메인 페이지
  Highlights ─ 숫자 중심 불릿 6줄
               3단 컬럼: [학위][경력][자격증][수료증] | [연구·논문][공모전 및 학회 활동] | [프로젝트][강의][기술]
  About Me ─ 아이콘형 카드(Tools / Ai Tools / 경력 / 학력)
  TimeLine ─ 활동 차트(섹션별 또는 반기별 막대, 분류별 색) · 타임라인
  Work / Competition / Certification / Project / Paper / Researcher ─ 기존 탭 이름 그대로의 갤러리
  포트폴리오 데이터(원본) ─ 마스터 DB "Portfolio Items" (모든 카드의 원본)

항목 페이지
  대표 이미지(썸네일) → 요약 quote(성과 문장·기간·역할·기관·기술·링크) → 기존 본문 → 결과 표·문제·접근·비용과 한계·산출물
```

실제 사례: 인라인 DB 9개(데이터 소스 15개, 50행)로 흩어져 있던 포트폴리오를 마스터 DB 1개 + 연결 뷰 18탭으로 합치고,
48페이지에 SGLang(선점 19→0건, goodput +9.1%), NMFC(저장소 7개), 교원실적 포털(pytest 340) 같은 README 기반 수치를 채웠습니다.

## 언제 자동 호출되나

"포트폴리오 노션에 만들어줘", "내 깃허브·드라이브 자료로 포트폴리오 정리", "갤러리 포트폴리오에 수치 근거 채워줘",
"타임라인·차트로 언제 뭐 했는지 보이게", "링크드인 소개처럼 하이라이트 구조화", "AI/LLM 엔지니어 취업용 포트폴리오 다듬기".

## 설치

저장소 루트 README 의 "다른 컴퓨터에서 설치하기"를 따라 이 폴더를 `~/.claude/skills/portfolio-notion/` 에 복사하세요.

## 사전 준비

- Python 3.10+, `pip install requests` (URL 검증용, 없어도 동작)
- Notion 통합 토큰: 환경변수 `NOTION_TOKEN`, 또는 Claude Code 의 Notion MCP 설정(`~/.claude.json` 의 `OPENAPI_MCP_HEADERS`)에서 자동으로 읽음.
  통합을 포트폴리오 페이지에 공유해 두어야 합니다.
- GitHub 근거 수집에 `gh auth login`, Drive 근거 수집에 `rclone`(원격 `gdrive:`), 외관 확인에 Claude in Chrome(선택).
- Notion API 는 2025-09-03(데이터 소스) 과 2026-03-11(뷰·이동) 을 직접 호출합니다. MCP 서버 버전과 무관하게 동작합니다.

## 작업 흐름 (요약)

1. `evidence_github.py`, `evidence_drive.py`, 링크드인 읽기로 근거 수집
2. `portfolio.config.json` · `items.json` · `highlights.json` · `pages_custom/` 작성 (assets 의 예시 복사)
3. `00_backup.py` → `01_create_master.py` → (`02_move_and_fill.py`) → `03_upsert_pages.py`
4. `04_build_main_page.py --dry-run` → 실행 → `05_gen_specs.py` → `06_push_content.py` → `07_cleanup_phrases.py` → `08_condense.py`
5. `09_verify.py` → Chrome 으로 확인 → `04_build_main_page.py --cleanup`

자세한 절차는 `references/WORKFLOW.md`, 입력 형식은 `references/SCHEMA.md`, 문장 규칙은 `references/STYLE.md`.

## 꼭 지키는 것

- 수치는 산출물 파일에 있는 것만. 이득 옆에 비용과 조건(n, 중앙값)을 같이.
- 이모지 없음, "근거:" "기재 예정" "측정 계획" 같은 작성 과정 문구 없음.
- 사용자의 탭 구조·이름은 그대로. 기존 블록은 지우지 않고 주변에만 삽입.
- 제목 20자, 한줄 성과 28자, Highlights 불릿 40자.

## 주의 (자세한 내용은 references/NOTION_API_GOTCHAS.md)

- 연결 뷰는 페이지 최상위에만 만들 수 있습니다(콜아웃 안 불가). 갤러리 커버 생성값은 `page_content`.
- 타임라인은 항목당 한 줄이라 압축되지 않습니다. 표 숨김 + 연 단위 줌, 그리고 차트 탭으로 보완합니다.
- status 옵션 이름은 API 로 바꿀 수 없어 영어 기본값으로 생기며 UI 에서 바꾸면 됩니다.
- `PATCH children` 응답에는 삽입 지점 이후의 형제 블록이 섞여 오므로 새 블록 id 를 셀 때 주의합니다.

## 폴더 구성

```
portfolio-notion/
├── SKILL.md
├── README.md
├── scripts/      notion_lib · evidence_github · evidence_drive · 00_backup ~ 10_highlights_layout
├── references/   WORKFLOW.md · SCHEMA.md · STYLE.md · NOTION_API_GOTCHAS.md
└── assets/       portfolio.config.example.json · schema.json · items/highlights/page_spec/concise 예시
```
