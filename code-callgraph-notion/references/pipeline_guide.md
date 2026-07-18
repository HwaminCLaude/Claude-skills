# code-callgraph-notion — 파이프라인 가이드 (참조용)

원자단위(함수·메서드) 호출그래프를 정확히 뽑아 계층형 Mermaid로 만들고 Notion에 발행하는 4단계.
SKILL.md의 요약을 보완하는 세부·함정 모음.

## 0. 전제

- 대상은 **Python 패키지**(디렉터리에 `__init__.py`, 내부는 절대 import `from <pkg>.a.b import c` 권장).
  상대 import(`from ..a import b`)와 `__init__.py` 재수출도 해석하지만, 절대 import일수록 정확도가 높다.
- 노드 click 딥링크를 만들려면 코드가 **GitHub에 올라가 있어야** 한다(`--github-base https://github.com/OWNER/REPO`,
  `--ref main`, `--url-prefix <repo루트→패키지루트 경로>`). 없으면 URL 없이 그래프만 생성된다.
- Mermaid 검증엔 `mmdc`(mermaid-cli)가 필요: `npm i -g @mermaid-js/mermaid-cli`.
- Notion 발행엔 `pip install notion-client` + 통합 토큰 + 페이지가 통합과 공유돼 있어야 한다.

## 1. AST 추출 (`scripts/ast_graph.py`)

```
python scripts/ast_graph.py <패키지루트디렉터리> <출력디렉터리> \
  --pkg-root src --github-base https://github.com/OWNER/REPO --ref main --url-prefix src --label myproj
```
- 산출 `graph.json`: `nodes[]`(mod, sym, kind, line, subsys, url), `edges[]`(src/dst mod·sym, kind, count), `counts`.
- 엣지 종류: `import-call`(import된 심볼 호출, 가장 정밀), `method-call`(코드베이스 전체에서 **고유한** 메서드명 호출),
  `local-call`(같은 파일 내 함수 호출).

### 정확도·함정
- **흔한 이름 오결선 방지**: `__init__`·`forward`·`update`·`predict`·`step`·`fit` 등은 여러 클래스에 중복되므로
  전역 이름매칭에서 제외한다(`COMMON_AMBIG`/`DUNDER`). 이 심볼들 사이 엣지가 꼭 필요하면 L2 chain에 수동으로 넣는다.
- **config 동적 분기**(팩토리 함수가 문자열/설정으로 클래스를 고르는 경우)는 AST가 못 잡는다 → L2 chain 또는
  layout에 수동 엣지로 표현.
- 추출 후 반드시 검산: `edges` 중 `dst_mod`가 `nodes`의 mod 집합에 없으면(팬텀) 패키지 루트/`--pkg-root` 설정이 틀린 것.
  아래 스니펫으로 0인지 확인.
```python
import json; g=json.load(open("graph.json",encoding="utf-8"))
nm={n["mod"] for n in g["nodes"]}
print("phantom:", [e for e in g["edges"] if e["dst_mod"] not in nm][:5])
```

## 2. 계층형 Mermaid 생성 (`scripts/build_mermaid.py`)

```
python scripts/build_mermaid.py <graph.json> <out_md> --layout layout.json --delta delta.json
```
- **layout.json**(형식은 `references/example_layout_nmfc.json` 참고):
  - `groups`: L1. 각 그룹 = 모듈 집합. 그룹 안의 노드 전부 + **양 끝이 그룹 안인 엣지만** 그린다
    (그래서 그룹을 겹치게 정의하면 cross-module 호출을 포착: 예 `heads.py`를 수학그룹·추론그룹 양쪽에 넣기).
    가독성 위해 **그룹당 노드 ≲40** 유지(넘으면 모듈을 더 잘게 쪼갠 그룹으로).
  - `chains`: L2. 순서 있는 `[src, dst, label]` 엣지 리스트. src/dst는 `"mod::sym"`(graph.json의 정확한 값).
    그래프에 없는 심볼은 자동 생략되고 문서에 주석으로 남는다.
  - `tones`(선택): 모듈/접두사 → 색(toneBlue/Amber/Mint/Rose/Indigo/Teal/Neutral). 없으면 top-level 폴더별 자동 배색.
  - layout 자체가 없으면 top-level 디렉터리별 자동 그룹(체인 없음)으로 폴백.
- **delta.json**(선택, 대상별 강조): `{owned_modules, owned_symbols(["mod::sym"]), intro_md, inactive_note}`.
  owned 노드는 굵은 주황(toneDelta)으로 강조되고, intro_md/inactive_note가 문서 상단에 삽입된다.
  여러 repo가 **동일 코드**를 공유할 때(예: 한 소스를 여러 프로젝트로 복사) 각 repo 델타만 다르게 주면 된다.
- **delta를 대량 자동 추출**하려면: 대상별 설명 문서를 읽혀 구조화(JSON) 반환하는 서브에이전트를 병렬로 돌리고,
  결과를 `graph.json`의 정확한 `mod`/`mod::sym` 키에 매핑해 delta.json으로 저장(수동 전사 금지 → 오류 0).

## 3. 검증 (`scripts/validate_mermaid.py`)

```
python scripts/validate_mermaid.py <out_md> [<out_md> ...]
```
- 모든 ```mermaid 블록을 mmdc로 렌더 → 실패 0 확인(반환코드 1이면 실패 있음). Notion 발행 **전에 필수**.
- 코드가 여러 repo에서 동일하면 구조가 같으므로 대표 1~2개 + 특화 chain만 검증해도 충분하다.
- GitHub URL 표본은 `curl -s -o /dev/null -w "%{http_code}" -L <url>` 로 200 확인.

## 4. Notion 발행 (`scripts/publish_notion.py`)

```
python scripts/publish_notion.py <page_id> <out_md> --label plan2 --sentinel "원자단위 아키텍처"
```
- 토큰 탐색 순서: `--token` → `NOTION_TOKEN` → `~/.claude.json`의 `mcpServers.notion.env.OPENAPI_MCP_HEADERS`(Bearer).
- **멱등**: 페이지에 센티넬 heading이 있으면 그 블록+이후 전부 삭제 후 재발행. 그 앞의 기존 내용(예: 원래 모듈지도)은 보존.
- 코드블록은 language `"mermaid"`, 2000자 초과 시 rich_text 다중 조각으로 자동 분할.

### Notion DB/페이지 ID 찾기 (함정)
- 새 Notion API의 `query-data-source`에 **database_id를 주면 `invalid_request_url`** 실패한다.
  DB 행(=페이지) ID는 `post-search`(제목 필터) 또는 `get-block-children`(부모 페이지)로 찾고,
  각 행 페이지의 `parent.data_source_id`가 그 DB인지로 걸러낸다.
- Notion Mermaid는 `click NODE "url"` 하이퍼링크를 **지원**한다(발행된 다이어그램 노드가 실제 GitHub로 이동).

## 발행 후 검증
- notion-client로 각 페이지 children을 나열해 `type=="code" & language=="mermaid"` 블록 수, heading 수,
  `toneDelta` 포함 여부를 확인. 원래(보존돼야 할) 블록이 그대로 있는지도 확인.
