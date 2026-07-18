# 코드 가이드북 spec 스키마 (LLM 워크플로가 채우는 JSON)

`publish_code_pages.py` 가 소비한다. **LLM은 설명(개념/용어/입력/로직/출력)만** 쓰고,
**코드·연결(호출)·GitHub 링크·헤딩은 publisher가 `units.json`에서 결정론적으로 삽입**한다(날조 0).

## 1) `glossary.json` — 개념·용어 개요(프로젝트당 1개, 코드가 같으면 1회 생성해 재사용)

```jsonc
{
  "title": "📖 <프로젝트> — 이게 뭘 하려는 프로젝트인가 + 용어집",
  "problem": "우리가 풀려는 문제 (12살 눈높이, 2~4문장)",
  "idea":    "핵심 아이디어 (12살, 왜 이 방법인지)",
  "flow":    "데이터가 흐르는 큰 그림 (12살, 몇 단계로)",
  "glossary": [
    {"term": "친화도(affinity) π", "def": "쉬운 정의 + 비유 (12살)"},
    {"term": "국소 에너지 E±",     "def": "..."}
  ]
}
```

## 2) 모듈 spec — `specs.json` = `{ "<module>": <module_spec>, ... }` (모듈=파일 1개)

```jsonc
{
  "nmfc/energy.py": {
    "title": "국소 에너지·기하 로짓",            // 페이지 제목 뒷부분(모듈 경로는 자동 접두)
    "module_concept": "이 파일은 …(12살, 이 파일이 프로젝트에서 맡은 개념·역할 2~3문장)",
    "prerequisites": "이 파일을 이해하려면 미리 알면 좋은 것 (한 줄, 없으면 생략)",
    "flowmap_goal": "이 파일이 결국 만들어내는 것 한 문장",
    "functions": [
      {
        "sym": "local_energies",                 // units.json의 sym과 정확히 일치(메서드는 Class.method)
        "concept": "이 함수가 구현하는 도메인 개념과 왜 필요한지 (12살, 1~3문장)",
        "terms": [ {"term": "국소 에너지", "def": "쉬운 정의 + 비유"} ],   // 없으면 []
        "input":  "파라미터가 대체로 무엇인지 12살 눈높이 한두 문장",
        "args":   [ {"name":"d2","meaning":"거리제곱 표","note":"클수록 멀다(선택)"} ], // 주요 인자/하이퍼파라미터. 없으면 []
        "logic":  ["단계1 무슨 일", "단계2", "…"],   // 큰 흐름(순서 있는 단계)
        "line_by_line": [ {"code":"e_pos = torch.einsum('pnm,nm->np', pi_pos, d2)", "explain":"이 줄은 …"} ], // 코드 핵심 줄 풀이. 긴 함수는 핵심 줄만. 없으면 []
        "output": "반환값이 무엇이고 무엇을 의미하는지",
        "tip_engineering": "⚙️ 이 값/설정을 어떻게 정하나 (하이퍼파라미터 있을 때만, 없으면 생략)",
        "tip_practice": "💼 실무에서는 언제 쓰나/흔한 실수/대안 (관련 있을 때만, 없으면 생략)"
      }
    ],
    "checklist": ["이 파일에서 꼭 기억할 것1", "…"]   // ✅ 핵심 체크리스트(2~5개)
  }
}
```

### 규칙
- `functions[].sym` 은 `units.json` 의 sym과 **정확히 일치**해야 매칭됨(불일치 시 그 함수 설명 누락).
- 12살 눈높이·친근한 어투(~예요/~해요). **코드·도메인 문서에 없는 내용 날조 금지**(개념 보충은 OK).
- 전문용어는 처음 나올 때 `terms`로 풀고, 큰 개념은 `glossary`에 → 페이지가 **읽는 내내 막힘없이** 이해되게.
- 코드 본문·시그니처·호출 관계·GitHub 링크는 **쓰지 말 것**(publisher가 units.json에서 넣음).

## Mode B+ 필드 (수식·예시 — math 함수에만, LLM이 추가)

기존 function 객체에 아래 2개를 **병합**(값 숫자·그림은 publisher가 trace.json에서 자동 삽입):
```jsonc
"formula_latex": "E^{\\pm}_k(z_i)=\\sum_j \\pi^{\\pm}_{ij}(k)\\,\\lVert z_i-z_j\\rVert^2",  // KaTeX. 수식 없으면 ""
"example_note":  "예시 데이터가 이 함수를 지나며 어떻게 변하는지 12살 1~3문장(값 숫자는 나열 말 것 — 자동 삽입)"
```
- `formula_latex`는 docstring 수식을 정식 KaTeX로. `example_note`는 개념 서술만(실제 값·shape·그림은 `trace.json`의 `funcs["mod::sym"]`에서 publisher가 code 블록+image로 삽입).
- `trace.json`(trace_harness.py 산출)·`drive_urls.json`(upload_figures.py 산출)을 `publish_code_pages.py --trace/--drive-urls`로 넘기면 📐수식·🔢예시(실행값)·📊그림이 함수 섹션에 렌더된다.

## publisher가 만드는 최종 페이지(모듈당)
`H1(모듈 — title)` → `🎯 callout(module_concept)` → `📍 flowmap(함수 목록)` → 함수마다:
`H2(시그니처)`(앵커) → 개념 → 📖 용어(terms, 용어집 링크) → 입력 → 로직(번호) → 출력 →
🔗 연결(units의 calls/called_by → 해당 모듈 페이지 링크) → ▶ 코드(toggle, python) → 원본(GitHub #Lxx).
