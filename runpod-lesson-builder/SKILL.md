---
name: runpod-lesson-builder
description: RunPod GPU Pod에서 실제로 실행한 결과로 비개발자가 혼자 따라 하는 독립형 실습 README(레슨 폴더 단위)를 만드는 스킬. 시작할 때 사람이 정할 것(범위·산출물·Pod·비용·병렬·끝난 뒤 처리)을 먼저 조사하고 대화형으로 물어 기록한 뒤 진행한다. 헤드리스 JupyterLab 실화면 캡처와 민감정보 마스킹, STEP별 해설 대본, README만 보고 재현되는지 검증, 여러 Pod에 레인을 나눈 병렬 제작을 다룬다. 사용자가 "RunPod 실습 교재 만들어줘", "실제 Pod에서 실행해서 README로", "JupyterLab 화면 캡처해서 따라하기 문서", "RunPod 레슨 README만 보고 재현되는지 검증", "RunPod 실습 README에 STEP별 해설 대본 붙여줘", "RunPod 레슨 README 품질 검사", "RunPod 실습 챕터 여러 개 병렬로 제작", "이 과정 다음 레슨 이어서 만들어줘", "남은 챕터 README 전부 만들어줘", "제작 끝났으면 REPORT.md 쓰고 Pod Stop해줘"라고 할 때 사용한다. 노션 변환은 pdf-to-notion이나 code-guidebook-notion, 영상 제작은 ai-concept-visualization-video를 쓴다.
---

# runpod-lesson-builder

비개발자가 RunPod 화면을 보며 혼자 따라 하는 실습 교재를 **실제 Pod에서 실행한 결과로만** 만든다. 산출물은 레슨마다 폴더 하나(독립형 `README.md`, 단일 원본 `playbook.yaml`, 마스킹된 실화면, 로그·실행된 노트북·기대 출력, `troubleshooting.md`, `evidence-manifest.json`)와 과정 전체 저장소(도구, 제작 계약서, 커리큘럼, 검증 기록, `REPORT.md`)다.

핵심은 세 가지다.
1. **증거가 먼저다.** JupyterLab 화면은 SSH 터널로 헤드리스 캡처(주소창·토큰 없음), RunPod 콘솔은 로그인된 Chrome 확장으로만, 출력은 SSH 로그와 실행된 노트북에서 가져온다. 숫자를 지어내지 않는다.
2. **README 하나로 끝난다.** 14절 형식, STEP마다 그 행동 바로 아래 그림, '꼭 같아야 할 것 / 달라도 되는 것', STEP 끝마다 🎙️ 해설 대본(인터뷰에서 'README만'을 고르면 생략). 영상은 사용자가 고른 레슨만 따로 만든다.
3. **검사는 기계가, 재현은 남이.** `check_lesson.py`가 결정적으로 막고, README만 읽은 두 에이전트(행동 목록·초보자 비평)와 다른 환경에서의 그대로 실행이 빈틈을 찾는다.

사용자에게는 한국어로 답한다. 코드 식별자·명령·UI 라벨은 영어 그대로 쓴다.

## 스킬 폴더

`<SK>` = 이 SKILL.md가 있는 폴더(`C:\Users\<user>\.claude\skills\runpod-lesson-builder`) — 명령의 `<SK>`는 이 경로로 바꿔 쓴다. `scripts/`의 도구는 과정 저장소 `tools/`에 복사해서 쓴다(저장소 루트 = `tools/`의 부모, 접속값은 루트의 `.env.local`).

| 경로 | 내용 | 쓰는 때 |
|---|---|---|
| `scripts/init_course.py` | 새 과정 저장소 뼈대(README·curriculum 초안, `docs/LESSON_GUIDE.md`·`docs/DECISIONS.md`, `tools/`, `environment/`(setup.sh·사전 점검·버전 기록 틀), `.gitignore`, `.env.local.example`, 빈 폴더). 이미 있는 파일이 있으면 아무것도 쓰지 않는다. `--check-tools`/`--update-tools`는 기존 저장소의 `tools/`만 비교/교체. `--init-decisions`는 기존 저장소에 없는 `docs/DECISIONS.md`만 만든다. `--force`는 README·curriculum·LESSON_GUIDE에 더해 `environment/`(setup.sh·사전 점검·버전 기록)·`tools/`·`.gitignore`·`.env.local.example`까지 템플릿으로 덮어쓰므로(`docs/DECISIONS.md`(인터뷰 기록)만 보존) 작업 중인 저장소에 쓰지 않는다 | Phase 1, 이어 만들기 |
| `scripts/pod.sh`, `scripts/pod_get.sh` | `.env.local` 접속값으로 Pod에 SSH 명령 / 파일 가져오기(Git Bash). 호스트 키는 저장소 `.ssh/`. 값이 비면 무엇을 채울지 알려 주고 멈춤 | 항상 |
| `scripts/jlab.py` | SSH 터널 + 헤드리스 Chromium으로 JupyterLab 열기·스크롤·Terminal·학습자처럼 새 파일에 붙여 넣고 저장(`new_file_paste`)·Run All·캡처(1600×900). 토큰은 메모리에만(오류 문구에서도 지움). 자기가 연 커널·Terminal만 정리 | 3-3 |
| `scripts/webshot.py` | 로그인 없는 공개 웹 페이지 캡처(1600×900) + capture-log 한 줄 | 3-3 |
| `scripts/redact.py` | `_raw/redact-spec.json`에 적힌 원본만 모자이크해 `screenshots/` + `_masking.json` | 3-4 |
| `scripts/annotate.py` | 마스킹본 위에 클릭 번호·강조 상자(`*-click-*.png`) | 3-4 |
| `scripts/check_lesson.py` | 레슨 품질 게이트(필드, 마스킹 경로, STEP 앵커·그림 배치, 해설 대본, 참조 파일, 노트북, 기대 출력, 비밀값) + `evidence-manifest.json`. `--repo`는 저장소 전체 비밀값 스캔 | 3-6, Phase 4·5·6 |
| `scripts/setup.sh` | Pod venv(기본 train/serve, `VENV_SET`)·커널 등록·lock·uv 캐시 정리. **버전 고정값의 단일 원본**. 이미 있는 venv가 목록과 다르면 멈춤 | Phase 2 |
| `scripts/stackcheck.sh` | 본 제작 전 스택 설치·동작 실측(컨테이너 디스크에서) | Phase 2(선택) |
| `assets/LESSON_GUIDE.template.md` | 과정 저장소 `docs/LESSON_GUIDE.md`(제작 에이전트용 계약서)의 원본 | Phase 1 |
| `assets/decisions.template.md` | 시작 인터뷰 기록 `docs/DECISIONS.md`의 틀(앞머리 YAML은 검사기·워크플로가 읽음, `narration: false`면 해설 대본 검사를 건너뜀). `init_course.py`가 복사(기존 저장소는 `--init-decisions`) | Phase 0-0, 요구가 바뀔 때 |
| `assets/readme-template.md` | 레슨 README 틀(머리말 표, 14절, STEP·코딩 블록·노트북 STEP, 해설 대본 블록) | 3-5 |
| `assets/playbook-template.yaml` | playbook 틀(필수 필드, `not_captured`) | 3-1, 3-5 |
| `assets/example-lesson/` | 완성된 예시 레슨(LLM 과정 파일럿 C02-L02의 글 파일, 그림 없음 — `_ABOUT.md` 먼저) | 과정에 파일럿이 생기기 전 형식 참고 |
| `assets/readme-only-check-template.js` | README-only 검증 워크플로(`args`로 레슨 지정) | Phase 4 |
| `assets/lesson-workflow-template.js` | 병렬 제작 워크플로(레인, 레슨 명세, 의존 약속, 이번 레슨만 verify·fix·재검사, 색인) | Phase 5 |
| `assets/preflight-report.template.md`, `assets/versions.template.md` | `environment/` 기록 틀(`init_course.py`가 채워 복사) | Phase 0·2 |
| `assets/env.local.example`, `assets/gitignore.txt` | `init_course.py`가 복사 | Phase 1 |

| 참고 문서 | 언제 읽나 |
|---|---|
| `references/intake-interview.md` | **맨 처음**: 자동 조사 항목, AskUserQuestion 질문 묶음(권장 선택지·건너뛰는 때), 사람이 할 준비물, 결정 기록과 답이 바꾸는 것 |
| `references/workflow.md` | 각 Phase의 정확한 명령(이어 만들기 점검, Pod Start·Stop 절차 포함). 새 과정이면 시작 전에 전부 |
| `references/lesson-guide.md` | README·playbook·해설 대본·expected-output·troubleshooting 형식, 학습자 환경 규칙, LESSON_GUIDE 채우기 |
| `references/runpod-jupyterlab-facts.md` | README에 UI 라벨·동작·버전을 쓰기 전(상태가 `조사`·`로컬`·`미확인`이면 Pod에서 실측) |
| `references/pitfalls.md` | 시작할 때 한 번, 무언가 막힐 때 |
| `references/verification.md` | `check_lesson.py` FAIL을 고칠 때, README-only 검증·Codex 리뷰를 할 때 |
| `references/parallel-production.md` | 레슨 여러 개를 Workflow로 돌릴 때(진행 순서·레인·콘솔 사전 촬영·끝내기), 도중에 요구가 바뀔 때, 야간 점검, REPORT.md |

## 빠른 시작

### 새 과정
먼저 작업 흐름 0의 **시작 인터뷰**로 범위·산출물·Pod·비용·병렬·끝난 뒤 처리를 정한다. 그다음:
```bash
python "<SK>/scripts/init_course.py" "D:/<과정>" --title "<과정 이름>"   # 로컬 파일만 만든다. 경로는 따옴표로(공백·한글)
# 인터뷰 결정을 docs/DECISIONS.md에, Pod 접속값을 .env.local(.env.local.example 복사)에 채운다(workflow.md 0-5 'Running이 되면' — Pod가 없거나 Stop이면 그 절의 가격 승인부터)
cd "/d/<과정>" && tools/pod.sh A 'nvidia-smi -L'                                 # Bash 도구(Git Bash)
```
그다음 작업 흐름 0(사전 점검 → 승인) → 2(Pod 환경) → 3(파일럿).

### 레슨 하나만 요청받으면
- 시작 인터뷰는 짧게 한다: 산출물·Pod·끝난 뒤 Pod 처리(와 과정 이름)만 묻고, 병렬·자리 비움·내용 검토 깊이는 묻지 않는다.
- 과정 이름·저장소 폴더는 시작 인터뷰에서 함께 묻는다(`intake-interview.md` 3절, 답이 없으면 레슨 주제로). 레슨 경로는 `chapters/chapter-01/lesson-01-<영문-kebab-slug>`.
- Pod 사양은 레슨이 실제로 필요로 하는 GPU로 정한다. GPU가 필요 없으면 그 사실과 가장 싼 선택지를 제안하고 사용자가 고르게 한다.
- 그 레슨이 파일럿이다: 3(메인 세션 혼자) → 4(README-only, 0에서 동의받은 뒤). `REPORT.md` 대신 대화로 보고한다. Pod는 인터뷰의 '끝난 뒤' 답(`after_done`)대로 하고, 답이 없을 때만 '반드시 지킬 것 → Pod 수명'대로 묻는다.

### 이미 있는 과정 저장소에서 이어 만들 때
- 저장소 경로를 받지 못했고 현재 작업 폴더도 과정 저장소(`docs/LESSON_GUIDE.md`·`tools/check_lesson.py`가 있는 폴더)가 아니면 묻는다.
- 그 저장소의 `docs/DECISIONS.md`를 읽고, 이번 요청과 달라진 결정만 묻는다(파일이 없으면 시작 인터뷰를 처음부터 하고, `init_course.py "<저장소>" --init-decisions`로 그 파일만 만들어 채운다 — `--force`는 쓰지 않는다).
- DECISIONS 확인을 마친 뒤 `workflow.md` '이어 만들기' 점검을 한다: `tools/` 비교(`--check-tools`), Pod·접속·용량·남은 프로세스, Chrome 연결, `curriculum.md` 상태 집계와 요청 범위 대조.
- 그 저장소의 `docs/LESSON_GUIDE.md`, 파일럿 레슨 폴더, `curriculum.md`를 먼저 읽고 Phase 3이나 5부터 한다.

## 작업 흐름

### 0. 시작 인터뷰 → 사전 점검(읽기 전용) → 보고 → 승인
- **시작 인터뷰를 가장 먼저 한다**(`references/intake-interview.md`): 알아낼 수 있는 것은 먼저 읽기 전용으로 조사한다(저장소·이전 결정·Pod 접속·Chrome 로그인·로컬 도구·Workflow 가능 여부). 그다음 사람만 정할 수 있는 것을 AskUserQuestion으로 2~3묶음에 나눠 묻는다(요청에 답이 있는 항목은 뺀다). 사람이 직접 할 준비물(RunPod 로그인, SSH 키 등록, Deploy)을 확인하고, 결정 표를 요약해 확인받은 뒤 `docs/DECISIONS.md`에 적는다.
- 새 과정의 순서: `init_course.py`(로컬 파일만)와 `docs/DECISIONS.md` 채우기 → (Pod가 없거나 Stop이면 `workflow.md` 0-5: 품목·가격을 보여 주고 승인 → Deploy/Start) → `.env.local` 채우기 → 아래 점검과 `environment/preflight-report.md` → 보고·승인 → `curriculum.md`·Phase 2. 이 단계에서는 0-5에서 승인받은 Deploy·Start·SSH 키 등록 말고는 Pod·계정에 아무것도 만들거나 바꾸지 않는다.
- 점검표(Chrome 연결·RunPod 콘솔 보기·스크린샷 저장·SSH 키와 접속·GPU·OS/Python·JupyterLab·저장소·자원 표시·다른 과정/세션·Pod 도구·Claude 쪽 도구(Workflow·Cron·필요한 스킬·Git Bash)·Codex·로컬 PC)를 채운다. 명령: `workflow.md` 0-1.
- 이번 과정에 쓸 UI 라벨·동작 중 `runpod-jupyterlab-facts.md`에서 `조사`·`로컬`·`미확인`인 것을 실측 체크리스트로 만든다. Pod 상태를 바꿔야 확인되는 것(Stop 뒤 kernelspec, Restart Pod)은 승인 뒤 아무도 그 Pod를 쓰지 않을 때만(`workflow.md` 0-6), 그 전에는 README에 '확인하지 않음'. 큰 과정이고 Workflow 동의가 있으면 읽기 전용 조사 워크플로(조사 4 + critic)를 돌린다(`workflow.md` 0-3).
- 사용자에게 결과, 결정할 것(저장 용량·비용, 모델·라이선스, 두 번째 Pod, 공개 범위, README-only 검증 워크플로 실행), 계획(파일럿 1개 → 병렬)을 보고하고 승인받는다.
- Pod가 없거나 Stop 상태면 `workflow.md` 0-5(사양·가격 확인 → 사용자가 Deploy / Start 절차).

### 1. 과정 저장소
- `init_course.py`로 뼈대를 만든다(`--pod-root` 기본 `/workspace/<저장소 폴더 이름>`). `curriculum.md`에 챕터·레슨(레슨 하나 = 목표 하나), 공통 환경 결정과 근거(학습자가 venv를 만드는 레슨 포함)를 쓴다. git은 로컬만.

### 2. Pod 환경
- 먼저 그 Pod를 다른 과정·세션이 쓰는지 본다(`<과정폴더>`가 비었는지, `/root/venvs`·tmux·GPU 프로세스). 쓰고 있으면 멈추고 묻는다 — 같이 쓰기로 하면 과정별 `--pod-root`·`--venvs`·`--kernel`을 쓴다.
- 각 Pod에 `setup.sh`를 올려 실행하고(Stop/Start 뒤에도 다시, 레슨이 쓰는 venv만 `VENV_SET`), 모델은 공유 볼륨의 `HF_HOME`에 미리 받는다. 필요하면 `stackcheck.sh`로 스택을 실측한 뒤 지운다.
- 실측 버전을 `environment/versions.md`와 `docs/LESSON_GUIDE.md` 1절(환경 표·자원 레인 표)에 채운다. `<…>`가 남은 채로 병렬 제작을 시작하지 않는다. 명령: `workflow.md` Phase 2.

### 3. 레슨 하나 (반복 단위, 파일럿은 메인 세션이 혼자) — 번호는 `workflow.md` 3-1~3-6과 같다
1. **3-1 설계** — 목표, 시작·완료 조건(학습자 환경 포함), Part로 묶은 STEP 목록을 `playbook.yaml` 초안으로.
2. **3-2 Pod에서 개발·실행** — 컨테이너 디스크의 `/root/dev-<레슨>/`에서 만들고 학습자와 같은 인터프리터·커널로 실제로 돌린다. 실패하면 고쳐서 다시. 끝나면 챕터 폴더를 학습자 시작 상태로 맞춘다.
3. **3-3 촬영과 증거** — 학습자 행동 그대로 하며 각 STEP의 행동 직후 화면을 `_raw/`에(JupyterLab `jlab.py` — 코드 파일 STEP은 `new_file_paste`, 콘솔은 메인 세션의 Chrome 확장, 공개 웹 `webshot.py`) + `capture-log.jsonl`. 출력은 같은 폴더의 로그(읽기만 하는 명령은 SSH 재실행 `*.ssh-rerun.log`)와 화면에 찍힌 그 노트북.
4. **3-4 마스킹·표시** — `redact-spec.json` → `redact.py` → (`annotate-spec.json` → `annotate.py`) → 결과 그림을 열어 확인.
5. **3-5 문서** — `playbook.yaml` 완성 → README + 🎙️ 해설 대본(`assets/readme-template.md`, 형식은 `lesson-guide.md` 5~8절) → `troubleshooting.md`, `expected-output/`, `code/`, `scripts/commands.sh`. 찍지 못한 STEP은 `not_captured`(README에 같은 문구).
6. **3-6 게이트와 정리** — `python tools/check_lesson.py <레슨>`이 모두 PASS일 때까지 고친다(`verification.md` 1절). README를 초보자 눈으로 다시 읽는다. Pod에서 자기 서버·tmux·커널·Terminal과 dev·scratch 폴더를 정리한다.

### 4. README만 보고 재현 검증
- `assets/readme-only-check-template.js`를 Workflow로 돌려(행동 목록 + 초보자 비평, 둘 다 README와 그림만 읽음) 결과를 받는다. 워크플로 스크립트를 쓰거나 고치기 전에는 `workflow-authoring` 스킬을 읽는다. Workflow 도구가 없으면 같은 프롬프트로 서브에이전트 두 개.
- 메인 세션이 행동 목록을 해석 없이 재현 환경(공유 볼륨이 아닌 Pod 우선)에서 실행해 대조한다. `do_not_execute` 행동은 누르지 않고 보이는지만 본다. underivable·실행 불일치·blocker·major는 모두 README 결함 → 고치고 다시. 선택으로 Codex 읽기 전용 리뷰. 절차: `verification.md` 2~4절.

### 5. 병렬 제작 (파일럿 통과 + 사용자 승인 뒤)
- 레슨을 레인(같은 Pod·GPU 한도·포트를 순서대로 쓰는 줄)으로 나눈다. 같은 챕터의 레슨은 한 레인에만 둔다. 레슨마다 고유 jlab 포트, 같은 Pod 안에서 고유한 서버 포트·GPU 상한. 다른 레인의 결과가 필요한 레슨은 의존 약속으로 기다린다.
- 콘솔 화면이 필요한 레슨은 메인 세션이 미리 그 레슨 `_raw/`에 찍어 둔다. `workflow-authoring` 스킬을 읽은 뒤 `assets/lesson-workflow-template.js`를 채워 Workflow로 실행한다. 스크립트가 이번 범위의 레슨만 check → 실패 레슨 수정 → 다시 check(횟수 제한) → README·curriculum 색인까지 한다.
- 도중에 요구가 바뀌면 멈추고, 결정 기록(`docs/DECISIONS.md` 값과 '바뀐 기록') → 계약서 → 검사기 → 프롬프트 순서로 고친 뒤 재개한다. 진행 순서·끝내는 순서·재개·야간 점검: `parallel-production.md`.

### 6. 보고
- 저장소 루트에 `REPORT.md`(형식: `parallel-production.md` 8절)를 쓰고 `python tools/check_lesson.py --repo`가 PASS인지 본 뒤 사용자에게 요약한다. 레슨 하나짜리 요청이면 대화로 보고한다.

### 7. Pod 끄기
- '반드시 지킬 것 → Pod 수명' 규칙대로 Stop한다. 끄기 전 점검과 클릭 경로: `workflow.md` Phase 7.

## 반드시 지킬 것

**시작 인터뷰와 결정**
- 시작 인터뷰(작업 흐름 0)를 마치기 전에는 Pod 생성·Start, 결제, Workflow 실행, 병렬 제작을 시작하지 않는다.
- Workflow(여러 에이전트 동시 실행)는 사용자가 동의했을 때만 쓴다: 인터뷰의 '병렬 = 예', 또는 같은 뜻의 요청. 동의가 없으면 레인마다 서브에이전트 하나를 차례로 쓴다.
- `docs/DECISIONS.md`가 기본값보다 우선한다. 요구가 바뀌면 이 파일부터 고친다.

**비밀값**
- 환경변수 값, 프로세스 명령줄(특히 jupyter), `/jupyter.log`, `/etc/rp_environment` 내용을 출력·캡처하지 않는다(`RUNPOD_API_KEY`, `JUPYTER_PASSWORD`, Jupyter 토큰이 나온다). 금지 예: `env`, `printenv`, `set`, `export -p`, `declare -x`, `cat /proc/*/environ`, `cat`·`tail /jupyter.log`, `jupyter server list`, `ps aux`, `pgrep -af jupyter`. 프로세스는 `ps -eo pid,etime,comm`, `pgrep -af "vllm serve" | cut -c1-120`. 변수 이름만 세야 하면 `compgen -e | grep -ciE "key|token|pass"`만 쓴다(이름만 나오는 bash 내장 명령 — Pod에서 아직 실행해 보지 않았으니 처음엔 숫자 하나만 나오는지 확인).
- vLLM API 키는 환경변수 `VLLM_API_KEY`로만 준다(명령줄 `--api-key`는 `ps`·로그에 찍힘). 모델은 토큰이 필요 없는 공개 모델이 기본이다. gated 모델은 사용자 승인 뒤에만 쓰고, Hugging Face 토큰은 사용자가 Pod에서 `hf auth login`으로 직접 넣는다(명령줄·노트북·로그에 값을 남기지 않고, 입력 화면은 찍지 않거나 가린다).
- IP·포트·Pod ID·토큰·키·SSH 지문을 README·로그·노트북·스크린샷·`environment/`·`verification/`·`REPORT.md`에 남기지 않는다. 공개 그림은 `redact.py`를 거친 것만, `_raw/`·`.env.local`·`.ssh/`는 공개하지 않는다. 주소창·링크 호버·브라우저 기록은 찍지 않는다(Jupyter Lab 링크에 `?token=`). `.env.local` 값을 대화에 다시 출력하지 않는다. 도구 오류 문구를 issues·REPORT에 옮기기 전에 `token=` 뒤를 지운다. 저장소 문서를 쓴 뒤에는 `check_lesson.py --repo`.

**실제 결과만**
- 화면·출력·숫자는 그 레슨을 실제로 실행·촬영한 것만 쓴다. 못 한 것은 README에 '실행하지 않음(이유)'/'촬영하지 않음(이유)', 추정은 '추정'. 실패한 단계는 고쳐서 다시 실행한다.
- 노트북 실행 번호·로그를 손으로 고치지 않는다. 허용되는 손질은 비밀값을 `<POD_IP>` 같은 자리 표시로 바꾸기와 관계없는 줄 생략뿐이고, 그 로그 첫머리에 `# edited: <무엇을 왜>`를 남긴다.

**화면 캡처**
- Windows 데스크톱(화면) 캡처를 쓰지 않는다(다른 프로그램이 찍혔다). JupyterLab은 `jlab.py`(메인 세션은 Chrome 확장 탭 캡처도 가능), RunPod 콘솔은 Chrome 확장 탭 캡처, 공개 웹은 `webshot.py`.
- JupyterLab에서 `File` 메뉴의 `Shut Down`을 누르지 않는다(서버 전체가 꺼진다). 서버 설정을 바꾸는 체크박스(*Do not ask me again.*, *Do not ask for rename on first save.*)와 `Settings` 메뉴를 건드리지 않는다(같은 서버를 쓰는 모든 레슨의 화면이 바뀐다).

**RunPod 계정**
- RunPod 콘솔은 **이미 로그인된 Chrome 확장 세션으로만** 메인 세션이 조작한다(`mcp__claude-in-chrome__*` 도구를 쓰기 전에 `claude-in-chrome` 스킬을 먼저 호출). 비밀번호를 묻거나 다루지 않고, Pod 안의 API 키나 `runpodctl`로 계정을 조작하지 않는다(예외: 사용자가 끄라고 한 Pod가 Pod 안에서 `runpodctl stop pod "$RUNPOD_POD_ID"`로 자기 자신만 Stop — `workflow.md` Phase 7). 서브에이전트·레슨 에이전트는 브라우저 확장을 쓰지 않는다.
- 결제가 생기는 행동(Deploy, 멈춘 Pod의 Start, 볼륨 증설, 크레딧, 유료 옵션)은 품목(GPU 종류·개수, Cloud, 디스크·볼륨 크기)과 화면에 보이는 가격을 사용자에게 보여 주고 명시적 승인을 받은 뒤에만 한다(요청이 그 Pod를 켜라고 분명히 말했으면 Start는 가격만 알리고 진행). 기본은 `Deploy Pod` 버튼 직전까지 준비하고 사용자가 누르게 한다. Web terminal 토글, `Edit Pod`(컨테이너 초기화), 계정 설정(SSH 공개키 등록 포함)도 승인 없이 하지 않는다.

**Pod 수명**
- **이번 요청에서 쓴 Pod만**, 그 요청의 제작(검증·REPORT 포함)이 모두 끝나면 Stop한다. 사용자가 '켜 둬'라고 했으면(`docs/DECISIONS.md` `after_done: keep-running` 포함) 예외. 어느 Pod를 언제 껐는지 보고한다.
- 제작 도중(어느 레인이든 아직 그 Pod를 쓰는 동안)에는 Stop하지 않고, Stop을 제안하지도 않는다.
- 끄기 전에 그 Pod에 내 것이 아닌 작업(다른 세션·과정의 tmux·서버·GPU 프로세스)이 있으면 끄지 말고 묻는다. 작업 전부터 Running이던 Pod와 파일럿만 만든 경우(다음 단계로 병렬 제작을 할지 함께)는, 사용자가 '끝나면 꺼줘'라고 하지 않았으면(`after_done: stop-all`이면 말한 것으로 본다) 끄기 전에 묻는다. 콘솔의 Pod는 `.env.local`의 `POD_<X>_NAME`·`POD_<X>_ID`로 맞춰 고른다.
- Chrome 확장도 Pod 안 `runpodctl` 자기 Stop도 쓸 수 없어 끄지 못하면 그 사실을 바로 보고한다(그 밖의 방법으로 끄지 않는다).
- **Terminate는 사용자가 명시적으로 요청할 때만** 한다(되돌릴 수 없다). Network Volume 삭제도 마찬가지.

**동시 작업과 범위**
- 레슨은 자기 챕터 폴더에서 자기가 만든 파일만 만들고 지운다. 개발·보충 촬영·재현용 임시 폴더는 컨테이너 디스크(`/root/dev-<레슨>/`, `/root/scratch-<레슨>/`)에 두고 끝나면 지운다. 다른 레인의 프로세스·커널·Terminal·tmux를 끄지 않는다(자기 포트·자기 세션 이름만). jlab 로컬 포트는 레슨마다 하나.
- 요청 범위 밖의 레슨은 사용자 승인 없이 고치거나 다시 만들지 않는다(검사기·계약서를 바꿔 기존 레슨이 새 항목에서 FAIL이 나도 보고만 한다).
- 실행 중인 워크플로가 쓰는 `tools/`는 바꾸지 않는다(끝난 뒤 `--update-tools`).

**저장소**
- 커밋·푸시는 사용자가 요청할 때만, git 원격 저장소 생성·영상 업로드도 요청 시만.

## 하지 않는 것
- 실행 없이 예상 출력으로 README 쓰기, 남의 화면이나 이미지 생성으로 실화면 대신하기.
- 사용자가 요청하지 않은 레슨의 영상(`storyboard.md`·`narration.md` 포함) 만들기 — 요청이 오면 그 레슨의 README·해설 대본·마스킹 그림을 입력으로 `ai-concept-visualization-video`를 쓴다.
- 검사기를 느슨하게 고쳐 FAIL을 없애기. FAIL은 레슨을 고쳐서 없앤다.
