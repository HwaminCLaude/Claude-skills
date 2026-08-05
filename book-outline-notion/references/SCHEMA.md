# 산출물 스키마

파이프라인이 `_output/` 에 쌓는 JSON 구조. 모든 단계가 이 파일들만 보고 동작하므로,
중간 단계를 손으로 고치거나 다른 도구로 갈아끼울 수 있다.

---

## `toc.json` — 목차 트리 (01단계)

목차 항목 하나 = 배열 원소 하나. 목차 순서대로 정렬돼 있다.

```jsonc
[
  {
    "id": "n0005",          // 고정 식별자. 이후 모든 단계가 이걸로 참조한다
    "seq": 5,               // 1부터. DB 정렬키
    "level": 5,             // 1~7
    "num": "1.1",           // 번호 부분만
    "prefix": "1.1)",       // 본문에 실제로 인쇄되는 접두사 (헤딩 매칭에 씀)
    "title": "AI 개념 및 발전과정",
    "display": "1.1) AI 개념 및 발전과정",   // DB 행 제목. 번호를 붙여야 중복 제목이 구분된다
    "path": "Ⅰ. > 1. > 1) > (1) > 1.1)",    // 전체 breadcrumb
    "part": "Ⅰ",            // 최상위 대분류
    "page": 43,             // 시작 쪽 (PDF 쪽번호)
    "end_page": 44,
    "pages": 2,
    "parent": "n0004",      // 없으면 null
    "children": ["n0006"]   // 직속 자식 id
  }
]
```

**게이트**: 노드 수가 `BOOK_EXPECTED_NODES` 와 다르거나 쪽번호 없는 항목이 있으면 중단한다.

---

## `sections.json` — 절별 본문 블록 (02단계)

`{node_id: {...}}` 맵. `toc.json` 의 메타에 실제 본문이 붙은 것.

```jsonc
{
  "n0005": {
    "id": "n0005", "seq": 5, "level": 5,
    "display": "1.1) AI 개념 및 발전과정",
    "path": "…", "part": "Ⅰ", "parent": "n0004", "children": [],
    "page_start": 43, "page_end": 44,
    "n_table": 1, "n_figure": 1,
    "blocks": [ /* 아래 블록 spec */ ],
    "text": "요약·검수용 평문"
  }
}
```

### 블록 spec

| type | 필드 | 의미 |
|------|------|------|
| `bul` | `text` | `▣` 불릿. 이어지는 줄이 병합된 완성 문장 |
| `sub` | `text` | `-`/`·` 하위 불릿. 직전 `bul` 의 children 으로 들어간다 |
| `p` | `text` | 일반 문단 |
| `caption` | `text`, `cat` | 짝을 못 찾은 `[표X-N]`/`[그림X-N]` 캡션 |
| `source` | `text` | 어디에도 안 붙은 `자료:` 출처 |
| `figure` | `fig_id`, `label`, `caption`, `page`, `source?` | 크롭 이미지. `fig_id` 로 `figures.json`·`figocr.json`·`drive_urls.json` 과 연결 |
| `table` | `caption`, `rows`, `page`, `page_end?`, `source?` | 진짜 표. `rows` 는 문자열 2차원 배열 |

**게이트**: 본문 줄 커버리지가 100%가 아니거나 헤딩을 하나라도 못 찾으면 중단한다.

---

## `figures.json` — 크롭 대상 (02단계)

```jsonc
[
  { "fig_id": "fig_044_1",       // 그림
    "page": 44,
    "rect": [40.0, 110.9, 555.0, 363.7],   // 크롭 좌표 (캡션 아래 ~ 다음 아이템 위)
    "label": "[그림Ⅰ-1]", "caption": "AI 기술 발전과정",
    "node": "n0005" },
  { "fig_id": "tab_370_15", … }  // 이미지로 그려진 '표' 는 tab_ 접두사
]
```

## `figocr.json` — 도식 판독 (04단계)

```jsonc
{ "fig_id": { "text": "도식 안 모든 글자·수치를 구조가 드러나게 옮긴 것",
              "summary": "이 도식이 말하는 바 한 문장" } }
```

## `drive_urls.json` — 이미지 임베드 URL (05단계)

```jsonc
{ "fig_id": "https://lh3.googleusercontent.com/d/<DriveFileId>" }
```
이 URL은 **'링크가 있는 모든 사용자' 권한이 있어야** 노션에서 보인다(`rclone link` 로 부여).

## `summaries.json` — 절별 한 줄 요약 (06단계)

```jsonc
{ "n0005": "AI는 규칙 기반·머신러닝·딥러닝을 거쳐 생성형 AI와 Agentic AI로 진화한다" }
```

## `page_blocks.json` — 노션 블록 (07단계)

`{node_id: [Notion block object, …]}`. **DB 행이 되는 노드만** 들어있다
(`level <= BOOK_MAX_DB_LEVEL`). 그 아래 절은 상위 노드의 블록 배열에 소제목으로 흡수돼 있다.

## `notion_state.json` — 업로드 상태 (09단계)

```jsonc
{ "rows": { "n0005": { "page_id": "…", "done": true } },
  "dbs":  { "n0004": "<child data_source_id>" },
  "purged": ["<archive 한 page_id>"] }
```
중단 후 다시 실행하면 이 파일을 보고 이어서 한다. 되돌리려면 여기 page_id 로 archive 한다.

## `qa.json` — 검수 결과 (08단계)

```jsonc
[ { "id": "n0340", "verdict": "ISSUE",
    "issues": ["표가 두 개로 쪼개졌다", "출처가 오배치되었다"] } ]
```
