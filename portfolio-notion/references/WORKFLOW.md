# 작업 흐름 (10단계)

모든 명령은 포트폴리오 작업 폴더(예: `D:\work\portfolio\`)에서 실행한다. 그 폴더에 `portfolio.config.json`,
`schema.json`, `items.json`, `highlights.json`, `pages_custom/` 를 두고, 스크립트는 스킬 폴더의 `scripts/` 를 절대경로로
호출한다. 환경변수 `PORTFOLIO_DIR` 로 작업 폴더를 바꿀 수 있다.

두 가지 모드가 있다.

| 모드 | 상황 | 사용하는 단계 |
|---|---|---|
| A. 신규 구축 | Notion에 포트폴리오 DB가 없고 자료(GitHub·Drive·이력서·링크드인)만 있음 | 0 → 1 → 2 → 4 → 5(03) → 6 → 7 → 8 → 9 |
| B. 기존 재구성 | 갤러리 형태의 인라인 DB 여러 개가 이미 있고 내용 보강이 목적 | 0 → 1 → 2 → 3 → 4 → 5(02+03) → 6 → 7 → 8 → 9 |

## 0. 인테이크 (질문은 최소로)

사용자에게 이미 들은 것은 다시 묻지 않는다. 꼭 필요한 것만 한 번에 묻는다.

- 메인 페이지 URL(또는 "새로 만들어 줘"), 자료 위치(GitHub 계정, Drive 폴더/rclone 원격, 링크드인 공개 여부)
- 목표 직무(예: AI/LLM 엔지니어) — 하이라이트 우선순위와 분류 축에 영향
- 다루면 안 되는 자료(비공개 저장소, 팀 성과 중 개인 몫이 불분명한 것)

사용자가 "묻지 말고 진행"이라고 하면 아래 기본값으로 진행하고 끝에 결정 목록을 보고한다: 공개 링크 미생성,
불일치 수치는 둘 다 출처와 함께 기재, 미확정 날짜는 비움, 팀 성과는 "팀 결과"로 표기.

## 1. 근거 수집

```bash
python <skill>/scripts/evidence_github.py <user1> <user2>        # evidence/github_inventory.md (+ README 숫자 줄)
python <skill>/scripts/evidence_drive.py gdrive: "졸업논문" "프로젝트A" --depth 2   # evidence/drive_tree.md
```

- GitHub: 저장소 설명·README·releases·results 파일에서 **실측 수치**(before→after, n, 조건)를 그대로 옮겨 적는다.
  SGLang 같은 저장소는 README 한 줄에 선점 19→0, +9.1% 처럼 핵심 수치가 이미 있다.
- Drive: 설계서·README·노트북 출력에서 규모 수치(건수, 쪽수, 표 개수)를 모은다. `rclone cat` 으로 작은 md/txt 를 읽는다.
- 링크드인: 사용자 Chrome이 로그인되어 있으면 `linkedin.com/in/me/` 로 소개·경력·학력·수상·논문 섹션을 읽어 날짜와
  구조를 가져온다(`get_page_text`). 링크드인 소개의 대괄호 소제목 구조를 Highlights 컬럼에 그대로 쓴다.
- 기존 Notion(모드 B): `00_backup.py` 가 행·본문·뷰·파일을 덤프한다. 본문 첫 이미지가 갤러리 썸네일이므로 절대 지우지 않는다.

수치 원칙: 파일에서 못 찾은 수치는 쓰지 않는다. 사용자 본인이 쓴 Notion 표의 수치는 "연구 페이지 결과표 기준"처럼
출처 성격을 붙여 쓸 수 있지만 Highlights 첫 줄에는 올리지 않는다.

## 2. 항목 큐레이션 — items.json

- 항목 하나 = 페이지 하나. 키는 짧은 영문 slug. 형식은 `references/SCHEMA.md`.
- `section` 은 사용자의 기존 탭 이름을 그대로(재분류 금지), `type` 은 타임라인·차트 색 축.
- `result` 는 카드에 보이는 28자 이내 한 줄(숫자 먼저), `long_result` 는 페이지 요약 첫 줄.
- 날짜 출처 우선순위: 기존 속성 → 본문 문장 → 공식 문서(수료증·공고·학회) → GitHub 생성일~마지막 push → Drive 파일 시각.
  월만 아는 날짜는 1일~말일로 넣고, 전혀 모르면 `period: null` 로 두고 보고서에 적는다.
- 공동 작업은 `role` 에 본인 몫만 적고 팀 성과 수치는 본문에서 "팀 결과"로 표기한다.

## 3. 백업 (모드 B, 또는 메인 페이지를 건드리기 전 항상)

```bash
python <skill>/scripts/00_backup.py      # backup/full_backup.json, backup/files/
```

## 4. 마스터 DB 생성

```bash
python <skill>/scripts/01_create_master.py
```
하위 페이지 "포트폴리오 데이터(원본)" 안에 `Portfolio Items` 를 만들고 관련 항목(relation)·시기(formula) 를 붙인다.
state.json 에 db_id / ds_id / prop_ids 가 기록된다.

## 5. 행 채우기

```bash
python <skill>/scripts/02_move_and_fill.py                 # 모드 B: 기존 행 move + 관계 + 파일 열 통합
python <skill>/scripts/03_upsert_pages.py                  # 속성 쓰기, 신규 페이지 생성(썸네일 이미지 포함)
python <skill>/scripts/02_move_and_fill.py --cleanup-legacy   # 모드 B: 옛 열 제거(03 이후)
```

## 6. 메인 페이지 구성

```bash
python <skill>/scripts/04_build_main_page.py --dry-run    # 계획 확인
python <skill>/scripts/04_build_main_page.py              # Highlights + 섹션 제목 + 연결 블록(탭)
# Chrome으로 외관 확인 후
python <skill>/scripts/04_build_main_page.py --cleanup    # 옛 DB 블록·콜아웃 휴지통(30일 복구)
```

## 7. 페이지 본문

```bash
python <skill>/scripts/05_gen_specs.py                    # pages/<key>.json (요약 quote + pages_custom 병합)
python <skill>/scripts/06_push_content.py                 # 멱등 삽입
```
대표 항목 5~10개는 `pages_custom/<key>.json` 에 결과 표·문제·접근·비용과 한계·산출물 절을 직접 쓴다(`STYLE.md`).

## 8. 다듬기

```bash
python <skill>/scripts/07_cleanup_phrases.py              # 기계 작성 티가 나는 문구 제거
python <skill>/scripts/08_condense.py                     # concise.json 으로 제목·한줄 성과 축약
python <skill>/scripts/10_highlights_layout.py            # Highlights 만 다시 그릴 때
```

## 9. 검증과 보고

```bash
python <skill>/scripts/09_verify.py                       # logs/verify_report.json
```
Chrome 으로 메인 페이지를 열어(아래 참고) Highlights·갤러리 첫 탭·차트를 눈으로 확인한다. 보고서에는 바꾼 것, 삭제한 것
(휴지통 복구 가능), 사용자가 채워야 할 것(미확정 날짜, 불일치 수치, 상태 옵션 이름), 만들지 않은 후보와 이유를 적는다.

### Chrome 확인 요령

Notion 웹이 데스크톱 앱으로 리디렉션되면 리디렉션 페이지의 "브라우저에서 사용하려면 여기를 클릭하세요" 링크를
`javascript_tool` 로 클릭한다 (`document.querySelectorAll('a')` 중 텍스트에 '브라우저' 포함 요소 `.click()`).
스크롤은 `find` 로 섹션 제목 ref 를 얻어 `scroll_to` 로 이동하는 쪽이 확실하다. 탭 전환 클릭은 자동화에서 잘 먹지 않으므로
첫 탭만 눈으로 보고 나머지는 `09_verify.py` 의 탭별 행 수로 확인한다.
