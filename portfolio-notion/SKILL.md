---
name: portfolio-notion
description: GitHub 저장소·Google Drive 자료·기존 Notion 페이지·링크드인 소개 같은 원천 자료에서 수치 근거를 모아 Notion 포트폴리오를 만들거나 재구성하는 스킬. 마스터 DB 1개(섹션·분류·기간·한줄 성과·링크·관련 항목) 위에 갤러리 탭·활동 차트·타임라인 연결 뷰를 올리고, 메인 페이지 상단에 링크드인 소개 구조의 Highlights(숫자 중심 6줄 + 3단 컬럼 이력)를 만들며, 항목 페이지마다 요약 quote와 결과 표·문제·접근·비용과 한계·산출물 절을 채운다. 수치는 산출물 파일에서 확인된 것만 쓰고 이모지와 작성 과정 문구를 넣지 않는다. 사용자가 "포트폴리오 노션에 만들어줘", "내 깃허브·드라이브 자료로 포트폴리오 정리", "갤러리 포트폴리오에 수치 근거 채워줘", "타임라인·차트로 언제 뭐 했는지 보이게", "링크드인 소개처럼 하이라이트 구조화", "AI/LLM 엔지니어 취업용 포트폴리오 다듬기"라고 할 때 사용한다. PDF 강의자료 변환은 pdf-to-notion, 노트북 가이드북은 code-guidebook-notion을 쓴다.
---

# 포트폴리오 Notion 구축·재구성

원천 자료(GitHub, Drive, 기존 Notion, 링크드인)에서 **확인 가능한 수치**를 모아, 채용 담당자가 30초 안에
"무엇을, 어떻게, 결과가 얼마나"를 읽는 Notion 포트폴리오를 만든다. 실제로 정화민 포트폴리오(인라인 DB 9개·데이터 소스 15개·
50행)를 마스터 DB 1개 + 연결 뷰 18탭으로 재구성하고 48페이지에 근거 기반 본문을 채운 파이프라인을 그대로 재현한다.

## 결과물 구조

```
메인 페이지
├─ 헤더(사진·연락처·버튼)            ← 건드리지 않음
├─ Highlights (heading_2)
│   ├─ 숫자 중심 불릿 6줄              ← 날짜 없음, 각 줄 성과 1개
│   └─ 3단 컬럼: [학위][경력][자격증][수료증] / [연구·논문][공모전 및 학회 활동] / [프로젝트][강의][기술]
├─ About Me (heading_2) + 연결 블록: Tools·Ai Tools(아이콘형 small/compact) · 경력 · 학력
├─ TimeLine (heading_2) + 연결 블록: 활동 차트(column, x=섹션 또는 반기, stack=분류) · 타임라인 보기
├─ Work / Competition / Certification / Project / Paper / Researcher (heading_1 파란 배경) + 연결 블록(탭 = 기존 탭 이름)
└─ 포트폴리오 데이터(원본) 하위 페이지 ← 마스터 DB "Portfolio Items" (모든 카드의 원본, 여기서 항목 추가)

항목 페이지
├─ 대표 이미지(기존 첫 블록, 갤러리 썸네일)
├─ 요약 quote: 긴 성과 문장 / 기간 / 역할 / 기관 / 기술 / 링크
├─ 기존 본문(보존)
└─ 추가 절(대표 항목): 핵심 결과 표 → 문제 → 접근 → 비용과 한계 → 산출물(링크)
```

## 원칙 (어기면 다시 한다)

1. 수치는 README·결과 파일·노트북 출력·원고·수료증에 있는 것만. 없으면 규모 수치로 대체하거나 쓰지 않는다. 계산해 만든 퍼센트 금지.
2. 이득 옆에 비용·조건(n, 중앙값, 단일 런)을 같은 표에 적는다. 공동 작업은 "팀 결과"로 구분한다.
3. 이모지 금지(콜아웃 대신 quote·표·제목). 페이지·DB 아이콘을 만들지 않는다.
4. 작성 과정을 드러내는 문장 금지: "본 페이지의 …는 YYYY-MM-DD 기준 … 에서 정리", "근거:", "근거 수준:", "기재 예정", "측정 계획:".
   근거는 "산출물" 절의 링크로만 남긴다.
5. 사용자가 만든 섹션(탭) 구조·이름은 그대로 둔다. 데이터 소스 이름·오타·빈 행만 고친다.
6. 제목 20자, 한줄 성과 28자(숫자 먼저), Highlights 불릿 40자, 컬럼 한 줄 30자.
7. 기존 블록은 옮기거나 지우지 않고 주변에만 삽입한다(Notion 호스팅 이미지는 URL 로 재생성 불가). 삭제는 휴지통(복구 가능)으로.
8. 날짜를 모르면 비운다. 월만 알면 1일~말일. 추정하지 않는다.

## 절차

세부 명령과 입력 형식은 `references/WORKFLOW.md`, `references/SCHEMA.md`. 문장 규칙은 `references/STYLE.md`.
Notion API 함정은 `references/NOTION_API_GOTCHAS.md` 를 작업 전에 한 번 읽는다.

1. **인테이크**: 메인 페이지 URL, 자료 위치(GitHub 계정·Drive 폴더·링크드인), 목표 직무를 확인한다. 이미 들은 것은 묻지 않는다.
   "묻지 말고 진행"이면 WORKFLOW.md 의 기본값으로 진행하고 끝에 결정 목록을 보고한다.
2. **근거 수집**: `scripts/evidence_github.py <user…>` 로 저장소 표와 README 숫자 줄을, `scripts/evidence_drive.py gdrive: <폴더…>` 로
   Drive 트리와 설계서를 모은다. 링크드인은 사용자 Chrome 으로 `linkedin.com/in/me/` 를 읽어 소개 구조와 날짜를 가져온다.
   기존 Notion 이 있으면 `scripts/00_backup.py` 로 행·본문·뷰·파일을 백업한다(파일 URL 은 1시간 만료).
3. **큐레이션**: 작업 폴더에 `portfolio.config.json`(assets 예시 복사), `schema.json`, `items.json`, `highlights.json`,
   `pages_custom/<key>.json`, `concise.json` 을 쓴다. 항목마다 섹션·분류·기간·짧은 성과·긴 성과·역할·링크를 채우고,
   수치 출처 파일을 `number_checks` 에 적는다.
4. **구축**: `01_create_master.py` → (재구성이면 `02_move_and_fill.py`) → `03_upsert_pages.py` → `04_build_main_page.py --dry-run`
   확인 후 실행 → `05_gen_specs.py` → `06_push_content.py` → `07_cleanup_phrases.py` → `08_condense.py`.
5. **검증**: `09_verify.py`(행 수·탭별 행 수·파일·URL·수치 재확인) 통과 후 Chrome 으로 Highlights·갤러리 첫 탭·차트를 눈으로 본다.
   그 다음에만 `04_build_main_page.py --cleanup` 으로 옛 블록을 휴지통에 보낸다.
6. **보고**: 바꾼 것, 삭제한 것(복구 방법), 사용자가 채울 것(미확정 날짜·불일치 수치·상태 옵션 이름), 만들지 않은 후보와 이유,
   스크립트·백업 위치. 이모지·장식 없이.

## 자주 쓰는 명령

```bash
export PORTFOLIO_DIR=/path/to/work            # 작업 폴더 (기본 cwd)
S=~/.claude/skills/portfolio-notion/scripts
python $S/evidence_github.py HwaminJung00 Junghwamin
python $S/00_backup.py && python $S/01_create_master.py
python $S/03_upsert_pages.py && python $S/04_build_main_page.py --dry-run && python $S/04_build_main_page.py
python $S/05_gen_specs.py && python $S/06_push_content.py && python $S/07_cleanup_phrases.py && python $S/08_condense.py
python $S/09_verify.py
python $S/10_highlights_layout.py             # Highlights 문구만 바꿨을 때
```

## 스크립트

| 파일 | 역할 |
|---|---|
| `scripts/notion_lib.py` | 설정·토큰 로딩, REST 호출(재시도), 페이지네이션, rich text 변환, 블록 빌더 |
| `scripts/evidence_github.py`, `evidence_drive.py` | 근거 수집(저장소 표·README 숫자 줄, Drive 트리·설계서) |
| `scripts/00_backup.py` | 기존 DB·메인 페이지·파일 백업 |
| `scripts/01_create_master.py` | 하위 페이지 + 마스터 DB + relation + 반기 formula |
| `scripts/02_move_and_fill.py` | 기존 행 move, 옛 내부 링크 → relation, 파일 열 통합, `--cleanup-legacy` |
| `scripts/03_upsert_pages.py` | items.json 속성 쓰기, 신규 페이지(썸네일) 생성, related 관계 |
| `scripts/04_build_main_page.py` | Highlights + 섹션 제목 + 연결 블록·탭(갤러리·차트·타임라인·보드), `--dry-run`, `--cleanup` |
| `scripts/05_gen_specs.py`, `06_push_content.py` | 요약 quote·추가 절 생성과 멱등 삽입 |
| `scripts/07_cleanup_phrases.py` | 기계 작성 티 나는 문구·절 제거 |
| `scripts/08_condense.py` | 제목·한줄 성과 축약 적용 |
| `scripts/09_verify.py` | 구조·탭·파일·URL·수치 출처 검증 |
| `scripts/10_highlights_layout.py` | Highlights(6줄 + 3단 컬럼) 빌더·재생성 |

## 자료

- `assets/portfolio.config.example.json`, `assets/schema.json`: 설정·스키마 출발점(섹션 14개·분류 13개 예시)
- `assets/items.example.json`, `assets/highlights.example.json`, `assets/page_spec.example.json`, `assets/concise.example.json`
- `references/WORKFLOW.md`(10단계·모드 A/B·Chrome 요령), `references/SCHEMA.md`(형식), `references/STYLE.md`(문장 규칙),
  `references/NOTION_API_GOTCHAS.md`(버전·뷰·move·차트 함정)
