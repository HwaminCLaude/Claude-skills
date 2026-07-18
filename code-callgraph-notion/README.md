# code-callgraph-notion

Python 코드베이스를 **함수·메서드(원자단위) 호출그래프**로 정적 분석해, **계층형 Mermaid 다이어그램**으로 만들고
각 노드를 **GitHub 소스 라인(#Lxx)** 에 딥링크한 뒤 **Notion 페이지**에 발행하는 Claude Code 스킬입니다.
파일/모듈 상자 수준을 넘어 "모든 코드의 연관관계·원자단위 코드 연결"까지 한 페이지에서 보여줍니다.

## 결과물 모양 (대상 1개 = 노션 페이지 1개)
```
H1: 원자단위 아키텍처 — <라벨> · 코드 링크 = GitHub #Lxx
> 규모(파일·클래스·함수·호출엣지) 요약
── (선택) 이 대상의 델타: 공유 코어 대비 신규/활성 모듈 + 비활성 안내 ──
## L1 — 서브시스템별 함수 호출 그래프
  mermaid: 그룹(모듈 집합)별 함수·메서드 노드 + 실제 호출 엣지 + click→GitHub
  … 서브시스템 수만큼 반복 …
## L2 — 핵심 실행 호출체인
  mermaid: 순서 있는 실행 경로(학습 루프·추론 경로·특정 파이프라인 등)
```
- 노드 = 함수/메서드, 화살표 = **정적 AST로 추출한 실제 호출/의존**(추정 아님).
- 델타(이 대상이 신규 작성·처음 활성화·핵심 사용하는 원자단위)는 **굵은 주황 테두리**로 강조.

## 언제 자동 호출되나
"코드 아키텍처를 함수 단위까지 세분화", "원자단위 코드 연결 다이어그램", "함수 호출 그래프를 머메이드로/노션에",
"모듈 다이어그램을 더 구체화(함수·메서드까지)", "call graph를 GitHub 링크 걸어서 정리" 등.
> 단순 파일 트리·개념 설명이 아니라 **실제 호출 엣지**를 원할 때. 강의자료·노트북 변환은 자매 스킬(pdf-to-notion / code-guidebook-notion) 사용.

## 설치
저장소 루트 README의 설치 안내를 따라 이 폴더를 `~/.claude/skills/code-callgraph-notion/` 에 복사하세요.

## 사전 준비
- **Python 3.10+** (추출·렌더는 표준 라이브러리만 사용)
- **mermaid-cli**(`npm i -g @mermaid-js/mermaid-cli`) — 발행 전 문법 검증용
- **notion-client**(`pip install notion-client`) + Notion 통합 토큰(페이지가 통합과 공유돼 있어야 함)
- 코드가 **GitHub에 있어야** 노드 click 딥링크 생성(없으면 URL 없이 그래프만)

## 사용 절차 (`scripts/`)
핵심 원칙: **정확한 그래프는 AST로(전사 오류 0), 의미(그룹핑·체인·델타)는 layout/delta 설정으로.**

| 단계 | 스크립트 | 하는 일 |
|------|----------|---------|
| 1. 추출 | `ast_graph.py <패키지루트> <out_dir> --pkg-root src --github-base https://github.com/OWNER/REPO --url-prefix src --label <이름>` | import 스코프 해석 호출그래프 → `graph.json`(심볼·lineno·엣지). `__init__/forward/update` 오결선 방지 내장 |
| 2. layout 작성 | (수기/에이전트) `layout.json` | `groups`(모듈 집합 → L1)·`chains`(순서 있는 `[mod::sym, mod::sym, 라벨]` → L2)·`tones`. 템플릿: [`references/example_layout_nmfc.json`](./references/example_layout_nmfc.json) |
| 3. 렌더 | `build_mermaid.py <graph.json> <out_md> --layout layout.json [--delta delta.json]` | 계층형 Mermaid(노드/URL verbatim). `delta.json`으로 대상별 강조·인트로 |
| 4. 검증 | `validate_mermaid.py <out_md>` | 모든 mermaid 블록을 `mmdc`로 렌더 → 실패 0 확인(발행 전 필수) |
| 5. 발행 | `publish_notion.py <page_id> <out_md> --label <이름> --sentinel "원자단위 아키텍처"` | notion-client로 멱등 발행(센티넬 이후만 교체, 기존 내용 보존, 2000자 분할) |

> 추출 직후 **팬텀 엣지 0** 검산(`dst_mod`이 노드에 없으면 `--pkg-root`/`--url-prefix` 틀림).
> chain 심볼은 `graph.json`에 실제로 있는 `mod::sym`만. 흔한 이름·config 동적 분기 엣지는 layout에 수동 추가.

## 정확도 설계 (왜 신뢰할 수 있나)
- **import 스코프 해석**: `from pkg.a.b import c` + `__init__` 재수출을 따라가 호출 대상을 정확히 특정.
- **흔한 이름 오결선 차단**: `__init__`·`forward`·`update`·`predict` 등은 여러 클래스 중복 → 전역 이름매칭에서 제외.
- **config 동적 분기**(팩토리가 문자열로 클래스 선택)는 AST가 못 잡으므로 layout의 L2 chain으로 수동 표현.
- 하나의 소스가 **여러 repo로 복사**된 경우 각 repo 관점의 델타만 다르게 주면 동일 그래프 재사용.

## Notion 함정
- 새 API의 `query-data-source`에 **database_id를 주면 `invalid_request_url`** → DB 행(페이지) ID는 `post-search`/`get-block-children`로 찾는다.
- Notion Mermaid는 `click NODE "url"` 하이퍼링크를 **지원**(발행된 노드가 실제 GitHub로 이동).

자세한 절차·함정은 [`references/pipeline_guide.md`](./references/pipeline_guide.md) 와 [`SKILL.md`](./SKILL.md) 참고.
