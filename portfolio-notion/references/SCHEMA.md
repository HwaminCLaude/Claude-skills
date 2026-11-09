# 데이터 형식

## 마스터 DB 속성 (01_create_master.py 가 만든다)

| 속성 | 타입 | 용도 |
|---|---|---|
| 이름 | title | 카드 제목. 20자 안쪽 |
| 섹션 | select | 갤러리 탭 필터 축. 사용자의 기존 탭 이름 그대로(schema.json `sections`) |
| 분류 | select | 차트 색·타입 축: Project, Paper, Award, Competition, Presentation, Teaching, Learning, Certification, Research, Career, Consulting, Education, Tool |
| 기간 | date(range) | 타임라인·차트 축. Tool 은 비움 |
| 시기 | formula | 기간 시작일의 반기 라벨("2026 상반기"). 보드·차트 그룹용. 자동 |
| 상태 | status | Notion 기본 옵션(Not started / In progress / Done). API로 이름 변경 불가 → UI에서 바꿈 |
| 한줄 성과 | rich_text | 카드 두 번째 줄. 28자 안쪽, 숫자 먼저 |
| 역할 | rich_text | 본인 몫 |
| 기술 스택 | multi_select | 값 쓰면 옵션 자동 생성 |
| 기관·주최 | rich_text | |
| GitHub / 배포 링크 / 논문/자료 링크 | url | 링크는 속성 1개씩만. 나머지 링크는 본문 "관련 자료" |
| 파일 | files | PDF 등. move 로 넘어온 파일은 이름이 다른 열에서 02 가 복사 |
| 관련 항목 | relation(self) | items.json `related` 또는 옛 내부 링크에서 생성 |
| 정렬 | number | 탭 안 카드 순서 |

`schema.json` 의 `extra_properties` 에 select 속성을 추가하면 01 이 만들고 03 이 items 의 같은 키 값을 쓴다.
`keep_properties` 에 없는 열은 `02 --cleanup-legacy` 가 지운다.

## items.json

```json
{
  "<key>": {
    "page_id": "기존 페이지 id (없으면 03 이 새로 만들고 채움)",
    "title": "카드 제목",
    "section": "섹션 옵션", "type": "분류 옵션", "status": "완료 | 진행 중 | 예정 | null",
    "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD 또는 null"} ,
    "result": "28자 한 줄(숫자 먼저)",
    "long_result": "페이지 요약 첫 줄에 들어가는 한 문장",
    "role": "...", "stack": ["..."], "org": "...",
    "github": "url", "deploy": "url", "paper": "url",
    "sort": 1,
    "image": "신규 페이지 썸네일용 외부 이미지 url (GitHub social preview: https://opengraph.githubassets.com/1/<owner>/<repo>)",
    "related": ["<다른 key 또는 page id>"]
  }
}
```

## highlights.json

```json
{"title": "Highlights",
 "highlights": ["숫자 먼저 40자 이내 6줄"],
 "columns": [[{"header": "[학위]", "items": ["..."]}, ...], [...], [...]]}
```
`columns` 는 3개 권장(왼쪽 학위·경력·자격·수료 / 가운데 연구·논문·공모전·학회 / 오른쪽 프로젝트·강의·기술).
한 줄 30자 안쪽이어야 컬럼에서 줄바꿈이 적다. 날짜는 공모전·학회·수료 항목에만 연월로.

## pages_custom/<key>.json (대표 항목 본문)

```json
{"key": "sglang", "append": [
  {"h2": "핵심 결과 — 조건"}, {"table": {"header": ["지표", "기준", "결과", "변화"], "rows": [["...", "...", "...", "..."]]}},
  {"p": "조건: 모델·하드웨어·n·반복"}, {"image": "https://raw.githubusercontent.com/.../fig.png"},
  {"h2": "문제"}, {"bullets": ["..."]},
  {"h2": "접근"}, {"bullets": ["..."]},
  {"h2": "비용과 한계"}, {"bullets": ["..."]},
  {"h2": "산출물"}, {"bullets": ["[README](url) · [ERRATA](url)"]}
]}
```
인라인 마크업: `**굵게**`, `` `코드` ``, `[라벨](url)`. 지원 블록: h2, h3, p, quote, bullets, numbered, table, image, bookmark, divider.

## concise.json

```json
{"<key>": {"title": "짧은 제목", "result": "28자 한 줄"}}
```

## portfolio.config.json 주요 키

| 키 | 의미 |
|---|---|
| main_page_id | 포트폴리오 메인 페이지 id |
| existing_databases | 모드 B 의 기존 인라인 DB id 들(백업·move 대상) |
| delete_pages / cleanup_block_ids | 휴지통으로 보낼 빈 행 / 옛 블록 |
| insert_after_block_id | Highlights·섹션을 삽입할 기준 블록(헤더 아래 divider 등) |
| sections[] | key, heading{text, level, color}, tabs[{name, type, filter{section,type,titles}, cover, cover_size, card_layout, show_result, x, stack_by, chart_type, zoom}] |
| remove_text_contains | 본문에서 지울 보일러플레이트 문장 |
| forbidden_phrases / quote_drop_prefixes / delete_section_headings | 07 이 지우는 문구·줄·절 |
| number_checks | {원본 URL: [본문에 쓴 숫자들]} — 09 가 원본에서 재확인 |
| timeline_center | 타임라인 중심 날짜 |

## state.json (스크립트가 관리)

`data_page_id`, `db_id`, `ds_id`, `prop_ids`, `status_options`, `created_blocks{key: {heading, block, views[]}}`.
지우면 01·04 가 새로 만들므로 함부로 삭제하지 않는다.
