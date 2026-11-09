# Notion API 주의점 (2026-11 실측)

## 버전·접속

- 데이터 소스·페이지·블록은 `Notion-Version: 2025-09-03`, 뷰(views)·페이지 이동(move)은 `2026-03-11` 이 필요하다.
- `@notionhq/notion-mcp-server` 가 `2022-06-28` 로 고정돼 있으면 `data_sources` 도구가 "Invalid request URL" 을 내고,
  데이터 소스가 2개 이상인 DB는 `retrieve-a-database` 가 거부한다. 이 스킬은 MCP 대신 `urllib` 로 직접 호출한다
  (토큰: `NOTION_TOKEN` 또는 `~/.claude.json` 의 `OPENAPI_MCP_HEADERS`).
- 429/5xx 는 재시도. 호출당 0.3~0.5초 걸리므로 50페이지 × 여러 호출은 수 분이다.

## 데이터베이스 / 데이터 소스

- `GET /databases/{id}` (2025-09-03+) 는 스키마 대신 `data_sources[{id,name}]` 를 준다. 스키마·쿼리는 `/data_sources/{id}`.
- `POST /databases` 는 `initial_data_source.properties` 로 첫 소스를 만든다. 자기 relation 은 생성 후 `PATCH /data_sources` 로
  `{"relation": {"data_source_id": <same>, "type": "single_property", "single_property": {}}}`.
- formula 속성은 `{"formula": {"expression": "..."}}` 로 생성 가능. 반기 라벨:
  `if(empty(prop("기간")), "", formatDate(prop("기간"), "YYYY") + if(toNumber(formatDate(prop("기간"), "M")) <= 6, " 상반기", " 하반기"))`
- status 속성은 영어 기본 옵션(Not started / In progress / Done)으로 생성되고, 옵션 이름을 PATCH 해도 반영되지 않는다.
  스크립트는 완료/진행 중/예정 을 존재하는 이름에 매핑한다. 한국어로 바꾸려면 UI 에서.
- select 옵션 삭제: 남길 옵션만 담은 `options` 배열로 PATCH 하면 나머지가 사라진다(값이 있는 행이 없어야 안전).
- 속성 삭제: `{"properties": {"열이름": null}}`.

## 페이지 이동 (`POST /pages/{id}/move`, 2026-03-11)

- 부모는 `{"type": "data_source_id", "data_source_id": ...}`. 페이지 id·URL·본문·아이콘·파일이 모두 유지된다.
- 값이 있는 속성은 **대상 데이터 소스에 같은 이름의 열을 자동 생성**해 넘어온다(비어 있던 속성은 안 넘어옴).
  같은 이름 열(예: 파일)은 그대로 합쳐진다. 그래서 move 뒤 옛 열이 스키마에 잔뜩 생기며, 값을 옮긴 뒤 `null` 로 지운다.
- 이름이 다른 files 열로 넘어온 Notion 호스팅 파일은 기존 file 객체를 그대로 `파일` 열에 PATCH 하면 복사된다
  (별도 업로드 불필요). 그래도 백업 단계에서 파일을 내려받아 둔다(서명 URL 1시간 만료).

## 뷰 (`/views`, 2026-03-11)

- 연결 뷰 생성: `POST /views` + `create_database: {parent: {type: "page_id", page_id}, position: {type: "after_block", block_id}, show_data_source_title: false}`.
  부모 타입은 `page_id` 만 허용. **콜아웃·컬럼 안에는 만들 수 없다**("cannot contain a linked database").
- 응답 `parent.database_id` 가 연결 블록의 id. 같은 블록에 탭을 더 붙이려면 `POST /views` 에 `database_id: <그 id>`.
- 갤러리 `cover` 는 생성 시 `page_content | page_cover | property` 만 허용. 읽기 응답의 `page_content_first` 를 그대로 보내면 400.
  커버 없는 아이콘형 카드는 `"cover": null`. `cover_size: small|medium|large`, `card_layout: compact|list`.
- 타임라인은 **항목당 1행**. 겹치지 않는 항목을 같은 줄에 압축하는 기능이 없다(공식 도움말: 드래그로 줄 순서만 변경).
  `show_table: false` 와 `preference.zoom_level: year` 로 한 화면에 넣는 것이 최선. `color_by` 는 boolean 만.
- 차트: `chart_type: column|bar|line|donut|number`, `x_axis` 는 group_by 객체(`{"type":"select","property_id":..,"sort":{"type":"manual"},"hide_empty_groups":true}`
  또는 formula: `{"type":"formula","property_id":..,"group_by":{"type":"text","group_by":"exact","sort":{"type":"ascending"}},"sort":{"type":"ascending"}}`),
  `y_axis: {"aggregator": "count"}`, `stack_by` 도 group_by 객체. `hide_empty_groups` 가 없으면 "없음" 막대가 생긴다.
- 보드 `group_by` 는 반드시 `type` 을 포함한 group_by 객체. `hide_empty_groups: true` 로 "없음" 열 숨김.
- 뷰 PATCH 는 얕은 병합이지만 `configuration` 일부만 보내면 `stack_by` 같은 필드가 null 로 바뀐 사례가 있다. 차트 설정은 항상 전체를 다시 보낸다.
- 뷰 삭제는 영구적. DB 삭제는 블록 DELETE(휴지통 30일).

## 블록

- `PATCH /blocks/{page}/children` 에 `after` 를 주면 그 블록 뒤에 삽입된다. 응답 `results` 에는 삽입 지점 이후의 **모든 형제 블록**이
  올 수 있으므로 "새로 만든 블록 id" 로 쓸 때는 앞에서 n개만 취한다.
- 블록 이동 API 가 없다. 재배치 = 삭제+재생성이며 Notion 호스팅 이미지는 URL 로 재생성할 수 없다 → 기존 블록은 두고 주변에만 삽입한다.
- column_list 는 column 2개 이상, 각 column 에 자식 1개 이상. 한 요청에서 column_list → column → 블록까지 2단계 중첩 허용.
- 표: `table` 블록에 `table_width`, `has_column_header`, 자식 `table_row.cells`(셀마다 rich_text 배열).
- 버튼 블록은 API 가 `unsupported` 로만 돌려준다(읽기·쓰기 불가).

## Chrome 확인

- Notion 웹이 데스크톱 앱으로 넘기는 환경에서는 `app.notion.com/native/...` 인터스티셜이 뜬다. 링크 텍스트에 '브라우저' 가 들어간 `<a>` 를
  `javascript_tool` 로 `.click()` 하면 웹 앱이 열린다(좌표 클릭·ref 클릭은 먹지 않았다).
- 긴 페이지에서 `scroll` 은 차트 위에서 먹히지 않을 수 있다. `find` 로 제목 ref 를 얻어 `scroll_to` 를 쓴다.
- 갤러리 탭 전환 클릭은 자동화로 잘 되지 않는다. 첫 탭만 눈으로 확인하고 나머지는 뷰 쿼리(`POST /views/{id}/queries`)로 행 수를 센다.
