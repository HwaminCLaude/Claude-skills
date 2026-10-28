# C02-L02 오류 해결

README 10절과 같은 내용을 단계별로 다시 정리했습니다. 모든 항목은 2026-10-28 실제 촬영 중 관찰했거나, 공식 문서에 나오거나, 초보자 따라 하기 점검(README만 보고 재현)에서 나온 증상입니다.

| ID | 단계 | 증상 | 원인 | 해결 | 근거 |
|---|---|---|---|---|---|
| T01 | S01–S02 | Pod 이름 앞이 초록 점이 아니거나 Jupyter Lab이 `Ready`가 아님 | Pod가 아직 시작 중 | 1~2분 기다린 뒤 새로고침 | RunPod docs: expose-ports |
| T02 | S03 | `Ready`인데 JupyterLab이 빈 화면 | 첫 로딩 지연 | 30~60초 뒤 `Ctrl+Shift+R`(Mac `⌘⇧R`) | RunPod docs: jupyterlab-blank-page |
| T03 | S03 | *Token authentication is enabled* 화면 | 토큰 없이 주소로 직접 접속 | Connect 패널의 **Jupyter Lab** 링크로 다시 열기 | 실측: 링크에 `?token=` 포함 |
| T04 | S05 | 새 폴더가 `Untitled Folder`로 보임 | 프록시를 거친 화면 반영 지연, 또는 이름을 치기 전에 다른 곳을 클릭함 | 1~2초 기다리기, 그래도 그대로면 우클릭 → **Rename (F2)** → `llm-course` (바로 아래 Delete 주의) | 실측(`_raw/s05b-untitled-folder-stale.jpg`, `screenshots/s05e-new-folder-name-edit-scratch.png`) |
| T05 | S07 | `groups: cannot find name for group ID 109` | 이미지 설정상 안내 문구 | 무시 | 실측 |
| T06 | S08 | 프롬프트는 `:/#`, `pwd`는 `/workspace/llm-course` | 프롬프트 표시가 실제 위치를 늦게 반영 | `cd /workspace/llm-course` | 실측(`screenshots/s08a-pwd.png`) |
| T07 | S09 | `nvidia-smi: command not found` 또는 GPU 안 보임 | GPU 없는 Pod 또는 Pod 꺼짐 | Pods 화면에서 GPU 종류와 Running 확인 | — |
| T08 | S10 | 출력 글자가 섞임 | 앞 명령이 끝나기 전에 다음 명령 입력 | 결과 확인 후 다음 명령 | 실측(`screenshots/s10-typeahead-messy-zoom.png`) |
| T09 | S13 | `IndentationError` | 7행 앞 공백 4칸이 깨짐 | 코드 상자의 복사 아이콘으로 전체를 다시 복사해 붙여 넣기 | — |
| T10 | S15 | `python: can't open file ... check_gpu.py: No such file or directory` | 다른 폴더에서 실행했거나 파일 이름이 다름(`untitled.py`, `check_gpu.py.py`) | `pwd` → `cd /workspace/llm-course`. 이름이 다르면 우클릭 → **Rename (F2)** → `check_gpu.py` | 실측: Rename file 창에서 `untitled`만 선택됨(`screenshots/s13b-rename-dialog.png`) |
| T11 | S24 | 노트북 탭을 닫아도 VRAM이 줄지 않음 | 커널은 살아 있음 | **Kernel → Shut Down Kernel**, 또는 왼쪽 아이콘 줄 위에서 두 번째 **Running Terminals and Kernels** | 실측(431MiB → 0MiB) |
| T12 | 공통(S24) | `File` → `Shut Down`을 눌러 JupyterLab이 끊김 | JupyterLab 서버 종료 | RunPod 콘솔 Pod ⋮ → **Restart Pod** | 실측(메뉴 라벨) |
| T13 | S20 | `NameError: name 'torch' is not defined` | 셀 1을 건너뜀, 또는 커널을 끈 뒤 셀 하나만 다시 실행 | 셀 1부터 순서대로, 또는 Restart Kernel and Run All Cells… | — |
| T14 | S05, S08 | `bash: ㅔㅈㅇ: command not found`처럼 앞 글자가 한글, 또는 폴더 이름이 한글 자모 | 한글 입력 상태로 입력함 | 한/영 키로 영문으로 바꾼 뒤 다시 입력 | — |
| T15 | S08 | `bash: cd: /workspace/llm-course: No such file or directory` | 폴더가 없거나 이름이 다름(`LLM-course`, `llm_course`, `Untitled Folder`) | File Browser에서 `/ workspace /` 아래 이름 확인 → 우클릭 → **Rename (F2)** → `llm-course` → 다시 `cd` | — |
| T16 | S13, S17 | 노트북 첫 저장 때 *Rename file* 창이 뜨지 않음 | S13에서 *Do not ask for rename on first save.* 를 켬 | `Untitled.ipynb` 우클릭 → **Rename (F2)** → `gpu_check.ipynb` | 실측: 체크박스 위치(`screenshots/s13b-rename-dialog.png`, `screenshots/s17c-notebook-rename-dialog-scratch.png`) |
| T17 | S05, S17 | 같은 이름의 폴더·파일이 이미 있음 | 이 강의를 다시 하는 중 | 폴더는 새로 만들지 말고 S06으로. 기존 파일은 지우지 말고 `_old` 이름으로 바꿔 보관 | — |
| T18 | S26 | 실습을 마쳤는데 Pods 목록에 초록 점이 남아 있음 | Pod가 아직 실행 중(시간당 요금 계속) | **Stop** (Terminate는 Pod 삭제라 되돌릴 수 없음) | RunPod docs: manage-pods |

## 보안 주의
- `env`, `printenv`, `cat /etc/rp_environment` 출력은 촬영·공유 금지: `RUNPOD_API_KEY`, `JUPYTER_PASSWORD`가 들어 있습니다(실측: Pod 환경변수에 존재).
- JupyterLab 탭의 주소(`...-8888.proxy.runpod.net`)는 토큰과 함께 열리므로 공유 금지.
- RunPod JupyterLab의 삭제는 휴지통 없이 영구 삭제입니다(`delete_to_trash=False`).
