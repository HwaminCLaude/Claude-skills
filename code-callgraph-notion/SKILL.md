---
name: code-callgraph-notion
description: 'Python 코드베이스를 함수·메서드(원자단위) 호출그래프로 정적 분석해, 계층형 Mermaid 다이어그램(L0 모듈지도, L1 서브시스템 함수그래프, L2 실행 호출체인)으로 만들고 각 노드를 GitHub 소스 라인에 딥링크한 뒤 Notion 페이지에 발행하는 스킬. 파일/모듈 상자 수준을 넘어 "모든 코드의 연관관계·원자단위 코드 연결"까지 보여준다. 나아가 코드 자체를 Notion 페이지에 복사하고 code-guidebook 방식(개념·전문용어·입력·로직·출력·연결을 12살 눈높이로)으로 설명해, 다이어그램 노드를 누르면 그 함수의 코드+가이드북이 Notion에서 열리는 코드 가이드북 모드도 지원한다(Mode B). 사용자가 "코드 아키텍처를 함수 단위까지 세분화", "원자단위 코드 연결 다이어그램", "함수 호출 그래프를 머메이드로/노션에", "모듈 다이어그램을 더 구체화(함수·메서드까지)", "call graph를 GitHub 링크 걸어서 정리", "코드 구조를 노션에 계층형으로", "코드를 노션에 옮기고 guidebook으로 이해하기 쉽게", "노드 누르면 코드+설명 노션에서 보게" 라고 할 때 사용한다. 단순 파일 트리나 개념 설명이 아니라 실제 호출 엣지를 원한다면 이 스킬.'
---

# code-callgraph-notion

Python 패키지에서 **함수·클래스·메서드(원자단위)** 호출그래프를 정적 추출(stdlib `ast`)해,
현재 스타일을 계승한 **계층형 Mermaid** 다이어그램으로 만들고, 각 노드를 **GitHub 소스 라인(#Lxx)** 에
딥링크한 뒤 **Notion**에 멱등 발행한다. 파일 단위 상자를 함수 단위 호출 엣지까지 심화하는 것이 목적.

## When to use

- 파일/모듈 수준 아키텍처 다이어그램을 **함수·메서드 단위로 더 구체화**하고 싶을 때.
- "원자단위 코드들의 연결", "call graph", "함수 호출 관계"를 정확히(추정 아님) 보고 싶을 때.
- 그 결과를 **GitHub 링크가 걸린 Mermaid**로, 또는 **Notion 페이지**로 정리하고 싶을 때.
- 하나의 소스가 여러 GitHub repo로 나뉘어 있고 각 repo 관점의 다이어그램이 필요할 때(델타 강조).

## 산출물

대상(플랜/모듈/repo)별로 다음을 포함한 `_diagrams.md` 1개 → Notion 페이지 블록:
- **L1**: layout.groups(모듈 집합)별 함수 호출 그래프. 그룹을 겹치게 정의하면 cross-module 호출도 포착.
- **L2**: layout.chains(순서 있는 실행 호출체인, 예 학습 루프·추론 경로·특정 파이프라인).
- 모든 노드 = 함수/메서드, click → GitHub `blob/<ref>/<prefix>/<mod>#L<line>`.
- (선택) 대상별 델타 강조(굵은 주황) + 인트로/비활성 안내.

## 워크플로 (4단계 — 세부·함정은 `references/pipeline_guide.md` 필독)

핵심 원칙: **정확한 그래프는 AST로(전사 오류 0), 의미(그룹핑·체인·델타)는 layout/delta 설정으로.**

1. **AST 추출** — 대상 repo의 패키지 루트에 대해 실행:
   ```
   python scripts/ast_graph.py <패키지루트> <out_dir> \
     --pkg-root src --github-base https://github.com/OWNER/REPO --ref main --url-prefix src --label <이름>
   ```
   → `graph.json`. 추출 직후 팬텀 엣지(`dst_mod`이 노드에 없음) 0인지 검산(가이드 참고). 0 아니면 `--pkg-root`/`--url-prefix` 조정.

2. **layout.json 작성** — `references/example_layout_nmfc.json`을 템플릿으로:
   - `graph.json`의 `counts`로 규모 파악(함수 노드가 수십~수백이면 반드시 계층 분할).
   - 자연스러운 서브시스템을 `groups`(모듈 집합, 그룹당 노드 ≲40)로, 핵심 실행 경로를 `chains`(`[mod::sym, mod::sym, 라벨]`)로 정의.
   - chain의 심볼은 `graph.json`에 실제로 있는 `mod::sym`만. 흔한 이름(`__init__`/`forward` 등)이나 config 동적 분기 엣지는 여기서 수동 추가.
   - (선택) 대상별 `delta.json`{owned_modules, owned_symbols, intro_md, inactive_note}. 대량이면 설명문서→구조화(JSON)를 서브에이전트 병렬로 뽑아 매핑.

3. **Mermaid 생성 + 검증**:
   ```
   python scripts/build_mermaid.py <graph.json> <out_md> --layout layout.json [--delta delta.json]
   python scripts/validate_mermaid.py <out_md>        # mmdc로 렌더, 실패 0 확인(발행 전 필수)
   ```

4. **Notion 발행** — 페이지 ID 확보 후(가이드의 'DB/페이지 ID 찾기' 함정 참고):
   ```
   python scripts/publish_notion.py <page_id> <out_md> --label <이름> --sentinel "원자단위 아키텍처"
   ```
   멱등(센티넬 이후만 교체, 기존 내용 보존). 발행 후 children을 나열해 mermaid 블록 수·구조를 검증.

## 코드 가이드북 모드 (Mode B — 코드를 Notion으로 옮기고 이해)

노드를 GitHub가 아니라 **Notion 코드페이지**로 연결하고, 각 함수의 코드+가이드북 설명(개념·전문용어·입력·로직·출력·연결, 12살 눈높이)을 Notion에 싣는다. code-guidebook-notion 스킬의 블록 형식을 이식했다. 세부는 `references/CODE_GUIDEBOOK_SCHEMA.md`.

1. **코드 단위 추출**: `python scripts/extract_code_units.py <패키지루트> <graph.json> <units.json> --pkg-root src`
   → 함수별 전체 소스(lineno..end_line)·시그니처·docstring·호출/피호출 엣지. (`ast_graph.py`가 `end_line`을 넣어줌)
2. **개요·용어집 + 모듈 spec 생성(LLM)**: 도메인 문서로 `glossary.json`(문제·아이디어·흐름 + 전문용어 사전, 12살), units로 모듈별 spec JSON(함수마다 concept/terms/input/args/logic/line_by_line/output/tips + 모듈 prerequisites/checklist). 스키마: `references/CODE_GUIDEBOOK_SCHEMA.md`. 형식만 지키면 코드·GitHub 링크는 쓰지 말 것(파이프라인이 units에서 삽입).
3. **코드페이지 발행 + 앵커 수집**:
   ```
   python scripts/publish_code_pages.py --plan-page <PARENT_PAGE_ID> --github-base https://github.com/OWNER/REPO \
     --units units.json --glossary glossary.json --specs specs.json --out-anchors anchors.json --label <이름>
   ```
   부모 페이지 아래에 📖 개요·용어집 + 모듈당 1 코드페이지 생성(멱등: 같은 title은 아카이브 후 재생성), 함수 heading 블록 앵커를 `anchors.json`(sym → `page_url#blockid`)에 수집.
4. **다이어그램을 Notion으로 재연결**: `build_mermaid.py ... --notion-map anchors.json` → 노드 click이 Notion 코드페이지 함수 앵커로(앵커 없으면 GitHub 폴백). 이어서 `publish_notion.py`로 재발행.

주의: 앵커는 발행 후에만 얻어짐 → **코드페이지 발행 뒤** 다이어그램 재연결(2패스). `publish_notion.py`는 child_page(코드페이지)를 삭제하지 않는다. 같은 소스가 여러 repo면 spec은 1회 생성해 재사용하고 `--github-base`/부모 페이지만 바꿔 반복.

## 도구·전제

- `mmdc`(mermaid-cli): `npm i -g @mermaid-js/mermaid-cli`. `notion-client`: `pip install notion-client`.
- Notion 토큰은 `--token`/`NOTION_TOKEN`/`~/.claude.json`(mcpServers.notion) 순으로 자동 탐색.
- 코드가 GitHub에 없으면 URL 없이 그래프만 생성 가능(Notion 발행은 그래도 됨, 링크만 비활성).

## 재사용 자원

- `scripts/ast_graph.py` — import 스코프 해석 호출그래프 추출기(흔한 이름 오결선 방지, `end_line` 포함).
- `scripts/build_mermaid.py` — graph+layout+delta → 계층형 Mermaid(결정론, 노드/URL verbatim). `--notion-map`으로 노드를 Notion 앵커로.
- `scripts/validate_mermaid.py` — mmdc 문법 검증.
- `scripts/publish_notion.py` — notion-client 멱등 발행(2000자 분할, mermaid 코드블록, child_page 보존).
- **[Mode B]** `scripts/extract_code_units.py` — 함수별 소스·시그니처·docstring·엣지 → units.json.
- **[Mode B]** `scripts/notion_blocks.py` — 가이드북 spec → Notion 블록(code-guidebook 빌더 이식: 링크·2000자 분할·flowmap·toggle).
- **[Mode B]** `scripts/publish_code_pages.py` — 개요/용어집 + 모듈 코드페이지 발행 + 함수 앵커 수집(멱등: 아카이브 후 재생성).
- `references/pipeline_guide.md` — 단계별 세부·함정(AST 정확도, Notion ID 찾기, click 지원 등).
- `references/CODE_GUIDEBOOK_SCHEMA.md` — **[Mode B]** glossary/모듈 spec 형식(개념·용어·입력·인자·로직·한줄풀이·출력·팁·체크리스트).
- `references/example_layout_nmfc.json` — 실제 사용한 layout(groups 7 + chains 3) 템플릿.
