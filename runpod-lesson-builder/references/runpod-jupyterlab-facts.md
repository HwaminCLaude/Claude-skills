# RunPod·JupyterLab 확인된 사실 (검증일 2026-10-28)

README에 UI 라벨·동작을 쓰기 전에 이 표에서 찾는다. 여기에 없거나 상태가 `조사`·`로컬`·`미확인`이면 Pod에서 직접 확인하고(Phase 0 실측 체크리스트), 확인한 결과는 과정 저장소의 `environment/versions.md`에 적는다 — 메인 세션이 적고, 레슨 에이전트는 결과의 `facts_observed`로 돌려준다(공유 문서를 동시에 고치지 않게). 이 스킬 파일은 사용자가 요청할 때만 고친다. RunPod 콘솔은 자주 바뀌므로 새 과정을 시작할 때마다 다시 본다.

상태 표기: **실측** = 2026-10-28 실제 Pod·콘솔에서 수행·촬영 / **문서** = 공식 문서 문장(화면 미촬영) / **조사** = 사전 조사 결과, Pod 실측 아님 / **로컬** = 이 PC의 JupyterLab 4.5.1에서 `jlab.py`를 시험하며 확인(RunPod의 4.6.4에서는 미확인) / **미확인** = 아직 아무도 확인 안 함.

근거 약어(모두 이 스킬 밖의 출처 표기용 — 없어도 된다): 작성자의 LLM 과정 저장소(비공개, 2026-10-28 제작)의 `PF` = `environment/preflight-report.md`, `VER` = `environment/versions.md`, `PILOT` = 파일럿 레슨 C02-L02 README(STEP 번호, 글 파일 사본은 `assets/example-lesson/`), `T` = 파일럿 `troubleshooting.md`, `D0x` = C02-L01 `_raw/capture-log.jsonl`(Deploy 화면 촬영 기록), `RUN` = `verification/stackcheck-2026-10-28/run.log`, `CUR` = `curriculum.md`. `PLAN` = 작성자의 승인 계획서(비공개, PHASE 0 결과·파일럿 설계), '전 챕터 워크플로' = 그 과정의 병렬 제작 워크플로(레슨 명세 메모, 틀: `assets/lesson-workflow-template.js`).

## 1. 촬영 환경 기준값

| 사실 | 근거 | 상태 |
|---|---|---|
| 템플릿 이미지 `runpod/pytorch:1.4.1-cu1281-torch280-ubuntu2404`(콘솔 표시 "CUDA 12.8.1 · Ubuntu 24.04 · 1.4.1-2.8.0") | VER | 실측 |
| 그날 콘솔의 기본 PyTorch 템플릿은 `torch291`(PyTorch 2.9.1) — 다른 템플릿이면 버전 숫자만 다르게 보인다고 README 머리말에 적는다 | PILOT 머리말 | 실측 |
| Ubuntu 24.04.5, Python 3.12.3(`python`=`python3`=`/usr/bin/python3.12`, `which python` → `/usr/local/bin/python`), PyTorch 2.8.0+cu128, torchvision 0.23.0 | VER, PILOT STEP 11 | 실측 |
| JupyterLab 4.6.4 (jupyter_server 2.21.1, ipykernel 7.4.0, notebook 7.6.3), pip 26.2.1, uv 0.13.1, git 2.43.0, tmux 3.4, runpodctl 1.14.15 | VER | 실측 |
| NVIDIA A40 46068MiB, Driver 595.91.07, `nvidia-smi`의 CUDA Version 13.2(드라이버가 지원하는 최대 CUDA), compute capability 8.6(Ampere: bf16 가능, FP8 연산 불가) | PF, PILOT STEP 9 | 실측 |
| 환경변수 중 값 공개 가능: `HF_HOME=/workspace/.cache/huggingface/`, `PIP_CACHE_DIR`·`UV_CACHE_DIR`도 `/workspace/.cache/…`, `PIP_BREAK_SYSTEM_PACKAGES=1`, `RUNPOD_CPU_COUNT=9`, `RUNPOD_MEM_GB=50` | VER | 실측 |
| 같은 환경에 `RUNPOD_API_KEY`, `JUPYTER_PASSWORD`가 있고 `/etc/rp_environment`는 누구나 읽을 수 있으며 `.bashrc`가 source한다 | PF 보안 관찰, PLAN | 실측 |
| SSH 비대화형 셸은 `/etc/rp_environment`를 읽지 않는다(HF_HOME 등이 비어 있음) | 과정 LESSON_GUIDE | 실측 |
| 할당은 vCPU 9 / RAM 50GB인데 `nproc`=96, `free`=503Gi(호스트 값이 보임) | PLAN 1절 | 실측 |
| Pod 안 포트: 8888 jupyter, 22 sshd, nginx 8001→8000·8081→8080·3001→3000. nginx가 듣는 포트 전체는 3001·7270·7861·8001·8081·9091(2026-10-28 `ss -ltnp` 실측) — 여기에 서버를 띄우면 Address already in use | PLAN 1절, `ss -ltnp` | 실측 |
| Pod 시계는 UTC → 화면 시각이 KST보다 9시간 늦고 날짜가 하루 전으로 보일 수 있다 | PILOT 머리말 | 실측 |

## 2. RunPod 콘솔 — Pod 만들기(Deploy) 흐름

| 사실 | 근거 | 상태 |
|---|---|---|
| `+ Deploy`를 누르면 *Deploy a Pod* 화면: **Workload**(템플릿 `PyTorch 2.8.0`, CUDA 드롭다운, `Set overrides`, Pod name), **Region**, **Compute**(GPU 카드에 시간당 가격 — 촬영 당시 H100 SXM $3.99, A40 $0.59), 오른쪽 **Summary**(`Deploy Pod` 버튼, 선택 전에는 비활성) | D01 | 실측(버튼은 누르지 않음) |
| Compute 구역: GPU/CPU 탭, 검색, 볼륨 필터, Filter, vRAM 정렬, Available/Recent/All | D02 | 실측 |
| Storage 구역: Container disk 50GB(Stop 시 삭제), Persistent storage에 Network volume → `/workspace` | D03 | 실측 |
| Credentials → **SSH Public Keys** 탭: `Add SSH key` 버튼, 등록된 키 이름·지문(Fingerprint)·생성일(지문은 마스킹) | D04 | 실측 |
| 공개키를 등록한 뒤 이미 켜져 있는 Pod에도 반영되는지 | 사전 조사 질문(답 없음) | 미확인 — 키는 Pod를 만들기 전에 등록 |
| `Set overrides`에서 HTTP 포트 8888(기본)에 8000·8001을 미리 더해 두기를 권장(나중에 `Edit Pod`로 포트를 더하면 컨테이너가 초기화됨) | PLAN 6.1, 전 챕터 워크플로 C02-L01 메모 | 조사 |
| 크레딧 충전·Low balance alert 화면, 최소 1시간 요금 | 전 챕터 워크플로 C02-L01 메모 | 문서(화면 미촬영) |
| Spot/Interruptible은 조사 시점 공식 문서에서 빠져 있었다 → 가르치지 않거나 콘솔에서 확인한 뒤 다룬다 | PLAN 10절 | 조사 |

## 3. Pods 목록과 상세 패널

| 사실 | 근거 | 상태 |
|---|---|---|
| 왼쪽 메뉴 **Pods** → 목록의 **Name** 열 글자를 누르면 오른쪽에 상세 패널 | PILOT STEP 1 | 실측 |
| 이름 앞 **초록 점** = Running(요금 발생 중). **Compute type** 열에 GPU 종류(예: `A40 x1`) | PILOT STEP 1 | 실측 |
| **Cost** 열에 Pod마다 시간당 요금(촬영 당시 A40 Secure Cloud `$0.60/hr` = GPU 0.59 + 컨테이너 디스크 50GB 0.007). 켜 둔 Pod마다 따로 과금 | PF, PLAN 1절, PILOT STEP 1 | 실측 |
| 상세 패널 탭: Connect / Details / Volumes / Telemetry / Logs / Template | PLAN 1절 | 실측(조회만) |
| 상세 패널 위쪽 빨간 **Stop** 버튼. 공식 문서: *"Click the Stop button (square icon) and confirm."* Stop 확인 창과 Stop 뒤 화면은 촬영하지 않았다 | PILOT STEP 26 | 버튼 위치 실측 / 확인 창 문서 |
| Pod ⋮ 메뉴 → **Restart Pod**(JupyterLab 서버를 꺼 버렸을 때 복구) | T12 | 실측(메뉴 라벨) |
| 멈춘(Stop) Pod를 다시 켜는 버튼(**Start**로 예상)과 확인 창, 켠 뒤 IP·포트가 바뀌는지 | — | 미확인 — 화면 그대로 따르고 Connect 값을 다시 읽는다(`workflow.md` 0-5) |
| **Terminate**(휴지통 아이콘) = Pod 삭제, 되돌릴 수 없음 | PILOT STEP 26 | 문서 |
| 콘솔 화면에 잔액, 아바타 이름, Pod ID, IP가 보인다 → 공개 전 마스킹. 탭 캡처 기준 오른쪽 위 잔액·아바타 영역 | PF, D04 | 실측 |

## 4. Connect 패널

| 사실 | 근거 | 상태 |
|---|---|---|
| **HTTP services**에 `Port 8888 → Jupyter Lab`, 줄 오른쪽 끝 초록 **Ready** | PILOT STEP 2 | 실측 |
| **Jupyter Lab** 링크는 `?token=` 쿼리가 붙은 프록시 주소(`<podid>-8888.proxy.runpod.net`)를 새 탭으로 열고, 열린 뒤 `/lab`으로 바뀐다(자동 로그인) | PLAN 1절·4.2, PF | 실측 |
| 그래서 주소창, 링크에 마우스를 올렸을 때 아래에 뜨는 주소, 브라우저 기록은 촬영 금지. 탭 캡처·헤드리스 캡처는 주소창을 포함하지 않는다 | PF 보안 관찰, PLAN 4.2 | 실측 |
| 토큰 없이 주소로 들어가면 *Token authentication is enabled* 화면 → Connect 패널의 링크로 다시 연다 | T03 | 링크의 토큰은 실측 / 화면 문구는 문서 |
| SSH 방식 두 가지: 프록시 SSH(ssh.runpod.io, SCP 불가)와 **SSH over exposed TCP**(공인 IP + 포트, SCP 가능). 그 밖에 Web terminal(꺼짐 — 토글하지 않는다), Direct TCP ports | PLAN 1절 | 실측(조회) |
| exposed TCP + `~/.ssh/id_ed25519` 키 인증으로 BatchMode 접속 성공 | PF, PLAN 1절 | 실측 |

## 5. 저장 공간과 수명

| 사실 | 근거 | 상태 |
|---|---|---|
| `/`(컨테이너 디스크, overlay 50G)는 Stop 때 지워진다. 시스템에 `pip install`한 것도 사라진다 | PLAN 1절·6.1, PILOT 13절 | 문서 + 실측(디스크 구성) |
| `/workspace`는 Stop해도 남는다(파일럿은 Network Volume 50GB) | PILOT 4-1·13절 | 문서 + 실측 |
| 같은 Network Volume을 붙인 두 Pod는 `/workspace`를 **공유**한다 → 한 Pod에서 만든 폴더가 다른 Pod에서도 보인다 | PF 저장소 | 실측 |
| Stop: GPU 시간 요금이 멈추고 `/workspace`는 남으며 저장소 요금은 계속. 다시 Start할 때 같은 GPU를 못 받을 수 있다 | PILOT 13절 | 문서 |
| Terminate: Network Volume이 아닌 저장소 파일은 모두 사라진다. Network Volume은 따로 남아 계속 과금되므로 필요 없으면 왼쪽 메뉴 **Storage**에서 지운다 | PILOT 13절 | 문서 |
| Network Volume 요금 참고: 150GB 증설 시 $0.07/GB/월 → 약 $10.5/월 | PLAN 6.1 | 조사 |
| Stop 뒤 kernelspec(`~/.local/share/jupyter`)이 남는지, `Restart Pod`가 컨테이너 디스크를 지우는지 | CUR | 미확인 — 확인은 승인 뒤 아무도 쓰지 않는 Pod에서만(`workflow.md` 0-6) |
| kernelspec·vLLM 캐시를 `/workspace`로 보내는 설정(`JUPYTER_DATA_DIR`, `VLLM_CACHE_ROOT`, `XDG_CACHE_HOME`)이 동작하는지 | CUR | 미확인 |

## 6. JupyterLab 4.6.4 화면

| 사실 | 근거 | 상태 |
|---|---|---|
| 메뉴 바: `File` `Edit` `View` `Run` `Kernel` `Tabs` `Settings` `Help` | PILOT STEP 4 | 실측 |
| `File` 메뉴: New ▸ · New Launcher · Open from Path… · Close Tab · Save · Save As… · Rename… · Download · Log Out · Shut Down | PLAN 5절 | 실측 |
| `File` → `Shut Down`은 JupyterLab **서버 전체**를 끈다(커널 하나가 아님) → 눌렀으면 RunPod 콘솔 Pod ⋮ → Restart Pod. 자동화에서도 절대 누르지 않는다 | PLAN 5절, T12 | 실측(라벨) |
| 노트북을 **열지 않은** 상태의 `Kernel` 메뉴: Interrupt Kernel · Restart Kernel… · Restart Kernel and Clear… · Restart Kernel and Run All · Shut Down Kernel · Shut Down All Kernels… · Change Kernel… | PLAN 5절(라벨이 두 가지로 보여 리허설에서 확정) | 실측 |
| 노트북을 **연** 상태의 `Kernel` 메뉴에서 쓰는 라벨: **Restart Kernel and Run All Cells…**, **Shut Down Kernel**. 확인 창 *Restart Kernel?* → **Restart** 버튼, 체크박스 *Do not ask me again.* | PILOT STEP 23·24 | 실측 |
| Restart and Run All 동안 셀 번호가 모두 `[*]`, 출력이 지워지고 상태 표시줄 `Busy` → 위에서부터 `[1]`…로 채워짐(4셀 약 8초). 도중에 상태 표시줄이 잠깐 `Idle`로 보일 수 있어 `[*]`가 모두 사라졌는지 함께 본다 | PILOT STEP 23 | 실측 |
| 새 파일을 처음 `Ctrl+S`하면 *Rename file* 대화상자: 확장자를 뺀 `untitled` 부분만 선택됨, **Rename and Save** / Cancel, 체크박스 *Do not ask for rename on first save.*(켜면 다음부터 창이 안 뜸). 노트북도 같은 창 | PILOT STEP 13·17 | 실측 |
| 그 이름 창에 이미 있는 파일 이름을 넣고 **Rename and Save**를 누르면 창은 닫히고 새 파일은 `untitled.py`로 남는다(오류 창 없음) | `jlab.py` 시험 | 로컬 |
| 편집기(CodeMirror)에 포커스가 있으면 `Ctrl+Shift+L`(New Launcher)을 편집기가 가져가 Launcher가 새로 생기지 않는다 → `File` 메뉴의 **New Launcher**는 된다 | `jlab.py` 시험 | 로컬 |
| Launcher: **Notebook** 구역 `Python 3 (ipykernel)`, 바로 아래 **Console** 구역에 같은 아이콘·같은 이름(누르면 콘솔), **Other** 구역: Terminal, Text File, Markdown File, Python File, Show Contextual Help | PLAN 1절, PILOT STEP 16 | 실측 |
| venv를 커널로 등록하면(`ipykernel install --user --name train --display-name "Python (train)"`) 노트북 커널 이름이 `Python (train)`, nbconvert에서는 `--ExecutePreprocessor.kernel_name=train` | 과정 setup.sh·LESSON_GUIDE | 등록은 실측 / Launcher 표시 화면은 미촬영 |
| File Browser 툴바: New Launcher(+), New Folder, Upload Files, Refresh, Toggle File Filter. 경로 표시줄 `/ workspace /`. root_dir=`/`, preferred_dir=`/workspace` | PLAN 1절, PILOT STEP 4 | 실측 |
| New Folder → 목록 맨 위 `Untitled Folder`, 이름이 파랗게 선택된 입력 칸 → 바로 이름 입력 + Enter. 먼저 다른 곳을 누르면 `Untitled Folder`로 굳는다 | PILOT STEP 5 | 실측 |
| 오른쪽 클릭 메뉴: **Rename** (F2), 바로 아래 **Delete**. RunPod JupyterLab의 삭제는 휴지통 없이 영구 삭제(`delete_to_trash=False`) | PILOT STEP 5, T 보안 주의 | 실측 |
| 왼쪽 끝 세로 아이콘 줄: 맨 위 폴더 아이콘 = File Browser, 위에서 두 번째(동그라미 안 네모) = **Running Terminals and Kernels** | PILOT STEP 4 | 실측 |
| 상태 표시줄 `Python 3 (ipykernel) \| Idle`(대기) / `Busy`(실행 중) / `Connecting`(커널 켜지는 중). 탭 이름 옆 ● = 저장 안 됨, File Browser 파일 이름 앞 ● = 커널 실행 중 | PILOT STEP 13·16·18 | 실측 |
| 첫 화면 오른쪽 아래 *"Would you like to get notified about official Jupyter news?"* → **No** | PILOT STEP 4 | 실측 |
| 노트북 커널 `Python 3 (ipykernel)` = `/usr/local/bin/python` = Terminal의 `which python` | PF, PILOT STEP 22 | 실측 |
| 노트북 탭을 닫아도 커널은 살아서 VRAM을 잡는다. `Kernel` → `Shut Down Kernel` 뒤 `nvidia-smi`의 커널 프로세스가 사라짐(파일럿: 431MiB → 0MiB) | PILOT STEP 24 | 실측 |
| PC 클립보드 → 편집기·노트북 셀 `Ctrl+V` 붙여 넣기 정상, 들여쓰기 유지 | PF | 실측 |
| 이름이 정확히 `checkpoints`인 폴더는 JupyterLab에서 열리지 않음 → Pod 쪽 폴더명은 `ckpt/` | PLAN 5절 오류 해결 후보 | 조사 |
| 경로 표시줄의 두 아이콘: 즐겨찾기 폴더 아이콘은 `/workspace`, 일반 폴더 아이콘은 `/`로 이동 | PLAN 5절 오류 해결 후보 | 조사 |

## 7. Terminal

| 사실 | 근거 | 상태 |
|---|---|---|
| 처음 열면 RunPod 글자 그림, `groups: cannot find name for group ID 109`(무시해도 됨), 프롬프트 `root@<컨테이너 이름>:/#` | PILOT STEP 7 | 실측 |
| Launcher에서 연 Terminal은 그 Launcher의 폴더에서 시작한다(`pwd` → `/workspace/llm-course`)는데 프롬프트는 `:/#`로 보인다 → README는 항상 `cd <작업 폴더>`로 확실히 이동시킨다 | PILOT STEP 8 | 실측 |
| `File` → `New` → `Terminal`은 `/`에서 열린다 | PLAN 5절 오류 해결 후보 | 조사(파일럿에서 미확인) |
| Terminal 글자는 canvas로 그려져 자동으로 텍스트를 뽑을 수 없다(사람은 마우스로 선택·복사 가능) → 같은 명령을 SSH로 다시 실행해 로그를 남긴다 | PF, PILOT 08절 | 실측 |
| 앞 명령의 출력이 끝나기 전에 다음 명령을 치면 화면에 글자가 섞여 보인다(명령은 실행됨) | PILOT STEP 11 | 실측 |
| 한글 입력 상태로 치면 `bash: ㅔㅈㅇ: command not found`처럼 된다 | PILOT STEP 8, T14 | README 예방 안내(촬영 아님) |

## 8. 프록시·네트워크

| 사실 | 근거 | 상태 |
|---|---|---|
| RunPod 프록시를 거쳐 그려지므로 새 폴더·새 이름이 1~2초 늦게 반영된다(저장 직후 `Saving completed`인데 이름이 잠깐 `untitled.py`) | PILOT STEP 5·14·18 | 실측 |
| `Ready`인데 JupyterLab이 빈 화면이면 30~60초 뒤 `Ctrl+Shift+R` | T02(RunPod docs: jupyterlab-blank-page) | 문서 |
| 프록시를 거치는 HTTP 요청은 100초 안에 끝나야 한다 → 긴 응답은 스트리밍 | PLAN 6.1 | 조사(100초 넘는 스트리밍 유지 여부 미확인, CUR) |
| vLLM은 Pod 안에서 `localhost:<포트>`로 부르는 것이 기본. 밖으로 열려면 HTTP 포트 추가(`Edit Pod`, 컨테이너 초기화)와 API 키가 필요 → 사용자 승인 | PLAN 6.1·8절 | 조사 |
| vLLM `--api-key`는 `/v1`·`/v2`·`/inference`만 보호한다(`/metrics` 등은 노출) | PLAN 6.3 | 조사 |

## 9. 화면 캡처 수단

| 수단 | 사실 | 근거 | 상태 |
|---|---|---|---|
| Chrome 확장 탭 캡처(메인 세션) | 전체 탭은 1568px 폭 JPEG(축소본), 확대(zoom) 캡처는 원본 픽셀 PNG. 주소창은 찍히지 않는다. 최대화된 창은 크기 조절이 안 돼 1920×911 viewport 그대로 썼다. 확장이 여러 개 연결되면 세션마다 브라우저를 다시 골라야 한다 | PF | 실측 |
| `tools/jlab.py`(헤드리스 Chromium + SSH 터널) | 1600×900 PNG, 주소창 없음, 토큰은 메모리에만. JupyterLab만 가능(RunPod 콘솔은 로그인이 필요해 불가) | 과정 LESSON_GUIDE, 전 챕터 워크플로 | 실측 |
| `tools/webshot.py`(Playwright 헤드리스, 공개 웹) | 로그인 없는 공개 페이지(예: huggingface.co 모델 카드) 캡처 1600×900, 쿠키 배너는 `--click`/`--hide`, capture-log 줄 자동 추가 | 전 챕터 워크플로 C01 메모, 로컬 시험 페이지 | 조사(실제 사이트는 미확인) |
| Windows 화면 캡처 | 다른 프로그램 화면이 찍혀 **폐기** — 쓰지 않는다 | PF | 실측 |
