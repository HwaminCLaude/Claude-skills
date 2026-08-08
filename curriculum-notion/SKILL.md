---
name: curriculum-notion
description: 강의자료(노트북·PDF) 묶음을 "기초지식 0인 사람이 from scratch로 따라가며 완전히 이해하는" 학습 커리큘럼으로 재구성해 Notion 중첩 DB로 발행하고, 유닛마다 자동 채점되는 Colab 실습 노트북까지 만드는 스킬. 주차 페이지 안에 유닛 하위 DB를 두고, 유닛마다 개념→수식(숫자 대입)→직접 구현→라이브러리 대조 검산→강의자료 적용→망가뜨리기 순서로 채운다. 정답 누출 검사와 "검산 셀 실제 실행" 검증이 포함돼 있어 돌아가지 않는 실습이 발행되지 않는다. 사용자가 "커리큘럼 만들어줘", "기초부터 순서대로 배우게", "from scratch로 이해하고 싶어", "강의 다 들었는데 이해가 안 돼", "코랩에서 따라하면서 배우는 자료", "학습 로드맵 노션에", "진도 관리되는 학습 DB" 라고 할 때 사용한다. 코드 한 줄 풀이만 원하면 code-guidebook-notion, PDF 스캔 2단 레이아웃은 pdf-to-notion.
---

# 강의자료 → from-scratch 학습 커리큘럼 (Notion + Colab)

강의를 다 들었는데도 "돌아가긴 하는데 왜 그런지 모르는" 상태를 없애는 것이 목표다.
강사 자료는 **기초를 안다고 가정**하고 만들어져 있으므로, 그 공백을 메운 **학습 경로**를 새로 만든다.

핵심 장치는 **자동 채점**이다. 학습자가 빈칸을 채우면 라이브러리 정답과 대조해 `✅`/실패가
바로 나온다. "이해한 것 같다"와 "실제로 맞다"를 가르는 유일한 방법이라 반드시 넣는다.

## 결과물 구조

```
<커리큘럼 DB>                      (워크스페이스 직속)
├ 00 · 학습 지도                   전체 인덱스 · 진도 · 선수지식 그래프
├ 01주차 · <주제>
│    (본문) 목표 · 할 수 있게 되는 것 · 공부법 · 원본 자료 위치
│    └ 📂 유닛 (인라인 하위 DB)     이름·순서·유형·난이도·상태·콜랩·예상시간
│         ├ 01 · <개념>            ← 유닛 페이지(아래 9층)
│         └ …
└ …
```

**유닛 페이지 9층 (순서·제목 고정)**
1. 🎯 목표 (주황 callout) — 한 줄 + 완료 기준
2. `🧭 먼저 알고 오세요` — 선수지식. 부족하면 앞 유닛으로 링크
3. `📖 개념` — 왜 필요한가 → 무엇인가 (matplotlib 그림 필수)
4. `🧮 수식` — Notion equation + **예시 숫자 대입**(코드 실행값과 일치해야 함)
5. `💻 직접 만들기` — 라이브러리 없이 구현
6. `🔬 맞는지 확인` — 라이브러리 대조 + **관례 차이** 경고
7. `🧪 강의 자료에 적용` — 실제 강의 노트북·데이터 경로
8. `✅ 스스로 확인` — 체크리스트 + 망가뜨리기 실험
9. `🔗 더 보기`

**콜랩 노트북 (유닛당 1개, 7장)**
①준비물 ②눈으로 보기 ③**직접 만들기(TODO 빈칸)** ④**맞는지 확인(자동 채점)**
⑤강의 자료 적용 ⑥망가뜨리기 ⑦정답 보기(`<details>` 접힘, 맨 끝)

## 사전 준비

- **Notion 통합 토큰** — `NOTION_TOKEN` 환경변수, 또는 `.env`(`KEY=값` 또는 값만 한 줄)
- **대상 DB** — 워크스페이스에 빈 DB 하나. 통합에 공유돼 있어야 함
- **rclone** — `RCLONE_BIN`(기본 `rclone`), remote `gdrive`. 노트북 업로드용
- **Codex CLI** (선택) — 유닛 본문 대량 저작용. 없으면 이 스킬을 읽는 에이전트가 직접 쓴다
- 파이썬 실행은 **항상** `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`

## 워크플로우

### Step 1. 커리큘럼 설계 — `scripts/curriculum.py`
강의자료를 실제로 열어(노트북 마크다운 소제목·import 라이브러리) **무엇을 다루는지** 파악한 뒤
주차별 유닛을 정의한다. 파일 이름만 보고 추측하지 말 것.

정할 것: 주차 폴더명 / 주차 한 줄 소개 / 유닛(제목·유형·난이도·분·목표 한 문장).
- 유형 `개념·실습·보충·프로젝트`, 난이도 `입문·기본·심화`
- **보충 유닛**은 필요한 유닛 **바로 앞**에 넣는다(0주차에 몰지 않는다 — 몰아두면 잊는다)
- 분량 기준: 유닛당 40~60분, 주차당 4~6유닛

```
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/curriculum.py --dump
```
검증(유형·난이도·선수지식·주차별 개수)이 통과해야 `curriculum.json` 이 저장된다.

### Step 2. 뼈대 발행 — `scripts/publish_skeleton.py`
```
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/publish_skeleton.py --dry   # 미리보기
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/publish_skeleton.py
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/verify_skeleton.py
```
주차 페이지 + 인라인 유닛 DB + 유닛 행(제목·속성만)을 만든다. 멱등이라 중단돼도 이어서 재개된다.
`verify_skeleton.py` 는 **누락뿐 아니라 초과(중복)** 도 잡는다.

### Step 3. 표본 1유닛 → 사용자 확인 ★건너뛰지 말 것
대표 유닛 하나를 끝까지(9층 + 노트북) 완성해 보여주고 승인받는다.
어투·분량·섹션 구성을 고칠 거라면 **여기가 가장 싸다**. 80유닛을 만든 뒤엔 비싸다.

### Step 4. 유닛 저작 — `references/AUTHORING_CONTRACT.md`
유닛 1개 = 파이썬 모듈 1개(`units/W04U05.py`). 규약 전문은 AUTHORING_CONTRACT 참조.
모듈이 정의할 것: `UNIT` `TITLE` `GOAL` `PREREQ` `figs(plt)` `build(B, IM)` `NB` `SOLUTION`.

Codex 로 대량 저작할 때:
```
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/make_week_prompt.py --all
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/run_weeks.py --rest -j 4
```
`make_week_prompt.py` 가 주차별 프롬프트에 **실제 강의자료 파일 목록**을 넣어 주므로
'적용' 섹션이 존재하지 않는 파일을 지어내지 않는다. 이미 만든 유닛은 자동으로 건너뛴다.

### Step 5. 검증 + 발행 — `scripts/publish_all.py`
```
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/publish_all.py --check-only
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/publish_all.py
```
유닛마다 preflight → 노트북 빌드 → **검산 셀 실제 실행** → 노션 발행 → 노트북 업로드 →
`콜랩` 속성 링크. 셋 중 하나라도 실패하면 **발행하지 않는다**. 멱등(`publish_state.json`).

## 검증이 실제로 잡는 것 (전부 실측으로 추가된 것)

| 검사 | 왜 넣었나 |
|---|---|
| **정답 누출** | `setup`/`explore` 에 정답을 미리 두면 TODO가 무의미. 이름만 바꾼 것(`sigmoid_ref`)도 **본문 줄 비교**로 잡는다 |
| **검산 실제 실행** | preflight 는 `allclose` 라는 *글자*만 본다. 진짜 통과하는지는 돌려봐야 안다 |
| **경고를 에러로** | `LogisticRegression(penalty=None)` 처럼 곧 제거될 API를 걸러낸다 (`C=np.inf` 로) |
| **블록 수 재대조** | 발행 후 실제 블록 수를 세어 **부족·초과 양쪽** 확인 |
| **수식↔코드 일치** | 수식 섹션의 손계산 숫자가 코드 출력과 같아야 한다 |

## 함정 (실측)

- code 블록 `language="text"` → 400. **`"plain text"`**
- 인라인 파서가 `_..._` 를 이탤릭으로 오인 → **밑줄 든 식별자는 백틱 필수**
- 청크(85블록)에 무효 블록 1개면 **청크 통째 실패** → 깨진 페이지는 비우고 재발행
- 이미지: Google **Workspace** 계정은 Drive `lh3` 임베드가 302로 막힘
  → **Notion File Upload API** 필수. `file_upload` id 는 **1회용**(첨부 시 소모)
- Notion 레이트리밋 3req/s → append 사이 ~0.34s, 429 백오프
- 발행은 **순차 1회**. 병렬·재시도하면 같은 블록이 두 번 올라간다
- Windows 에서 `codex` 는 npm 셔임이라 `shutil.which("codex")` 로 실제 경로를 찾아야 한다
- 무거운 학습 코드 금지 — 검증이 매번 돌아야 하므로 **작은 데이터·적은 스텝**

## 완료 기준

1. `verify_skeleton.py` 통과 (유닛 수 = 커리큘럼 정의, 중복 0)
2. 전 유닛 `publish_all.py --check-only` 통과
3. 발행 후 블록 수 일치, 이미지 `__IMG__` 잔재 0
4. 노트북 검산 셀이 **실제로** `✅` 출력
