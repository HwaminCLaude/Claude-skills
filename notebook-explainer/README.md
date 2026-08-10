# notebook-explainer

Jupyter 노트북(`.ipynb`)이나 스크립트(`.py`, `.js` …)를 **단일 HTML 인터랙티브 해설 페이지**로 바꿉니다.
이 저장소의 다른 스킬과 달리 **Notion이 아니라 로컬 HTML 파일 하나**를 만듭니다. 외부 서비스·API 키가 필요 없습니다.

문서가 아니라 *수업*입니다 — 코드 줄마다 클릭하면 설명이 뜨고,
**모양(shape)이 바뀌는 곳과 모델 구조에는 예외 없이 위젯이 붙습니다.**

## 무엇이 만들어지나

`<원본이름>_인터랙티브_해설.html` 하나가 **원본 파일 옆에** 생깁니다.

- **코드 줄 클릭 → 설명 패널** — 문법 재진술이 아니라 의도와 결과를 가르칩니다
  ("표준화를 안 하면 Assault가 거리 계산을 독차지한다")
- **텐서/데이터 shape 추적기** — 단계별 입력 → 출력 → 파라미터 수와 그 계산식
- **모델 구조 다이어그램** — 인라인 SVG, **화살표마다 shape 라벨**
- **양방향 결합** — 층을 클릭하면 그 코드 줄이, 코드 줄을 클릭하면 그 층이 하이라이트됩니다
- **변환 체인 스테퍼 · 데이터 흐름 파이프라인 · 슬라이더 위젯** 등
- **소스의 문제를 정직하게 드러냄** — 죽은 코드, 시드 없음, 복사한 그래프 제목,
  잘못된 스케일, 재현 안 되는 출력 등을 배너로 표시합니다

의미색으로 차원의 종류를 구분합니다(예: 공간 차원 = 주황 / 특징 차원 = 파랑).
그래서 "MLP는 시작하자마자 그림을 펴 버리고, CNN은 `Flatten`까지 2차원을 유지한다" 같은 사실이
**설명 없이 그림만으로** 전달됩니다.

## 핵심 원칙 — 숫자를 지어내지 않는다

HTML은 정적이라 PyTorch/TF를 실행할 수 없습니다. 그래서 모든 수치는 **작성 시점에 확정해 박아 넣습니다.**
다만 출처를 반드시 구분합니다.

| 배지 | 뜻 |
|---|---|
| `관측값` | 노트북 출력에 실제로 찍힌 값 (`print(x.shape)`, `model.summary()` 표) |
| `추정` | 코드에서 계산해 낸 값 |
| `기호` | 실행 시점에 정해지는 값 (`None`, 배치 크기) |

`model.summary()` 가 있으면 그 표가 정답입니다. 없으면 그 모델의 모양은 전부 `추정`이고,
페이지가 그 사실을 명시합니다. **근거 없는 숫자는 쓰지 않습니다.**

## 사용법

Claude Code에서 그냥 말하면 됩니다.

```
이 노트북 설명해줘                   ← 파일 하나
lesson5_1_clustering.ipynb 해설 만들어줘
이 폴더 노트북 전부 해설 만들어줘      ← 폴더 일괄
```

트리거: `설명해줘` · `셀 단위로 이해시켜줘` · `인터랙티브하게 설명` · `HTML로 해설 만들어줘` ·
`shape이 어떻게 바뀌는지 보여줘` · `모델 구조 그려줘` · `explain this notebook`

### 큰 노트북

코드셀·총셀·소스 크기가 임계값을 넘으면 **통째로 만들지 않고 목차를 보여준 뒤
"어느 장부터 어느 장까지?"를 먼저 묻습니다.** 완성하지 못할 페이지를 조용히 쓰기 시작하는 걸 막는 장치입니다.
임계값은 `scripts/extract_notebook.py` 상단 상수가 유일한 기준입니다.

폴더 일괄 모드에서는 묻지 않고 건너뛴 뒤, 마지막에 "개별 실행이 필요한 파일" 목록을 보고합니다.

## 폴더 구조

```
notebook-explainer/
├── SKILL.md                          ← 스킬 본문(절차·규칙). Claude가 읽고 따라 함
├── README.md                         ← (이 파일)
├── references/
│   ├── widget-recipes.md             ← 범용 위젯 5종 (클릭 코드줄·행렬·스텝·슬라이더·스윕)
│   └── architecture-recipes.md       ← ML 전용 5종 (shape 추적기·SVG 구조도·파이프라인·변환체인·호출그래프)
└── scripts/
    ├── extract_notebook.py           ← .ipynb → 해설용 JSON (base64·ANSI 제거)
    └── verify_page.js                ← 생성한 페이지를 실제 브라우저로 검증
```

## scripts/extract_notebook.py

`.ipynb` 를 **그대로 읽으면 안 되는 이유**가 있습니다. 실측한 노트북 모음에서
최대 **97%가 base64 이미지**였습니다 (`Step0_EDA.ipynb` = 3766KB 중 3649KB, 실제 소스는 54KB).

이 스크립트는 소스를 **무손실로 보존하면서 출력만 요약**해 40배 이상 줄입니다.

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/extract_notebook.py <노트북.ipynb>
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/extract_notebook.py <노트북.ipynb> --stats
```

- 이미지 → `[이미지 출력: PNG, 240KB]` 플레이스홀더 (디스크에 저장하지 않음)
- **ANSI 색상 코드 제거** — `model.summary()` 출력이 `ESC[38;5;33m` 같은 코드로 덮여 있어,
  벗기지 않으면 하드코딩할 관측값의 근거가 통째로 날아갑니다
- `error` / traceback은 **전문 보존** (교육 가치가 가장 높은 출력)
- `shape_hints` 로 shape 튜플과 `model.summary()` 표를 따로 모아 줌
- 대용량 게이트 판단용 통계(`stats.gate_exceeded`, `gate_reasons`) 제공

> `.py` / `.js` 등 일반 스크립트는 이 스크립트를 거치지 않고 `Read` 도구로 직접 읽습니다.

## scripts/verify_page.js

"클릭이 정말 동작하는가"는 정적 검사로 증명할 수 없습니다. 실제 브라우저로 확인합니다.

```bash
# 최초 1회만
npm i -g playwright && npx playwright install chromium-headless-shell

python -m http.server 8899 --bind 127.0.0.1        # file:// 은 브라우저 제약이 있어 http 로 연다
node scripts/verify_page.js http://127.0.0.1:8899/<파일>.html \
     --expect "269,322|(None, 288)|98.99"
```

`verdict: PASS` / `FAIL` 을 돌려주고, FAIL이면 `failedChecks` 로 원인을 알려줍니다.

검사 항목 — 콘솔 에러 0 · 가로 스크롤 없음 · 줄 클릭이 패널을 채움 ·
`--expect` 로 넘긴 관측값이 페이지에 실제로 존재 · **양방향 결합이 두 방향 다 동작**.

> 마지막 항목이 중요합니다. 추적기 표는 멀쩡한데 코드 줄에 `data-viz` 를 안 달면
> 페이지는 정상으로 보이면서 기능의 절반이 죽습니다. 눈으로는 못 잡아서 검증기가 FAIL로 잡습니다.

playwright는 로컬 → 전역 → `PLAYWRIGHT_PATH` 순으로 찾습니다.

## 다른 스킬과의 구분

| 하고 싶은 것 | 스킬 |
|---|---|
| 노트북을 **로컬 HTML 인터랙티브 해설**로 | **notebook-explainer** (이 스킬) |
| 노트북을 **Notion 가이드북 페이지**로 | [`code-guidebook-notion`](../code-guidebook-notion) |
| 코드베이스의 **호출 그래프를 Notion**으로 | [`code-callgraph-notion`](../code-callgraph-notion) |

## 요구 사항

- Python 3 (표준 라이브러리만 — 추출 스크립트에 외부 의존성 없음)
- Node.js + playwright (검증 단계에만 필요, 생략 가능하지만 권장)
- 생성된 HTML은 **완전 자립형**입니다. 외부 JS 라이브러리 없이 vanilla JS + 인라인 SVG로만 동작하고,
  외부 리소스는 Google Fonts 하나뿐입니다.
