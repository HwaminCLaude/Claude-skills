# 레슨 제작 가이드 (제작 에이전트용 계약서) — {{COURSE_TITLE}}

이 과정은 `docs/DECISIONS.md`의 대상(기본: **비개발자**)이 RunPod 화면을 보며 따라 하는 실습 교재다. 레슨 하나 = 목표 하나.
모든 레슨은 **실제 Pod에서 실행한 결과**로만 만든다. 기준 예시(파일럿)는
`chapters/<chapter-NN>/<lesson-MM-slug>/`다(파일럿을 끝내면 이 경로를 고친다). 형식이 헷갈리면 그 README와 playbook.yaml을 그대로 따라 한다.
파일럿이 생기기 전에는 형식 참고로 `{{EXAMPLE_LESSON}}`(스킬에 든 예시 레슨 — 글 파일만, 그림 없음)을 본다.

> `<…>` 자리는 이번 Pod에서 실측한 값으로 채운다(만든 날: {{DATE}}). 채우기 전에는 병렬 제작을 시작하지 않는다.

> **사용자 결정은 `docs/DECISIONS.md`가 우선한다**(시작 인터뷰 기록): 범위, 산출물(해설 대본을 넣는지, 영상을 만들 레슨), 대상 학습자, Pod·예산, 끝난 뒤 Pod 처리, 내용 검토 깊이, 공개 계획. 이 계약서의 기본값과 다르면 DECISIONS를 따르고, 헷갈리면 메인 세션에 묻는다.

## 1. 환경 계약 (<YYYY-MM-DD> 실측)

| 항목 | 값 |
|---|---|
| Pod A | `<POD_A_NAME>` — <GPU 이름> <VRAM>GB, 이미지 `<템플릿 이미지 태그>` |
| Pod B | `<POD_B_NAME>` — <같은 사양 / 쓰지 않음> |
| 공유 저장소 | <두 Pod가 같은 Network Volume을 `/workspace`로 공유(<크기>GB) / Pod마다 따로> |
| 학습자 작업 폴더 | `{{POD_ROOT}}/chNN/` (예: `ch03`). 파일 이름은 `lMM_설명.ipynb` / `lMM_설명.py`(MM = 레슨 번호) |
| venv | `{{VENVS}}/train` — 고정 버전은 `environment/setup.sh`, 실제 버전은 lock(`{{LOCKDIR}}/train.lock`): <주요 패키지 실측 버전>. 노트북 커널 **`{{KERNEL_LABEL}}`**(kernelspec `{{KERNEL}}`) |
|  | `{{VENVS}}/serve` — <서빙 패키지 실측 버전, 서빙 명령 경로 예: `{{VENVS}}/serve/bin/vllm` / 쓰지 않음> |
| venv 재생성 | Pod 재시작 등으로 venv가 없으면 `bash /root/setup.sh` (약 <N>분). 학습자용 원본은 `environment/setup.sh` |
| 학습자 환경 | <학습자가 venv·커널을 만드는 레슨(링크)과 그 전 레슨이 쓰는 환경(예: 시스템 Python `Python 3 (ipykernel)`)> |
| 모델 캐시 | `HF_HOME=/workspace/.cache/huggingface` — 미리 받아 둔 것: <모델 ID 목록>. <N>GB 넘는 모델은 받지 않는다. 토큰이 필요한 gated 모델은 쓰지 않는다(사용자가 승인한 것만) |
| 고정값 | <과정 전체에서 바꾸지 않는 값> |

LLM 과정 기본값(2026-10-28: A40 48GB, 이미지 `runpod/pytorch:1.4.1-cu1281-torch280-ubuntu2404`, 버전은 `environment/setup.sh`의 고정값)은 **참고용**이다. 표에는 이번 Pod에서 `setup.sh` 출력·lock 파일·`nvidia-smi`로 다시 확인한 값만 쓴다(같으면 그대로, 다르면 고친다 — 고정 버전이 같아도 `--torch-backend=auto`가 고르는 CUDA 변형은 Pod에서 확인한다). LLM 과정의 모델·고정값: `Qwen/Qwen3-0.6B`, `Qwen/Qwen3-4B-Instruct-2507`(10GB 넘는 모델은 받지 않음), LoRA r=16, `--max-lora-rank 16`, `--max-model-len 8192`, `--served-model-name qwen`, `--tool-call-parser hermes`, `--enable-auto-tool-choice`, reasoning parser 없음.

### SSH로 Pod 쓰기 (이 PC에서)
- 셸 명령은 저장소 루트에서 실행한다(셸 호출마다 폴더가 처음으로 돌아갈 수 있다): `cd "{{REPO_GITBASH}}" && tools/pod.sh A '명령'`. 여러 줄 스크립트는 `tools/pod.sh A < script.sh`. Pod B는 `.env.local`에 `POD_B_*`가 있을 때만.
- 파일 가져오기: `tools/pod_get.sh A {{POD_ROOT}}/ch03/l01_x.ipynb chapters/chapter-03/lesson-01-x/notebooks/`
- 파일 올리기: `tools/pod.sh A 'mkdir -p /root/dev-c03l01 && cat > /root/dev-c03l01/l01_x.py' < 로컬파일` — 개발·시험 실행은 컨테이너 디스크의 dev 폴더에서 한다(아래 '동시 작업 규칙').
- SSH 비대화형 셸은 `/etc/rp_environment`를 읽지 않는다. HF 캐시를 쓰는 명령 앞에는 `source /etc/rp_environment >/dev/null 2>&1;`를 붙인다(값은 출력하지 말 것).
- 파이썬: `{{VENVS}}/train/bin/python file.py`. 학습자 README에는 학습자가 실제로 쓰는 환경대로 쓴다(`source {{VENVS}}/train/bin/activate` 후 `python file.py`, 또는 시스템 `python`). 제작 실행도 그 환경·커널로 한다.

### 노트북 실행 (실제 출력이 담긴 .ipynb 만들기)
1. 로컬에서 `nbformat`으로 .ipynb를 만든다(셀마다 짧고, 마크다운 설명 셀 포함). 출력이 없어야 하는 셀은 셀 메타데이터 태그 `no-output`(코드에 주석을 남기지 않는다).
2. Pod에 올린 뒤 실행: `cd <폴더> && source /etc/rp_environment >/dev/null 2>&1; jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name={{KERNEL}} --ExecutePreprocessor.timeout=1800 lMM_x.ipynb`
3. 실행된 노트북을 레슨 `notebooks/`로 가져온다. 실행 번호는 1..n이어야 한다(검사기가 확인). README의 숫자·그림은 화면에 찍힌 바로 그 저장본 하나에서만 가져온다(두 실행의 숫자를 섞지 않는다).

### GPU·포트 자원 분배 (동시에 여러 레인이 같은 GPU를 쓴다)
| 레인 | Pod | 챕터(같은 챕터는 한 레인에만) | GPU 규칙 | 포트(같은 Pod 안에서 고유) |
|---|---|---|---|---|
| 1 | A | <챕터 순서> | <예: 모델 로딩 최대 1개(4B 이하), 끝나면 커널 종료> | <— / 서버 포트> |
| 2 | A | <챕터 순서> | <예: 학습은 `flock /root/gpu-train.lock` 안에서, 벤치마크는 레인 1이 끝난 뒤 vLLM 상한 0.5> | <예: vLLM 8000> |
| 3 | B | <챕터 순서> | <예: vLLM `--gpu-memory-utilization 0.45` 이하> | <예: vLLM 8000, FastAPI 8002 — nginx가 쓰는 3001·7270·7861·8001·8081·9091은 피한다> |
| 4 | B | <챕터 순서> | <예: vLLM `--gpu-memory-utilization 0.35` 이하> | <예: vLLM 8010, FastAPI 8011> |
| 5 | B(GPU 거의 안 씀) | <GPU가 필요 없는 챕터> | GPU 거의 안 씀 | — |

### 비밀값 규칙 (어기면 레슨 불합격)
- 원칙: 환경변수 값, 프로세스 명령줄(특히 jupyter), `/jupyter.log`, `/etc/rp_environment` 내용을 출력·캡처하지 않는다. 금지 예: `env`, `printenv`, `set`, `export -p`, `declare -x`, `cat /proc/*/environ`, `cat`·`tail /jupyter.log`, `jupyter server list`, `ps aux`, `pgrep -af jupyter`. 프로세스는 `ps -eo pid,etime,comm`이나 `pgrep -af "vllm serve" | cut -c1-120`. 변수 이름만 세야 하면 `compgen -e | grep -ciE "key|token|pass"`만 쓴다(이름만 나오는 bash 내장 명령).
- vLLM API 키가 필요하면 환경변수 `VLLM_API_KEY`로만 준다(명령줄 `--api-key` 금지). Hugging Face 토큰을 쓰지 않는다.
- IP·포트·Pod ID·토큰·키·SSH 지문을 README·로그·노트북·결과(issues)에 남기지 않는다. 도구 오류 문구를 옮길 때는 `token=` 뒤를 지운다. `tools/check_lesson.py`가 스캔한다.

### 동시 작업 규칙
- Pod에서는 자기 레슨이 만든 파일만 만들고 지운다(`{{POD_ROOT}}/chNN/`의 `lMM_*`, `logs/lMM_*`). 다른 레슨·다른 챕터의 파일은 건드리지 않는다.
- 개발·시험 실행은 `/root/dev-<레슨ID 소문자>/`, 보충 촬영은 `/root/scratch-<레슨ID 소문자>/`(컨테이너 디스크 — 다른 Pod와 학습자 화면의 `/workspace`에 보이지 않는다)에서 하고 끝나면 둘 다 지운다. 촬영 전에는 챕터 폴더를 학습자 시작 상태로 맞춘다(학습자가 아직 만들지 않은 파일이 화면에 보이지 않게).
- 오래 도는 서버·학습은 Pod 안에서 `tmux new -d -s <레슨ID>-이름 '...'` 또는 `nohup ... > logs/lMM_x.log 2>&1 &`로 띄우고, 끝나면 **반드시** 멈춘다(`tmux kill-session -t <내 세션>`, `pkill -f "vllm serve .*--port <내 포트>"`). 다른 레인의 프로세스는 끄지 않는다.
- 노트북 커널은 `jlab`의 `shutdown_kernels()`(자기가 연 노트북 커널만), Terminal은 `shutdown_terminals()`(자기가 연 것만)로 닫는다.
- JupyterLab에서 `File` → `Shut Down`을 누르지 않는다(서버 전체가 꺼진다). 서버 설정을 바꾸는 체크박스(*Do not ask me again.*, *Do not ask for rename on first save.*)와 `Settings` 메뉴를 건드리지 않는다. 다른 레슨의 폴더가 화면에 보이면 README의 '달라도 되는 것'에 적는다.
- Pod 상태를 바꾸는 행동(Deploy, Start·Stop, Restart Pod, Edit Pod, Terminate)은 하지 않는다. 그런 STEP은 공식 문서 문장으로 쓰고 '실행하지 않음(이유)'.
- `jlab.py`의 로컬 포트와 workspace 이름은 레슨마다 다르게 받는다(제작 워크플로가 정해 준다).
- 브라우저 확장(claude-in-chrome)은 쓰지 않는다. RunPod 콘솔 화면은 메인 세션이 미리 찍어 둔 `_raw/` 원본만 쓰고, 없으면 그 STEP을 공식 문서 기준 글로 쓰고 playbook `not_captured`에 이유를 적는다.
- 가이드에 없거나 '미확인'이던 UI 라벨·동작을 실측했으면 결과의 `facts_observed`로 돌려준다(공유 문서·스킬 파일을 직접 고치지 않는다).

## 2. 증거 수집

| 종류 | 방법 | 저장 위치(레슨 폴더 기준) |
|---|---|---|
| 명령 실행 로그 | SSH로 실행, `2>&1 \| tee`로 Pod의 `chNN/logs/lMM_*.log`에 남기고 가져온다. 학습자와 같은 폴더에서 실행한 것만 증거다(dev 폴더 실행은 개발용). 파일 첫 줄 `# source: ssh-run (Pod A, <날짜>)` | `logs/` |
| Terminal 화면의 글자 | 같은 명령을 SSH로 다시 실행한 로그, 첫 줄 `# source: ssh-rerun (Pod A, <날짜>, 화면 STEP N)`. 상태를 바꾸는 명령(mkdir·mv·rm·다운로드·학습·서버)은 다시 실행하지 않는다 — 화면 판독으로 대신하고 README 08절에 적는다 | `logs/*.ssh-rerun.log` |
| 노트북 출력 | 위의 nbconvert 실행 결과 | `notebooks/` |
| 화면 | `tools/jlab.py`(헤드리스 Chromium, SSH 터널, 1600×900): 파일 목록, 노트북 출력, Terminal 명령 결과, 학습자처럼 새 파일에 붙여 넣고 저장하는 모습(`new_file_paste`) 등 **각 STEP의 행동 직후 화면**. 공개 웹은 `tools/webshot.py` | `_raw/` → 마스킹 후 `screenshots/` |
| 클릭 위치 | 마스킹본 위에 `tools/annotate.py`로 번호 표시(선택) | `screenshots/*-click-*.png` |
| 촬영 기록 | 한 줄에 하나: `{"file": "<_raw 안의 파일 이름>", "step": "S05", "kind": "current/click/result/execution/verification", "note": "…", "source": "real-capture", "tool": "tools/jlab.py 1600x900", "pod": "A", "copied_at": "<ISO 시각>"}` | `_raw/capture-log.jsonl` |

`jlab.py` 사용 예(이 PC의 `python`으로 실행):
```python
import sys; sys.path.insert(0, r"{{REPO_PATH}}\tools")
from jlab import JLab
with JLab("A", port=<레슨별 포트>, workspace="c03l03") as j:
    j.open("{{POD_ROOT_REL}}/ch03/l03_tokenizer.ipynb")   # 경로는 JupyterLab 루트(/) 기준, 앞에 / 없음
    j.shot(r"<레슨>\_raw\s05-notebook-top.png")
    j.scroll_to_text("토큰 개수")             # 보여 줄 출력 근처로
    j.shot(r"<레슨>\_raw\s06-token-count.png")
    j.new_file_paste(open(r"<레슨>\code\l03_count.py", encoding="utf-8").read(), "l03_count",
                     folder="{{POD_ROOT_REL}}/ch03",
                     shots={"pasted": r"<레슨>\_raw\s07a-code-pasted.png", "rename": r"<레슨>\_raw\s07b-rename-dialog.png",
                            "saved": r"<레슨>\_raw\s07c-saved.png"})
    j.terminal(["cd {{POD_ROOT}}/ch03", "ls -la"], wait=2)
    j.shot(r"<레슨>\_raw\s08-terminal.png")
    j.shutdown_terminals()
    j.shutdown_kernels()
```
- 노트북은 nbconvert로 이미 실행해 두었으므로 화면 촬영 때 다시 돌릴 필요는 없다(출력이 저장되어 있음). 필요하면 `j.run_all()`.
- Terminal 화면을 찍을 때 화면에 비밀값이 나오는 명령은 치지 않는다. 컨테이너 호스트 이름(`root@<컨테이너>`)은 가리지 않아도 된다.
- RunPod 콘솔 화면(로그인 필요)은 헤드리스로 찍을 수 없다. 메인 세션이 로그인된 Chrome 확장으로 미리 찍어 둔 `_raw/` 원본을 쓴다(제작 에이전트는 브라우저 확장을 쓰지 않는다).
- `_raw/redact-spec.json`에 공개할 원본을 모두 적고(가릴 것이 없으면 `"boxes": []`) `python tools/redact.py <레슨폴더>` → `screenshots/`. 명세에 없는 원본은 공개되지 않는다.

## 3. 레슨 폴더 구성
`chapters/chapter-NN/lesson-MM-slug/`
- `README.md` — 아래 4절 형식
- `playbook.yaml` — 파일럿과 같은 스키마(lesson 머리 + steps[]: id, part, screen, env, cwd, action, ui_target, file, command, code_file, change, save, run, result, success_check, screenshots[], not_captured, logs[], concept, readme_anchor, scene_id, troubleshooting[] + troubleshooting 사전). 그림을 찍지 못한 STEP은 `screenshots: []`와 `not_captured: "<이유>"`, README의 그 STEP에 같은 이유 문구를 그대로 쓴다
- `troubleshooting.md`
- 영상은 사용자가 요청한 레슨만 따로 만든다. 요청 전에는 `storyboard.md`, `narration.md`를 만들지 않는다.
- `code/`, `notebooks/`, `scripts/`, `logs/`, `expected-output/`(머리에 `# log: logs/...`, `# after: ...`, 그 아래 정규식 줄), `screenshots/`, `_raw/`

## 4. README 형식
머리말 표(촬영일·GPU·이미지·주요 버전) → 01 목표 → 02 최종 결과 미리 보기(실제 이미지) → 03 준비물(앞 레슨에서 이어지는 파일·서버 상태, **학습자가 쓰는 파이썬 환경과 그것을 만드는 레슨**, 처음 하는 경우·다시 하는 경우) → 04 핵심 개념(쉬운 말 + 그림이 있으면 `shared/diagrams/`) → 05 작업 화면·파일 구조 → 06 단계별 따라 하기(각 STEP 앵커 `<a id="step-N"></a>`, 현재 화면 / 행동 / 코드 / 저장 / 실행 / 결과 / 성공 확인, **이미지는 그 행동 바로 아래**) → 07 전체 완성 코드 → 08 실행 결과(로그 링크) → 09 코드·명령 해설(표) → 10 오류 해결(실제로 겪은 것 우선) → 11 응용 실습 → 12 완료 체크리스트 → 13 다음 강의 준비(무엇을 남기고 무엇을 끄는지, Stop 뒤 다시 만들 환경) → 14 공식 참고 자료(직접 열어 제목을 확인한 URL만).

코딩 단계는 반드시 이 블록을 쓴다: 파일 위치 / 현재 화면 / 수행할 행동 / 파일 이름 / 코드 입력 / 저장 / 실행 환경 / 실행 명령어 / 결과 확인 / 스크린샷(붙여 넣은 모습 → 이름 창 → 실행 결과, `new_file_paste`로 찍는다).

### 🎙️ 해설 대본 (기본 필수 — `docs/DECISIONS.md`의 `narration: false`면 넣지 않는다)
영상은 만들지 않아도, 나중에 영상·강의에 그대로 쓸 수 있는 해설을 README에 붙인다. 형식(접는 블록):

```markdown
<details><summary>🎙️ 해설 대본 — STEP 3</summary>

> (말하듯 쓴 문장 3~6개)

</details>
```
- **위치**: 머리말 표 바로 아래에 `🎙️ 해설 대본 — 시작`(이번 강의에서 무엇을 하고 왜 중요한지, 끝나면 무엇을 할 수 있는지), **모든 STEP 구역의 끝**(그 STEP의 이미지·성공 확인 다음)에 `🎙️ 해설 대본 — STEP N`, 12절 체크리스트 앞에 `🎙️ 해설 대본 — 마무리`(한 일 요약, 핵심 개념 2~3개, 다음 강의 예고).
- **내용 순서**: 지금 화면이 어디인지 → 어디를 누르거나 무엇을 입력하는지 → 화면에 무엇이 나타나는지(실제 결과 숫자 그대로) → 그 결과가 무슨 뜻인지(개념을 쉬운 비유로) → 다음에 무엇을 하는지.
- **말투**: 강사가 화면을 가리키며 말하는 습니다체, 2~3문장마다 질문형('~일까요?', '~죠?')을 섞는다. 화면의 영어 라벨과 명령은 그대로 쓰고 필요하면 읽는 법을 괄호로(예: `nvidia-smi`(엔비디아 에스엠아이)). 비밀값·IP는 말하지 않는다.
- 검사기(`check_lesson.py`)가 시작·마무리 블록과 모든 STEP 구역의 해설 블록을 확인한다(`narration: false`면 검사기도 이 항목을 건너뛴다).

문체: 한국어, 기술 용어는 영어 병기, 쉬운 말. UI 라벨은 화면 그대로(영어). 숫자는 실제 실행 결과만 쓴다(추정치는 '추정'이라고 밝힌다).

## 5. 품질 게이트
- `python tools/check_lesson.py <레슨폴더>` → 모두 PASS(그림이 없으면 README에서 링크하지 말 것). 검사기를 고쳐서 통과시키지 않는다.
- README를 처음부터 끝까지 초보자 입장에서 다시 읽고, 빠진 클릭·경로·명령·성공 기준이 없는지 확인한다.
- 실행이 실패한 단계는 원인을 고쳐 다시 실행한다. 끝내 실행 못 한 내용은 README에 '실행하지 않음(이유)'으로 분명히 적는다(가짜 결과 금지).
- 끝나면 Pod에서 자기가 띄운 서버·커널·Terminal·tmux와 dev·scratch 폴더를 모두 정리한다.
