# 여러 레슨 병렬 제작 (Workflow + 자원 레인)

전제: 시작 인터뷰를 마쳐 `docs/DECISIONS.md`가 채워져 있음(이어 만들기면 바뀐 것만 다시 물음), 파일럿 레슨이 `check_lesson.py` 전부 PASS + README-only 검증 통과, `docs/LESSON_GUIDE.md`의 `<…>`가 실측값으로 채워짐, 쓸 Pod가 모두 Running이고 `setup.sh`가 끝나 있음(멈춘 Pod는 `workflow.md` 0-5), 아래 진행 순서 4의 승인. 시작 틀은 `assets/lesson-workflow-template.js`(실제로 54레슨을 돌린 스크립트에서 뽑음). 안전 규칙(시작 인터뷰와 Workflow 동의, 비밀값, 결제, Pod 수명, 동시 작업, 범위)은 SKILL.md '반드시 지킬 것'.

## 진행 순서
1. **도구 판** — 기존 저장소면 `python "<SK>/scripts/init_course.py" "<저장소>" --check-tools`. 다르면 사용자에게 알리고, 그 `tools/`를 쓰는 워크플로가 없을 때 `--update-tools`(tools/만). 나머지 재개 점검은 `workflow.md` '이어 만들기'.
2. **범위** — 남은 레슨(`curriculum.md`의 ⬜·🟡)과 앞 레슨이 남긴 산출물을 확인하고 요청 범위와 맞춘다. 범위 밖 레슨은 손대지 않는다.
3. **레인 표 → 레슨 명세**(1·2절).
4. **승인** — 레인·레슨 수·예상 Pod 사용 시간과 비용을 보여 주고 승인을 받는다(요청에 범위와 비용 상한이 모두 있으면 생략). 추정: 가장 긴 레인의 레슨 수 × 파일럿 하나의 제작 시간 = 예상 시간, × 켜 둘 Pod 수 × 시간당 요금(콘솔 Cost 열). '추정'이라고 밝힌다. `docs/DECISIONS.md` `budget` 한도와 비교해 80%에 가까우면 멈추고 묻는다(`after-pilot`인데 아직 한도를 정하지 않았으면 여기서 묻는다).
5. **콘솔 사전 촬영** — 명세에서 RunPod 콘솔 STEP이 있는 레슨을 뽑아, 메인 세션이 그 레슨의 `_raw/`에 직접 찍고(`workflow.md` 0-1 '스크린샷 저장') capture-log에 적은 뒤, 명세 `notes`에 파일 이름과 마스킹 상자를 적는다. 다른 레슨의 원본을 같이 쓰면 그 레슨 `_raw/`에 복사하고 그림 아래에 '공유 촬영(<날짜>, <원래 레슨>)'을 밝힌다(`lesson-guide.md` 3절). 필요한 화면이 없는 STEP은 레슨 에이전트가 '촬영하지 않음(이유)'으로 쓴다.
6. **Workflow 실행** — 먼저 `docs/DECISIONS.md`의 `parallel_workflow: true`(또는 같은 뜻의 요청)인지 본다. 아니면 Workflow를 쓰지 않고, 레인마다 서브에이전트 하나를 한 번에 하나씩 차례로 쓴다(5절 마지막 항목의 프롬프트 그대로). 맞으면 `workflow-authoring` 스킬을 읽고 템플릿을 채워 실행한다. 끝난 뒤 조치(REPORT·Stop)까지 맡긴 요청이면 7절대로 띄운다.
7. **(`unattended_checks: cron-30min`이면) 점검 크론** — 7절.
8. **끝내기** — 워크플로가 끝나면(템플릿이 이번 레슨만 verify → fix → 다시 verify를 `MAX_FIX_ROUNDS`까지 한다):
   1. 메인 세션이 이번 범위의 레슨 전부에 `python tools/check_lesson.py`를 다시 돌린다.
   2. README-only 검증: 챕터마다 1개 이상, 콘솔·서버·학습 STEP이 있는 레슨 우선(`verification.md` 2절). Pod가 필요하므로 Stop보다 먼저.
   2-1. 내용 검토 — `content_review`대로 한다(`sample+consistency`: 표본 + 레슨 간 정합성 / `full`: 전 레슨 / `gate-only`: 건너뜀). 방법은 아래 '끝난 뒤 내용 검토'. 고칠 때 Pod가 필요하면 Stop보다 먼저 한다.
   3. 지적을 고치고 `check_lesson.py`를 다시(같은 레슨 최대 2번). 그래도 남은 FAIL은 미해결로 둔다.
   4. 결과의 `facts_observed`를 `environment/versions.md`에 옮긴다(메인 세션만).
   5. REPORT.md(8절) → `python tools/check_lesson.py --repo` PASS.
   6. Pod 끄기(9절).

## 1. 레인 설계
**레인 = 같은 자원을 순서대로 쓰는 레슨 줄.** 레인 안은 순서대로(앞 레슨의 결과 요약이 다음 레슨 프롬프트로 넘어감), 레인끼리는 동시에 돈다. 자원 축으로 겹치지 않게 나눈다.

| 축 | 규칙 |
|---|---|
| Pod·폴더 | 레슨마다 Pod 하나(`pod: 'A'`). **같은 챕터의 레슨은 한 레인에만** 둔다(같은 `chNN/`을 두 레슨이 동시에 쓰지 않게). 레슨은 자기 레슨이 만든 파일(`lMM_*`, `logs/lMM_*`)만 만들고 지운다. dev·scratch·재현 폴더는 컨테이너 디스크(`/root/dev-<레슨>/`, `/root/scratch-<레슨>/`)에 두고 끝나면 지운다 |
| GPU 메모리 | 한 레인 안에서 모델 로딩은 한 번에 하나(끝나면 커널 종료). 같은 GPU의 vLLM은 레인마다 `--gpu-memory-utilization` 상한(합이 1을 넘지 않게, 노트북 커널 몫도 남김 — 기본값 0.92는 GPU를 거의 다 잡는다). 학습은 `flock /root/gpu-train.lock …`. 벤치마크처럼 GPU를 독점해야 하는 레슨은 같은 GPU의 다른 레인이 끝난 뒤(의존 약속) |
| 포트 | 서버 포트는 **같은 Pod 안에서** 레인마다 다르게(예: Pod B의 vLLM 8000 / 8010 / 8020, FastAPI 8002 / 8011 / 8021 — 다른 Pod끼리는 같은 번호여도 된다. Pod 이미지의 nginx가 쓰는 3001·7270·7861·8001·8081·9091은 피한다). `jlab.py` 로컬 포트는 **레슨마다** 고유(예: 188xx — 이 PC 한 대에서 모두 열리므로), jlab workspace 이름 = 레슨 ID 소문자 |
| 세션 이름 | tmux 세션·로그 이름에 레슨 ID를 넣는다. 정리할 때 자기 세션·자기 포트만 끈다(`pkill -f "vllm serve .*--port <내 포트>"`). 커널은 `jlab.shutdown_kernels()`, Terminal은 `jlab.shutdown_terminals()`(둘 다 자기가 연 것만) |
| Pod 상태 | Pod 상태를 바꾸는 레슨(Stop/Start, Restart Pod, `File → Shut Down` 시연)은 FINAL 레인에서 그 레슨만 쓰는 전용 Pod로 하거나 '실행하지 않음(이유)'으로 쓴다(다른 레인이 그 Pod를 쓰는 동안에는 하지 않는다) |

LLM 과정 레인을 이 규칙대로 고친 예(실제 실행에서는 C02가 레인 3·5로, C04가 레인 1·6으로 나뉘어 같은 챕터 폴더를 동시에 썼다 — 이 스킬에서는 한 레인으로 모은다):

| 레인 | Pod | 챕터 | GPU 규칙 | 포트 |
|---|---|---|---|---|
| 1 | A | Ch03 → Ch04 | 모델 로딩 최대 1개(4B 이하), 끝나면 프로세스 종료 | — |
| 2 | A | Ch05 → Ch06 → Ch10 | 학습은 `flock /root/gpu-train.lock` 안에서(레인 안은 순서대로라 학습 중에 이 레인의 vLLM은 뜨지 않는다). Ch10 벤치마크는 레인 1이 끝난 뒤(의존 약속), vLLM `--gpu-memory-utilization 0.5`(실제 C10-L01 값) | vLLM 8000 |
| 3 | B | Ch07 → Ch11 | vLLM `--gpu-memory-utilization 0.45` 이하. Ch11은 Ch09의 도구 파일이 생긴 뒤(의존 약속) | vLLM 8000, FastAPI 8002 |
| 4 | B | Ch08 → Ch09 | vLLM `--gpu-memory-utilization 0.35` 이하 | vLLM 8010, FastAPI 8011 |
| 5 | B | Ch01 → Ch02(L01·L03·L04) | GPU 거의 안 씀 | — |
| 6 | B | Ch12 (FINAL — 다른 레인이 끝난 뒤) | 다른 레인이 끝난 뒤 | vLLM 8020, FastAPI 8021 |

- Workflow의 동시 에이전트 수는 `min(16, CPU 수 - 2)`가 상한이다. 레인 수가 더 많으면 남는 레인은 자리가 날 때까지 기다린다.
- 브라우저(Chrome 확장)는 **메인 세션만** 쓴다. 레슨 에이전트는 `jlab.py`(헤드리스 JupyterLab), SSH, `webshot.py`(공개 웹)만 쓴다. 콘솔 화면은 진행 순서 5에서 미리 찍어 준다.

## 2. 레슨 명세 쓰기
`L(id, slug, title, pod, port, notes)` — `notes`가 레슨 에이전트의 실제 작업 지시다. 구체적으로:
- 무엇을 실행·촬영하는지(노트북 셀 주제, Terminal 명령, 서버 옵션 그대로), 어떤 venv·커널, 어떤 포트·GPU 상한.
- 다음 레슨에 남길 산출물의 **Pod 경로**(예: `…/ch06/outputs/lora-r16`) — 결과 스키마의 `outputs_for_next`로 돌아와 다음 레슨 프롬프트에 붙는다.
- 의존 산출물이 없을 때의 대안: '시작할 때 산출물 경로를 확인하고, 없으면(만드는 레슨이 실패했거나 빠짐) 작은 대체 산출물을 직접 만들고 그 사실을 README에 밝힌다'. 기다리는 것은 `before` 훅이 이미 했으므로 프롬프트에서 따로 기다리게 하지 않는다(워크플로 스크립트는 시간 함수를 쓸 수 없어 '60분까지 기다리기' 같은 제한도 걸 수 없다).
- 실행할 수 없는 것을 미리 알면 그렇게 적는다(예: GPU 1장이라 Tensor Parallel은 실행하지 않음 — 개념 레슨으로).
- 비밀값이 나올 수 있는 화면 주의(예: 키 지문, 환경변수는 이름만 세기 `compgen -e | grep -ciE "key|token|pass"` — LLM 과정 C08-L02 명세는 `printenv | cut -d= -f1 | grep -ciE …`였지만 파이프가 빠지면 값이 나오므로 이 스킬은 `compgen -e`를 쓴다. 파일럿에서 실행해 보지 않았으니 처음 쓸 때 숫자 하나만 나오는지 확인).
- 진행 순서 5에서 찍어 둔 콘솔 원본(파일 이름·마스킹 상자).

## 3. 의존 약속(deferred promise)
```js
function deferred() { let r; const p = new Promise((res) => { r = res }); return { p, r } }
const adapterReady = deferred(), lane1Done = deferred()
lane(LANE1).finally(() => lane1Done.r(true))
lane(LANE2, { after: { 'C06-L03': () => adapterReady.r(true) }, before: { 'C10-L01': () => lane1Done.p } })
  .finally(() => adapterReady.r(true))
lane(LANE3, { before: { 'C07-L05': () => adapterReady.p } })
```
- 만드는 쪽: 산출물을 만든 레슨의 `after` 훅에서 푼다(그 레슨이 실패해 `null`이어도 훅은 불린다). **그 레인이 끝날 때 한 번 더** 푼다(`.finally`) — 명세에서 그 레슨을 빼거나 레인이 예외로 끝나도 기다리는 레인이 영원히 멈추지 않는다(두 번 풀어도 무해).
- 기다리는 쪽: `before` 훅에서 기다리고, 프롬프트에는 산출물이 없을 때의 대안을 둔다(2절).
- 순환 의존을 만들지 않는다. '모든 레인이 끝난 뒤' 레슨은 `await Promise.allSettled(lanes)` 다음의 `FINAL` 레인으로.

## 4. 세마포어(무거운 작업 동시 수 제한)
```js
function makeSemaphore(n) { /* 템플릿 참고 */ }
const podSem = makeSemaphore(4)
await parallel(items.map((it) => () => podSem(() => agent(…))))
```
수정 단계처럼 많은 에이전트가 한꺼번에 Pod를 쓰려 할 때, 그리고 사용자가 요청한 영상 렌더(실제 스크립트는 4개로 제한)에 쓴다. 수정 에이전트에게도 원래 레슨의 Pod·jlab 포트를 넘겨 포트 충돌을 막는다(템플릿의 `specOf` — 절대·상대 경로 모두 `chapter-NN/lesson-MM-slug`로 맞춘다).

## 5. 스크립트 규칙(Workflow)
스크립트를 쓰거나 고치기 전에 `workflow-authoring` 스킬을 읽는다(아래는 이 제작에서 중요했던 것만).
- 첫 문장은 `export const meta = {…}` — **순수 리터럴**(변수·함수 호출·전개·템플릿 문자열 금지). `phases` 제목은 `phase()` 호출과 같은 글자.
- 일반 JavaScript(타입 표기 금지). 현재 시각·난수 함수(`Date.now()`, `Math.random()`, 인자 없는 `new Date()`)는 재개를 깨뜨려 예외가 난다 → 시각이 필요하면 `args`로 넘기거나 워크플로가 끝난 뒤 메인 세션이 적는다.
- `agent()`는 에이전트가 죽거나 사용자가 건너뛰면 `null`을 돌려준다 → `summarize(null)`처럼 다룬다. `parallel()`은 거부되지 않고 실패한 칸이 `null`이 된다.
- 구조화 결과는 `schema`로 받는다(레슨: status, lesson_dir, check_lesson 요약 줄, outputs_for_next, not_executed, facts_observed, issues).
- 프롬프트마다 `cd "<REPO>" && …`(셸 호출마다 폴더가 처음으로 돌아갈 수 있다)와 비밀값·격리 규칙 문장을 붙인다(템플릿의 `CWD`·`SECRET`·`ISOLATION`). verify·fix는 이번 실행의 레슨만.
- 마지막에 결과 객체를 `return` 한다 — 메인 세션이 REPORT.md를 쓸 재료다.
- 실행: `Workflow({ script })`(처음) → 결과에 runId와 저장된 스크립트 경로가 나온다. 고친 뒤에는 그 파일을 고치고 `Workflow({ scriptPath, resumeFromRunId })`로 다시 띄운다.
- **Workflow 도구가 없거나 사용자가 동의하지 않았으면**(동의가 없으면 레인도 한 번에 하나씩): 레인마다 서브에이전트 하나에게 그 레인의 레슨을 순서대로 맡기고(같은 레슨 프롬프트 문장), 의존 약속은 메인 세션이 레인을 띄우는 순서로 대신한다. 끝나면 메인 세션이 verify·fix를 직접 한다.

## 6. 실행 중에 요구가 바뀌면 (멈춤 → 고침 → 재개)
실제로 있었던 일: 계획에는 레슨마다 영상이 있었는데 실행 중에 'README만, 영상은 요청한 레슨만', 'STEP마다 🎙️ 해설 대본 필수'로 바뀌었다.
1. **멈춘다** — 실행 중인 워크플로를 중지한다(/workflows에서 중지, 또는 백그라운드 작업이면 TaskStop). 더 진행할수록 다시 할 일이 늘어난다.
2. **Pod를 확인한다**(각 Pod): `tmux ls`, `pgrep -af "vllm serve" | cut -c1-120`, `nvidia-smi --query-compute-apps=pid,used_memory --format=csv`. 멈춘 레슨의 서버·tmux는 레슨 세션 이름·포트로 골라 끈다. 레슨 폴더와 Pod의 중간 산출물은 **지우지 않는다**(이어 하기에 쓴다).
3. **고치는 순서**: 결정 기록(`docs/DECISIONS.md`의 값과 '바뀐 기록' 한 줄) → 계약서(`docs/LESSON_GUIDE.md`) → 검사기(검사할 수 있는 요구면 `check_lesson.py`에 항목 추가, 예: 해설 대본 3-1) → 레슨 프롬프트·명세 → 빠진 범위의 코드는 지운다(쓰지 않는 영상 코드를 남겨 두지 않는다). 검사기를 바꿔도 범위 밖의 끝난 레슨은 다시 검사·수정하지 않는다 — 새 항목에서 FAIL이 날 수 있다고 사용자에게 알리고 고칠지 묻는다.
4. **다시 띄운다** — `Workflow({ scriptPath, resumeFromRunId })`: 바뀌지 않은 앞부분의 `agent()` 호출은 저장된 결과를 즉시 돌려주고, 처음 바뀐 호출부터 다시 돈다(프롬프트를 고쳤으면 사실상 모든 레슨이 다시 돈다). 레슨 프롬프트의 '앞선 실행의 중간 작업이 있으면 살펴보고 이어서 하라'는 문장 때문에 끝난 부분은 다시 만들지 않는다. 이미 끝난 레슨이 많으면 '새 요구만 덧붙이고 check_lesson 다시' 하는 작은 보완 워크플로를 따로 돌리는 편이 빠르다.
5. 사용자에게 무엇이 바뀌고 무엇을 다시 하는지 한 번 알린다.
- 결과가 비었거나 이상하면 진단 전에 실행 기록 폴더의 `journal.jsonl`(에이전트마다 실제 반환값)을 먼저 읽는다.

### 끝난 뒤 내용 검토가 꼭 필요하다 (2026-10-28 실측)
- check_lesson이 전부 PASS여도 내용 오류는 남는다. 레슨 4개를 초보자 시각으로 표본 검토하자 레슨당 약 5건(글과 그림이 반대, 로그에 없는 근거 표시, 다음 강의 예고 오류)이 나왔고, 56개 레슨의 13절 예고와 README·curriculum을 맞춰 보는 정합성 점검에서 40건이 더 나왔다.
- 순서: 표본 검토(레슨 몇 개, 읽기 전용) + 레슨 간 정합성(모든 레슨의 '다음 강의' 예고 ↔ 실제 다음 레슨, 색인 문서, 고정값) → 수정 에이전트는 레슨마다 하나(같은 파일을 두 에이전트가 고치지 않게 레슨 ID로 묶음) → 수정 에이전트가 '다른 레슨에도 같은 문구가 있다'고 남긴 것을 모아 한 번 더 정리 → 전체 재검사.
- 수정 프롬프트에는 '로그에 없는 숫자를 새로 넣지 말 것', '파일의 원래 줄바꿈(CRLF/LF) 유지'를 넣는다. 리뷰가 제안한 계산값도 로그에 없으면 넣지 않는다.
- 서브에이전트는 보고서 파일(REPORT.md 등)을 쓰지 못한다(하네스가 막음 — '결과는 글로 돌려줘라'). 보고서 초안은 결과 글로 받아 메인 세션이 저장한다.
- 끝난 서브에이전트에 SubagentStop 훅이 새 턴을 계속 넣어 워크플로가 그 에이전트를 기다리며 멈출 수 있다. 결과가 저장소에 반영됐는지 확인한 뒤 SendMessage로 '한 줄로 답하고 끝내라'고 보낸다.

### 재개 캐시는 호출 순서에 묶인다 (2026-10-28 실측)
- `journal.jsonl`의 `v2:` 키는 프롬프트·옵션뿐 아니라 **전체 `agent()` 호출 순서**에 따라 정해진다. 레인을 새로 끼워 넣어 6번째 호출이 바뀌자 그 뒤 키가 모두 달라져, 이미 끝난 레슨 5개가 처음부터 다시 돌기 시작했다(곧바로 멈춤).
- 레인 구조를 바꿔 재개할 때는 원래 실행의 `started` 순서를 journal에서 읽어 목록(REPLAY)으로 만든다. 레슨은 목록의 앞 항목이 호출된 뒤에만 `agent()`를 부르고, 새 레슨과 끝나지 않은 레슨은 목록의 마지막 호출 뒤로 미룬다(deferred 게이트, `assets/lesson-workflow-template.js`의 `REPLAY`).
- 재개 직후 journal에 **끝난 레슨 이름의 새 `started` 줄**이 생기는지 확인한다. 생기면 바로 TaskStop하고 순서를 다시 맞춘다.
- 띄우기 전에 모의 실행으로 호출 순서와 교착을 점검한다. `export const meta`를 `const meta`로 바꾸고, 본문을 `new Function('agent', 'parallel', 'log', 'phase', 'return (async () => {' + 본문 + '})()')`로 감싸 가짜 `agent()`로 node에서 돌린다. `node --check`는 최상위 `return` 때문에 실패하므로 쓰지 않는다.
- 에이전트 하나가 StructuredOutput 없이 끝나면 `agent()`가 예외를 던진다. 레슨 호출을 try/catch로 감싸지 않으면 `Promise.all`로 묶인 레인 전체와 진행 중인 다른 레슨까지 함께 멈춘다. 템플릿은 3번까지 다시 시도하는데, 첫 시도의 프롬프트·옵션을 그대로 두어야 재개 캐시가 맞는다.

## 7. 사용자가 자리를 비울 때(야간) 점검
- 끝난 뒤 조치(REPORT·Stop)까지 맡긴 요청이면 Workflow를 백그라운드로 띄워(도구가 지원하면) 메인 세션이 응답을 끝내게 하고 크론을 건다. 크론은 메인 세션이 응답 중이 아닐 때만 돈다 — 워크플로를 기다리며 응답 중이면 돌지 않는다. 백그라운드로 띄울 수 없으면 크론 대신 워크플로가 끝난 뒤 메인 세션이 진행 순서 8을 직접 한다.
- `CronCreate`로 주기 점검을 건다. 정각·30분을 피한 분(예: `"17 * * * *"` 매시 17분, `"7,37 * * * *"`)을 고른다.
- 알아 둘 것: 작업은 **이 세션 안에서만** 살아 있다(세션을 닫으면 사라짐). 반복 작업은 주기의 최대 50%(최대 30분)까지 늦게 돌 수 있다. 반복 작업은 7일 뒤 자동으로 지워진다. 실제 다음 실행 시각은 결과·`CronList`에 나온 값을 사용자에게 알려 준다.
- 점검 프롬프트 예문(`<…>`를 채운다):
  ```text
  RunPod 병렬 제작 점검(<저장소>). 읽기와 아래 조치만 한다. 셸은 cd "<저장소 Git Bash 경로>" && 로 시작한다.
  1. 진행: 워크플로 실행 기록 폴더(<runId의 기록 폴더>)의 journal.jsonl에서 끝난·실패한 레슨을 세고, chapters/ 아래 이번 범위 레슨 폴더(<목록>)의 README.md·playbook.yaml 유무와 가장 최근 수정 시각을 본다.
  2. Pod마다: tools/pod.sh A 'df -h /workspace; nvidia-smi --query-compute-apps=pid,used_memory --format=csv; tmux ls 2>&1 | head'
  3. 90분 넘게 새 파일이 없는 레인, /workspace 남은 용량 10% 미만, 어느 레슨 것인지 모를 GPU 프로세스는 verification/night-check.md에 적고(알림 도구가 있으면 알림도) 끄거나 지우지 않는다.
  4. 모든 레인·verify·fix가 끝났으면 parallel-production.md 진행 순서 8(끝내기)을 하고 CronDelete로 이 점검을 지운다.
  Deploy·Start·Terminate·결제는 하지 않는다. Stop은 진행 순서 8의 마지막 단계에서 SKILL.md 'Pod 수명' 규칙대로만 한다.
  ```

## 8. REPORT.md (저장소 루트)
```markdown
# 제작 보고 — <날짜>
## 요약            레슨 수, done/partial/failed, check_lesson 전부 PASS 수
## 레슨별 상태      | 레슨 | 상태 | check_lesson | 실행하지 않음 | 남은 문제 | (워크플로 결과 + 마지막 verify, unresolved)
## README-only 검증 대상 레슨, underivable·blocker 수, 고친 것
## 남은 문제와 사용자 결정  (미해결 FAIL, 용량·비용·라이선스·공개 범위·토큰 교체, 범위 밖 레슨에 생긴 새 FAIL)
## Pod·비용         Pod별 사용 시간(Start·Stop 시각, 추정이면 '추정'), 시간당 요금(콘솔 Cost 열), 합계 추정
## Pod 상태         Stop한 Pod와 시각, 남은 Network Volume(계속 과금)
## 산출물 경로      chapters/, verification/, environment/versions.md
```
다 쓴 뒤 `python tools/check_lesson.py --repo`(워크플로 오류 문구에 섞인 토큰·주소가 없는지).

## 9. 끝내기와 Pod 끄기
순서는 위 진행 순서 8. 남은 FAIL은 REPORT.md에 미해결로 적고 Stop한다(고치려고 Pod를 켜 두지 않는다 — 사용자가 이어서 하라고 하면 그때 다시 켠다). 끄는 규칙은 SKILL.md '반드시 지킬 것 → Pod 수명', 끄기 전 점검과 클릭 경로는 `workflow.md` Phase 7.
