# 단계별 절차와 명령 (Phase 0 → 7)

`<SK>` = 이 스킬 폴더(명령의 `<SK>`는 그 경로로 바꿔 쓴다), `REPO` = 과정 저장소(예: `D:\<과정>`), Git Bash 경로는 `/d/<과정>`. `<과정폴더>` = Pod 안 학습자 작업 폴더(`init_course.py --pod-root`, 기본 `/workspace/<저장소 폴더 이름>`, LLM 과정은 `/workspace/llm-course`).
경로에 공백·한글이 있으므로 모든 경로는 따옴표로 감싼다. `pod.sh`·`pod_get.sh`는 Bash 도구(Git Bash)에서, Python 도구는 이 PC의 `python`으로 돌린다. 셸 호출마다 폴더가 처음으로 돌아갈 수 있으므로 명령 앞에 `cd "/d/<과정>" &&`를 붙인다.
안전 규칙(비밀값, 결제, Pod 수명, 동시 작업)은 SKILL.md '반드시 지킬 것'에 한 번만 적혀 있다. 이 문서는 그 규칙을 지키는 절차다.

---

## Phase 0. 시작 인터뷰 → 사전 점검(읽기 전용) → 보고 → 승인

목표: 쓰기 전에 사람만 정할 수 있는 것을 먼저 묻고, 무엇이 되고 안 되는지 실측한다. 이 단계에서는 0-5에서 승인받은 Deploy·Start·SSH 키 등록 말고는 Pod·계정에 아무것도 만들거나 바꾸지 않는다.
**새 과정의 순서**: 0-0 시작 인터뷰 → Phase 1의 `init_course.py`(로컬 파일만 만든다 — 승인 전에 해도 된다)와 `docs/DECISIONS.md` 채우기 → (Pod가 없거나 Stop이면 0-5: 품목·가격을 보여 주고 승인 → Deploy/Start) → `.env.local` 채우기(0-5 'Running이 되면') → 0-1 점검과 `environment/preflight-report.md` → 0-4 보고·승인 → `curriculum.md`·Phase 2.

### 0-0. 시작 인터뷰 (가장 먼저)
`references/intake-interview.md`대로 한다: 자동 조사(읽기 전용) → AskUserQuestion 묶음 질문(요청에 답이 있는 항목은 빼고) → 사람이 할 준비물 확인 → 결정 표 요약 확인 → `docs/DECISIONS.md` 기록. 이어 만들기면 기존 `docs/DECISIONS.md`를 읽고 바뀐 것만 묻는다. 인터뷰가 끝나기 전에는 Pod 생성·결제·Workflow 실행을 하지 않는다.

### 0-1. 점검표 (결과는 `init_course.py`가 만든 `environment/preflight-report.md` 틀에 — 다 쓴 뒤 `python tools/check_lesson.py --repo`)

| 항목 | 방법(읽기 전용) |
|---|---|
| Chrome 연결 | 먼저 `claude-in-chrome` 스킬을 호출한 뒤, 그 도구를 ToolSearch로 한 번에 불러온다(`tabs_context_mcp, navigate, computer, read_page, tabs_create_mcp, tabs_close_mcp` + 필요하면 `list_connected_browsers, select_browser`). 확장이 여러 개 연결되어 있고 고른 것이 없으면 `list_connected_browsers`의 목록(이름·OS·이 PC 여부)을 사용자에게 보여 주고 고르게 한다(직접 고르지 않는다) |
| RunPod 콘솔 | 로그인된 탭에서 `console.runpod.io` → Pods 목록 → Pod 이름 → Connect 탭을 **보기만** 한다. GPU 종류, 템플릿, Cloud, Cost 열, HTTP services Ready, SSH 방식을 적는다. Deploy·Start·Stop·Terminate·Web terminal 토글·계정 설정은 누르지 않는다 |
| 스크린샷 저장 | `computer` 도구의 `screenshot`(탭 전체, 1568폭 JPEG)과 `zoom`(`region: [x0, y0, x1, y1]`, 원본 픽셀 PNG)을 `save_to_disk: true`로 찍는다 → 결과에 나온 저장 경로의 파일을 `<레슨>/_raw/sNN-<무엇>.jpg`(zoom은 `.png`)로 복사 → Read로 열어 크기·판독성 확인 → `capture-log.jsonl`에 한 줄(3-3). 파일로 저장할 수 없는 환경이면 콘솔 STEP은 '촬영하지 않음(이유)'과 글로 안내한다. Windows 화면 캡처는 쓰지 않는다 |
| SSH 키 | `test -f ~/.ssh/id_ed25519 && echo key-ok`. 없으면 사용자 동의를 받고 PowerShell에서 `ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_ed25519"`(Git Bash의 ssh 도구는 한글 사용자 경로의 `~/.ssh`에 쓰지 못할 수 있다) |
| SSH | `.env.local`을 채운 뒤 `tools/pod.sh A 'nvidia-smi -L'` (BatchMode, 종료 코드 0) |
| GPU·OS·Python | `tools/pod.sh A 'nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv; head -2 /etc/os-release; python --version; which python; python -c "import torch;print(torch.__version__, torch.cuda.is_available())"'` |
| JupyterLab | `tools/pod.sh A 'jupyter lab --version'`, 화면은 `python tools/jlab.py A 18899 "<scratch>/selftest.png"` → 그림을 열어 본다 |
| 저장소 | `tools/pod.sh A 'df -h / /workspace'` — 컨테이너 디스크 크기, `/workspace`가 Network Volume인지(두 Pod 공유인지) |
| 자원 표시 | `tools/pod.sh A 'nproc; free -g | head -2; source /etc/rp_environment >/dev/null 2>&1; echo "RUNPOD_CPU_COUNT=$RUNPOD_CPU_COUNT"'` (변수는 이 하나만 출력. SSH 비대화형 셸은 `/etc/rp_environment`를 읽지 않으므로 source가 필요하다) |
| 다른 과정·세션 | `tools/pod.sh A 'ls -A <과정폴더> 2>/dev/null | head -5; ls /root/venvs 2>/dev/null; tmux ls 2>&1 | head -5; nvidia-smi --query-compute-apps=pid,used_memory --format=csv'` — `<과정폴더>`가 비어 있지 않거나 남의 venv·tmux·GPU 프로세스가 있으면 멈추고 사용자에게 묻는다 |
| 도구(Pod) | `tools/pod.sh A 'uv --version; tmux -V; git --version'` |
| 도구(Claude 쪽) | 쓸 수 있는 도구에 Workflow, CronCreate·CronList·CronDelete, TaskStop이 있는지, `workflow-authoring`·`claude-in-chrome` 스킬, `bash --version`(Git Bash). 없으면 대안: README-only는 서브에이전트 2개(`verification.md` 2절), 병렬 제작은 레인별 서브에이전트(`parallel-production.md` 5절), 야간 점검을 못 걸면 사용자에게 알리고 끝난 뒤 메인 세션이 직접 마무리 |
| Codex(선택) | `codex --version` — 읽기 전용 교차 리뷰에만 쓴다 |
| 영상 스킬(선택) | 사용자가 영상을 원할 때만 `imcommit-style-video` 준비 상태 확인 |
| 로컬 PC | `python -c "import playwright, PIL, yaml, nbformat"` — 없으면 `python -m pip install playwright pillow pyyaml nbformat`, 브라우저는 `python -m playwright install chromium` |

### 0-2. 실측 체크리스트 (새 과정·새 템플릿이면 다시 확인)
`references/runpod-jupyterlab-facts.md`에서 상태가 `조사`·`로컬`·`미확인`인 항목 중 이번 과정에 쓰는 것을 파일럿 리허설 때 Pod에서 확인한다. 파일럿 때 확인한 목록:
- 노트북을 연 상태의 `Kernel` 메뉴 라벨과 재시작 확인 버튼 이름, 첫 저장 때 *Rename file* 창과 버튼 이름
- Launcher에서 연 Terminal과 `File → New → Terminal`의 시작 위치
- Terminal 글자 추출 가능 여부(불가 → SSH 재실행 로그), 클립보드 붙여 넣기
- `!nvidia-smi`에 커널 메모리가 보이는지, 커널을 끄면 VRAM이 돌아오는지
- 스택: 설치 명령이 고르는 torch·CUDA 변형, venv 크기(`du -sh`)

Pod 상태를 바꿔야 확인되는 항목(Stop 뒤 kernelspec이 남는지, `Restart Pod`가 컨테이너 디스크를 지우는지)은 여기서 하지 않는다 → 0-6.

### 0-3. 사전 조사(선택, 큰 과정일 때)
Workflow라 사용자 동의가 있을 때만 한다(`docs/DECISIONS.md`가 `parallel_workflow: true`이고 인터뷰 때 사전 조사도 Workflow로 한다고 알렸거나, 따로 동의를 받았을 때). 동의가 없으면 건너뛰거나 메인 세션이 직접 조사한다.
읽기 전용 Workflow로 조사 에이전트 4개(RunPod·JupyterLab UI / 소프트웨어 스택 / 모델·GPU / 영상)를 병렬로 돌리고, critic이 모순·'Pod에서 꼭 확인할 주장(확인 명령 포함)'·빠진 정보·보안/비용 위험을 낸다. 조사 에이전트는 브라우저·SSH·파일 쓰기를 하지 않고 모든 주장에 출처를 단다. critic의 확인 명령은 0-2에서 Pod로 확인한다.

### 0-4. 보고와 승인
사용자에게 점검표, 결정할 것(저장 용량·증설 비용, 모델·라이선스와 gated 여부, 두 번째 Pod, 공개 범위), 제작 계획(파일럿 → README-only 검증 → 병렬)을 보여 주고 승인받는다. README-only 검증은 에이전트 두 개를 띄우는 Workflow라 시간·비용이 든다 — 계획에 넣어 동의를 받는다. 결제가 생기는 행동은 SKILL.md '반드시 지킬 것 → RunPod 계정'대로 한다.

### 0-5. Pod가 아직 없거나 멈춰 있으면
- **없으면**: 필요한 사양을 정해 사용자에게 보여 준다 — GPU 종류·개수(레슨이 실제로 쓰는 만큼. GPU가 필요 없는 과정이면 그 사실과 가장 싼 선택지), Cloud, 템플릿, 컨테이너 디스크 크기, Network Volume 크기·Region, 미리 열 HTTP 포트, **TCP 22 노출(SSH over exposed TCP — 없으면 `pod.sh`·`pod_get.sh`·`jlab.py`가 모두 동작하지 않는다. 템플릿 기본값인지는 Deploy 화면에서 확인)**. 승인 뒤 메인 세션이 콘솔의 `+ Deploy` 화면을 그 값으로 채우고(Deploy 흐름 화면도 레슨 자료로 촬영), `Deploy Pod`는 사용자가 누른다(또는 품목·가격을 다시 보여 주고 명시적 승인을 받은 뒤). 공개키(`~/.ssh/id_ed25519.pub`)는 Pod를 만들기 전에 Credentials → **SSH Public Keys**에 등록한다 — 사용자 승인 뒤 메인 세션이 `Add SSH key`를 누르거나 사용자가 직접(이미 켜진 Pod에 반영되는지는 미확인).
- **Running이 되면**: 메인 세션이 Connect 패널(SSH over exposed TCP)에서 IP·포트를, 목록과 상세 패널에서 Pod 이름·ID를 읽어 `.env.local`에 채운다(값을 대화에 다시 출력하지 않는다).
- **멈춰 있으면(Stop)**: Start는 결제 행동이다(시간 요금이 다시 나가고 같은 GPU를 못 받을 수 있다) — 요청이 그 Pod를 켜라고 분명히 말하지 않았으면 시간당 요금을 보여 주고 확인받은 뒤: 콘솔 **Pods** → Pod 이름 → **Start**(라벨·확인 창은 미확인 — 화면 그대로 따른다) → 목록의 초록 점(Running)과 Connect의 Jupyter Lab **Ready** 확인 → Connect에서 IP·포트를 다시 읽어 `.env.local`을 고친다 → `Host key verification failed`가 나면 `ssh-keygen -R "[<ip>]:<port>" -f "/d/<과정>/.ssh/known_hosts"` → `tools/pod.sh A 'nvidia-smi -L'` → Phase 2의 `setup.sh` → 모델 캐시 확인(`ls /workspace/.cache/huggingface/hub`). GPU를 받지 못하면 멈추고 보고한다. Start 시각을 적어 둔다(REPORT.md 비용 계산).

### 0-6. (승인 뒤) Pod 상태를 바꿔야 확인되는 것
Stop 뒤 kernelspec(`~/.local/share/jupyter`)이 남는지, `Restart Pod`가 컨테이너 디스크를 지우는지 같은 항목은 사용자 승인을 받고, 아무도 그 Pod를 쓰지 않을 때(진행 중인 레인·다른 세션 없음 — 0-1 '다른 과정·세션' 명령으로 확인) 또는 이 확인만을 위한 임시 Pod에서만 한다. 확인 전에는 README·facts에 '확인하지 않음'으로 쓴다.

---

## 이어 만들기 (이미 있는 과정 저장소)
먼저 0-0 시작 인터뷰를 한다 — 기존 `docs/DECISIONS.md`를 읽고 이번 요청과 달라진 것만 묻는다. 파일이 없으면 인터뷰를 처음부터 하고, `python "<SK>/scripts/init_course.py" "<저장소>" --init-decisions --title "<과정 이름>"`으로 `docs/DECISIONS.md`만 만든 뒤 채운다(다른 파일은 손대지 않는다. `init_course.py --force`는 쓰지 않는다). 인터뷰를 마친 뒤 0-1~0-4 대신 아래를 확인하고 Phase 3이나 5부터 한다.
1. **저장소 경로**: 사용자가 주지 않았고 현재 작업 폴더도 과정 저장소(`docs/LESSON_GUIDE.md`와 `tools/check_lesson.py`가 있는 폴더)가 아니면 묻는다.
2. **도구 판**: `python "<SK>/scripts/init_course.py" "<저장소>" --check-tools` → 다른 파일이 있으면 사용자에게 알리고, 그 `tools/`를 쓰는 워크플로가 돌고 있지 않을 때 `--update-tools`(tools/만 바꾼다). `--force`는 README·curriculum·LESSON_GUIDE·`environment/`·`tools/`·`.gitignore`·`.env.local.example`까지 템플릿으로 덮어쓰므로(`docs/DECISIONS.md`(인터뷰 기록)만 보존) 쓰지 않는다. 구판 `tools/check_lesson.py`는 DECISIONS.md를 읽지 못하므로, 다르면 `--update-tools`가 필요하다.
3. **계약서**: `docs/LESSON_GUIDE.md`, 파일럿 레슨, `curriculum.md`를 읽는다.
4. **Pod·접속**: `.env.local`의 이름·ID가 콘솔 목록과 맞는지, `tools/pod.sh A 'nvidia-smi -L; df -h /workspace; tmux ls 2>&1 | head; pgrep -af "vllm serve" | cut -c1-120; nvidia-smi --query-compute-apps=pid,used_memory --format=csv'` — 이전에 중단된 실행이 남긴 tmux·vLLM·커널은 레슨 세션 이름·포트로 골라 정리한다(누구 것인지 모르면 묻는다). Pod가 Stop이면 0-5(인터뷰를 마친 뒤, 시간당 요금을 보여 주고 승인).
5. **Chrome 확장** 연결(콘솔 촬영과 마지막 Stop에 필요).
6. **범위**: `curriculum.md`의 ⬜·🟡 레슨을 세어 요청(예: '남은 챕터 10개')과 맞는지 사용자에게 확인한다.

---

## Phase 1. 과정 저장소 만들기

```bash
python "<SK>/scripts/init_course.py" "D:/<과정>" --title "<과정 이름>" [--pod-root workspace/<과정폴더>] [--venvs root/venvs/<과정>] [--kernel <과정>-train] [--kernel-label "Python (<과정>)"]
```
- 과정 이름은 시작 인터뷰에서 정한 값을 쓴다(기본값은 폴더 이름).
- `--pod-root` 기본값은 `/workspace/<저장소 폴더 이름>`(다른 과정과 섞이지 않게). Git Bash에서는 `--pod-root`·`--venvs` 값의 앞 `/`를 빼고 쓴다(붙이면 Git Bash가 `C:/Program Files/Git/…`로 바꿔 넘겨서 스크립트가 멈춘다). `--venvs`·`--kernel`·`--kernel-label`은 같은 Pod를 다른 과정도 쓸 때 과정별로 준다(`environment/setup.sh` 기본값과 `docs/LESSON_GUIDE.md`에 함께 들어간다).
- 이미 있는 파일이 하나라도 있으면 아무것도 쓰지 않고 멈춘다. `--force`는 기존 저장소에 쓰지 않는다('이어 만들기' — 인터뷰 기록만 없으면 `--init-decisions`). `.env.local`은 만들지 않는다.
- `.env.local.example` → `.env.local` 복사 후 채운다(0-5). 값은 따옴표 없이. Pod B를 쓰면 `POD_B_*` 줄 주석을 푼다.
- `docs/LESSON_GUIDE.md`의 `<…>` 자리를 Phase 2 실측값으로 채운다(방법: `references/lesson-guide.md` 9절).
- `curriculum.md`: 챕터·레슨(레슨 하나 = 목표 하나), 공통 환경 결정과 근거(학습자가 venv를 어느 레슨에서 만드는지 포함), 사용자 결정 목록, 아직 실측 안 한 것.
- 레슨 하나만 요청받았으면 그 레슨 경로는 `chapters/chapter-01/lesson-01-<영문-kebab-slug>`.
- `git init`은 로컬만. 커밋·푸시는 사용자가 요청할 때만.

---

## Phase 2. Pod 환경

```bash
cd "/d/<과정>"
tools/pod.sh A 'ls -A <과정폴더> 2>/dev/null | head -5; ls /root/venvs 2>/dev/null; tmux ls 2>&1 | head -5'   # 다른 과정·세션(0-1)
tools/pod.sh A 'cat > /root/setup.sh' < environment/setup.sh
tools/pod.sh A 'bash /root/setup.sh' 2>&1 | tail -5        # LLM 기본값 실측 약 1.5~2분
tools/pod.sh B 'cat > /root/setup.sh' < environment/setup.sh && tools/pod.sh B 'bash /root/setup.sh' 2>&1 | tail -5
```
- `setup.sh`는 버전 고정값의 단일 원본이다. 컨테이너 디스크에 venv를 만들고(`VENV_SET` — 기본 `train,serve`. 레슨이 쓰는 venv만 만든다: 서빙이 없는 과정은 `tools/pod.sh A 'VENV_SET=train bash /root/setup.sh'`), train venv를 커널(`KERNEL`·`KERNEL_LABEL`)로 등록하고, lock 파일(`/workspace/.course-env/<과정폴더 이름>/*.lock` — 학습자 화면 밖 숨김 폴더)을 남기고, uv 캐시를 지운다. 다른 과정이면 패키지 목록만 바꾼다.
- 이미 있는 venv가 고정 목록과 다르면 아무것도 바꾸지 않고 `exit 3`으로 멈춘다: 다른 과정의 venv면 지우지 말고 과정별 `VENVS`로(`init_course.py --venvs`), 혼자 쓰는 Pod에서 설치가 중간에 끊긴 venv면 `tools/pod.sh A 'rm -rf /root/venvs/train'` 뒤 다시 실행.
- Pod를 Stop/Start하면 `/root`가 비므로 위 두 줄을 다시 실행한다.
- 모델 미리 받기(공유 볼륨의 HF 캐시, 다시 받지 않음). 학습자에게는 첫 다운로드 크기·시간이 다르게 보이므로 README '달라도 되는 것'에 적는다(`VENVS`가 기본값이 아니면 경로를 바꾼다):
  ```bash
  tools/pod.sh A 'source /etc/rp_environment >/dev/null 2>&1; /root/venvs/train/bin/hf download Qwen/Qwen3-0.6B >/dev/null && echo ok'
  ```
- 스택 실측(선택, 본 제작 전 한 번): 컨테이너 디스크에서만 돌리고 결과를 회수한 뒤 지운다(약 46GB 사용). Pod가 하나면 B 대신 A(제작에 쓰지 않는 시간에).
  ```bash
  tools/pod.sh B 'mkdir -p /root/stackcheck && cat > /root/stackcheck/run.sh' < tools/stackcheck.sh
  tools/pod.sh B 'nohup bash /root/stackcheck/run.sh > /root/stackcheck/run.log 2>&1 &'
  # 끝나면(run.log 마지막 줄 'DONE')
  tools/pod_get.sh B /root/stackcheck/run.log "verification/stackcheck-<날짜>/"
  tools/pod_get.sh B /root/stackcheck/logs "verification/stackcheck-<날짜>/"
  tools/pod.sh B 'rm -rf /root/stackcheck'
  ```
- 결과를 `environment/versions.md`(init_course.py가 만든 틀)와 `docs/LESSON_GUIDE.md` 1절에 적는다.

---

## Phase 3. 레슨 하나 만들기 (파일럿은 반드시 혼자, 메인 세션에서)

### 3-1. 설계
레슨 목표 하나, 시작 조건(앞 레슨에서 이어지는 파일·서버 상태, 학습자가 쓰는 파이썬 환경), 완료 조건, STEP 목록(Part로 묶음)을 정해 `playbook.yaml` 초안을 만든다(`assets/playbook-template.yaml`. 과정에 파일럿이 없으면 `assets/example-lesson/`도 본다). UI 라벨은 `runpod-jupyterlab-facts.md`에서 찾고, 없으면 리허설에서 실측한다.

### 3-2. Pod에서 개발·실행
개발과 시험 실행은 컨테이너 디스크의 `/root/dev-<레슨>/`에서 한다(공유 `/workspace`의 챕터 폴더에 파일을 미리 만들면 학습자처럼 새로 만드는 화면을 찍을 수 없고, 다른 Pod 화면에도 보인다).
```bash
tools/pod.sh A 'mkdir -p /root/dev-c03l01 && cat > /root/dev-c03l01/l01_x.py' < "chapters/chapter-03/lesson-01-x/code/l01_x.py"
tools/pod.sh A 'cd /root/dev-c03l01 && source /etc/rp_environment >/dev/null 2>&1; /root/venvs/train/bin/python l01_x.py'
```
- 학습자와 같은 인터프리터·커널로 돌린다(README 03절의 환경 — 시스템 Python이면 `python`, venv면 그 venv의 python과 커널).
- 노트북: 로컬에서 `nbformat`으로 만든다(짧은 코드 셀 + 마크다운 설명 셀, 출력이 없어야 하는 셀은 셀 태그 `no-output`) → dev 폴더에서 nbconvert로 돌려 본다.
- 오래 걸리는 서버·학습: `tmux new -d -s <레슨세션> '…'` 또는 `nohup … > logs/x.log 2>&1 &`, 학습은 `flock /root/gpu-train.lock …`. 끝나면 `tmux kill-session -t <레슨세션>`, `pkill -f "vllm serve .*--port <내 포트>"`.
- 실행이 실패하면 원인을 고쳐 다시 실행한다. 끝내 못 하면 README에 '실행하지 않음(이유)'.
- 다 되면 **챕터 폴더를 학습자 시작 상태로 맞춘다**(앞 레슨이 남긴 것만 있고 이 레슨이 만들 파일은 없게).

### 3-3. 화면 촬영과 증거 (`_raw/`에 원본, 이름 `sNN-<무엇>.png`, 같은 STEP 여러 장은 `sNNa`, `sNNb`)
학습자 시작 상태의 챕터 폴더에서 README의 행동을 그대로 하며 각 STEP의 행동 직후 화면을 찍는다. 증거(화면·로그·노트북)는 모두 이 실행에서 나온다.
- **JupyterLab**: `tools/jlab.py` (레슨마다 고유 로컬 포트·workspace 이름)
  ```python
  import sys; sys.path.insert(0, r"D:\<과정>\tools")
  from jlab import JLab
  L = r"D:\<과정>\chapters\chapter-03\lesson-01-x"
  code = open(L + r"\code\l01_x.py", encoding="utf-8").read()
  with JLab("A", port=18811, workspace="c03l01") as j:
      j.new_file_paste(code, "l01_x", folder="workspace/<과정폴더>/ch03",      # JupyterLab 루트(/) 기준, 앞에 / 없음
                       shots={"pasted": L + r"\_raw\s04a-code-pasted.png",
                              "rename": L + r"\_raw\s04b-rename-dialog.png",
                              "saved": L + r"\_raw\s04c-saved.png"})
      j.terminal(["cd /workspace/<과정폴더>/ch03", "python l01_x.py"], wait=3)
      j.shot(L + r"\_raw\s05-run.png")
      j.open("workspace/<과정폴더>/ch03/l01_x.ipynb")
      j.shot(L + r"\_raw\s06-notebook-top.png")
      j.scroll_to_text("<출력에 보이는 글자>")
      j.shot(L + r"\_raw\s07-result.png")
      j.shutdown_terminals()                               # 내가 연 Terminal만
      j.shutdown_kernels()                                 # 내가 연 노트북 커널만
  ```
  `new_file_paste`는 Launcher → **Python File** → 코드 붙여 넣기 → 첫 `Ctrl+S` → *Rename file* → **Rename and Save**를 학습자처럼 하고 그 순간들을 찍는다(같은 이름 파일이 있으면 멈춘다). 메뉴 클릭·대화상자처럼 jlab에 없는 동작은 `j.page`(Playwright Page)로 직접 한다. 일부 확대 그림은 PIL로 원본에서 잘라 `*-zoom.png`로 저장하고 자른 좌표를 capture-log의 `tool`에 적는다.
- **RunPod 콘솔**(로그인 필요): 메인 세션만, Chrome 확장으로(저장 절차는 0-1 '스크린샷 저장'). 잔액·아바타·Pod ID·IP·SSH 지문은 마스킹 대상으로 좌표를 적어 둔다(좌표는 그 원본 픽셀 기준 — 탭 캡처는 1568폭). 주소창·링크 호버는 찍지 않는다. 병렬 제작이면 레슨 에이전트가 쓸 콘솔 원본을 미리 찍어 그 레슨 `_raw/`에 넣는다(`parallel-production.md` 진행 순서 5).
- **메인 세션이 학습자처럼 JupyterLab을 직접 조작할 때**(파일럿 본 촬영 방식): Chrome 확장으로 클릭·입력하고 탭 캡처 + 작은 글자는 zoom 캡처. 여러 줄 코드는 PowerShell `Set-Clipboard`로 PC 클립보드에 넣고 편집기·셀에서 `Ctrl+V` — README에서 복사해 붙이는 학습자 동작과 같고 편집기 자동 들여쓰기로 코드가 깨지지 않는다(실측).
- **공개 웹 페이지**: `python tools/webshot.py "<URL>" "<레슨>/_raw/s02-model-card.png" --step S02 --click "Reject all"` — 로그인 없는 페이지만, 쿠키 배너는 개인정보를 덜 주는 버튼(`--click`)이나 `--hide <CSS 선택자>`로 치운다. capture-log 줄을 자동으로 더한다. README 14절에 넣을 공식 문서 URL도 직접 열어 제목을 확인한다.
- **Terminal 출력 텍스트**: 읽기만 하는 명령(`nvidia-smi`, `ls`, `pwd`, 출력만 하는 스크립트)은 촬영 직후 같은 폴더에서 SSH로 다시 실행해 로그로 남긴다. 명령마다 `$ <명령>` 줄을 앞에 찍으면 expected-output의 `# after:`가 그 뒤부터 검사한다:
  ```bash
  tools/pod.sh A 'cd <과정폴더>/ch03 && { echo "# source: ssh-rerun (Pod A, <날짜>, 화면 STEP 5)"; echo "\$ python l01_x.py"; /root/venvs/train/bin/python l01_x.py; } 2>&1' > "chapters/chapter-03/lesson-01-x/logs/terminal.ssh-rerun.log"
  ```
  상태를 바꾸는 명령(`mkdir`·`mv`·`rm`, 다운로드, 학습, 서버 실행)은 다시 실행하지 않는다 — Terminal에서 처음부터 `… 2>&1 | tee logs/lMM_x.log`로 남기거나(README에는 tee 없는 명령을 쓰고 08절에 이유를 적는다) 화면에서 읽는다. SSH로 처음 실행해 얻은 로그는 첫 줄 `# source: ssh-run (Pod A, <날짜>)`.
- **노트북**: 증거 노트북 = 화면에 찍힌 바로 그 실행의 저장본이다. (a) 에이전트 방식: 노트북을 챕터 폴더에 올려 nbconvert로 실행 → jlab으로 열어 저장된 출력을 찍는다 → 그 파일을 가져온다. (b) UI 방식(파일럿): 학습자처럼 UI에서 만들고 실행(마지막에 Restart Kernel and Run All Cells…)·저장한 그 파일을 가져온다. 두 실행의 숫자를 섞지 않는다.
  ```bash
  tools/pod.sh A 'cd <과정폴더>/ch03 && source /etc/rp_environment >/dev/null 2>&1; jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=train --ExecutePreprocessor.timeout=1800 l01_x.ipynb'
  tools/pod_get.sh A <과정폴더>/ch03/l01_x.ipynb "chapters/chapter-03/lesson-01-x/notebooks/"
  ```
  실행 번호는 1..n이어야 한다. 셀 코드는 `notebooks/cells/cellN.py`로도 남긴다(README·playbook의 `code_file`). 커널 이름은 LESSON_GUIDE 1절(기본 `train`).
- **촬영 기록**: `_raw/capture-log.jsonl`에 한 줄씩 — `check_lesson.py`가 evidence-manifest를 만들 때 읽는다. `file`은 `_raw` 안의 원본 파일 이름(= redact-spec의 키, 다르면 manifest에 kind·note가 비어 들어간다), `copied_at`은 원본을 `_raw/`에 저장한 시각(ISO 8601, KST), `kind`는 current(행동 전) / click(누를 곳) / result / execution(진행 중) / verification(확인):
  ```json
  {"file": "s06-notebook-top.png", "step": "S06", "kind": "result", "note": "노트북 위쪽, 셀 1~2 출력", "source": "real-capture", "tool": "tools/jlab.py 1600x900", "pod": "A", "copied_at": "2026-10-28T04:09:42+09:00"}
  ```
- **보충 촬영**(놓친 상태): 같은 사양 Pod의 컨테이너 디스크 임시 폴더 `/root/scratch-<레슨>/`에서 그 상태만 다시 찍는다(파일 이름에 `scratch`, README 그림 아래 *기울임*으로 다른 점 — 경로 표시줄이 `/ root / scratch-… /`로 보이는 등). 촬영 뒤 폴더를 지운다.

### 3-4. 마스킹·클릭 표시
1. `_raw/redact-spec.json` — 공개할 원본 **모두**: `{"<원본>": {"out": "<공개 이름>.png", "boxes": [[x0,y0,x1,y1], …]}}`(가릴 것 없으면 `"boxes": []`, 좌표는 원본 픽셀).
2. `python tools/redact.py "<레슨폴더>"` → `screenshots/` + `screenshots/_masking.json`.
3. (선택) `_raw/annotate-spec.json` — `{"sNN-click-<대상>.png": {"src": "<마스킹본>.png", "marks": [{"box": [...], "n": 1}, {"box": [...], "n": 2, "anchor": "right"}]}}` → `python tools/annotate.py "<레슨폴더>"`.
4. 결과 그림을 열어 가림 상태·번호 위치를 눈으로 확인한다(검사기는 그림 속 글자를 보지 못한다).

### 3-5. 문서
- `playbook.yaml` 완성(단일 원본) → `README.md`(`assets/readme-template.md`, 14절 + STEP + 🎙️ 해설 대본) → `troubleshooting.md`(ID | 단계 | 증상 | 원인 | 해결 | 근거) → `expected-output/*.txt`, 레슨의 Terminal 명령 모음 `<레슨>/scripts/commands.sh`(통째로 실행하지 말라는 주석과 STEP 번호), `code/`. 형식 규칙은 `references/lesson-guide.md`.
- 그림을 찍지 못한 STEP은 playbook에 `screenshots: []`와 `not_captured: "<이유>"`, README 그 STEP에 같은 문구를 그대로 쓴다.
- 개념 그림은 `shared/diagrams/<레슨접두어>-<개념>.png`(matplotlib 등으로 그림, README에 '*설명용 그림*').

### 3-6. 게이트와 정리
```bash
python tools/check_lesson.py "chapters/chapter-03/lesson-01-x"     # 마지막 줄 'N PASS / 0 FAIL'
```
FAIL을 고친 뒤(`references/verification.md` 1절) README를 처음부터 초보자 입장에서 다시 읽는다. Pod에서 자기 서버·tmux·커널·Terminal과 dev·scratch 폴더를 정리하고 `nvidia-smi`로 확인한다.

---

## Phase 4. README만 보고 재현되는지 검증
파일럿은 반드시. 이후 레슨은 챕터마다 1개 이상(콘솔·서버·학습 STEP이 있는 레슨 우선) 또는 전부. 절차: `references/verification.md` 2~4절(`assets/readme-only-check-template.js` + 행동 목록을 재현 환경에서 실행 + 선택 Codex 읽기 전용 리뷰).

## Phase 5. 병렬 제작
파일럿이 전부 PASS와 README-only 검증을 통과한 뒤, 사용자 승인을 받고 `assets/lesson-workflow-template.js`로 레인을 나눠 돌린다. 진행 순서·레인 설계·의존·재개·야간 점검·끝내기: `references/parallel-production.md`.

## Phase 6. 보고
`REPORT.md`(저장소 루트, 형식은 `parallel-production.md` 8절)를 쓰고 `python tools/check_lesson.py --repo`가 PASS인지 본다(FAIL이면 그 값을 지우고 다시). 사용자에게는 레슨별 상태, 남은 문제, 결정할 것, Pod 상태를 짧게 보고한다. 레슨 하나짜리 요청이면 REPORT.md 없이 대화로 보고한다.

## Phase 7. Pod 끄기
먼저 `docs/DECISIONS.md`의 `after_done`을 본다. 어느 Pod를 언제 끄는지는 SKILL.md '반드시 지킬 것 → Pod 수명'. 절차:
1. 모든 레인·verify·fix·README-only 검증·REPORT.md가 끝났는지 확인한다.
2. 끌 Pod마다 남은 작업을 본다: `tools/pod.sh A 'tmux ls 2>&1 | head; pgrep -af "vllm serve" | cut -c1-120; nvidia-smi --query-compute-apps=pid,used_memory --format=csv'` — 내 세션·내 포트가 아닌 것이 있으면 끄지 말고 묻는다. 내 서버·tmux·커널이 남았으면 먼저 정리한다.
3. 메인 세션이 `claude-in-chrome` 스킬을 호출한 뒤 로그인된 Chrome 확장으로 `console.runpod.io` → **Pods** → `.env.local`의 `POD_<X>_NAME`과 같은 이름(상세 패널의 Pod ID로 한 번 더 확인) → 상세 패널 위쪽 빨간 **Stop** → 확인 → 목록에서 초록 점이 사라졌는지 확인(Pod마다).
   - 대안(사용자가 그 Pod를 끄라고 했을 때만): Pod 안에서 자기 자신만 끈다. `tools/pod.sh A 'source /etc/rp_environment 2>/dev/null; runpodctl stop pod "$RUNPOD_POD_ID" 2>&1 | sed -e "s/$RUNPOD_POD_ID/<pod>/g"'` — Pod마다 들어 있는 Pod 전용 키를 쓰고, 키 값은 출력하지 않는다. 2026-10-28 runpodctl 1.14.15에서 실측: `Runpod config file not found` 안내 뒤에도 `pod "<pod>" stopped`가 나오고, 곧바로 SSH가 `Connection refused`로 바뀐다. 콘솔을 볼 수 있으면 목록에서 한 번 더 확인한다.
4. 끈 Pod와 시각, 남은 Network Volume(계속 과금)을 REPORT.md(레슨 하나짜리 요청이면 대화)에 적는다.
5. Chrome 확장도 Pod 안 `runpodctl`도 쓸 수 없으면 끄지 못했다고 바로 보고한다(Pod 이름, 켜져 있는 Pod 수와 시간당 요금, 사용자가 직접 끄는 경로: Pods → Pod 이름 → Stop).
