# 실제로 겪은 함정과 해결 (LLM 과정 제작, 2026-10-28)

실제 제작 중에 일어났거나 실측으로 확인한 것이다. 각 항목: **증상** → 원인 → **해결**(스킬 어디에 반영됐는지) · 근거.
`(코드 검토)` 표시는 겪기 전에 원본 도구의 코드를 읽다가 찾아 이 스킬 판에서 고친 것이다.
README의 '오류 해결'에 넣을 학습자용 함정은 G절에 따로 모았다.

## A. 이 PC(Windows)·SSH

1. **Git Bash ssh가 `~/.ssh`에 쓰지 못함** — 사용자 폴더 이름이 한글(`C:\Users\<한글이름>`)이면 Git Bash의 ssh가 `~/.ssh/known_hosts`를 열지·쓰지 못한다.
   → **해결**: 호스트 키를 저장소 `.ssh/known_hosts`(git 제외)에 두고 `-o UserKnownHostsFile=...`, `StrictHostKeyChecking=accept-new`로 처음 접속 때 등록한다(`scripts/pod.sh`·`pod_get.sh`·`jlab.py`). `~/.ssh/config`는 고치지 않는다. 키 파일(`-i ~/.ssh/id_ed25519`)은 읽힌다. · `environment/preflight-report.md`, pod.sh 주석
2. **공백이 있는 저장소 경로** — 저장소가 `D:/My Course/...`처럼 공백을 품으면 `UserKnownHostsFile` 값이 잘린다.
   → **해결**: 값 안쪽에 따옴표를 한 겹 더: bash `-o "UserKnownHostsFile=\"$ROOT/.ssh/known_hosts\""`, Python `f'UserKnownHostsFile="{kh}"'`. · pod.sh, jlab.py
3. **Git Bash가 Windows 프로그램 인자의 `/경로`를 바꿈** — Git Bash에서 `python init_course.py … --pod-root /workspace/x`를 실행하면 MSYS가 인자를 `C:/Program Files/Git/workspace/x`로 바꿔 넘겼다(이 스킬을 만들며 시험하다 겪음). bash 스크립트(`pod.sh`·`pod_get.sh`)와 그 안의 ssh·scp에는 생기지 않는다.
   → **해결**: Windows 프로그램(python.exe 등)에 Pod 경로를 넘길 때는 앞의 `/`를 빼거나(`workspace/x`) 명령 앞에 `MSYS_NO_PATHCONV=1`. `init_course.py`는 바뀐 값을 알아채고 멈춘다. · scripts/init_course.py
4. **cp949 콘솔에서 한글·기호 출력** — 파이프로 받은 출력이 cp949로 인코딩되어 기호가 깨지거나 `UnicodeEncodeError`.
   → **해결**: 모든 스크립트가 `sys.stdout.reconfigure(encoding="utf-8")`. 스킬 검사기(skill-creator 스킬의 `quick_validate.py`)처럼 파일을 기본 인코딩으로 읽는 도구는 `PYTHONUTF8=1`로 돌린다. · check_lesson.py 주석

## B. 화면 캡처

5. **Windows 화면 캡처가 다른 프로그램을 찍음** — PowerShell로 창을 캡처하는 방식이 엉뚱한 앱 화면을 저장했다.
   → **해결**: 그 이미지는 즉시 삭제, 방식 자체를 **금지**. RunPod 콘솔은 Chrome 확장 탭 캡처, JupyterLab은 `jlab.py` 헤드리스 캡처(레슨 에이전트)나 메인 세션의 Chrome 확장 탭 캡처만 쓴다. · preflight-report
6. **확장 탭 캡처는 1568px JPEG 축소본** — 전체 탭 캡처는 폭 1568 JPEG라 작은 글자가 흐리다. 확대(zoom) 캡처는 원본 픽셀 PNG.
   → **해결**: 작은 글자(HTTP services 줄, 대화상자 입력값)는 zoom 캡처를 따로 남긴다(`*-zoom.png`). `redact-spec.json` 좌표는 **그 원본 이미지의 픽셀 기준**(탭 캡처면 1568폭)으로 잡는다. · preflight-report, 파일럿 `_masking.json`(size 1568×744)
7. **최대화된 Chrome 창은 크기 조절이 안 됨** — 16:9(1600×900)로 맞추려던 resize가 무시됐다.
   → **해결**: 콘솔 캡처는 1920×911 viewport 그대로 쓰고, JupyterLab은 `jlab.py`(1600×900 고정)로 찍는다. · preflight-report
8. **Chrome 확장이 여러 개 연결됨** — 세션마다 어떤 브라우저를 조작할지 다시 골라야 했다.
   → **해결**: 콘솔 작업 전에 연결된 브라우저 목록을 보고 이 PC의 Chrome을 고른다. 브라우저 확장은 **메인 세션만** 쓴다(서브에이전트는 탭 그룹·브라우저 선택을 공유하지 못한다). · preflight-report, 승인 계획서 Step 6
9. **Terminal 글자를 뽑을 수 없음** — JupyterLab Terminal(xterm)은 canvas라 페이지 텍스트로 출력이 안 나온다.
   → **해결**: 촬영 직후 같은 Pod에서 같은 명령을 SSH로 다시 실행해 로그로 남기고 `ssh-rerun`으로 표시한다(파일 이름 `*.ssh-rerun.log`, README 08절에 이유와 '시각·온도는 화면과 조금 다름'을 적음). · preflight-report, 파일럿 README 08절
10. **놓친 화면 상태** — 이름 입력 칸이 열린 순간, Run All 진행 중 `[*]`처럼 지나가 버린 상태를 본 촬영에서 못 찍었다.
    → **해결**: '보충 촬영' — 같은 사양의 Pod 임시 폴더에서 그 상태만 다시 찍고 폴더를 지운다. 파일 이름에 `scratch`, README 그림 아래에 무엇이 다른지(경로 표시줄 등) 적는다. 파일럿은 `/workspace/c02l02-fix`(공유 볼륨)를 썼는데 다른 Pod의 촬영 화면에도 보일 수 있어, 이 스킬은 컨테이너 디스크 `/root/scratch-<레슨>/`을 쓴다(15번). · 파일럿 playbook 머리 주석, README STEP 5·17·23
11. **콘솔의 Stop 확인 창을 찍을 수 없음** — 촬영 Pod를 다른 레슨 제작에 계속 써야 해서 실제로 Stop할 수 없었다.
    → **해결**: 공식 문서 문장(*"Click the Stop button (square icon) and confirm."*)과 실제 Stop 버튼 위치(상세 패널 그림에 덧그림)로 쓰고, 그림 아래에 '촬영하지 않음(이유)'을 밝힌다. · 파일럿 STEP 26

## C. Pod 저장소·환경

12. **uv 캐시 22GB** — venv 두 개를 설치하면 uv 캐시가 22GB 쌓인다. 이미지 기본값은 `UV_CACHE_DIR`·`PIP_CACHE_DIR`가 `/workspace/.cache/…`라 그대로 두면 공유 Network Volume(50GB)을 채운다.
    → **해결**: `setup.sh`가 `UV_CACHE_DIR=/root/.cache/uv`(컨테이너 디스크)로 바꾸고 설치가 끝나면 `rm -rf`. · versions.md(serve 17GB, train 5.9GB, uv-cache 22GB), setup.sh
13. **컨테이너 디스크는 Stop 때 지워짐** — `/root/venvs`와 `/root/setup.sh`도 사라진다.
    → **해결**: venv는 컨테이너 디스크에 두고 Pod를 켤 때마다 `setup.sh`로 다시 만든다(실측 1.5~2분). 모델은 `HF_HOME=/workspace/.cache/huggingface`(남음)에 두고 다시 받지 않는다. Start 뒤에는 `setup.sh`를 다시 올리고 실행한다. 컨테이너 디스크는 80GB 이상 권장. · curriculum 결정 1(안 B), setup.sh 주석
14. **50GB Network Volume이 모자람** — venv 23GB + uv 캐시 22GB + 모델(0.6B 1.5GB, 4B 8GB, 14B 29.5GB)을 다 담을 수 없다.
    → **해결**: 위 13의 배치 + 10GB 넘는 모델은 받지 않는다. 증설은 사용자 결정(비용 확인 후). · curriculum 결정 1, LESSON_GUIDE 모델 캐시
15. **두 Pod가 `/workspace`를 공유** — 한 Pod에서 만든 실험 폴더가 다른 Pod의 촬영 화면(File Browser)에 보인다.
    → **해결**: 레슨은 자기 레슨이 만든 파일(`<과정폴더>/chNN/lMM_*`)만 만들고 지운다. 같은 챕터의 레슨은 한 레인에만 둔다(실제 실행에서는 C02·C04가 두 레인에 나뉘어 같은 챕터 폴더를 동시에 썼다). 개발·보충 촬영·재현 같은 제작용 폴더와 스택 실측은 컨테이너 디스크(`/root/dev-<레슨>/`, `/root/scratch-<레슨>/`, `/root/stackcheck`)에서 하고 끝나면 지운다(stackcheck 하나가 약 46GB를 쓴다). · preflight-report, stackcheck.sh 주석, run.log STEP 4, LESSON_GUIDE 레인 표
16. **SSH로 돌린 명령에 HF_HOME이 없음** — SSH 비대화형 셸은 `/etc/rp_environment`를 읽지 않아 모델 캐시 경로가 달라진다.
    → **해결**: HF를 쓰는 명령 앞에 `source /etc/rp_environment >/dev/null 2>&1;`(값은 절대 출력하지 않음). · LESSON_GUIDE
17. **반쯤 설치된 venv·남의 venv** `(코드 검토)` — 원래 `setup.sh`는 `bin/python`이 있는지만 봐서, 설치가 중간에 끊긴 venv나 같은 Pod를 쓰는 다른 과정의 venv(`/root/venvs/train`)를 '있음'으로 보고 이 과정의 패키지 목록을 조용히 건너뛰었다.
    → **해결**: 스킬의 `setup.sh`는 이미 있는 venv의 `uv pip freeze`를 고정 목록(이름==버전)과 비교해 다르면 아무것도 바꾸지 않고 `exit 3`으로 멈춘다. 남의 venv면 과정별 `VENVS`(`init_course.py --venvs`), 혼자 쓰는 Pod의 반쯤 깔린 venv면 `rm -rf /root/venvs/<이름>` 후 다시 실행. · scripts/setup.sh
18. **`nproc`·`free`가 호스트 값** — 할당은 vCPU 9 / RAM 50GB인데 `nproc`=96, `free`=503Gi.
    → **해결**: 데이터로더 worker 수 등은 `RUNPOD_CPU_COUNT`(이 변수 하나만 echo)를 기준으로 가르친다. · 승인 계획서 1절

## D. 동시 제작(레인)

19. **커널 정리가 남의 커널까지 끔** `(코드 검토)` — 원본 `jlab.shutdown_kernels()`는 설명('이 세션이 연 커널')과 달리 서버의 모든 커널을 지운다. 같은 Pod를 쓰는 다른 레인의 노트북 커널까지 죽일 수 있다.
    → **해결**: 스킬의 `jlab.py`는 기본으로 **이 JLab이 `open()`한 노트북의 커널만** 끈다(`prefix=`로 폴더 추가, `everything=True`는 혼자 쓸 때만). · scripts/jlab.py
20. **연결 실패 뒤 'port is busy'** `(코드 검토)` — 원본은 토큰 읽기나 브라우저 실행이 실패하면 SSH 터널을 남겨, 다음 실행이 같은 포트를 못 쓴다.
    → **해결**: `__enter__`가 실패하면 터널·브라우저를 정리하고 예외를 다시 던진다. 레슨마다 고유 로컬 포트를 쓴다. · scripts/jlab.py
21. **같은 GPU를 여러 레인이 씀** — vLLM 기본 `--gpu-memory-utilization`은 0.92(GPU 메모리를 거의 다 잡음)라, 같은 GPU를 다른 레인의 서버·노트북 커널이 쓰고 있으면 낮춰야 한다.
    → **해결**: 레인별 상한(예: 0.45 / 0.35), 학습은 `flock /root/gpu-train.lock` 안에서, 레인별 서버 포트(8000/8010/8020…), 끝나면 자기 세션만 종료. · LESSON_GUIDE 자원 분배 표, vllm_flags(default 0.92)

## E. 라이브러리 동작(실측, Qwen/Qwen3-0.6B·A40)

22. **forward hook의 반환값이 레이어 출력을 바꿈** — 스택 실측 스크립트 자신이 이 함정에 걸렸다: hook을 `lambda …: seen.setdefault(…)`로 써서 튜플을 반환 → 다음 레이어가 `AttributeError: 'tuple' object has no attribute 'dtype'`로 죽었다.
    → **해결**: 관찰용 hook은 반드시 `None`을 반환(`def keep(mod, a, o): ...` — return 없음). 스킬의 `stackcheck.sh`는 고쳐 두었다. 레슨에서는 '일부러 값을 반환하면 출력이 바뀐다'를 실험으로 보여 준다. · `verification/stackcheck-2026-10-28/run.log`, versions.md
23. **transformers v5 디코더 레이어 hook의 output은 Tensor** — `Tensor (1, 10, 1024)`. v4식 `output[0]`은 첫 배치만 잡는 조용한 버그. · versions.md
24. **SDPA는 attention을 돌려주지 않음** — `output_attentions=True`면 경고(`` `sdpa` attention does not support `output_attentions=True`. Please set your attention to `eager` …``)와 빈 결과. `model.set_attn_implementation("eager")` 뒤 `(1, 16, 10, 10)`. · run.log, versions.md
25. **`apply_chat_template(..., return_tensors="pt")`는 BatchEncoding** — `input_ids`, `attention_mask`를 함께 돌려주므로 `model.generate(**inputs)`로 넘긴다. · versions.md
26. **TRL `SFTConfig`** — `max_length`가 있고 `max_seq_length`는 없다. `SFTTrainer(quantization_config=…)`는 지원. · versions.md
27. **vLLM과 학습 스택 버전 충돌** — vLLM 0.32.0이 torch 2.13.0·transformers <5.20을 고정 → serve venv와 train venv를 나눈다(두 venv는 HTTP로만 통신). `uv pip install … --torch-backend=auto`가 torch cu132를 골랐다. · curriculum, versions.md
28. **vLLM 기본값** — `--max-lora-rank` 기본 16(선택지 1, 8, 16, 32, 64, 128, 256, 320, 512 — 어댑터 r 이상으로), `--host` 기본 None. · vllm_flags.txt, versions.md

## F. 비밀값

29. **`ps` 출력에 Jupyter 토큰이 그대로 나옴** — 필터 없는 `ps`나 `jupyter server list` 한 번으로 토큰이 대화 기록·로그에 남는다.
    → **해결**: 환경변수 값·프로세스 명령줄·`/jupyter.log`·`/etc/rp_environment`를 출력하지 않는다(명령 목록과 허용 명령은 SKILL.md '반드시 지킬 것 → 비밀값'). 토큰이 노출됐으면 사용자에게 알리고, Pod 재배포로 토큰을 바꿀지 묻는다. · preflight-report 보안 관찰
30. **명령줄 `--api-key`는 `ps`와 시작 로그에 찍힘** → vLLM 키는 환경변수 `VLLM_API_KEY`로만. · 승인 계획서 8절
31. **Jupyter Lab 링크에 `?token=`** — 주소창·링크 호버·기록을 찍으면 토큰이 샌다 → 탭 캡처·헤드리스 캡처만, 비밀값 스캔에 `token=` 패턴. · preflight-report

## G. 학습자 화면에서 실제로 관찰된 것 (README '오류 해결' 단골)

| 관찰 | README에 쓰는 해결 | 근거 |
|---|---|---|
| New Folder 뒤 `Untitled Folder`로 남아 보임(반영 지연 또는 이름 치기 전 다른 곳 클릭) | 1~2초 기다리기 → 그대로면 우클릭 → Rename (F2). 바로 아래 Delete 주의 | 파일럿 T04 |
| 프롬프트는 `:/#`인데 `pwd`는 작업 폴더 | `cd <작업 폴더>`로 확실히 이동, `cd`는 성공하면 출력 없음 | 파일럿 T06 |
| 명령을 빨리 연달아 치면 출력이 섞임 | 결과를 보고 한 줄씩 | 파일럿 T08 |
| 첫 저장 이름 창에 `.py`까지 치면 `.py.py` | 이름만 입력(확장자는 이미 있음), 체크박스는 건드리지 않기 | 파일럿 T10·T16 |
| 노트북 탭을 닫아도 VRAM이 안 줄어듦 | Kernel → Shut Down Kernel 또는 Running Terminals and Kernels | 파일럿 T11 |
| `groups: cannot find name for group ID 109` | 무시해도 됨 | 파일럿 T05 |
| 저장 직후 이름이 잠깐 `untitled.py`로 남음 | 1~2초 뒤 바뀜 | 파일럿 STEP 14 |
| 텐서 136MB인데 `nvidia-smi`는 431MiB | CUDA 컨텍스트·캐시·다른 프로그램 몫이 더해져서 정상 | 파일럿 STEP 21 |
| `torch.cuda` 메모리 44.4 'GB'와 `nvidia-smi` 46068MiB 차이 | 코드가 `1024**3`으로 나눠 GiB, 세는 범위도 다름 | 파일럿 STEP 20 |
| 여러 줄 명령을 Terminal에 붙여 넣으면 실행되지 않고 반전 표시로 멈춤(붙여 넣기 보호, bracketed paste). 밝은 테마 Terminal에서 반전은 **검은 바탕에 흰 글자**다 — README에 '흰 바탕'이라고 잘못 쓰기 쉽다(LLM 과정 12개 레슨에서 같은 오류를 고침). 커서도 흰 Terminal에서는 검은 네모 | Enter 한 번. 색·모양을 글로 쓰기 전에 그 STEP 그림을 열어 확인 | 2026-10-28 표본 검토·정합성 점검 |
| JupyterLab Terminal에서 바로 띄운 파이썬·`tail -f`·셸 반복문이 `Ctrl+C`로 안 멈춤(`^C`만 찍힘). 셸이 SIGINT를 '무시'로 물려받아 자식도 무시(`SigIgn`), 다른 창에서 보낸 `pkill -INT`도 무시됨 | `Ctrl+Z` → `kill %1`, 또는 다른 Terminal에서 `pkill -f <스크립트>`(SIGTERM, 종료 코드 143). 오래 도는 일은 tmux 안에서 돌린다(tmux 안에서는 `Ctrl+C` → `KeyboardInterrupt`, 130). `nvidia-smi -l`은 `Ctrl+C`로 멈춤. 입력 중인 줄 지우기에는 `Ctrl+C`가 됨. 레슨에 'Ctrl+C로 멈춘다'고 쓰기 전에 그 실행 환경에서 실측 | 2026-10-28 LLM 과정 C08-L01·C08-L04·C06-L02 실측 |

## H. 문서·게이트

32. **README만 보고는 못 따라 하는 곳** — 파일럿의 오류 해결 표에는 'README만 보고 재현' 점검에서 나온 증상이 들어갔다(파일럿 troubleshooting 머리말). 완성된 파일럿 README에는 Mac 단축키, 한/영 입력 상태, '이 강의를 다시 하는 경우', '꼭 같아야 할 것 / 달라도 되는 것', 보충 촬영 그림의 차이 설명 같은 장치가 있다.
    → **해결**: README-only 검증(행동 목록 + 초보자 비평)을 레슨마다 돌리고, 이 장치들을 템플릿(`assets/readme-template.md`)에 넣어 두었다. · 파일럿 README·troubleshooting.md, `verification.md`
33. **도구가 레슨 폴더에 상태 폴더를 만듦** — 파일럿 레슨 폴더 안에 에이전트 도구의 세션 로그·상태 폴더 `.omx/`가 생겼다(git 제외 목록에도 없었음).
    → **해결**: 외부 CLI는 레슨 폴더 밖에서 실행, `.gitignore`에 `.omx/`·`.omc/`, 비밀값 스캔은 점(.) 폴더를 공개 대상에서 뺀다. · 파일럿 폴더 관찰
34. **요구가 제작 도중에 바뀜** — 계획에는 레슨마다 영상이 있었는데 실행 중에 'README만(영상은 요청한 레슨만)', 'STEP마다 🎙️ 해설 대본 필수'로 범위가 바뀌었다.
    → **해결**: 워크플로를 멈추고 계약서(LESSON_GUIDE) → 검사기(check_lesson, 해설 대본 검사 추가) → 레슨 프롬프트 순서로 고친 뒤, '중간 작업이 있으면 이어서 하라'는 프롬프트로 다시 띄운다(`parallel-production.md` 6절). · 전 챕터 워크플로(쓰지 않는 영상 코드가 남아 있음), LESSON_GUIDE 3·4절
35. **IP 스캔 때문에 명령을 바꿈** — 레슨 비밀값 스캔의 IPv4 패턴이 `0.0.0.0`에도 걸려, C10-L05 에이전트가 `vllm serve`에서 `--host 0.0.0.0`을 뺐다(vLLM 0.32.0은 `--host`가 없으면 모든 주소에서 받는다).
    → **해결**: 레슨 게이트는 그대로 두고(명령에는 `localhost`를 쓰거나 설명으로), 저장소 스캔(`--repo`)은 루프백·`0.0.0.0`을 비밀값으로 보지 않는다. · C10-L05 playbook, `verification.md` 1절

## I. 이 스킬을 고치며 로컬 JupyterLab(4.5.1)으로 시험하다 찾은 것

36. **토큰이 오류 문구로 샘** `(코드 검토)` — `jlab.py`는 `…/lab?token=<토큰>`으로 처음 접속하므로, 터널이 안 열려 그 탐색이 실패하면 Playwright 오류 문구에 토큰이 든 주소가 그대로 실렸다(대화·워크플로 기록·REPORT로 샐 수 있음).
    → **해결**: 터널이 열렸는지 먼저 확인하고(안 열리면 토큰을 쓰기 전에 멈춤), `__enter__`·`__exit__`에서 오류 문구 속 토큰을 `<TOKEN>`으로 바꾼 새 예외를 던진다(원래 예외는 감춤). 결과를 옮길 때도 `token=` 뒤를 지운다. · scripts/jlab.py
37. **숨은 탭의 Launcher 카드를 누르려다 멈춤** — Launcher가 둘 이상 열려 있으면 `.jp-LauncherCard`의 첫 항목이 보이지 않는 탭의 카드라 클릭이 시간 초과됐다.
    → **해결**: `:visible` 카드만 누른다. · scripts/jlab.py
38. **편집기에 포커스가 있으면 `Ctrl+Shift+L`이 먹지 않음** — 코드를 붙여 넣은 뒤 새 Launcher가 생기지 않았다(편집기가 단축키를 가져감).
    → **해결**: Launcher 수가 늘지 않았으면 `File` 메뉴의 **New Launcher**를 누른다(`_new_launcher()`). · scripts/jlab.py
39. **첫 저장 이름이 겹치면 조용히 실패** — 이미 있는 이름을 넣고 **Rename and Save**를 누르면 창만 닫히고 새 파일은 `untitled.py`로 남았다.
    → **해결**: `new_file_paste()`가 저장 전에 그 이름이 있는지 보고(있으면 멈춤), 저장 뒤 탭 이름이 바뀌었는지 확인한다. 촬영 전에는 챕터 폴더를 학습자 시작 상태로 맞춘다. · scripts/jlab.py
