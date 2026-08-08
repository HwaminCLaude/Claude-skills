# 코딩북 유닛 저작 규약

한 유닛 = 파이썬 모듈 파일 하나 `units/W04U05.py`.
이 파일만 만들면 나머지(그림 생성·이미지 업로드·노션 발행·노트북 빌드)는 자동이다.

**독자**: 프로그래밍도 수학도 처음인 성인. 친절하지만 얕지 않게.

---

## 1. 모듈이 반드시 정의할 것

```python
# -*- coding: utf-8 -*-
UNIT  = "W04U05"                     # curriculum.json 의 id
TITLE = "05 · 로지스틱 회귀 — 시그모이드와 로그손실"
GOAL  = "시그모이드·로그손실을 직접 구현하고 왜 MSE를 안 쓰는지 설명한다."
PREREQ = "04주차 02 경사하강법 (기울기로 파라미터를 고치는 과정)"

def figs(plt):        # matplotlib 그림. unitkit.save(fig, key) 로 저장
    ...

def build(B, IM):     # 노션 블록 리스트를 반환
    return [ ... ]

NB = { "setup": [...], "explore": [...], "todo": [...],
       "check": [...], "apply": [...], "wreck": [...] }
```

- `figs(plt)` — `plt` 는 한글 폰트가 이미 잡힌 pyplot. 그림마다
  `from unitkit import save; save(fig, "w04u05_sigmoid")` 로 저장.
- `build(B, IM)` — `B` 는 `blocks.py`. `IM("w04u05_sigmoid", "캡션")` 은 `B.image` 단축.
- 이미지 key 는 **유닛id 소문자 접두사**를 붙일 것 (`w04u05_...`). 충돌 방지.

---

## 2. 노션 페이지 9층 구조 (순서·제목 고정)

`build()` 는 아래 순서를 **정확히** 지켜 블록을 만든다. heading 문구도 그대로.

| # | 블록 | 내용 |
|---|---|---|
| 1 | `B.callout(..., "🎯", B.ORANGE)` | 목표 한 줄 + 완료 기준 |
| 2 | `B.h2("🧭 먼저 알고 오세요")` | 선수지식. 없으면 "처음이어도 괜찮아요" 로 |
| 3 | `B.h2("📖 개념")` | 왜 필요한가 → 무엇인가. **그림 1~2장 필수** |
| 4 | `B.h2("🧮 수식")` | `B.equation()` + **예시 숫자 대입** |
| 5 | `B.h2("💻 직접 만들기")` | 라이브러리 없이 구현한 코드 |
| 6 | `B.h2("🔬 맞는지 확인")` | 라이브러리 대조 + **관례 차이 경고** |
| 7 | `B.h2("🧪 강의 자료에 적용")` | 실제 메타코드 노트북·데이터 이름 명시 |
| 8 | `B.h2("✅ 스스로 확인")` | 체크리스트 + 망가뜨리기 실험 |
| 9 | `B.h2("🔗 더 보기")` | 관련 개념 안내 |

---

## 3. 글쓰기 규칙

- 친근한 존댓말(**~예요/~이에요/~해요**). "~한다" 금지.
- 처음 나오는 전문용어는 **굵게** + 한글(영어) 병기 → **손실 함수(loss function)**
- 코드·변수·파일명은 백틱. **밑줄 들어간 식별자는 반드시 백틱**
  (파서가 `_..._` 를 이탤릭으로 오인함) → `` `log_loss` `` (O), `log_loss` (X)
- 비유를 쓰되 비유로 끝내지 말고 반드시 수식·코드로 연결.
- 콜아웃 색: 주황=목표, 파랑=팁, 빨강=주의, 초록=정답 확인.

---

## 4. 절대 하면 안 되는 것 (실측된 함정)

| 금지 | 이유 |
|---|---|
| `B.code(src, "text")` | 400 에러. `"plain text"` 를 쓸 것 |
| 블록 수식에 `$` 넣기 | `B.equation("x^2")` 처럼 `$` 없이 LaTeX만 |
| 토글 안에 표·토글 | 중첩 2단계 초과 → 실패 |
| 이미지 외부 URL 직접 | 이 계정은 Drive 임베드가 막힘. 반드시 `B.image(key)` |
| 한 rich_text 2000자 초과 | `dump_chunks` 가 분할하지만 애초에 문단을 쪼갤 것 |
| 노션 API 직접 호출 | 발행은 파이프라인이 한다. 모듈은 **블록만** 반환 |

---

## 5. 노트북 `NB` 규약

6장. 각 항목은 `("md", "마크다운")` 또는 `("code", "파이썬")` 튜플의 리스트.

- `setup` — import + `np.random.seed(0)` 등 재현 고정.
  **절대 금지**: 여기(또는 `explore`)에 `todo` 의 정답을 미리 넣지 말 것.
  `sigmoid_ref` 처럼 이름만 바꾼 정답도 금지다 — TODO 위쪽에 답이 있으면 연습이 무의미해진다.
  `explore` 에서 개념을 관찰할 때는 **함수로 감싸지 말고 식을 그 자리에 직접** 쓰거나
  (`p = 1 / (1 + np.exp(-z))`) 계산된 숫자만 보여줄 것.
- `explore` — 아주 작은 예(원소 3~5개)로 개념 관찰. 손으로 검산 가능해야 함
- `todo` — **`# TODO:` 주석과 빈칸**이 반드시 있어야 함. 학습자가 채울 자리
- `check` — **`np.allclose` 또는 `assert` 필수**. 통과 시 `print("✅ ...")`.
  라이브러리 정답과 대조하는 게 원칙
- `apply` — 실제 강의 데이터. 드라이브 마운트 후
  `/content/drive/MyDrive/메타코드 실습프로젝트/<주차폴더>/...` 경로 사용
- `wreck` — 조건을 일부러 어겨 이론대로 망가지는지 확인

`check` 에 채점이 없으면 **빌드가 실패**한다(`build_unit_notebook.py` 가 막음).

### `SOLUTION` (필수)
`todo` 는 `NotImplementedError` 라서 그대로는 실행이 안 된다. 그래서 **정답 구현 문자열**을
따로 준다. 검증기가 `setup → explore → SOLUTION → check` 를 실제로 돌려 채점이
통과하는지 확인한다.

```python
SOLUTION = """
def sigmoid(z):
    return 1 / (1 + np.exp(-z))
...
"""
```

`todo` 의 빈칸을 정확히 채운 것이어야 하고, 이것만으로 `check` 가 통과해야 한다.

### 그림 속 문자 주의
matplotlib 그림(`figs()`)에서 **`ŷ` `∑` `∂` `≈` 같은 문자를 그대로 쓰지 마라.**
Malgun Gothic 에 그 글자가 없어 **네모(두부)로 찍힌다.** family 목록에 DejaVu 를 넣어도
폴백이 동작하지 않는 걸 실측 확인했다. 반드시 **mathtext** 로:

    ax.set_ylabel(r"$\hat{y}$")     # O
    ax.set_ylabel("ŷ")              # X — 네모로 나옴

preflight 가 글리프 경고를 잡아 실패시킨다. (`fix_glyphs.py` 로 일괄 치환 가능)

### 라이브러리 버전 주의 (검증기가 경고도 에러로 잡는다)
- `LogisticRegression(penalty=None)` 은 **deprecated**(sklearn 1.8, 1.10에서 제거).
  규제를 끄려면 **`C=np.inf`** 를 쓸 것.
  단 `C=np.inf` 는 `"Setting penalty=None will ignore the C..."` 라는 **무해한 안내**를 띄운다.
  초보자가 놀라지 않게 셀 설명에 "이 안내는 정상이에요" 한 줄을 반드시 넣을 것.
- `FutureWarning`/`DeprecationWarning` 이 하나라도 나면 검증 실패다. 최신 API로 쓸 것.

---

## 6. 검증 (작성 후 스스로 돌려볼 것)

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python build_unit_notebook.py units/W04U05.py
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python preflight_unit.py units/W04U05.py
```

둘 다 통과해야 발행 대상이 된다. 노션 발행은 파이프라인(사람)이 한다.
