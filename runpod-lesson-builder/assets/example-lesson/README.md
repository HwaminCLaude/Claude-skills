# C02-L02 JupyterLab 접속하고 GPU 확인하기 — Terminal · Python 파일 · Notebook

> **이 문서만 보고 따라 할 수 있게 만든 실습 교재입니다.** 모든 화면은 실제 RunPod Pod에서 촬영했습니다.
>
> | 항목 | 촬영 당시 값 |
> |---|---|
> | 촬영일 | 2026-10-28 (KST) |
> | GPU | NVIDIA A40 1장 (Secure Cloud, CA-MTL-1) |
> | Pod 이미지(템플릿) | `runpod/pytorch:1.4.1-cu1281-torch280-ubuntu2404` |
> | JupyterLab | 4.6.4 |
> | Python / PyTorch | 3.12.3 / 2.8.0+cu128 |
> | 보충 촬영 | 같은 날, 같은 사양의 두 번째 Pod 안 임시 폴더(`/workspace/c02l02-fix`, 촬영 뒤 삭제). 해당 그림 아래에 따로 적었습니다(STEP 5·6·17·23) |
>
> 지금 RunPod의 기본 PyTorch 템플릿은 `torch291`(PyTorch 2.9.1)입니다. 그 템플릿으로 Pod를 만들었다면 **PyTorch 버전 숫자만** 다르게 보이고, 메뉴와 순서는 같습니다. GPU 종류가 다르면 GPU 이름과 메모리 숫자도 달라집니다.
>
> 🕘 **화면 속 날짜와 시각**: Pod의 시계는 UTC(세계 표준시) 기준이라 한국 시간보다 9시간 늦게 보입니다. 그래서 터미널 그림의 `Tue Oct 27 18:03:29 2026`은 한국 시간으로 10월 28일 오전 3시 3분입니다. 하루 전 날짜처럼 보여도 같은 날 촬영한 화면입니다.
>
> 스크린샷의 빨간 테두리 모자이크는 계정 잔액, Pod ID, 접속 주소 같은 개인 정보를 가린 것입니다. 주황색 번호 표시는 설명을 위해 덧그린 '클릭 위치'입니다.

<details><summary>🎙️ 해설 대본 — 시작</summary>

> 이번 강의에서는 RunPod에 만들어 둔 GPU 컴퓨터, 즉 Pod에 브라우저로 접속해서 GPU가 정말 있는지 세 가지 방법으로 확인합니다. 터미널의 `nvidia-smi`(엔비디아 에스엠아이), 파이썬 파일, 그리고 주피터 노트북이죠. 왜 같은 GPU를 세 번이나 확인할까요? 앞으로 모델을 올리고 학습시키는 모든 강의가 바로 이 세 도구 위에서 돌아가기 때문입니다. 강의가 끝나면 GPU 이름과 메모리를 직접 읽고, 노트북이 붙잡고 있던 GPU 메모리를 돌려주고, 마지막에 Pod를 Stop해서 요금까지 멈출 수 있게 됩니다.

</details>

---

## 01. 이번 강의 목표

RunPod에 만들어 둔 GPU 컴퓨터(Pod)에 브라우저로 접속해서, **GPU가 정말 있는지 세 가지 방법으로 직접 확인**합니다.

1. **Terminal(터미널)** 에서 `nvidia-smi` 명령으로 확인
2. **Python 파일**(`check_gpu.py`)을 만들어 실행해서 확인
3. **Jupyter Notebook**(`gpu_check.ipynb`)의 셀을 실행해서 확인

이 과정에서 앞으로 모든 강의에서 쓰는 기본 동작을 익힙니다: JupyterLab 화면 구성, 폴더 만들기, 터미널 기본 명령(`pwd`, `cd`, `clear`, `ls`), 파일 저장과 이름 바꾸기, 노트북 셀 실행, 커널(kernel — 노트북 코드를 실제로 실행하는 파이썬 프로그램) 재시작과 종료, GPU 메모리(VRAM) 관찰, 실습을 마친 뒤 Pod 끄기(Stop).

## 02. 최종 결과 미리 보기

강의를 마치면 아래 세 화면을 직접 만들게 됩니다.

**① Terminal의 `nvidia-smi`** — GPU 이름(NVIDIA A40)과 메모리 총량(46068MiB)이 보입니다.

![nvidia-smi 결과](screenshots/s09-nvidia-smi-zoom.png)

**② Python 파일 실행 결과** — `CUDA Available: True`와 GPU 이름이 출력됩니다. CUDA(쿠다)는 NVIDIA GPU에 계산을 시키는 소프트웨어이고, `True`는 '파이썬이 GPU를 쓸 수 있다'는 뜻입니다.

![check_gpu.py 실행 결과](screenshots/s15-run-check-gpu-zoom.png)

**③ Notebook 실행 결과** — 같은 정보를 셀 단위로 확인하고, GPU 메모리가 실제로 쓰이는 모습까지 봅니다.

![노트북 셀 실행 결과](screenshots/s22-cell4-saved.png)

## 03. 준비물

| 준비물 | 설명 |
|---|---|
| RunPod 계정과 **실행 중인 GPU Pod** | Pod를 만드는 방법은 C02-L01에서 다룹니다. 이 강의는 Pod가 `Running`인 상태에서 시작합니다. |
| 앞 강의에서 이어지는 것 | C02-L01에서 만든 Pod 하나. 이 강의를 처음 한다면 JupyterLab의 `/workspace` 목록은 비어 있습니다(STEP 3 그림처럼). 이미 한 번 해 봤다면 STEP 5의 **'이 강의를 다시 하는 경우'** 를 먼저 읽으세요. |
| 브라우저 | Chrome으로 촬영했습니다. |
| 키보드 | 단축키는 Windows 기준으로 적었습니다. **Mac은 `Ctrl` 대신 `⌘ Cmd`** 를 누릅니다(`⌘V` 붙여 넣기, `⌘S` 저장, `⌘⇧R` 강력 새로고침). 단, 터미널에서 실행을 멈추는 `Ctrl+C`(11절)와 노트북의 `Shift+Enter`는 Mac에서도 같습니다. 명령과 파일 이름은 모두 영문이므로, 입력하기 전에 **한/영 키로 영문 입력 상태**인지 확인합니다. |
| 추가 설치 | **없습니다.** RunPod PyTorch 템플릿에 Python과 PyTorch가 이미 들어 있습니다. |
| 비용 | Pod가 켜져 있는 동안 시간당 요금이 나갑니다(촬영한 A40 Secure Cloud: 시간당 $0.60). 켜 둔 Pod가 여러 개면 **각각** 요금이 나갑니다. 끄는 방법은 마지막 **STEP 26**에서 다룹니다. |

## 04. 핵심 개념

### 4-1. 내 코드는 어디서 실행될까?

브라우저에 보이는 JupyterLab은 **화면일 뿐**입니다. 실제 계산은 RunPod 데이터센터의 Pod에서 일어나고, 그 Pod에 GPU가 연결되어 있습니다. Pod는 컨테이너(container — 큰 서버 안에 따로 떼어 만든 독립된 리눅스 환경)입니다. Terminal, Python 파일, Notebook은 모두 **같은 Pod 안의 같은 파이썬**을 씁니다.

![코드가 실행되는 위치](../../../shared/diagrams/c02l02-where-code-runs.png)

*설명용 그림*

- **컨테이너 디스크(`/`)**: Pod를 Stop하면 지워지는 공간입니다.
- **`/workspace`**: Pod를 Stop해도 남는 저장 공간입니다(이 Pod는 Network Volume 50GB). 그래서 실습 폴더는 항상 `/workspace` 안에 만듭니다.

### 4-2. RAM과 VRAM

CPU는 컴퓨터 메모리(RAM)를, GPU는 자기 전용 메모리(**VRAM**)를 씁니다. PyTorch에서 `device="cuda"`라고 쓰면 데이터가 VRAM으로 올라갑니다. 노트북 커널이 살아 있는 동안에는 VRAM을 계속 잡고 있다가, 커널을 끄면 돌려줍니다(STEP 24에서 직접 확인합니다).

![RAM과 VRAM](../../../shared/diagrams/c02l02-ram-vs-vram.png)

*설명용 그림*

### 4-3. 드라이버, CUDA, PyTorch의 관계

- **NVIDIA 드라이버**: GPU를 움직이는 기본 소프트웨어입니다. `nvidia-smi`의 `CUDA Version: 13.2`는 "이 드라이버가 **최대 CUDA 13.2까지** 지원한다"는 뜻입니다.
- **PyTorch**: `2.8.0+cu128`의 `cu128`은 "CUDA 12.8용으로 만든 PyTorch"라는 뜻입니다.
- 이 실습의 CUDA 12.8용 PyTorch는 CUDA 13.2까지 지원하는 드라이버와 호환됩니다(드라이버가 지원하는 CUDA 버전이 PyTorch가 빌드된 CUDA 버전보다 높거나 같아야 한다는 것이 큰 원칙).
- 다만 버전 숫자만으로 끝까지 보장되지는 않습니다. **실제로 GPU를 쓸 수 있는지는 `torch.cuda.is_available()`가 `True`이고 STEP 21의 GPU 계산이 성공하는 것으로 확인**합니다.

![드라이버·CUDA·PyTorch](../../../shared/diagrams/c02l02-driver-cuda-pytorch.png)

*설명용 그림*

### 4-4. `nvidia-smi` 화면 읽는 법

![nvidia-smi 화면 지도](../../../shared/diagrams/c02l02-nvidia-smi-map.png)

*실제 화면 위에 설명 표시를 덧그린 그림*

각 칸의 뜻은 STEP 9의 표에도 같은 내용으로 정리해 두었습니다.

## 05. 현재 작업 화면 및 파일 구조

- **시작 화면**: RunPod 콘솔(`console.runpod.io`)의 **Pods** 화면
- **작업 공간**: JupyterLab(브라우저 새 탭)
- **완료 후 Pod 안 파일 구조**:

```text
/workspace/
└── llm-course/
    ├── .ipynb_checkpoints/   ← JupyterLab이 자동으로 만드는 백업 폴더(숨김)
    ├── check_gpu.py          ← STEP 12~14(Part D)에서 만듦
    └── gpu_check.ipynb       ← STEP 16~17(Part E)에서 만듦
```

---

## 06. 단계별 따라 하기

진행 순서: **Part A** 접속 → **Part B** 폴더 → **Part C** Terminal → **Part D** Python 파일 → **Part E** Notebook → **Part F** 마무리(파일 확인, Pod 끄기)

> ✅ **성공 확인 읽는 법**: STEP에 적힌 숫자는 촬영 환경(A40, PyTorch 2.8.0) 값입니다. 결과를 비교하는 STEP에는 **꼭 같아야 할 것**과 **달라도 되는 것**을 나눠 적었습니다. GPU나 템플릿이 다르면 버전, GPU 이름, 메모리 숫자는 달라도 정상입니다.

### Part A. RunPod에서 JupyterLab 열기

<a id="step-1"></a>
#### STEP 1 · RunPod 콘솔에서 Pod 찾기 (S01)

- **현재 화면**: RunPod 콘솔
- **행동**: ① 왼쪽 메뉴에서 **Pods**를 누릅니다. ② 목록에서 **내 Pod 이름**(Name 열의 글자)을 누릅니다.

![Pods 메뉴와 Pod 이름 클릭 위치](screenshots/s01-click-pods-and-pod.png)

- 그림의 `<POD_A_NAME>`은 촬영에 쓴 Pod의 이름입니다. Pod 이름은 Pod를 만들 때 정해지므로 여러분 화면에는 다른 이름이 보입니다.
- **Pod가 여러 개 보이면**: C02-L01에서 만든 Pod의 이름을 누릅니다. 이름이 기억나지 않으면 **Compute type** 열(GPU 종류, 촬영 화면은 `A40 x1`)을 머리말 표와 비교해 고릅니다. 이름을 누르면 열리는 상세 패널에도 **Details**, **Volumes**, **Template** 탭이 있어 더 자세히 볼 수 있습니다(이 탭들의 화면은 촬영하지 않았습니다).
- **확인**: 이름 앞에 **초록 점**이 있으면 Pod가 실행 중(Running)입니다. 촬영 화면에는 Pod가 두 개 보이지만, 여러분은 하나만 보여도 정상입니다.

> 💰 초록 점이 켜진 Pod는 **하나하나 따로** 시간당 요금이 나갑니다(촬영 화면: 두 Pod 모두 `$0.60/hr`). 오늘 쓰지 않을 Pod는 마지막 STEP 26에서 함께 Stop합니다.

<details><summary>🎙️ 해설 대본 — STEP 1</summary>

> 지금 보시는 화면은 RunPod 콘솔의 Pods 화면입니다. 왼쪽 메뉴에서 ① Pods를 누르면 내 Pod 목록이 나오죠. 촬영 화면에는 Pod가 두 개 있고, 둘 다 이름 앞에 초록 점이 켜져 있습니다. 초록 점은 Pod가 켜져 있다, 즉 지금 요금이 나가고 있다는 뜻인데요, 오른쪽 Cost 열을 보면 각각 시간당 0.60달러죠? 여러분은 C02-L01에서 만든 내 Pod의 이름을 ② 누르면 됩니다.

</details>

<a id="step-2"></a>
#### STEP 2 · Connect 탭에서 Jupyter Lab이 Ready인지 확인 (S02)

- **현재 화면**: 오른쪽에 열린 Pod 상세 패널
- **행동**: ① **Connect** 탭을 누릅니다. ② **HTTP services**의 `Port 8888 → Jupyter Lab` 줄을 **찾기만** 합니다. ②는 아직 누르지 않습니다(STEP 3에서 누릅니다).

![Connect 탭과 Jupyter Lab 링크](screenshots/s02-click-connect-jupyter.png)

- **확인**: 줄 오른쪽 끝에 초록색 **Ready**가 보여야 합니다.

![HTTP services 확대](screenshots/s02-http-services-zoom.png)

<details><summary>🎙️ 해설 대본 — STEP 2</summary>

> Pod 이름을 누르면 오른쪽에 상세 패널이 열립니다. 여기서 ① Connect(커넥트) 탭을 누르세요. HTTP services 아래에 `Port 8888 → Jupyter Lab` 줄이 보이시죠? 줄 오른쪽 끝에 초록색 Ready(레디)가 떠 있으면 JupyterLab에 접속할 준비가 끝났다는 뜻입니다. Jupyter Lab 글자는 다음 STEP에서 누르니, 지금은 Ready만 확인하고 넘어갑니다.

</details>

<a id="step-3"></a>
#### STEP 3 · Jupyter Lab 열기 (S03)

- **행동**: Ready를 확인했으면 STEP 2 그림의 ② **Jupyter Lab** 글자를 **한 번** 누릅니다.
- **결과**: 브라우저에 **새 탭**이 열리고 JupyterLab 화면이 나타납니다.

![JupyterLab 첫 화면](screenshots/s03-jupyterlab-first-screen.png)

- 이 강의를 처음 한다면 왼쪽 목록이 그림처럼 비어 있습니다. 전에 만든 `llm-course` 같은 폴더가 보여도 정상입니다(STEP 5의 '이 강의를 다시 하는 경우' 참고).

> ⚠️ **주소 공유 금지**: 이 탭의 주소(`...-8888.proxy.runpod.net`)는 접속 열쇠(토큰)와 함께 열립니다. 주소를 아는 사람은 여러분의 Pod를 조작할 수 있으므로, 주소창을 캡처하거나 남에게 보내지 마세요.

<details><summary>🎙️ 해설 대본 — STEP 3</summary>

> Ready를 확인했으니 이제 Jupyter Lab 글자를 한 번 누릅니다. 브라우저에 새 탭이 열리면서 JupyterLab(주피터랩) 화면이 나타나죠. 이 화면은 내 컴퓨터가 아니라 RunPod 데이터센터의 Pod 안에서 돌아가는 프로그램을 브라우저로 보고 있는 겁니다. 그런데 이 탭의 주소에는 접속 열쇠, 즉 토큰이 들어 있습니다. 주소를 남에게 보내면 어떻게 될까요? 그 사람도 내 Pod를 조작할 수 있으니 주소창은 절대 캡처하거나 공유하지 마세요.

</details>

<a id="step-4"></a>
#### STEP 4 · JupyterLab 화면 구성 익히기 (S04)

화면은 크게 세 부분이고, 가장자리에 자주 쓰는 곳이 두 군데 더 있습니다.

| 위치 | 이름 | 하는 일 |
|---|---|---|
| 맨 위 | 메뉴 바 (`File` `Edit` `View` `Run` `Kernel` `Tabs` `Settings` `Help`) | 저장, 커널 재시작 같은 명령 |
| 왼쪽 | **File Browser** | Pod 안의 파일과 폴더. 위쪽 경로 표시줄에 `/ workspace /` |
| 가운데 | **Launcher** | 새 Notebook, Terminal, Python File 만들기 |
| 왼쪽 끝 세로 아이콘 줄 | 맨 위 폴더 아이콘 = File Browser, **위에서 두 번째(동그라미 안 네모) = Running Terminals and Kernels** | 지금 켜져 있는 터미널과 커널 목록을 보고 끌 수 있는 곳(10절에서 사용) |
| 맨 아래 | **상태 표시줄** | 노트북 커널 상태(`Idle` = 기다리는 중, `Busy` = 실행 중) 등. STEP 18·23에서 봅니다 |

- **행동**: 오른쪽 아래에 *"Would you like to get notified about official Jupyter news?"* 알림이 보이면 ① **No**를 누릅니다(소식 알림을 받지 않음).

![알림 No와 New Folder 위치](screenshots/s04-s05-click-no-newfolder.png)

<details><summary>🎙️ 해설 대본 — STEP 4</summary>

> JupyterLab 화면은 크게 세 부분입니다. 맨 위 메뉴 바, 왼쪽 파일 목록인 File Browser(파일 브라우저), 가운데 새 작업을 만드는 Launcher(런처)죠. 왼쪽 끝 세로 아이콘 줄과 맨 아래 상태 표시줄도 뒤에서 자주 봅니다. File Browser 위쪽 경로 표시줄에 `/ workspace /`가 보이시나요? 오른쪽 아래에 Jupyter news 알림이 떠 있으면 ① No를 눌러 닫고, 다음 STEP에서 ② New Folder 버튼을 씁니다.

</details>

### Part B. 작업 폴더 만들기

<a id="step-5"></a>
#### STEP 5 · `llm-course` 폴더 만들기 (S05)

- **현재 화면**: JupyterLab, 경로 표시줄 `/ workspace /`
- **입력 전 확인**: 키보드가 **영문 입력** 상태인지 한/영 키로 확인합니다. 한글 상태로 치면 `llm-course`가 `ㅣㅣㅡ-채ㅕㄱㄴㄷ`처럼 엉뚱한 이름이 됩니다.
- **행동**: STEP 4 그림의 ② **New Folder** 버튼(폴더 모양 + 아이콘)을 누릅니다.
- **결과**: 목록 맨 위에 `Untitled Folder`가 생기고, 이름 글자가 **파랗게 선택된 입력 칸**이 됩니다.

![Untitled Folder 이름 입력 칸](screenshots/s05e-new-folder-name-edit-scratch.png)

*보충 촬영(두 번째 Pod의 임시 폴더 `/workspace/c02l02-fix`)이라 경로 표시줄이 `/ workspace / c02l02-fix /`로 보입니다. 여러분 화면은 `/ workspace /`입니다.*

- **행동**: **다른 곳을 클릭하지 말고** 그대로 `llm-course`를 입력하고 **Enter**를 누릅니다. 영문 소문자, 가운데 하이픈(`-`), 띄어쓰기 없음입니다(`LLM-course`, `llm_course`는 다른 폴더가 됩니다).
- **확인**: 목록에 `llm-course`가 생깁니다.

![llm-course 폴더 생성 확인](screenshots/s05f-llm-course-created-scratch.png)

*보충 촬영(임시 폴더) — 경로 표시줄만 여러분 화면과 다릅니다.*

> 💡 화면이 RunPod **프록시**(proxy — RunPod가 중간에서 Pod의 화면을 브라우저로 전달해 주는 서버)를 거쳐 그려지기 때문에 **새 폴더나 새 이름이 1~2초 늦게 보일 수 있습니다.** 바로 안 바뀌어도 잠시 기다리세요.
>
> 💡 이름이 `Untitled Folder`로 굳어 버렸다면(이름을 치기 전에 다른 곳을 클릭한 경우): 그 폴더를 오른쪽 클릭 → **Rename** (F2) → `llm-course` → Enter. 오른쪽 클릭 메뉴에서 Rename 바로 아래의 **Delete는 누르지 마세요**(휴지통 없이 바로 삭제됩니다).

> 🔁 **이 강의를 다시 하는 경우**(이미 `llm-course`나 실습 파일이 있을 때)
>
> - `llm-course` 폴더가 이미 있으면 새로 만들지 말고 STEP 6으로 넘어갑니다(같은 이름의 폴더는 하나만 있을 수 있습니다).
> - 그 폴더 안에 `check_gpu.py`나 `gpu_check.ipynb`가 이미 있으면 **지우지 말고** 오른쪽 클릭 → **Rename** 으로 `check_gpu_old.py`, `gpu_check_old.ipynb`처럼 이름을 바꿔 둔 뒤 그대로 진행합니다. 그러면 STEP 13·17에서 같은 이름과 부딪히지 않습니다. JupyterLab에서 지운 파일은 휴지통 없이 바로 사라지므로 삭제는 권하지 않습니다.

<details><summary>🎙️ 해설 대본 — STEP 5</summary>

> 이제 실습 파일을 모아 둘 폴더를 만듭니다. ② New Folder(뉴 폴더) 버튼을 누르면 목록 맨 위에 `Untitled Folder`가 생기고 이름 글자가 파랗게 선택되죠. 이때 다른 곳을 클릭하면 어떻게 될까요? 이름이 Untitled Folder로 굳어 버리니, 영문 상태에서 바로 `llm-course`를 치고 Enter를 누릅니다. 화면이 프록시를 거쳐 그려져서 1~2초 늦게 바뀔 수 있지만, 목록에 llm-course가 보이면 성공입니다.

</details>

<a id="step-6"></a>
#### STEP 6 · 폴더 안으로 들어가기 (S06)

- **행동**: ① `llm-course`를 **더블클릭**합니다.

![llm-course 더블클릭](screenshots/s06-click-llm-course.png)

*보충 촬영(임시 폴더) 화면에 클릭 위치를 덧그린 그림입니다.*

- **확인**: 경로 표시줄이 `/ workspace / llm-course /`로 바뀌고, Launcher 위 제목도 `workspace/llm-course`가 됩니다.

![llm-course 안](screenshots/s06-inside-llm-course.png)

<details><summary>🎙️ 해설 대본 — STEP 6</summary>

> 방금 만든 폴더 안으로 들어가 보겠습니다. 목록의 ① `llm-course`를 더블클릭하세요. 경로 표시줄이 `/ workspace / llm-course /`로 바뀌었죠? Launcher 위 제목도 `workspace/llm-course`가 됩니다. 이 폴더 안에 있어야 앞으로 만드는 파일이 여기에 저장되니, 파일을 만들기 전에는 이 제목을 확인하는 습관을 들이세요.

</details>

### Part C. Terminal에서 GPU 확인하기

<a id="step-7"></a>
#### STEP 7 · Terminal 열기 (S07)

- **현재 화면**: Launcher (제목 `workspace/llm-course`)
- **행동**: **Other** 구역의 ① **Terminal**을 누릅니다.

![Terminal 위치](screenshots/s07-click-terminal.png)

- **결과**: Terminal 탭이 열리고 RunPod 글자 그림과 프롬프트가 보입니다.

![Terminal 첫 화면](screenshots/s07-terminal-opened.png)

- 맨 위의 `groups: cannot find name for group ID 109`는 **무시해도 되는 안내 문구**입니다.
- 마지막 줄 `root@<컨테이너>:/#`가 **프롬프트**입니다. 형식은 `사용자@컴퓨터이름:현재위치#`입니다. 컴퓨터 이름은 Pod마다 다릅니다.

<details><summary>🎙️ 해설 대본 — STEP 7</summary>

> GPU를 확인할 첫 번째 도구, Terminal(터미널)을 열어 봅니다. Launcher의 Other 구역에서 ① Terminal을 누르세요. 새 탭에 RunPod 글자 그림과 `root@<컨테이너>:/#` 같은 줄이 나타나죠? 이 줄이 프롬프트, 즉 명령을 기다리는 자리입니다. 맨 위 `groups: cannot find name for group ID 109`는 무시해도 되는 안내이고, 컴퓨터 이름 부분은 Pod마다 달라도 괜찮습니다.

</details>

<a id="step-8"></a>
#### STEP 8 · 현재 위치 확인하고 작업 폴더로 이동 (S08)

- **실행 환경**: JupyterLab Terminal. 터미널 화면을 한 번 클릭한 뒤 입력합니다.
- **입력 전 확인**: 영문 입력 상태인지 한/영 키로 확인합니다. 한글 상태로 `pwd`를 치면 `ㅔㅈㅇ`이 되어 `bash: ㅔㅈㅇ: command not found`가 나옵니다.
- **입력할 명령** (한 줄 입력 → Enter → 결과 확인 → 다음 줄):

```bash
pwd
cd /workspace/llm-course
```

| 명령 | 뜻 |
|---|---|
| `pwd` | print working directory — 지금 있는 폴더를 보여 줍니다. |
| `cd 경로` | change directory — 그 폴더로 이동합니다. |

![pwd 결과](screenshots/s08a-pwd.png)

- **결과 읽기**: `pwd`는 `/workspace/llm-course`라고 답했는데, 프롬프트는 `:/#`로 보입니다. Launcher에서 연 Terminal은 실제로는 그 폴더에서 시작하지만, 프롬프트 표시가 그걸 반영하지 못한 상태입니다. 그래서 `cd /workspace/llm-course`로 **확실하게 이동**합니다. `pwd` 결과가 `/`나 `/workspace`로 나와도 괜찮습니다. 다음 줄의 `cd`로 이동하면 됩니다.
- **성공 확인**: `cd`는 성공하면 **아무 글자도 출력하지 않습니다.** 대신 다음 줄의 프롬프트가 `root@...:/workspace/llm-course#`로 바뀝니다. 아래 그림의 4번째 줄 `root@<컨테이너>:/workspace/llm-course#` 부분입니다(그 뒤의 `nvidia-smi`는 다음 STEP에서 입력한 명령).

![cd 뒤 바뀐 프롬프트](screenshots/s08b-cd-prompt-zoom.png)

- `bash: cd: /workspace/llm-course: No such file or directory`가 나오면 폴더 이름이 다른 것입니다. 10절 오류 해결을 보세요.

<details><summary>🎙️ 해설 대본 — STEP 8</summary>

> 한/영 키로 영문 상태인지 확인하고 `pwd`(피더블유디)를 입력해 보세요. `/workspace/llm-course`라고 답하는데, 프롬프트는 아직 `:/#`로 보이죠? 이상하지 않나요? 프롬프트 표시가 실제 위치를 늦게 반영한 것이라서 `cd /workspace/llm-course`로 확실하게 이동합니다. `cd`는 성공하면 아무 글자도 출력하지 않고, 다음 줄 프롬프트가 `/workspace/llm-course#`로 바뀌면 성공입니다.

</details>

<a id="step-9"></a>
#### STEP 9 · `nvidia-smi`로 GPU 확인 (S09)

```bash
nvidia-smi
```

![nvidia-smi 전체 화면](screenshots/s09-nvidia-smi.png)

**결과 읽기** (확대 그림과 4-4절 지도 참고):

![nvidia-smi 확대](screenshots/s09-nvidia-smi-zoom.png)

| 보이는 값 | 뜻 |
|---|---|
| `NVIDIA A40` | GPU 이름 |
| `Driver Version: 595.91.07` | 설치된 NVIDIA 드라이버 버전 |
| `CUDA Version: 13.2` | 이 드라이버가 지원하는 **최대** CUDA 버전 |
| `0MiB / 46068MiB` | GPU 메모리(VRAM) 사용량 / 전체. 지금은 아무도 안 씀 |
| `0%` (GPU-Util) | GPU 계산 사용률 |
| `No running processes found` | GPU를 쓰는 프로그램 없음 |

- **성공 확인**: GPU 이름과 메모리 총량이 보이면 성공입니다.
- **꼭 같아야 할 것**: GPU 이름 줄과 `숫자MiB / 숫자MiB` 메모리 칸이 보이는 것 / **달라도 되는 것**: GPU 이름, 메모리 숫자, 드라이버·CUDA 버전, 온도(GPU 종류와 Pod에 따라 다름)

<details><summary>🎙️ 해설 대본 — STEP 9</summary>

> 이제 핵심 명령 `nvidia-smi`(엔비디아 에스엠아이)를 입력합니다. 표가 하나 나오죠? GPU 이름은 NVIDIA A40, 메모리 칸은 `0MiB / 46068MiB`로 아직 아무도 쓰지 않는 상태입니다. 위쪽 Driver Version 595.91.07은 드라이버 버전이고, CUDA Version 13.2는 이 드라이버가 지원하는 최대 CUDA 버전이에요. 맨 아래 `No running processes found`까지 확인했다면, GPU 이름과 메모리 총량이 보이는 것으로 첫 번째 확인은 성공입니다.

</details>

<a id="step-10"></a>
#### STEP 10 · 화면 지우고 GPU 요약만 보기 (S10)

```bash
clear
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
```

- `clear`: 터미널 화면을 깨끗하게 지웁니다(파일은 그대로).
- `--query-gpu=...`: 원하는 항목만 골라 보기. `--format=csv`: 쉼표로 구분한 표로 출력.

![GPU 요약과 다음 STEP 명령까지 실행한 화면](screenshots/s10-s11-query-and-python.png)

- **결과**: 맨 위 명령 줄 **바로 아래 두 줄** — `name, memory.total [MiB], memory.used [MiB]` / `NVIDIA A40, 46068 MiB, 0 MiB`. 그림 아래쪽의 `python --version`, `which python`과 그 결과는 다음 STEP에서 입력합니다.
- **꼭 같아야 할 것**: 제목 줄과 값 줄, 두 줄이 나오는 것 / **달라도 되는 것**: GPU 이름과 메모리 숫자

<details><summary>🎙️ 해설 대본 — STEP 10</summary>

> 표가 길어서 화면이 복잡하죠? `clear`(클리어)로 화면을 지우고, 필요한 항목만 골라 보겠습니다. `nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv`를 입력하세요. 명령 줄 바로 아래에 `name, memory.total [MiB], memory.used [MiB]`와 `NVIDIA A40, 46068 MiB, 0 MiB` 두 줄이 나옵니다. 이름, 전체 메모리, 사용 중인 메모리만 쉼표로 나뉘어 나오니 기록하고 비교하기 편하겠죠?

</details>

<a id="step-11"></a>
#### STEP 11 · 이 Terminal이 쓰는 파이썬 확인 (S11)

```bash
python --version
which python
```

![요약 출력과 파이썬 위치](screenshots/s10-s11-zoom.png)

- **결과**: `Python 3.12.3` / `/usr/local/bin/python` (그림 위쪽 세 줄은 STEP 10의 명령과 결과입니다)
- `which python`의 답(`/usr/local/bin/python`)을 기억해 두세요. STEP 22에서 노트북의 파이썬과 비교합니다.
- **달라도 되는 것**: 파이썬 버전 숫자

> 💡 **명령은 한 줄씩**: 앞 명령의 결과가 나오기 전에 다음 명령을 빨리 치면 화면에 글자가 섞여 보입니다(아래는 실제로 섞인 예). 명령은 제대로 실행되지만 읽기 어려우니, 결과를 보고 다음 줄을 입력하세요.
>
> ![글자가 섞인 예](screenshots/s10-typeahead-messy-zoom.png)

<details><summary>🎙️ 해설 대본 — STEP 11</summary>

> 다음은 이 터미널이 어떤 파이썬을 쓰는지 확인합니다. `python --version`은 `Python 3.12.3`, `which python`(위치 파이썬)은 `/usr/local/bin/python`이라고 답하죠. 왜 위치까지 확인할까요? 한 Pod 안에도 파이썬이 여러 개 있을 수 있어서, 터미널과 노트북이 같은 파이썬을 쓰는지 STEP 22에서 비교하려는 겁니다. 명령은 결과를 보고 한 줄씩 입력해야 글자가 섞이지 않습니다.

</details>

### Part D. Python 파일로 GPU 확인하기

<a id="step-12"></a>
#### STEP 12 · 새 Python 파일 만들기 (S12)

- **현재 화면**: JupyterLab. 가운데 위쪽 탭 줄에서 **Launcher** 탭을 누릅니다. 없으면 왼쪽 위 파란 **+** 버튼(New Launcher)으로 엽니다.
- **행동**: Launcher 제목이 `workspace/llm-course`인지 확인하고 **Other** 구역의 ① **Python File**을 누릅니다.

![Python File 위치](screenshots/s12-click-python-file.png)

*STEP 6 직후 화면에 클릭 위치를 덧그린 그림이라 탭 줄에 Launcher만 보입니다. 여러분 화면에는 Terminal 탭(`root@...`)도 보이는 것이 정상입니다.*

- **결과**: `untitled.py`가 `llm-course` 안에 생기고 빈 편집기가 열립니다.

![untitled.py 생성](screenshots/s12-python-file-created.png)

<details><summary>🎙️ 해설 대본 — STEP 12</summary>

> 두 번째 방법은 파이썬 파일입니다. 탭 줄에서 Launcher 탭을 누르고, 제목이 `workspace/llm-course`인지 먼저 확인하세요. 그다음 Other 구역의 ① Python File(파이썬 파일)을 누르면 `untitled.py`라는 빈 파일이 llm-course 안에 생기고 편집기가 열립니다. 이름이 untitled라서 마음에 걸리시나요? 이름은 처음 저장할 때 정하니 지금은 그대로 둡니다.

</details>

<a id="step-13"></a>
#### STEP 13 · 코드 붙여 넣고 이름을 정해 저장하기 (S13)

| 항목 | 내용 |
|---|---|
| **파일 위치** | `/workspace/llm-course/check_gpu.py` |
| **현재 화면** | JupyterLab 편집기(`untitled.py` 탭) |
| **수행할 행동** | 아래 코드 상자 전체를 복사 → 편집기 빈 곳 클릭 → `Ctrl+V` (Mac `⌘V`) |
| **파일 이름** | `check_gpu.py` (첫 저장 때 정함. 입력은 `check_gpu`만) |
| **저장** | `Ctrl+S` (Mac `⌘S`) → *Rename file* 대화상자 → `check_gpu`만 입력(`.py`는 이미 있음) → **Rename and Save** |
| **실행 환경** | JupyterLab Terminal (STEP 15) |
| **실행 명령어** | `python check_gpu.py` |
| **결과 확인** | `CUDA Available: True`, `GPU: NVIDIA A40` |

**코드 입력** — 전체를 그대로 붙여 넣습니다. GitHub에서 보고 있다면 코드 상자 오른쪽 위의 **복사 아이콘**을 누르면 7줄이 들여쓰기까지 통째로 복사됩니다. 마우스로 드래그하면 일부가 빠지거나 7행 앞 공백 4칸이 깨질 수 있습니다.

```python
import torch

print("PyTorch:", torch.__version__)
print("CUDA Available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
```

![코드 붙여 넣은 모습](screenshots/s13a-code-pasted.png)

탭 이름 옆의 **●** 는 "아직 저장 안 됨"이라는 뜻입니다. 이제 **`Ctrl+S`** 를 누르면 처음 저장할 때만 이름을 묻는 창이 뜹니다.

> ⚠️ **이름 창의 함정 세 가지**
>
> - `untitled` 부분만 선택되어 있으므로 **`check_gpu`만** 입력합니다. `.py`까지 치면 `check_gpu.py.py`가 됩니다.
> - 창 아래 체크박스 *Do not ask for rename on first save.* 는 **건드리지 마세요.** 켜면 STEP 17에서 이름 창이 뜨지 않습니다.
> - **Cancel**을 누르면 이름이 `untitled.py`로 남아 STEP 15에서 `No such file or directory`가 납니다. 그때는 왼쪽 목록에서 파일을 오른쪽 클릭 → **Rename** (F2) → `check_gpu.py`로 고칩니다.

![Rename file 대화상자](screenshots/s13b-rename-dialog.png)

`untitled` 부분이 이미 선택되어 있으므로 바로 `check_gpu`를 입력하면 `check_gpu.py`가 됩니다. **Rename and Save**를 누릅니다.

![이름 입력](screenshots/s13c-rename-dialog-filled-zoom.png)

<details><summary>🎙️ 해설 대본 — STEP 13</summary>

> README의 코드 상자를 통째로 복사해서 편집기에 `Ctrl+V`로 붙여 넣습니다. 탭 이름 옆에 ●가 생겼죠? 아직 저장되지 않았다는 표시입니다. `Ctrl+S`를 누르면 Rename file(리네임 파일) 창이 뜨고 `untitled` 부분만 파랗게 선택되어 있는데, 여기서 `.py`까지 치면 어떻게 될까요? `check_gpu.py.py`가 되어 버리니 `check_gpu`만 치고 Rename and Save(리네임 앤드 세이브)를 누르세요.

</details>

<a id="step-14"></a>
#### STEP 14 · 저장 확인 (S14)

- **확인**: 탭 이름과 왼쪽 목록이 `check_gpu.py`로 바뀌고 **●** 표시가 사라졌습니다.

![check_gpu.py 저장 완료](screenshots/s14-check-gpu-saved.png)

> 💡 저장 직후 아래쪽에 `Saving completed`가 떠도 이름이 잠깐 `untitled.py`로 남아 보일 수 있습니다(화면 반영 지연, 아래 그림). 1~2초 뒤 바뀝니다.
>
> ![이름 반영 지연](screenshots/s13d-saving-completed-latency.png)

<details><summary>🎙️ 해설 대본 — STEP 14</summary>

> 저장이 끝나면 탭 이름과 왼쪽 목록이 `check_gpu.py`로 바뀌고 ● 표시가 사라집니다. 혹시 아래쪽에 Saving completed가 떴는데 이름은 아직 `untitled.py`로 보이나요? 화면 반영이 1~2초 늦는 것이니 잠깐 기다리면 바뀝니다. 이름이 정확해야 다음 STEP에서 이 이름으로 실행할 수 있겠죠?

</details>

<a id="step-15"></a>
#### STEP 15 · Terminal에서 실행하기 (S15)

- **행동**: 탭 줄에서 ① Terminal 탭(`root@...`)의 **글자 부분**을 누르고(탭 오른쪽 끝 `×`는 탭을 닫는 버튼), 터미널 화면을 한 번 클릭합니다.

![Terminal 탭으로 이동](screenshots/s15-click-terminal-tab.png)

- **Terminal 탭이 없으면**(닫았다면): Launcher → **Terminal**로 새로 열고, 새 터미널은 시작 위치가 다를 수 있으므로 `cd /workspace/llm-course`부터 다시 입력한 뒤 아래 명령을 칩니다.

```bash
clear
python check_gpu.py
```

- `python 파일이름`: 그 파이썬 파일을 처음부터 끝까지 실행합니다. 현재 위치(`/workspace/llm-course`)에 파일이 있어야 합니다.

![check_gpu.py 실행 화면](screenshots/s15-run-check-gpu.png)

![check_gpu.py 실행 결과 확대](screenshots/s15-run-check-gpu-zoom.png)

- **성공 확인**: 세 줄 — `PyTorch: 2.8.0+cu128`, `CUDA Available: True`, `GPU: NVIDIA A40`
- **꼭 같아야 할 것**: `CUDA Available: True`, 그리고 `GPU:` 줄이 나오는 것 / **달라도 되는 것**: PyTorch 버전 숫자(템플릿에 따라 다름), GPU 이름

<details><summary>🎙️ 해설 대본 — STEP 15</summary>

> 탭 줄에서 ① 터미널 탭의 글자 부분을 누르고 화면을 한 번 클릭합니다. `clear`로 화면을 지운 뒤 `python check_gpu.py`를 입력하세요. `PyTorch: 2.8.0+cu128`, `CUDA Available: True`, `GPU: NVIDIA A40`, 세 줄이 나오죠? 여기서 꼭 봐야 할 것은 CUDA Available이 True, 즉 파이썬이 GPU를 쓸 수 있다는 줄입니다. 버전 숫자와 GPU 이름은 여러분 Pod에 따라 달라도 괜찮습니다.

</details>

### Part E. Jupyter Notebook으로 GPU 확인하기

<a id="step-16"></a>
#### STEP 16 · 새 Notebook 만들기 (S16)

- **행동**: 왼쪽 위 파란 **+** 버튼(New Launcher)으로 Launcher를 엽니다. Launcher 제목이 `workspace/llm-course`인지 확인하고, 맨 위 **Notebook** 구역의 ① **Python 3 (ipykernel)** 을 누릅니다.
- 바로 아래 **Console** 구역에도 같은 아이콘, 같은 이름이 있습니다. 그것을 누르면 노트북이 아니라 콘솔이 열리므로 **맨 위 Notebook 구역**의 것을 누르세요.
- `ipykernel`(아이파이커널)은 노트북에서 파이썬 코드를 실행해 주는 커널 프로그램의 이름입니다. 즉 'Python 3로 코드를 실행하는 노트북'이라는 뜻입니다.

![Notebook 위치](screenshots/s16-click-notebook.png)

*STEP 6 직후 화면에 클릭 위치를 덧그린 그림입니다. 여러분 화면에는 왼쪽 목록의 `check_gpu.py`와 탭 줄의 Terminal·`check_gpu.py` 탭이 보이는 것이 정상입니다.*

- **결과**: `Untitled.ipynb`가 열리고 빈 셀 `[ ]:` 하나가 보입니다. 오른쪽 위에 `Python 3 (ipykernel)` 표시가 있습니다. 맨 아래 상태 표시줄은 잠깐 `Connecting`으로 보입니다(커널이 켜지는 중).

![Untitled.ipynb](screenshots/s16b-notebook-created.png)

<details><summary>🎙️ 해설 대본 — STEP 16</summary>

> 세 번째 방법은 주피터 노트북입니다. 왼쪽 위 파란 + 버튼으로 Launcher를 열고 제목이 `workspace/llm-course`인지 확인한 다음, 맨 위 Notebook 구역의 ① Python 3 (ipykernel)(파이썬 쓰리 아이파이커널)을 누르세요. 바로 아래 Console 구역에도 똑같은 아이콘이 있는데, 그건 노트북이 아니니 조심해야겠죠? `Untitled.ipynb`가 열리고 빈 셀 `[ ]:` 하나가 보이면 됩니다. 아래 상태 표시줄의 Connecting(커넥팅)은 커널이 켜지는 중이라는 뜻입니다.

</details>

<a id="step-17"></a>
#### STEP 17 · Notebook 이름 정하기 (S17)

- **행동**: `Ctrl+S` → *Rename file* 창에 `gpu_check` 입력 → **Rename and Save**

> ⚠️ 파이썬 파일은 `check_gpu`, 노트북은 **`gpu_check`** — **단어 순서가 반대**입니다. 방금 친 `check_gpu`를 또 치지 않도록 주의하세요. 노트북도 `.ipynb`는 이미 있으니 `gpu_check`만 입력합니다.

![Notebook Rename file](screenshots/s17c-notebook-rename-dialog-scratch.png)

*보충 촬영(임시 폴더 `/workspace/c02l02-fix/llm-course`에서 노트북만 만든 상태)이라 경로 표시줄과 탭 줄이 여러분 화면과 조금 다릅니다. 여러분 화면에는 `check_gpu.py`와 Terminal 탭도 보입니다.*

![gpu_check 입력](screenshots/s17b-notebook-rename-filled-zoom.png)

- **이름 창이 뜨지 않으면**(STEP 13에서 체크박스를 켰거나 Cancel을 누른 경우): 왼쪽 목록의 `Untitled.ipynb`를 오른쪽 클릭 → **Rename** (F2) → `gpu_check.ipynb` → Enter. 끝의 `.ipynb`는 한 번만 있어야 합니다.

<details><summary>🎙️ 해설 대본 — STEP 17</summary>

> 노트북도 처음 저장할 때 이름을 정합니다. `Ctrl+S`를 누르면 아까와 같은 Rename file 창이 뜨고 `Untitled`가 선택되어 있죠. 이번에는 `gpu_check`를 입력합니다. 잠깐, 아까 파이썬 파일 이름은 뭐였죠? `check_gpu`였으니 단어 순서가 반대입니다, 천천히 확인하고 Rename and Save를 누르세요.

</details>

<a id="step-18"></a>
#### STEP 18 · 커널 상태 확인 (S18)

- **확인**: 탭 이름이 `gpu_check.ipynb`, 오른쪽 위에 `Python 3 (ipykernel)`, 맨 아래 상태 표시줄에 `Python 3 (ipykernel) | Idle`.
- 상태 표시줄이 아직 `Connecting`이면 `Idle`이 될 때까지 몇 초 기다리세요.

![커널 Idle](screenshots/s18-kernel-idle.png)

- 그림처럼 왼쪽 목록이 잠깐 `Untitled.ipynb`로 남아 보여도 1~2초 뒤 `gpu_check.ipynb`로 바뀝니다(화면 반영 지연).
- 왼쪽 목록에서 파일 이름 앞의 **●** 는 '커널 실행 중' 표시입니다. 저장과는 관계없습니다(저장 여부는 **탭 이름 옆**의 ●로 봅니다). STEP 24에서 커널을 끄면 사라집니다.

**커널(kernel)** 은 노트북의 코드를 실제로 실행하는 파이썬 프로그램입니다. `Idle`은 "실행할 준비가 되어 일을 기다리는 중"이라는 뜻입니다.

<details><summary>🎙️ 해설 대본 — STEP 18</summary>

> 탭 이름이 `gpu_check.ipynb`로 바뀌었는지 보세요. 오른쪽 위에는 `Python 3 (ipykernel)`, 맨 아래 상태 표시줄에는 `Python 3 (ipykernel) | Idle`이 보이죠? 커널(kernel)은 노트북 코드를 실제로 실행하는 파이썬 프로그램이고, Idle(아이들)은 일을 기다리는 중이라는 뜻입니다. 왼쪽 목록 이름 앞의 ●는 커널이 실행 중이라는 표시라서 저장과는 관계없습니다. 목록 이름이 잠깐 Untitled.ipynb로 남아 있어도 곧 바뀌니 걱정하지 마세요.

</details>

#### 셀 실행 방법 (STEP 19~22 공통)

1. **맨 아래의 빈 셀** `[ ]:` 입력 칸을 클릭합니다(파란 테두리). 이미 실행한 위쪽 셀을 클릭해 코드를 덧붙이지 않습니다.
2. 아래 코드를 복사해 `Ctrl+V`(Mac `⌘V`)로 붙여 넣습니다.
3. **`Shift+Enter`** 를 누릅니다(Mac도 같음). 셀이 실행되고 결과가 아래에 나오며, 다음 빈 셀이 자동으로 생깁니다.
4. 실행 중에는 셀 왼쪽이 **`[*]`** 로 보이고, 끝나면 숫자(`[1]`, `[2]` …)로 바뀝니다. 이 숫자가 실행 순서입니다. `import torch`처럼 몇 초 걸리는 셀도 있으니, **숫자가 나올 때까지 다시 누르지 말고 기다리세요.**

<a id="step-19"></a>
#### STEP 19 · 셀 1 — PyTorch 불러오기 (S19)

```python
import torch
print("PyTorch 버전:", torch.__version__)
```

- **예상 결과**: `PyTorch 버전: 2.8.0+cu128`
- **꼭 같아야 할 것**: 오류 없이 `PyTorch 버전:` 줄이 나오는 것 / **달라도 되는 것**: 버전 숫자

![셀 1 결과](screenshots/s19-cell1.png)

<details><summary>🎙️ 해설 대본 — STEP 19</summary>

> 이제 첫 셀을 실행해 봅니다. 맨 아래 빈 셀을 클릭하고 셀 1 코드를 붙여 넣은 뒤 `Shift+Enter`(시프트 엔터)를 누르세요. 셀 왼쪽이 잠깐 `[*]`로 보이다가 `[1]`로 바뀌고, `PyTorch 버전: 2.8.0+cu128`이 출력되죠? `[*]`는 지금 실행 중이라는 표시라서, `import torch`처럼 몇 초 걸려도 다시 누르지 말고 숫자가 나올 때까지 기다리면 됩니다.

</details>

<a id="step-20"></a>
#### STEP 20 · 셀 2 — GPU 정보 보기 (S20)

```python
print("CUDA 사용 가능:", torch.cuda.is_available())
print("GPU 이름:", torch.cuda.get_device_name(0))
print("GPU 전체 메모리(GB):", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1))
```

- **예상 결과**: `CUDA 사용 가능: True` / `GPU 이름: NVIDIA A40` / `GPU 전체 메모리(GB): 44.4`
- **꼭 같아야 할 것**: 첫 줄의 `True` / **달라도 되는 것**: GPU 이름, 메모리 숫자
- 첫 줄이 `False`라면 다음 두 줄에서 오류가 납니다. 그때는 더 진행하지 말고 10절 오류 해결의 "GPU가 안 보임"을 확인하세요.

![셀 2 결과](screenshots/s20-cell2.png)

- 셀 1에서 만든 `torch`를 셀 2가 그대로 씁니다. **노트북은 앞 셀에서 만든 변수를 기억합니다.** 그래서 셀은 위에서부터 순서대로 실행해야 합니다.
- **단위 주의**: 코드가 `1024**3`으로 나누므로 출력 라벨의 `GB`는 정확히는 **GiB**입니다(셀 3의 `MB`도 정확히는 **MiB**). 44.4GiB가 `nvidia-smi`의 46068MiB(약 45.0GiB)보다 조금 작은 것은 두 도구가 세는 범위가 달라서이며 정상입니다.

<details><summary>🎙️ 해설 대본 — STEP 20</summary>

> 셀 2에서는 GPU 정보를 봅니다. 결과는 `CUDA 사용 가능: True`, `GPU 이름: NVIDIA A40`, `GPU 전체 메모리(GB): 44.4`입니다. 그런데 셀 2에는 `import torch`가 없는데 어떻게 torch를 쓸 수 있었을까요? 노트북은 앞 셀에서 만든 것을 기억하기 때문이고, 그래서 셀은 위에서부터 순서대로 실행해야 합니다. 44.4가 `nvidia-smi`의 46068MiB보다 작아 보이는 건 단위가 GiB이고 세는 범위가 달라서이니 정상입니다.

</details>

<a id="step-21"></a>
#### STEP 21 · 셀 3 — GPU 메모리를 실제로 써 보기 (S21)

```python
x = torch.randn(4096, 4096, device="cuda")
y = x @ x
torch.cuda.synchronize()
print("이 노트북이 GPU에 만든 텐서(MB):", round(torch.cuda.memory_allocated() / 1024**2))
!nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

![셀 3 결과](screenshots/s21-cell3.png)

**텐서(tensor)** 는 숫자를 담은 표·행렬로, PyTorch가 계산할 때 쓰는 기본 단위입니다.

| 줄 | 하는 일 |
|---|---|
| `torch.randn(4096, 4096, device="cuda")` | 4096×4096 크기의 난수 행렬(텐서)을 **GPU 메모리에** 만듭니다. |
| `y = x @ x` | GPU에서 행렬 곱셈을 합니다. |
| `torch.cuda.synchronize()` | GPU 계산이 끝날 때까지 기다립니다. |
| `memory_allocated()` | PyTorch가 텐서용으로 잡은 VRAM 양 |
| `!nvidia-smi ...` | 줄 맨 앞 `!` 는 **노트북에서 터미널 명령을 실행**한다는 표시입니다. |

- **결과 읽기**: PyTorch가 텐서용으로 할당한 양은 `136`MiB인데 `nvidia-smi`의 GPU 전체 사용량은 `431 MiB`입니다. `nvidia-smi` 쪽에는 GPU를 쓰기 위한 기본 준비 공간(CUDA 컨텍스트), PyTorch가 다시 쓰려고 잡아 둔 여유 메모리(캐시), 다른 GPU 프로그램의 사용량까지 모두 들어가기 때문에 더 큽니다.
- **꼭 같아야 할 것**: 오류 없이 숫자 두 개(텐서 MB, `memory.used`)가 나오는 것 / **달라도 되는 것**: `136`, `431 MiB` 같은 숫자(GPU, 버전, 다른 프로그램에 따라 다름)

<details><summary>🎙️ 해설 대본 — STEP 21</summary>

> 셀 3에서는 GPU 메모리를 실제로 써 봅니다. 4096×4096 크기의 난수 행렬, 즉 텐서를 GPU에 만들고 곱셈까지 하죠. 결과를 보면 PyTorch가 만든 텐서는 `136`MB인데 `nvidia-smi`는 `431 MiB`를 쓰고 있다고 합니다. 왜 세 배 넘게 차이가 날까요? GPU를 쓰려면 CUDA 컨텍스트라는 기본 준비 공간과 다시 쓰려고 잡아 둔 여유 메모리가 따로 필요하기 때문입니다.

</details>

<a id="step-22"></a>
#### STEP 22 · 셀 4 — 노트북이 쓰는 파이썬 확인 (S22)

```python
import sys
print("이 노트북의 파이썬:", sys.executable)
```

- **예상 결과**: `/usr/local/bin/python` — STEP 11에서 Terminal의 `which python` 결과와 **같습니다**. 즉 이 Pod에서는 Terminal과 Notebook이 같은 파이썬을 씁니다.
- **꼭 같아야 할 것**: STEP 11의 `which python` 결과와 같은 경로인 것 / **달라도 되는 것**: 경로 자체(Pod 이미지에 따라 다를 수 있음)
- 마지막으로 `Ctrl+S`로 저장합니다.

![셀 4 결과와 저장](screenshots/s22-cell4-saved.png)

> 💡 맨 아래에 생긴 빈 셀은 그대로 둬도 됩니다. 지우려면 빈 셀을 클릭하고 `Esc`를 누른 뒤 `D`를 두 번 누릅니다.

<details><summary>🎙️ 해설 대본 — STEP 22</summary>

> 셀 4는 이 노트북이 쓰는 파이썬의 위치를 출력합니다. 결과는 `/usr/local/bin/python`이죠. STEP 11에서 터미널의 `which python`이 뭐라고 답했는지 기억나시나요? 똑같이 `/usr/local/bin/python`이었으니, 이 Pod에서는 터미널과 노트북이 같은 파이썬을 쓴다는 뜻입니다. 확인했으면 `Ctrl+S`로 저장합니다.

</details>

<a id="step-23"></a>
#### STEP 23 · 처음부터 다시 실행해 보기 (S23)

노트북은 **위에서 아래로 처음부터 다시 실행해도 같은 결과**가 나와야 제대로 된 노트북입니다.

- **행동**: ① 메뉴 **Kernel** → **Restart Kernel and Run All Cells…**

![Restart Kernel and Run All Cells](screenshots/s23-click-run-all.png)

- 확인 창 *Restart Kernel?* 에서 ② **Restart**를 누릅니다(모든 변수가 지워지고 처음부터 다시 실행됨). 체크박스 *Do not ask me again.* 은 건드리지 않습니다.

![Restart 확인](screenshots/s23-click-restart.png)

- **실행 중 모습**: Restart를 누르면 셀 4개의 번호가 모두 **`[*]`** 로 바뀌고 출력이 지워집니다. 맨 아래 상태 표시줄은 **`Busy`** 입니다.

![다시 실행 중: 모든 셀이 [*]](screenshots/s23d-run-all-in-progress-scratch.png)

*보충 촬영(임시 폴더에서 같은 노트북을 다시 실행, Restart를 누르고 약 2초 뒤)이라 경로 표시줄과 탭 줄이 다릅니다. 왼쪽 아래 상태 표시줄의 `Python 3 (ipykernel) | Busy`를 보세요.*

![셀 번호 [*] 확대](screenshots/s23e-run-all-in-progress-scratch-zoom.png)

*위 보충 촬영 그림의 셀 부분을 확대한 것입니다.*

- 그다음 위에서부터 `[1]` → `[2]` → `[3]` → `[4]` 순서로 숫자와 결과가 다시 채워집니다. 보충 촬영에서는 끝까지 약 8초 걸렸습니다.
- **성공 확인**: **`[*]`가 하나도 남지 않고** 셀 번호가 `[1]`~`[4]`이며, 상태 표시줄이 **`Idle`** 로 돌아오면 끝입니다. 결과는 STEP 19~22와 같습니다. `Ctrl+S`로 저장합니다. 실행 도중에도 상태 표시줄이 잠깐 `Idle`로 보일 때가 있으니(보충 촬영에서 관찰) `[*]`가 모두 사라졌는지 함께 확인하세요.

![다시 실행 완료](screenshots/s23c-run-all-done.png)

- STEP 22에서 빈 셀을 남겨 뒀다면 맨 아래에 빈 셀 `[ ]:`이 하나 더 보여도 정상입니다.
- `[*]`로 바뀌는 모습 없이 그대로라면 확인 창에서 Cancel을 누른 것입니다. ①부터 다시 하세요.

<details><summary>🎙️ 해설 대본 — STEP 23</summary>

> 노트북이 제대로 만들어졌는지 처음부터 다시 실행해 보겠습니다. 메뉴 ① Kernel에서 Restart Kernel and Run All Cells…(리스타트 커널 앤드 런 올 셀즈)를 고르고 확인 창에서 ② Restart를 누르세요. 셀 번호가 모두 `[*]`로 바뀌고 출력이 지워졌다가, 위에서부터 `[1]`, `[2]`, `[3]`, `[4]`로 다시 채워지죠? 보충 촬영에서는 약 8초 걸렸습니다. `[*]`가 하나도 남지 않고 상태 표시줄이 Busy(비지)에서 Idle로 돌아오면, 처음부터 다시 돌려도 같은 결과가 나오는 노트북이라는 뜻입니다.

</details>

<a id="step-24"></a>
#### STEP 24 · 커널을 꺼서 GPU 메모리 돌려주기 (S24)

1. **Terminal 탭**에서 `nvidia-smi`를 실행합니다. 노트북 커널이 VRAM을 잡고 있는 것이 보입니다(431MiB, 프로세스 `/usr/local/bin/python` 422MiB).

```bash
nvidia-smi
```

![커널이 VRAM 사용 중](screenshots/s24a-nvidia-smi-kernel-alive-zoom.png)

2. **gpu_check.ipynb 탭**으로 가서 메뉴 **Kernel** → ① **Shut Down Kernel**.

![Shut Down Kernel](screenshots/s24-click-shutdown-kernel.png)

> ⚠️ **File 메뉴의 Shut Down이 아니라 Kernel 메뉴의 Shut Down Kernel**입니다. `File` → `Shut Down`은 JupyterLab 전체를 끕니다(잘못 눌렀다면 10절 마지막 줄 참고).

오른쪽 위가 `No Kernel`로 바뀝니다.

![No Kernel](screenshots/s24b-kernel-shutdown.png)

3. 다시 **Terminal 탭**에서 `clear` 후 `nvidia-smi`를 실행합니다.

```bash
clear
nvidia-smi
```

![커널 종료 후 VRAM 0MiB](screenshots/s24d-vram-released-zoom.png)

- **성공 확인**: 프로세스 목록에서 노트북 커널(`/usr/local/bin/python`)이 사라지고, 그 커널이 쓰던 메모리가 돌아옵니다. 다른 GPU 작업이 없던 촬영 환경에서는 `0MiB / 46068MiB`, `No running processes found`가 되었습니다.
- **꼭 같아야 할 것**: 종료 전에 보이던 python 프로세스가 사라지는 것(다른 GPU 작업이 없으면 `0MiB`) / **달라도 되는 것**: 431MiB, 422MiB 같은 숫자

> ⚠️ **탭을 닫는 것과 커널을 끄는 것은 다릅니다.** 노트북 탭만 닫으면 커널은 계속 살아서 VRAM을 잡고 있습니다. 큰 모델을 다루는 다음 강의부터는 이 차이가 매우 중요합니다.

<details><summary>🎙️ 해설 대본 — STEP 24</summary>

> 커널이 GPU 메모리를 붙잡고 있는 모습을 직접 확인해 봅니다. 터미널 탭에서 `nvidia-smi`를 실행하면 `431MiB / 46068MiB`, 그리고 프로세스 목록에 `/usr/local/bin/python`이 `422MiB`를 쓰고 있죠? 이게 바로 노트북 커널입니다. 노트북 탭에서 File이 아닌 Kernel 메뉴의 ① Shut Down Kernel을 누르면 오른쪽 위가 No Kernel로 바뀌고, 다시 `nvidia-smi`를 보면 `0MiB`와 `No running processes found`로 돌아옵니다. 탭만 닫아서는 커널이 꺼지지 않는다는 것, 꼭 기억하세요.

</details>

### Part F. 마무리

<a id="step-25"></a>
#### STEP 25 · 만든 파일 확인 (S25)

```bash
ls -la
```

![ls -la 결과](screenshots/s25-ls-la-zoom.png)

- `ls -la`: 숨김 파일까지 포함해 파일 목록을 자세히 보여 줍니다. 맨 오른쪽이 이름, 그 왼쪽의 `Oct 27 18:05` 같은 값이 수정 시각(UTC), 그 왼쪽 숫자가 크기(바이트)입니다.
- 위쪽 두 줄의 `.`은 지금 폴더(`llm-course`), `..`은 한 단계 위 폴더(`/workspace`)입니다. `..`은 누구나 쓸 수 있는 폴더라서 터미널이 이름을 **초록 칸**으로 칠해 보여 줍니다.
- **성공 확인**: `check_gpu.py`와 `gpu_check.ipynb`가 있으면 완료입니다. `.ipynb_checkpoints`는 JupyterLab이 만드는 자동 백업 폴더입니다.
- **달라도 되는 것**: 크기 숫자. 촬영 때 `check_gpu.py`는 182바이트였지만 붙여 넣는 방식(마지막 줄바꿈 등)에 따라 몇 바이트 달라질 수 있으니 **약 180바이트**면 정상입니다.

<details><summary>🎙️ 해설 대본 — STEP 25</summary>

> 마지막으로 만든 파일을 확인합니다. 터미널에서 `ls -la`(엘에스 마이너스 엘에이)를 입력하세요. `check_gpu.py`는 182바이트, `gpu_check.ipynb`는 2503바이트로 보이죠? `.ipynb_checkpoints`는 JupyterLab이 자동으로 만드는 백업 폴더이고, 크기 숫자는 붙여 넣는 방식에 따라 조금 달라도 괜찮습니다. 두 파일이 보이면 실습 파일은 모두 완성입니다.

</details>

<a id="step-26"></a>
#### STEP 26 · Pod 끄기 (S26)

> ⚠️ **커널 종료나 브라우저 닫기로는 GPU 요금이 멈추지 않습니다.** Pod를 **Stop**해야 시간당 요금(촬영한 A40: $0.60)이 멈춥니다.

- **현재 화면**: RunPod 콘솔(`console.runpod.io`). JupyterLab 탭은 닫아도 됩니다.
- **행동**: 왼쪽 메뉴 **Pods** → 내 Pod 이름을 누릅니다(STEP 1 그림과 같은 위치). 오른쪽 상세 패널 위쪽의 빨간 ① **Stop**을 누르고, 확인을 묻는 창이 나오면 확인합니다(RunPod 공식 문서: *"Click the Stop button (square icon) and confirm."*).

![Stop 버튼 위치](screenshots/s26-click-stop.png)

*STEP 2의 상세 패널 그림에 Stop 위치를 덧그린 그림입니다. Stop 확인 창과 Stop 뒤의 화면은 촬영하지 않았습니다(콘솔은 로그인이 필요해 자동 촬영을 할 수 없고, 촬영에 쓴 Pod는 다른 강의 제작에 계속 쓰기 때문입니다).*

- **성공 확인**: Pods 목록에서 내 Pod 이름 앞의 **초록 점이 사라졌는지** 확인합니다.
- **켜 둔 Pod가 여러 개면**: 쓰지 않는 Pod도 같은 방법으로 모두 Stop합니다. 초록 점이 켜진 Pod는 하나하나 따로 요금이 나갑니다.
- ⛔ **Terminate**(휴지통 아이콘)는 누르지 마세요. Pod를 **삭제**하는 것이라 **되돌릴 수 없습니다.** 이 강의에서는 Stop만 씁니다.
- Stop해도 `/workspace`의 `llm-course` 폴더와 두 파일은 남습니다(13절). 다음에 Pod를 다시 켜면 이어서 쓸 수 있습니다.

<details><summary>🎙️ 해설 대본 — STEP 26</summary>

> 실습이 끝났으면 Pod를 꺼야 합니다. 커널을 끄거나 브라우저를 닫으면 요금도 멈출까요? 아닙니다, Pod가 켜져 있는 동안은 시간당 0.60달러가 계속 나갑니다. RunPod 콘솔 Pods에서 내 Pod 이름을 누르고 상세 패널 위쪽의 빨간 ① Stop을 누른 뒤, 목록에서 이름 앞 초록 점이 사라졌는지 확인하세요. Terminate(터미네이트)는 Pod를 지워서 되돌릴 수 없으니 이 강의에서는 누르지 않습니다.

</details>

---

## 07. 전체 완성 코드

| 파일 | 위치(Pod) | 저장소 사본 |
|---|---|---|
| Python 파일 | `/workspace/llm-course/check_gpu.py` | [`code/check_gpu.py`](code/check_gpu.py) |
| Notebook | `/workspace/llm-course/gpu_check.ipynb` | [`notebooks/gpu_check.ipynb`](notebooks/gpu_check.ipynb) (실행 결과 포함) |
| 셀별 코드 | — | [`notebooks/cells/`](notebooks/cells/) (`cell1.py` ~ `cell4.py`) |
| Terminal 명령 모음 | — | [`scripts/commands.sh`](scripts/commands.sh) |

**`check_gpu.py`** (STEP 13과 동일)

```python
import torch

print("PyTorch:", torch.__version__)
print("CUDA Available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
```

**Terminal 명령 순서** (STEP 8~25)

```bash
pwd                      # STEP 8
cd /workspace/llm-course # STEP 8
nvidia-smi               # STEP 9
clear                    # STEP 10
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv   # STEP 10
python --version         # STEP 11
which python             # STEP 11
clear                    # STEP 15
python check_gpu.py      # STEP 15
nvidia-smi               # STEP 24-1: 커널이 살아 있을 때
clear                    # STEP 24-3
nvidia-smi               # STEP 24-3: 커널을 끈 뒤 다시 확인
ls -la                   # STEP 25
```

## 08. 실행 결과

- 스크린샷: [`screenshots/`](screenshots/) — 모두 2026-10-28 실제 촬영(민감정보 가림, 클릭 표시는 덧그림). 보충 촬영 그림은 파일 이름에 `scratch`가 붙어 있고(`s06-click-llm-course.png`는 보충 촬영 그림 위에 클릭 표시를 덧그린 것), 그림 아래에 따로 적었습니다.
- 원본 로그: [`logs/terminal-commands.ssh-rerun.log`](logs/terminal-commands.ssh-rerun.log)
  - JupyterLab Terminal의 글자는 마우스로 선택해 복사할 수 있지만, 촬영 도구가 화면 글자를 자동으로 읽어 오지는 못합니다(그림처럼 그려지는 방식). 그래서 촬영 직후 **같은 Pod에서 같은 명령을 SSH로 다시 실행해** 텍스트로 남겼습니다. 시각과 온도 같은 값만 화면과 조금 다릅니다.
- 성공 판별 기준: [`expected-output/`](expected-output/)

```text
$ python check_gpu.py
PyTorch: 2.8.0+cu128
CUDA Available: True
GPU: NVIDIA A40
```

## 09. 코드 및 명령어 해설

### Terminal 명령

| 명령 | 하는 일 | 이 강의에서 본 결과 |
|---|---|---|
| `pwd` | 지금 위치 출력 | `/workspace/llm-course` |
| `cd /workspace/llm-course` | 폴더 이동(성공하면 아무것도 출력하지 않음) | 프롬프트가 `/workspace/llm-course#`로 바뀜 |
| `clear` | 화면 지우기 | 빈 화면 |
| `nvidia-smi` | GPU 상태 전체 보기 | A40, 0MiB / 46068MiB |
| `nvidia-smi --query-gpu=... --format=csv` | 원하는 항목만 표로 | `NVIDIA A40, 46068 MiB, 0 MiB` |
| `python --version` | 파이썬 버전 | `Python 3.12.3` |
| `which python` | `python` 명령이 실제로 가리키는 파일 | `/usr/local/bin/python` |
| `python check_gpu.py` | 파이썬 파일 실행 | 세 줄 출력 |
| `ls -la` | 숨김 파일 포함 자세한 목록 | 파일 2개 + 백업 폴더 |

### `check_gpu.py` 한 줄씩

| 줄 | 코드 | 뜻 |
|---|---|---|
| 1 | `import torch` | PyTorch 라이브러리를 불러옵니다. |
| 3 | `print("PyTorch:", torch.__version__)` | 설치된 PyTorch 버전을 출력합니다. `+cu128`은 CUDA 12.8용이라는 뜻입니다. |
| 4 | `print("CUDA Available:", torch.cuda.is_available())` | PyTorch가 GPU를 쓸 수 있으면 `True`입니다. |
| 6 | `if torch.cuda.is_available():` | GPU를 쓸 수 있을 때만 아래 줄을 실행합니다. |
| 7 | `print("GPU:", torch.cuda.get_device_name(0))` | 0번 GPU의 이름을 출력합니다. 앞의 공백 4칸이 "if 안쪽"이라는 표시입니다. |

### Notebook에서 알아 둘 것

- **셀 실행 순서가 곧 프로그램 순서**: 셀 2는 셀 1의 `torch`를 씁니다. 순서를 건너뛰면 `NameError`가 납니다.
- **`[*]`**: 셀이 실행 중이라는 표시입니다. 끝나면 실행 순서 숫자로 바뀝니다.
- **`!명령`**: 노트북 안에서 터미널 명령을 실행합니다.
- **Restart Kernel and Run All Cells…**: 기억하던 변수를 모두 지우고 처음부터 다시 실행합니다. 노트북이 깨끗하게 재현되는지 확인하는 습관입니다.
- **Shut Down Kernel**: 커널을 꺼서 VRAM을 돌려줍니다.

## 10. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| Pod 이름 앞이 초록 점이 아니거나 Jupyter Lab이 `Ready`가 아님 | Pod가 아직 시작 중 | 1~2분 기다린 뒤 새로고침 |
| `Ready`인데 JupyterLab이 빈 화면 | 첫 로딩 지연 | 30~60초 뒤 `Ctrl+Shift+R`(Mac `⌘⇧R`, 강력 새로고침) |
| *Token authentication is enabled* 화면 | 토큰 없이 주소로 직접 들어감 | RunPod 콘솔 Connect 패널의 **Jupyter Lab** 링크로 다시 열기 |
| 새 폴더 이름이 `Untitled Folder`로 남음 | 화면 반영 지연, 또는 이름을 치기 전에 다른 곳을 클릭함 | 잠시 기다리기. 그대로면 오른쪽 클릭 → **Rename (F2)** → `llm-course` (바로 아래 Delete는 누르지 않기) |
| `bash: ㅔㅈㅇ: command not found`처럼 `command not found` 앞 글자가 한글 | 한글 입력 상태로 명령을 침 | 한/영 키로 영문으로 바꾼 뒤 다시 입력 |
| `groups: cannot find name for group ID 109` | 이미지 설정상 표시되는 안내 | 무시해도 됨 |
| 프롬프트는 `:/#`인데 `pwd`는 `/workspace/llm-course` | 프롬프트 표시가 늦게 반영됨 | `cd /workspace/llm-course`로 명확히 이동 |
| `bash: cd: /workspace/llm-course: No such file or directory` | 폴더가 없거나 이름이 다름(`LLM-course`, `llm_course`, `Untitled Folder` 등) | 왼쪽 File Browser에서 `/ workspace /` 바로 아래 폴더 이름 확인 → 다르면 오른쪽 클릭 → **Rename (F2)** → `llm-course` → 다시 `cd` |
| `nvidia-smi: command not found` 또는 GPU가 안 보임 | GPU 없는 Pod이거나 Pod가 꺼짐 | Pods 화면에서 GPU 종류와 Running 상태 확인 |
| 출력 글자가 섞여 보임 | 앞 명령이 끝나기 전에 다음 명령을 입력 | 결과를 확인한 뒤 다음 명령 입력 |
| `IndentationError` | 7행 앞 공백이 깨짐 | 7행 앞은 공백 4칸. 코드 상자의 복사 아이콘으로 통째로 다시 복사해 붙여 넣기 |
| `python: can't open file ... check_gpu.py: No such file or directory` | 다른 폴더에서 실행했거나, 파일 이름이 다름(`untitled.py`, `check_gpu.py.py`) | `pwd`로 위치 확인 → `cd /workspace/llm-course`. 이름이 다르면 왼쪽 목록에서 파일 오른쪽 클릭 → **Rename (F2)** → `check_gpu.py` |
| 노트북 첫 저장 때 *Rename file* 창이 뜨지 않음 | STEP 13에서 *Do not ask for rename on first save.* 를 켬 | 왼쪽 목록에서 `Untitled.ipynb` 오른쪽 클릭 → **Rename (F2)** → `gpu_check.ipynb` |
| 같은 이름의 폴더나 파일이 이미 있음 | 이 강의를 다시 하는 중 | STEP 5의 '이 강의를 다시 하는 경우' 참고(지우지 말고 이름 바꿔 보관) |
| `NameError: name 'torch' is not defined` | 셀 1을 실행하지 않고 셀 2를 실행, 또는 커널을 끈 뒤 셀 하나만 다시 실행 | 셀 1부터 순서대로, 또는 Restart Kernel and Run All Cells… |
| 노트북을 닫았는데 VRAM이 줄지 않음 | 탭만 닫고 커널은 살아 있음 | **Kernel → Shut Down Kernel**, 또는 왼쪽 끝 세로 아이콘 줄의 위에서 두 번째(동그라미 안 네모) **Running Terminals and Kernels** 패널에서 그 커널 종료 |
| 실습을 마쳤는데 Pods 목록에 초록 점이 남아 있음 | Pod가 아직 실행 중(요금이 계속 나감) | STEP 26대로 **Stop** (Terminate는 삭제라 누르지 않기) |
| 메뉴 `File` → `Shut Down`을 눌러 JupyterLab이 끊김 | JupyterLab 서버 자체를 꺼 버림 | RunPod 콘솔에서 Pod의 ⋮ 메뉴 → **Restart Pod** (`/workspace` 파일은 남음) |

> ⚠️ **절대 하지 말 것**: 터미널에서 `env`, `printenv`를 실행한 화면을 캡처하거나 공유하지 마세요. Pod 안에는 `RUNPOD_API_KEY` 같은 비밀 값이 환경변수로 들어 있습니다.
>
> ⚠️ RunPod의 JupyterLab에서 파일을 지우면 **휴지통 없이 바로 삭제**됩니다.

## 11. 응용 실습

> STEP 24에서 커널을 껐으므로, 노트북을 다시 쓰는 실습(1·2번)은 먼저 노트북 탭에서 커널을 다시 연결(오른쪽 위 `No Kernel` 클릭 → `Python 3 (ipykernel)` 선택)하고 **Kernel → Restart Kernel and Run All Cells…** 로 셀 1~4를 다시 실행한 뒤 진행하세요. 셀 3만 실행하면 새 커널에는 `torch`가 없어서 `NameError: name 'torch' is not defined`가 납니다. 실습이 끝나면 커널을 다시 끄고(STEP 24) Pod를 Stop하세요(STEP 26).

1. **GPU 상태를 1초마다 보기**: `nvidia-smi -l 1` (멈출 때는 `Ctrl+C`, Mac도 같음). 먼저 위 안내대로 셀 1~4를 다시 실행한 뒤, 다른 탭에서 노트북 셀 3을 실행하며 메모리 숫자가 바뀌는 것을 관찰해 보세요.
2. **더 큰 텐서 만들기**: 위 안내대로 셀 1~4를 다시 실행한 뒤, 셀 3의 `4096`을 `8192`로 바꾸고 다시 실행해 보세요. 텐서 메모리가 약 4배가 되는지 확인합니다(가로·세로가 각각 2배).
3. **온도와 전력 보기**: `nvidia-smi --query-gpu=temperature.gpu,power.draw,utilization.gpu --format=csv`
4. **`python3`로 실행해 보기**: `python3 check_gpu.py` — 이 Pod에서는 `python`과 같은 파이썬이라 결과가 같습니다.

<details><summary>🎙️ 해설 대본 — 마무리</summary>

> 오늘은 RunPod의 Pod에 JupyterLab으로 접속해서 GPU를 세 가지 방법으로 확인했습니다. 터미널의 `nvidia-smi`는 NVIDIA A40과 46068MiB를, 파이썬 파일은 `CUDA Available: True`를, 노트북은 GPU에서 실제로 계산하는 모습까지 보여 줬죠. 꼭 기억할 것 세 가지는 무엇일까요? 파일은 Stop해도 남는 `/workspace` 안에 만들고, 탭을 닫는 것과 커널을 끄는 것은 다르며, 실습이 끝나면 Pod를 Stop해 요금을 멈춘다는 것입니다. 다음 강의에서는 브라우저 대신 SSH로 Pod에 접속하는 방법을 배웁니다.

</details>

## 12. 완료 체크리스트

- [ ] RunPod Connect 패널에서 Jupyter Lab을 열었다.
- [ ] `/workspace/llm-course` 폴더를 만들고 그 안으로 들어갔다.
- [ ] Terminal에서 `pwd`, `cd`, `clear`, `nvidia-smi`, `ls -la`를 실행했다.
- [ ] `nvidia-smi`에서 GPU 이름, 드라이버 버전, 메모리 총량을 읽을 수 있다.
- [ ] `check_gpu.py`를 만들어 저장하고 `CUDA Available: True`를 확인했다.
- [ ] `gpu_check.ipynb`에서 셀 4개를 실행하고, Restart Kernel and Run All Cells…로 다시 실행했다(`[*]`가 `[1]`~`[4]`로 바뀌는 것을 봤다).
- [ ] 커널을 끄면 `nvidia-smi`에서 그 커널 프로세스가 사라지고 메모리가 돌아오는 것을 확인했다.
- [ ] 실습을 마친 뒤 Pod를 **Stop**하고, Pods 목록에서 초록 점이 사라진 것을 확인했다.
- [ ] 접속 주소와 `env` 출력을 공유하면 안 되는 이유를 설명할 수 있다.

## 13. 다음 강의 준비

- **유지할 것**: `/workspace/llm-course/` 폴더와 두 파일. `/workspace`는 Pod를 **Stop**해도 남습니다.
- **실습을 마칠 때**: 커널 종료나 브라우저 닫기로는 GPU 요금이 멈추지 않습니다. **STEP 26**대로 RunPod 콘솔 → **Pods** → 내 Pod → **Stop**을 누르고, 이름 앞 초록 점이 사라졌는지 확인하세요.
- **Pod 상태**:
  - **Stop**: GPU 요금은 멈추고 `/workspace`는 남습니다. 저장소 요금은 계속 나갑니다. 다시 Start할 때 같은 GPU를 못 받을 수 있습니다.
  - **Terminate**: Pod를 삭제합니다. **되돌릴 수 없습니다.** Network Volume이 아닌 저장소의 파일은 모두 사라집니다. 내 Pod에 Network Volume이 있는지 모른다면 누르지 마세요. Network Volume은 Pod를 Terminate해도 따로 남아 계속 과금되므로, 필요 없으면 왼쪽 메뉴 **Storage**에서 따로 지워야 합니다.
  - Pod 안에 `pip install`로 설치한 것은 Stop하면 사라집니다(다음 강의부터 대비 방법을 다룹니다).
- **다음 강의**: C02-L03 SSH로 Pod 접속하기 / C02-L04 Bash 기초와 작업 환경 만들기

## 14. 공식 참고 자료

- RunPod — Connect to a Pod: https://docs.runpod.io/pods/connect-to-a-pod
- RunPod — Storage types (Container disk / Volume / Network volume): https://docs.runpod.io/pods/storage/types
- RunPod — Manage Pods (Stop, Restart, Terminate): https://docs.runpod.io/pods/manage-pods
- JupyterLab — Working with files: https://jupyterlab.readthedocs.io/en/stable/user/files.html
- JupyterLab — Terminals: https://jupyterlab.readthedocs.io/en/stable/user/terminal.html
- JupyterLab — Notebooks: https://jupyterlab.readthedocs.io/en/stable/user/notebook.html
- PyTorch — torch.cuda: https://docs.pytorch.org/docs/stable/cuda.html
- NVIDIA — nvidia-smi: https://docs.nvidia.com/deploy/nvidia-smi/index.html
