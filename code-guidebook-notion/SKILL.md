---
name: code-guidebook-notion
description: Jupyter 노트북(.ipynb) 폴더를 "코드를 하나도 모르는 사람"용 가이드북으로 만들어 Notion DB에 올리는 스킬. 노트북별 1페이지로, 코드 한 줄씩 풀이 + 함수 문법 + 하이퍼파라미터 의미 + 실행 결과(output) + matplotlib 그림(Google Drive 임베드) + 실무 팁을 친근한 한국어로 채운다. 사용자가 "코드 가이드북 만들어줘", "노트북을 노션에 익히기 쉽게", "각 주차 코드 가이드북", "ipynb를 노션으로 초보자용 설명", "코드 결과랑 그림도 붙여서 노션에" 라고 할 때 사용한다. PDF 강의자료 변환은 pdf-to-notion 스킬 사용.
---

# 코드 노트북 → Notion 가이드북

Jupyter 노트북 폴더를, **코드 0 기초자가 익힐 수 있는 가이드북**으로 만들어 Notion DB에 올린다.
노트북 1개 = 노션 페이지 1개. 메타코드 68개 노트북(2·3·4·6·9주차)을 가이드북으로 변환한 실제
파이프라인을 그대로 재현한다.

## 결과물 구조 (가이드북 1개당)

```
H1: 📘 [가이드북] <제목> (파란 배경)
🎯 callout: 이 노트북으로 할 수 있게 되는 것 + 선수지식
📍 flowmap: 이 노트북 흐름 지도 — 목적 + 5~8단계 데이터 shape 여정 (주황 callout + 정렬 code 지도)
import 섹션: 라이브러리마다 "무엇을·왜" (bul)
── 의미 단위 섹션 (h2/h3) 반복 · 각 섹션 제목에 [②] 단계 배지(h2 stage) ──
  code 블록: 실제 코드 발췌
  p: 한 줄씩 무슨 뜻인지 풀이 + 함수 문법
  bul/표: 하이퍼파라미터 = 의미·권장기준
  output 블록: 실제 실행 결과 + "이 결과는 ~를 의미해요"
  image_ref → image: 코드가 만든 그림(matplotlib 등, Drive 임베드) + 해설
  callout(blue): ⚙️ 실무 팁 / callout: 💼 실무 적용 / ⚠️ 흔한 실수
✅ 핵심 체크리스트 (num)
```

## 사전 준비 (사용자 환경 의존)

- **rclone**: `RCLONE_BIN`(기본 `C:\Users\정화민\rclone\rclone.exe`), remote `gdrive`. 인증은 사용자가 한다.
- **Notion MCP** (`mcp__notion__API-*`): 워크스페이스에 통합 연결 필요. 업로드는 이 방식.
- **환경변수** (재사용 시 폴더만 바꾸면 됨):
  - `METACODE_ROOT` = 노트북이 들어있는 작업 폴더 루트
  - `RCLONE_BIN`, `RCLONE_REMOTE`, `GB_DRIVE_DEST`(그림), `GB_FILES_DRIVE_DEST`(원본 .ipynb, 기본 `메타코드/가이드북자료파일`) (기본값 있음)
  - `METACODE_SOURCE_FILES_PROP` = 원본 파일을 붙일 노션 속성 이름 (기본 `원본 파일`)

## 워크플로우

`scripts/` 사용. **cp949 이모지 출력 에러 방지**로 항상 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 를 붙인다.

### Step 0. 사전 점검 (인터랙티브) — `scripts/preflight.py` ★먼저 실행
작업 전 **반드시** 환경·입력을 자동 점검한다. 안 갖춰진 게 있으면 바로 들어가지 말고 사용자에게 요구/조치한다.
```
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/preflight.py gb "<작업폴더>" --db "<Notion DB URL/ID>"
```
점검 항목: 작업 폴더 존재 + `.ipynb` 유무 / 외부 구글드라이브·캐글 링크(.txt) 감지 / rclone 바이너리·`gdrive:` remote / 대상 DB 입력 / UTF-8.

출력 해석 및 **인터랙티브 처리**:
- 종료코드 0(`진행 가능 ✅`)이면 Step 1로.
- 종료코드 1이면 `MISSING`/`ASK>`/`FIX>` 처리:
  - `ASK>` → **`AskUserQuestion` 으로 사용자에게 물어 받아낸다**(대상 DB URL, 정확한 폴더 경로, 캐글 .ipynb 직접 다운로드 요청, rclone remote 인증 등).
  - `FIX>` → 가능하면 **자동 조치**(외부 드라이브 링크면 제시된 `rclone copy --drive-root-folder-id=...` 로 노트북 내려받기 등).
  - 조치 후 **preflight 재실행**, `진행 가능 ✅` 될 때까지 반복(최대 3회).
- preflight가 못 보는 것은 Claude가 직접: 대상 DB가 실제 열리는지 `mcp__notion__API-retrieve-a-database` 로, **title property 이름이 `이름`인지** 확인. 폴더명·DB명 헷갈리면 추측 말고 사용자에게 확인.

### Step 1. 노트북 추출 — `scripts/extract_notebooks.py`
```
PYTHONUTF8=1 METACODE_ROOT="<루트>" python scripts/extract_notebooks.py <주차폴더>
```
- 폴더 안 모든 `.ipynb`(.ipynb_checkpoints 제외)에서 코드/마크다운 source + **출력(outputs) + 출력이미지** 추출.
- 노트북별 `<주차>/_guidebook/nb_<slug>.json` 생성. 각 code 셀에 `source`, `outputs`(800자), `output_images`(키 목록).
- base64 출력 그림은 `<주차>/_guidebook/images/<slug>/<slug>__c{NNN}_{j}.png` 로 저장(키=파일명 stem). 마크다운 안 base64는 `[그림]`으로 치환.

### Step 2. 그림 Drive 업로드 + 원본 노트북 업로드 — `scripts/upload_guidebook_images.py`
```
PYTHONUTF8=1 METACODE_ROOT="<루트>" python scripts/upload_guidebook_images.py <주차폴더>
```
- **(그림)** `_guidebook/images/` 의 PNG 전체를 `gdrive:메타코드/가이드북이미지/<주차>` 로 copy + 공개 권한. `<주차>/_guidebook/gb_drive_urls.json` 생성 (`{key: 임베드URL}`, key=파일명 stem = `output_images`의 키와 동일).
- **(원본 파일)** `notebooks.json` 의 `path` 로 각 **원본 .ipynb 파일**을 `gdrive:메타코드/가이드북자료파일/<주차>/<nb_slug>/<원본파일명>.ipynb` 로 `copyto` + 공개 권한 → 공유링크를 `<주차>/_guidebook/gb_drive_files.json` (`{nb_slug: [{"name":"....ipynb","url":"..."}]}`) 에 저장. 이 링크가 Step 5에서 노션 `원본 파일` 속성에 붙는다. (extract_notebooks.py 를 먼저 돌려 `notebooks.json` 이 있어야 함)

### Step 3. 가이드북 spec 작성 — `<주차>/_guidebook/gb_<slug>.json`  ★핵심
`nb_<slug>.json` 을 읽고 노트북마다 가이드북 spec(`{title, blocks:[...]}`)을 쓴다.
- 블록 타입·작성 원칙은 **`references/GUIDEBOOK_SCHEMA.md` 를 반드시 읽고 그대로** 따른다.
  (h2/h3/p/callout/num/bul/code/eq/quote/divider + **output**(실행결과) + **image_ref**(그림 key)).
- **출력·그림 규칙**: 어떤 코드 셀에 `outputs`가 있으면 그 코드 설명 직후 `output` 블록으로 실제 결과를 보여주고
  "이 결과는 ~예요" 해설. `output_images`가 있으면 각 key를 `image_ref` 블록으로 넣는다.
  **key는 절대 지어내지 말 것** — nb json의 `output_images`에 있는 값만 사용.
- 노트북당 spec이 크면 파이썬 dict로 구성해 `json.dump` 로 저장(이스케이프 안전).
- 어투·구성은 아래 "가이드북 작성 규칙"을 그대로 따른다.

### Step 4. 노션 블록 변환 + 청크 분할 — `scripts/build_guidebook.py`
```
PYTHONUTF8=1 python scripts/build_guidebook.py <gb_json> <chunk_out_dir> <prefix>
예: ... build_guidebook.py 6주차/_guidebook/gb_실습2.json 6주차/_guidebook/chunks 실습2
```
- gb spec → 노션 블록. `output`은 회색 plain text 코드블록("📤 실행 결과\n…"), `image_ref` key는 `gb_drive_urls.json`으로 image 블록 치환(URL 없으면 스킵).
- H1 추가 후 **25블록 청크**로 잘라 `<chunk_out_dir>/<prefix>_c{NN}.json` 저장. `03_build_notion.py` 빌더 재사용.

### Step 5. 노션 업로드

**5-1. 페이지 생성** — `mcp__notion__API-post-page` 로 대상 DB에 빈 페이지 생성 (제목: `📘 [가이드북] …`).
이때 **`원본 파일` 속성도 `gb_drive_files.json[nb_slug]` 로 함께 세팅**한다(아래 "원본 파일 속성" 절 참조).
페이지 `id` 를 받아 둔다.

**5-2. 본문 블록 업로드 — ⭐️ 직접 REST 업로드(권장, `scripts/notion_direct_upload.py`)**
```
PYTHONUTF8=1 python scripts/notion_direct_upload.py <page_id> <chunk_dir> --glob "<prefix>_c*.json" --verify --expect <총블록수>
```
- 통합 토큰으로 `PATCH /v1/blocks/{page}/children` 에 청크를 **이름순으로 순차 PATCH** → 수백 블록도 **수초** 만에 순서·원형(코드/이미지/수식/콜아웃) 그대로 올라간다. `--verify`(+`--expect`)로 업로드 직후 총 블록 수·타입 분포를 자동 대조.
- 토큰은 `OPENAPI_MCP_HEADERS`/`NOTION_TOKEN` 환경변수 또는 `~/.claude.json` 의 `mcpServers.notion.env.OPENAPI_MCP_HEADERS` 에서 **런타임에 읽으며 저장/출력하지 않는다.**
- **왜 직접 REST 인가**: 업로드를 서브에이전트에 맡기면 블록 JSON을 툴 인자로 재출력하다 **32k output-token 한도**에 걸려 대용량 청크가 통째로 실패하고(워크플로 에이전트에서 확인), MCP 지연·5xx 재시도로 청크당 10~30분씩 걸린다. 직접 REST는 이 둘을 모두 없앤다.

**5-3. (대안) MCP/에이전트 업로드** — 토큰 경로를 못 쓰는 환경이면 `mcp__notion__API-patch-block-children` 로 청크 c01부터 **순차** append. 대량이면 업로드 에이전트에 위임하되 **아래 불변 규칙**을 반드시 준수(에이전트는 청크당 블록 수를 작게, 한 에이전트당 청크도 적게).

## 원본 파일 속성 (Files & media) — DB에서 원본 노트북 바로 열기

각 노션 페이지 속성 **`원본 파일`**(Files & media, 이름은 `METACODE_SOURCE_FILES_PROP`)에
그 노트북의 원본 .ipynb 공유링크를 붙인다. 링크·이름은 Step 2가 만든 `<주차>/_guidebook/gb_drive_files.json` 에 있다.

**1) 속성이 DB에 있는지 확인 (최초 1회):**
- `mcp__notion__API-retrieve-a-database` 로 `원본 파일`(type `files`)이 있는지 확인.
- 없으면 `mcp__notion__API-update-a-data-source` 로 추가 (DB의 `data_source_id` 필요):
  ```json
  {"data_source_id": "<DS_ID>", "properties": {"원본 파일": {"files": {}}}}
  ```
- ⚠️ **구버전 API MCP 주의**: 로컬 `@notionhq/notion-mcp-server`(npx)는 **구버전 API(2022-06-28)** 라 `retrieve/update/query-a-data-source` 가 database_id를 넣어도 `invalid_request_url` 로 실패한다 → **API로 DB 속성 생성 불가**. 이 경우 **사용자가 노션 UI에서 `원본 파일`·`데이터` 등 파일&미디어 속성을 직접 만든 뒤**, 이미 만든 페이지에 `mcp__notion__API-patch-page` 로 값만 채운다(속성명이 `파일과 미디어` 기본값으로 생기면 그 이름 그대로 patch, rename은 UI에서). 값 채우기(patch-page)는 구버전 API에서도 정상 동작.

**2) 페이지 생성 시 속성 세팅** — `mcp__notion__API-post-page` 의 `properties` 에 title과 함께:
```json
{
  "parent": {"database_id": "<대상 DB ID>"},
  "properties": {
    "이름": {"title": [{"text": {"content": "📘 [가이드북] <제목>"}}]},
    "원본 파일": {"files": [
      {"type": "external", "name": "<원본파일명>.ipynb",
       "external": {"url": "https://drive.google.com/file/d/<ID>/view?usp=sharing"}}
    ]}
  }
}
```
- `files` 배열 = `gb_drive_files.json[nb_slug]` 의 각 항목을 `{"type":"external","name":name,"external":{"url":url}}` 로 변환.
- 그 nb_slug 키가 없으면 속성 생략하고 페이지만 생성. 이미 만든 페이지엔 `mcp__notion__API-patch-page` 로 같은 `properties` 만 보내 나중에 붙일 수 있다.

## 🚨 업로드 불변 규칙 (가장 자주 깨지는 부분 — 반드시 지킬 것)

업로드 에이전트가 종종 "MCP는 paragraph만 지원"이라며 거부하거나 `code`/`image`/`equation`을
`paragraph`로 **변형**한다 → 임무 실패. 실제로 이 변형 때문에 여러 페이지를 archive 후 재업로드했다.

- **사실**: `mcp__notion__API-patch-block-children` 는 스키마에 paragraph만 보여도
  **code·image·equation·callout·column_list·heading·divider 등 모든 블록을 처리한다.**
- 업로드 에이전트 지시 문구:
  > 🚨 Read한 청크 JSON을 **변형 없이 그대로** children에. MCP는 code/image/equation/callout 등 모든 블록을 처리한다. code를 paragraph로 바꾸거나 image를 빼면 임무 실패. Bash 불필요. 529/소켓에러는 같은 청크 재시도. 페이지 `<id>` 에 c01~cNN 순차 업로드.
- **100블록/요청 제한** → 25블록 청크 유지.
- **업로드 에이전트는 `executor`(sonnet)를 쓴다.** `executor-high`(opus)는 Notion MCP 툴이 노출되지 않아 업로드 불가(노트북 추출·gb spec 작성 같은 파일 작업엔 executor-high 사용 가능).
- **청크 누적 버그**: 한 업로드 에이전트에 청크가 8개+면 간헐적으로 청크를 합쳐 한 요청에 보내 `400 no low surrogate`(거대 요청) 에러가 난다(청크 자체는 깨끗). 대응: ①**한 에이전트당 청크 ≤8** ②실패 반복 시 **단일 청크 에이전트 순차** ③청크 8개 초과 페이지는 c01~c08 먼저(에이전트 A) → 끝난 뒤 c09~ (에이전트 B) 식으로 **순차 배치**(같은 페이지 동시 업로드는 순서 꼬임).
- 세션 한도·소켓에러로 중단되면 부분 업로드 페이지를 `API-delete-a-block`로 archive 후 재생성·재업로드.
- 업로드 후 **code/image 블록 보존 여부를 실제로 확인**한다(추측 금지). 변형됐으면 다시 올린다.

## 가이드북 작성 규칙 (다음에도 동일 양식 유지 — 핵심 목적)

`references/GUIDEBOOK_SCHEMA.md` 의 원칙을 따르되 톤은 이렇게 고정:

- **대상**: 코드를 하나도 모르는 사람. 변수·함수·문법을 당연하게 여기지 말고 풀어 설명.
- **어투**: 친근하게 (~예요 / ~이야 / ~합니다). 전문용어는 쉬운 말 병기.
- **맨 위** `callout`로 "이 노트북으로 할 수 있게 되는 것" + 선수지식.
- 이어서 **📍 흐름 지도(`flowmap`)**: 노트북 전체를 5~8단계 + 데이터 shape 여정으로 요약(숲 먼저). 각 섹션 `h2`엔 `stage`를 달아 `[②]` 배지로 잇는다. 상세·예시는 `references/GUIDEBOOK_SCHEMA.md`의 "흐름 지도 작성 규칙" 참조.
- import는 라이브러리마다 "무엇을·왜" `bul` 한 줄.
- 코드 조각마다: `code`(실제 발췌) → `p`로 한 줄씩 풀이 → 함수는 "`함수()`는 ~를 한다" 식 문법 설명.
- 하이퍼파라미터/인자는 `bul`/표로 "인자 = 의미, 이 값이면 이렇게, 권장 기준" + ⚙️ 실무 팁 callout(blue).
- `outputs` 있으면 `output` 블록 + 결과 해설, `output_images` 있으면 `image_ref`로 그림 + 해설.
- 💼 실무 적용 / ⚠️ 흔한 실수 callout, 수식은 `eq`(LaTeX).
- **맨 끝** "✅ 핵심 체크리스트" `num`.
- 노트북에 없는 내용을 지어내지 말 것. 개념 보충 설명은 OK.

## 재사용 체크리스트 (새 폴더 적용 시)
1. `METACODE_ROOT`(노트북 루트) 설정.
2. Step1 추출 → nb json의 `n_code`/`n_img`로 코드·그림 수 확인.
3. Step2 그림+원본 노트북 업로드 → `gb_drive_urls.json` key가 `output_images` key와 맞는지, `gb_drive_files.json` 에 노트북별 원본 .ipynb 링크가 담겼는지 확인.
4. Step3에서 위 "가이드북 작성 규칙"으로 spec 작성 (어투·구성 동일, output/image_ref 포함).
5. Step4 변환 → Step5 업로드(불변 규칙 준수). **DB에 `원본 파일`(Files) 속성 보장** 후 페이지 생성 시 `gb_drive_files.json` 링크로 속성 세팅.
6. 업로드 후 code/image 블록 보존 여부 + **`원본 파일` 속성 링크**를 텍스트로 검증.
