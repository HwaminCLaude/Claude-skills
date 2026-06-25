---
name: pdf-to-notion
description: 강의자료/문서 PDF 폴더를 Notion 데이터베이스의 페이지로 변환하는 스킬. PDF를 페이지별 PNG로 쪼개 Google Drive(rclone)에 올려 임베드하고, 페이지마다 "이미지 | 친근한 한국어 설명" 2단(column) 레이아웃을 만든다. 사용자가 "PDF를 노션에 올려줘", "강의자료 노션 변환", "pdf를 이미지로 찢어서 노션에", "이 폴더 자료들 노션 DB에 같은 작업" 이라고 하거나 폴더 안 PDF들을 참조 페이지 스타일로 노션에 정리해달라고 할 때 사용한다. 코드 노트북 변환은 code-guidebook-notion 스킬 사용.
---

# PDF → Notion 변환

폴더 안의 PDF 강의자료를 **Notion DB 안 페이지마다 "PDF 페이지 이미지 | 친근한 한국어 설명"
2단 레이아웃**으로 변환한다. 메타코드 강의자료(2·3·4·6·9주차, 16개 자료)를 노션으로 옮긴 실제
파이프라인을 그대로 재현한다.

## 🆕 v2 권장: Vision + 2단(교수 / 중학생 토글) 모드 — 도식·수식 많은 슬라이드용

**언제**: 도식·그래프·예시영상·수식이 "그림으로" 들어간 강의 슬라이드(이공계·대학원). 호서대 영상처리 413슬라이드(9 PDF)에서 검증됨.

**왜 Vision 필수**: PDF 텍스트 추출(pdfplumber/PyMuPDF)만 보면 그림으로 그려진 수식(예: `M=Σw(x,y)[[Ix²,IxIy],[IxIy,Iy²]]`)·도식·예시영상을 **못 본다** → 설명이 부정확·단순해진다. 슬라이드를 그림으로 정확히 읽으려면 에이전트가 **Read 도구로 슬라이드 PNG를 한 장씩 직접 열어 보고** 써야 한다.

**슬라이드당 2단 설명 구조** (오른쪽 column children):
```
💡 callout(desc)  ← 대학원 교수 수준. 슬라이드에 실제 그려진 수식/도식/예시를 정확히 옮기고 의미·유도·한계까지. 인라인 수식 허용.
▶ toggle "🧒 쉽게 이해하기 — 용어·수식 풀이"  ← 기본 접힘. children=중학생용 불릿(easy[])
     • Σ(시그마) — '여러 개를 전부 더해라'라는 뜻이에요. 1+2+3을 짧게 쓴 거죠.
     • 컨볼루션(합성곱) — 작은 도장(커널)을 사진 위에 한 칸씩 옮겨 찍으며 주변 값을 섞는 계산이에요.
```
토글이라 평소엔 깔끔(교수 설명만 보임), 어려우면 펼쳐 중학생용 풀이 → **정확함과 친절함을 한 페이지에**. (사용자 요구로 도출된 핵심 패턴.)

**검증된 메커니즘 (rclone·lh3·MCP 대신 — 더 안정적)**:
- **GDrive**: `googleapiclient` OAuth(`.gdrive_token.json`) + 폴더에 `permissions.create(role=reader,type=anyone)` **한 번** → 내부 파일 전부 per-file 권한 없이 `https://drive.google.com/thumbnail?id={ID}&sz=w1600` 로 렌더. `lh3.googleusercontent.com`·`uc?export=view` 형식은 Notion PATCH가 **거부**. ⚠️ OAuth 앱이 "테스트" 게시상태면 **refresh token이 7일마다 만료**(`invalid_grant`) → `_reauth_gdrive.py`(InstalledAppFlow 브라우저 동의)로 사용자 재인증 필요. 근본해결은 Cloud Console에서 동의화면을 "프로덕션"으로 게시.
- **Notion**: `requests` 직접 호출(POST `/pages`, PATCH `/blocks/{id}/children` 90블록 배치). MCP보다 대량·구조변경에 안정적.
- **설명 워크플로우**: 챕터를 ~13장 **청크로 쪼개 배치 6 순차**(in-flight ≤6 → 서버 rate limit 회피). 큰 PDF는 워크플로우 JS 안에서 내부 청킹(`chunks(n,13)`). 두 워크플로우 동시 실행 금지.
- **재개 가능 패치**: 텍스트만 수정할 땐 **이미지 재업로드 없이** 발행된 페이지의 오른쪽 column children만 삭제→[callout, toggle] 재생성. `_published.json`에 `{stem:{pid,ok}}` 기록.

**Vision 적대적 감사**: 감사관 에이전트도 **슬라이드 PNG를 직접 Read** 해서 ① desc가 실제 그림과 일치하는지 ② easy에 오개념 없는지 검증. 텍스트만 보는 감사는 vision 오독을 못 잡는다. 영상처리에서 실제로 히스토그램 좌우 뒤집힘·격자크기 날조(7×7→6×6)·패널 개수 오독을 적발. 적발 건은 감사관 fix + **사람(메인)이 슬라이드 재확인 후** 교정.

> 텍스트만으로 충분한 단순 자료는 아래 기존(텍스트) 파이프라인을 그대로 쓴다.

## 결과물 구조 (페이지 1개당)

```
H1: 강의자료 제목 (파란 배경)
--- PDF 페이지마다 반복 ---
  H2: 섹션 제목 또는 p001 (파란 배경)
  column_list
    ├─ 왼쪽 column: image (Google Drive 외부 URL — PDF 그 페이지 스캔)
    └─ 오른쪽 column: 그 페이지 내용을 풀어쓴 설명 블록들
  divider
```

## 사전 준비 (사용자 환경 의존)

- **rclone**: `RCLONE_BIN`(기본 `C:\Users\정화민\rclone\rclone.exe`), remote `gdrive`. 인증은 사용자가 한다.
- **Notion 업로드 경로 2가지** — 보통 **(B) MCP** 사용:
  - (A) `notion-client` + `NOTION_TOKEN` 환경변수 (03_build_notion.py 직접 실행)
  - (B) **Notion MCP** (`mcp__notion__API-*`). 워크스페이스에 통합(integration)이 연결돼 있어야 함. 실제 작업은 이 방식.
- **Python 패키지**: `PyMuPDF`(fitz), `pdfplumber`, (A 경로면 `notion-client`).
- **환경변수** (재사용 시 폴더/DB만 바꾸면 됨):
  - `METACODE_ROOT` = PDF가 들어있는 작업 폴더 (기본 메타코드 루트)
  - `METACODE_DB_ID` = 업로드 대상 Notion DB ID
  - `RCLONE_BIN`, `RCLONE_REMOTE`, `PDF_DRIVE_DEST` (기본값 있음)

## 워크플로우

`scripts/` 를 번호 순서대로 실행한다. **cp949 이모지 출력 에러 방지**를 위해 항상
`PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 를 붙인다.

### Step 0. 사전 점검 (인터랙티브) — `scripts/preflight.py` ★먼저 실행
작업을 시작하기 전에 **반드시** 환경·입력이 갖춰졌는지 자동 점검한다. 안 갖춰진 게 있으면 바로 작업에 들어가지 말고 사용자에게 요구/조치한다.
```
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/preflight.py pdf "<작업폴더>" --db "<Notion DB URL/ID>"
```
점검 항목: 작업 폴더 존재 + PDF/PPTX 유무 / PPTX 있으면 LibreOffice 유무 / 외부 구글드라이브·캐글 링크(.txt) 감지 / rclone 바이너리·`gdrive:` remote / PyMuPDF·pdfplumber / 대상 DB 입력 / UTF-8.

출력 해석 및 **인터랙티브 처리**:
- 종료코드 0(`진행 가능 ✅`)이면 Step 1로 진행.
- 종료코드 1이면 출력의 `MISSING`/`ASK>`/`FIX>` 를 보고 처리:
  - `ASK>` 항목 → **`AskUserQuestion` 으로 사용자에게 물어 받아낸다** (예: 대상 DB URL, 정확한 폴더 경로, 캐글 .ipynb 직접 다운로드 요청, rclone remote 인증 요청).
  - `FIX>` 항목 → 가능하면 **자동 조치** (예: 외부 드라이브 링크면 제시된 `rclone copy --drive-root-folder-id=...` 로 자료 내려받기, PPTX면 LibreOffice 추출·`soffice --convert-to pdf` 로 PDF 변환).
  - 조치 후 **preflight를 다시 실행**해 `진행 가능 ✅` 이 될 때까지 반복(최대 3회).
- preflight가 못 보는 것은 Claude가 직접 확인: 대상 DB가 실제 열리는지 `mcp__notion__API-retrieve-a-database` 로, **title property 이름이 `이름`인지** 확인. 폴더명·DB명이 헷갈리면(예: "8주차"인데 9주차로 착각) 추측 말고 사용자에게 확인.

### Step 1. PDF 분할 + 텍스트 추출 — `scripts/01_split_and_extract.py`
```
PYTHONUTF8=1 METACODE_ROOT="<작업폴더>" python scripts/01_split_and_extract.py
```
- 폴더 아래 모든 PDF를 재귀 탐색 → 페이지별 `_split_images/{deck_slug}/p{NNN}.png` (DPI 200).
- pdfplumber로 페이지 텍스트 추출 → `_output/content_cache.json`.
- deck_slug = `{강사식별자}_{상위폴더}_{파일명}`. 강사 식별 키워드(Sam/Liam/Bob/김동환=Kim/머신러닝=ML/통계=Stat/배상민=Bae/김도형=Koh/Jason/선형대수=LinAlg/마케팅=Mkt/파이썬=Py)가 내장돼 있다. **새 강사면 `01_split_and_extract.py`의 instructor 분기에 한 줄 추가**(안 그러면 `unknown`). slugify는 영숫자·한글 외 문자(공백·`+`·괄호 등)를 `_`로 정리한다.

### Step 2. Google Drive 업로드 → 임베드 URL — `scripts/02_upload_to_drive.py`
```
PYTHONUTF8=1 METACODE_ROOT="<작업폴더>" python scripts/02_upload_to_drive.py
```
- `_split_images/` 전체를 `gdrive:메타코드/노션이미지` 로 copy → `rclone link --expire 0` 로 **공개 권한 일괄 부여**.
- 파일 ID로 임베드 URL `https://lh3.googleusercontent.com/d/{ID}` 생성 → `_output/drive_urls.json` (`{deck_slug: {p001: url, ...}}`).

### Step 3. 설명(본문) 작성 — `_output/explanations_*.json`  ★핵심
PDF 페이지 텍스트(content_cache.json)를 읽고 **읽는 사람이 몰라도 이해되도록** 페이지마다 설명 블록을 쓴다.
- 스키마·블록 타입은 `references/SCHEMA.md` 참조 (`p`/`h3`/`callout`/`quote`/`num`/`bul`/`code`/`mermaid`/`divider`/`eq`).
- 파일명 `explanations_<무엇>.json`, 구조 `{deck_slug: {page_explanations: {"1":[...]}, section_titles: {"3":"제목"}}}`.
- **어투·양식은 아래 "텍스트 작성 규칙"을 그대로 따른다** (재사용 시 동일 톤 유지가 목적).
- 여러 파일로 나눠 쓴 뒤 `scripts/merge_explanations.py` 로 `_output/explanations.json` 병합.

### Step 4. 노션 블록 직렬화 — `scripts/04_serialize_blocks.py`
```
PYTHONUTF8=1 METACODE_ROOT="<작업폴더>" python scripts/04_serialize_blocks.py
```
- content_cache + explanations + drive_urls → `_output/page_blocks.json` (자료별 완성 블록 시퀀스). `03_build_notion.py`의 빌더 재사용.

### Step 5. 노션 업로드
- **(B) MCP 경로 (권장, 실제 사용)**: page_blocks.json을 **25~30블록 청크로 잘라** 순차 append.
  1. `mcp__notion__API-post-page` 로 DB(`METACODE_DB_ID`)에 빈 페이지 생성 (title property 이름은 DB 스키마 확인).
  2. `mcp__notion__API-patch-block-children` 로 청크를 그대로 children에 append.
  3. 업로드는 **아래 "🚨 업로드 불변 규칙"** 을 지키는 에이전트에 위임 가능.
- **(A) notion-client 경로**: `NOTION_TOKEN` 설정 후 `python scripts/03_build_notion.py`.

## 🚨 업로드 불변 규칙 (가장 자주 깨지는 부분 — 반드시 지킬 것)

업로드를 에이전트에 맡기면 종종 "MCP는 paragraph만 지원한다"며 거부하거나
`image`/`code`/`equation`/`column_list` 를 `paragraph` 로 **변형**한다. 이는 임무 실패다.

- **사실**: `mcp__notion__API-patch-block-children` 는 스키마에 paragraph/bulleted만 보여도
  **실제로는 image·code·equation·callout·column_list·heading·divider 등 모든 블록 타입을 처리한다.**
- 업로드 에이전트 지시 문구:
  > 🚨 Read한 청크 JSON을 **변형 없이 그대로** children에 넣어라. MCP는 code/image/equation/callout/column_list 등 모든 블록을 처리한다. code를 paragraph로 바꾸거나 image를 빼면 임무 실패. Bash 불필요. 529/소켓에러는 같은 청크 재시도.
- **100블록/요청 제한** → column_list children까지 합산되므로 **보수적으로 25~30블록**씩.
- **업로드 에이전트는 `executor`(sonnet)를 쓴다.** `executor-high`(opus)는 Notion MCP 툴이 노출되지 않아 업로드 불가(설명·spec 작성 같은 파일 작업엔 executor-high 사용 가능).
- **청크 누적 버그**: 한 업로드 에이전트에 청크가 많으면(8개+) 간헐적으로 에이전트가 청크들을 합쳐 한 요청에 보내 `400 no low surrogate`(거대 요청) 에러가 난다(청크 자체는 깨끗). 대응: ①**한 에이전트당 청크 ≤8** ②실패 반복 시 **단일 청크 에이전트 순차 발사** ③한 페이지의 청크가 8개 초과면 c01~c08, c09~ 식으로 **순차 배치**(같은 페이지 동시 업로드는 순서 꼬임 위험). ④100p+ 대형 PDF는 애초에 노션 페이지를 2~3개로 분할.
- 중단·중복 업로드가 의심되면 **실제 블록 텍스트를 확인**하고 판단한다(추측 금지). 깨진 페이지는
  `mcp__notion__API-delete-a-block` 로 archive 후 재생성·재업로드(이어붙이기는 경계 불확실하므로 지양).

## 텍스트 작성 규칙 (다음에도 동일 양식 유지 — 핵심 목적)

오른쪽 설명 column은 **참조 노션 페이지("기초통계 Part1") 스타일**을 따른다:

- **어투**: 친근하게 (~예요 / ~이야 / ~입니다). 전문용어는 쉬운 말 병기 (예: 회귀(regression)).
- **핵심 용어는 `**굵게**`**, 코드/변수명은 `` `백틱` ``, 강조는 `_이탤릭_`.
- **페이지 한 줄 요약**은 맨 위 `callout`(orange_background, 💡).
- **팁**은 `callout`(blue_background ⚙️), **주의**는 red_background.
- "정의 = 설명" 나열은 `num`, 특징·항목 나열은 `bul`.
- 개념 흐름/분류는 `mermaid` flowchart, 수식은 `eq`(LaTeX).
- **표지·목차·간지** 페이지는 짧은 안내 1~2줄만.
- 자료에 없는 내용을 지어내지 말 것. 이해를 돕는 개념 보충은 OK.
- 새 단원이 시작되는 페이지에는 `section_titles` 로 H2 제목을 지정.

자세한 스키마·예시는 `references/SCHEMA.md` 를 읽고 그대로 따른다.

## 재사용 체크리스트 (새 폴더 적용 시)
1. `METACODE_ROOT`(PDF 폴더), `METACODE_DB_ID`(노션 DB) 설정.
2. 새 강사/카테고리가 있으면 `01_split_and_extract.py` 강사 식별 키워드 보강.
3. Step1→2 실행 후 `drive_urls.json` 페이지 수가 PDF 페이지 수와 맞는지 확인.
4. Step3에서 위 "텍스트 작성 규칙"으로 설명 작성 (어투 동일).
5. Step4 직렬화 → Step5 업로드(불변 규칙 준수).
6. 업로드 후 각 페이지 이미지 누락/중복/블록 변형 여부를 텍스트로 검증.
