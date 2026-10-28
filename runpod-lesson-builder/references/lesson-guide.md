# 레슨 제작 계약 (일반화판)

과정 저장소의 `docs/LESSON_GUIDE.md`(= `assets/LESSON_GUIDE.template.md`를 채운 것)는 제작 에이전트가 읽는 짧은 계약서다. 이 문서는 그 계약의 **세부 규칙과 이유**, 그리고 템플릿을 채우는 법이다. 형식이 헷갈리면 그 과정의 파일럿 레슨을 그대로 따른다. 파일럿이 생기기 전에는 `assets/example-lesson/`(LLM 과정 파일럿 C02-L02의 글 파일 사본, 13 PASS, 그림 없음 — 원본은 작성자의 LLM 과정 저장소(비공개)의 `chapters/chapter-02/lesson-02-first-gpu-check`)과 `assets/readme-template.md`·`assets/playbook-template.yaml`을 기준으로 한다.

## 1. 원칙
- 독자는 **비개발자**다. README 하나만 보고 처음부터 끝까지 따라 할 수 있어야 한다(영상 없이).
- 레슨 하나 = 목표 하나. 모든 숫자·출력·화면은 **그 레슨을 실제 Pod에서 실행한 결과**다. 추정치는 '추정', 못 한 것은 '실행하지 않음(이유)'.
- 문체: 한국어, 쉬운 말, 기술 용어는 처음 나올 때 영어 병기와 짧은 설명. UI 라벨·명령·파일 이름은 화면 그대로(영어). 단축키는 Windows 기준 + Mac 표기(`Ctrl` → `⌘ Cmd`).
- 영상은 사용자가 레슨을 골라 요청할 때만 만든다(`ai-concept-visualization-video`). 그 전에는 `storyboard.md`·`narration.md`를 만들지 않는다. 대신 README의 🎙️ 해설 대본이 나중에 영상 대본의 바탕이 된다.
- 모델은 토큰이 필요 없는 공개 모델이 기본이다. gated 모델(접근 신청·토큰이 필요한 모델)은 사용자가 승인했을 때만 쓰고, 그때 Hugging Face 토큰은 사용자가 Pod에서 `hf auth login`으로 직접 넣는다(또는 `/root`의 파일). 토큰 값은 명령줄·노트북·로그에 남기지 않고, 입력 화면은 찍지 않거나 가린다. README에는 학습자가 자기 토큰을 넣는 절차를 같은 방식으로 쓴다.

## 2. 환경 계약 표 채우는 법
| 항목 | 채우는 법(실측) | LLM 과정 기본값(2026-10-28, 참고용) |
|---|---|---|
| Pod A/B | 콘솔 Pods 목록의 이름, Compute type, 템플릿 이미지 태그 | A40 48GB ×2, `runpod/pytorch:1.4.1-cu1281-torch280-ubuntu2404` |
| 공유 저장소 | `df -h /workspace`, 콘솔 Storage. 두 Pod가 같은 Network Volume인지 | 두 Pod가 Network Volume 50GB를 `/workspace`로 공유 |
| 학습자 작업 폴더 | 과정 하나에 폴더 하나(`init_course.py --pod-root`), 챕터별 하위 폴더 `chNN`, 파일 `lMM_설명.py/.ipynb` | `/workspace/llm-course/chNN/` |
| venv | 고정 버전의 단일 원본은 `environment/setup.sh`(TRAIN_PKGS·SERVE_PKGS). 표에는 lock 파일(`/workspace/.course-env/<과정폴더 이름>/*.lock`)과 `setup.sh` 마지막 출력에서 확인한 주요 버전, 커널 이름 | train: `setup.sh` 고정값(실측 torch 2.14.1+cu132) — 커널 `Python (train)` / serve: `vllm[bench]==0.32.0`(실측 torch 2.13.0+cu132, transformers 5.19.0), `/root/venvs/serve/bin/vllm` |
| venv 재생성 | `setup.sh` 실행 시간 | `bash /root/setup.sh` 약 2분 |
| 학습자 환경 | 학습자가 venv·커널을 만드는 레슨과 그 전 레슨이 쓰는 환경(5절 '03 준비물') | 파일럿 C02-L02는 시스템 Python(`Python 3 (ipykernel)`), 학습자가 venv를 만드는 레슨은 C02-L04(`setup.sh`) |
| 모델 캐시 | `HF_HOME`(공유 볼륨), 미리 받은 모델, 크기 상한, gated 여부 | `Qwen/Qwen3-0.6B`, `Qwen/Qwen3-4B-Instruct-2507`(Apache-2.0, 게이트 없음), 10GB 넘는 모델은 받지 않음 |
| 고정값 | 과정 전체에서 바꾸지 않는 값(한 곳에서만 정한다) | LoRA r=16, `--max-lora-rank 16`, `--max-model-len 8192`, `--served-model-name qwen`, `--tool-call-parser hermes`, `--enable-auto-tool-choice`, reasoning parser 없음 |
| 자원 레인 | 레인 = Pod·GPU 한도·포트 묶음(`parallel-production.md` 1절) | 레인 6개(같은 챕터는 한 레인 — `parallel-production.md` 예시 표) |

LLM 과정에서 교재에 넣기로 한 버전 함정(실측): hook 출력은 Tensor, hook 반환값은 출력을 대체, SDPA는 attention 미반환(eager 필요), `apply_chat_template`는 BatchEncoding, TRL은 `max_length`, vLLM 기본 `--gpu-memory-utilization` 0.92 → `pitfalls.md` E절. 조사 단계의 주의(실측 아님): 메인 모델 기본 컨텍스트가 길어 `--max-model-len`을 반드시 준다, `--max-lora-rank` ≥ 어댑터 r, 노트북에서 건 hook·패치는 vLLM 엔진에 반영되지 않는다(반영 경로: 가중치(LoRA·merge), `--model-impl transformers`, 플러그인), LoRA 서빙 뒤 베이스와 같은 프롬프트로 비교해 '조용히 무시'되지 않았는지 확인.

## 3. 증거 규칙
| 종류 | 만드는 법 | 위치 | 규칙 |
|---|---|---|---|
| 명령 로그 | 학습자와 같은 폴더에서 SSH로 실행, `2>&1 \| tee` | `logs/*.log` | 첫 줄 `# source: ssh-run (Pod A, <날짜>)`. dev 폴더 실행은 증거가 아니다 |
| Terminal 화면의 글자 | 읽기만 하는 명령을 촬영 직후 같은 폴더에서 SSH로 다시 실행 | `logs/*.ssh-rerun.log` | 첫 줄 `# source: ssh-rerun (Pod A, <날짜>, 화면 STEP N)`, 명령마다 `$ <명령>` 줄. 상태를 바꾸는 명령은 다시 실행하지 않는다(Terminal에서 `tee`로 남기거나 화면 판독, README 08절에 이유) |
| 노트북 | 로컬 `nbformat` 작성 → Pod에서 nbconvert 실행(또는 UI 실행) | `notebooks/*.ipynb`, `notebooks/cells/cellN.py` | 화면에 찍힌 그 실행의 저장본 하나. 실행 번호 1..n, 코드 셀마다 출력(출력이 없어야 하는 셀은 셀 태그 `no-output`. 옛 방식인 첫 줄 `# no-output` 주석도 통과하지만 학습자 코드에 남는다) |
| 화면 | `jlab.py`(JupyterLab — 코드 파일 STEP은 `new_file_paste`), 메인 세션 Chrome 확장(콘솔), `webshot.py`(공개 웹) | `_raw/` → `screenshots/` | 각 STEP의 **행동 직후 화면**. 공개는 `redact.py`를 거친 것만 |
| 클릭 위치 | `annotate.py`(마스킹본 위) | `screenshots/*-click-*.png` | '덧그림'이라고 README 머리말·캡션에 밝힘 |
| 촬영 기록 | `_raw/capture-log.jsonl` | `_raw/` | file(= `_raw` 안의 파일 이름, redact-spec 키와 같게), step, kind, note, source, tool, pod, copied_at(원본을 저장한 ISO 시각) |
| 확대 그림 | 원본에서 PIL로 자르기 | `*-zoom.png` | 자른 좌표를 capture-log의 tool에 |
| 보충 촬영 | 같은 사양 Pod의 컨테이너 디스크 `/root/scratch-<레슨>/`에서 그 상태만 | `*-scratch.png` | README 그림 아래에 다른 점, 촬영 뒤 폴더 삭제 |
| 공유 촬영 | 다른 레슨이 찍은 콘솔 원본을 같이 쓸 때(메인 세션만 콘솔을 찍을 수 있어서) | 그 레슨 `_raw/`에 복사 | 그림 아래에 '공유 촬영(<날짜>, <원래 레슨>)' |

- 공개 산출물에 IP·포트·Pod ID·토큰·키·SSH 지문이 있으면 불합격. 컨테이너 호스트 이름(`root@<컨테이너>`)은 가리지 않아도 된다.
- 콘솔 화면 마스킹 대상: 잔액, 아바타 이름, Pod ID, IP:포트, SSH 사용자, SSH 키 지문.
- 로그를 손으로 고치지 않는다. 허용되는 손질은 비밀값을 `<POD_IP>` 같은 자리 표시로 바꾸기와 관계없는 줄 생략뿐이고, 그 로그 첫머리(출처 줄 다음)에 `# edited: <무엇을 왜>`를 남긴다.

## 4. 레슨 폴더
```text
chapters/chapter-NN/lesson-MM-slug/
├── README.md            ← 5~8절 형식
├── playbook.yaml        ← 단일 원본(10절 스키마)
├── troubleshooting.md   ← 12절 형식
├── code/  notebooks/(cells/)  scripts/commands.sh
├── logs/  expected-output/
├── screenshots/         ← 공개(마스킹본·클릭 표시본·_masking.json)
├── _raw/                ← 원본·명세·촬영 기록(git 제외)
└── evidence-manifest.json  ← check_lesson.py가 만든다
```

## 5. README 14절
| 절 | 꼭 들어갈 것 |
|---|---|
| 머리말(인용 블록) | '이 문서만 보고 따라 할 수 있게…', 표: 촬영일(KST)·GPU(장수, Cloud)·이미지 태그·JupyterLab·Python/PyTorch(+ 이 레슨 패키지)·보충 촬영. 템플릿·GPU가 다르면 무엇이 달라 보이는지, UTC 시계 안내, 마스킹·주황 번호의 뜻 |
| 🎙️ 해설 대본 — 시작 | 머리말 바로 아래(8절) |
| 01 목표 | 목표 한 문단 + 할 일 목록 + 익히는 기본 동작 |
| 02 최종 결과 미리 보기 | 실제 결과 그림(마스킹본) |
| 03 준비물 | 표: 실행 중인 Pod(만드는 레슨, 없으면 공식 문서), **앞 레슨에서 이어지는 것**(처음 하는 경우·다시 하는 경우), **파이썬 환경**(아래 규칙), 브라우저, 키보드(Mac·한/영), 추가 설치, 비용(시간당 요금, 켜 둔 Pod마다 과금) |
| 04 핵심 개념 | 쉬운 말 + 비유, 그림은 `../../../shared/diagrams/…` + '*설명용 그림*' |
| 05 작업 화면·파일 구조 | 시작 화면, 작업 공간, 완료 후 Pod 안 파일 트리(어느 STEP에서 만드는지) |
| 06 단계별 따라 하기 | Part로 묶은 STEP들(6절). 맨 앞에 '성공 확인 읽는 법' |
| 07 전체 완성 코드 | 표(파일, Pod 위치, 저장소 사본 링크) + 완성 코드 + 명령 순서 |
| 08 실행 결과 | 스크린샷·로그·expected-output 링크, ssh-rerun 이유(다시 실행하지 않은 명령은 화면에서 읽었다고), 대표 출력 |
| 09 코드·명령 해설 | 표(명령/코드, 하는 일, 이 강의에서 본 결과), 코드 한 줄씩 표 |
| 10 오류 해결 | 표(증상, 원인, 해결) — 실제로 겪은 것 우선, 화면 문구 그대로 + '절대 하지 말 것'(env·printenv 캡처, 휴지통 없는 삭제) |
| 11 응용 실습 | 하나씩 바꿔 보기. 다시 실행 전 준비(커널 재연결 등) 먼저 |
| 🎙️ 해설 대본 — 마무리 | 12절 체크리스트 바로 앞 |
| 12 완료 체크리스트 | 확인 가능한 문장의 체크박스 |
| 13 다음 강의 준비 | 유지할 것, 끌 것, Pod를 다시 켰을 때 다시 만들 것(컨테이너 디스크의 venv 등), Stop vs Terminate, 다음 레슨 |
| 14 공식 참고 자료 | URL 목록(공식 문서 우선). **직접 열어 제목을 확인한 URL만** 쓴다(`webshot.py`로 열어 보거나 브라우저로 확인) — 검사기는 http 링크를 확인하지 않는다 |

**03 준비물의 파이썬 환경 규칙** — 학습자가 이 레슨의 코드를 어떤 인터프리터·커널로 돌리는지 반드시 정해 쓴다.
- (a) 앞 레슨이 환경(venv·커널)을 만들면 그 레슨 링크를 걸고, '다시 하는 경우'(Pod를 Stop했다 켜서 `/root`가 비었을 때) 다시 만드는 명령을 적는다.
- (b) 그런 레슨이 없으면(새 과정의 첫 레슨 등) 이 레슨 안에 '환경 준비' Part를 넣어 명령을 README에 그대로 쓰거나, 시스템 Python(`Python 3 (ipykernel)`)과 `pip install <패키지>==<버전>`을 쓴다(시스템 설치는 Stop 때 지워진다는 것도 적는다).
- (c) 제작 실행도 학습자와 같은 인터프리터·커널로 한다. 제작자가 미리 받아 둔 모델처럼 학습자 화면과 다를 수 있는 것(첫 다운로드 크기·시간, 진행 표시)은 '달라도 되는 것'에 적는다.

제목 꼴은 `## 01. 이번 강의 목표` … `## 14. 공식 참고 자료`(파일럿과 같게). 검사기는 STEP 구역을 '다음 STEP 앵커 또는 코드 블록 밖의 다음 `## ` 제목'에서 끊으므로, STEP 안에서는 `##` 제목을 쓰지 않는다(`###` Part, `####` STEP).

## 6. STEP 형식
```markdown
<a id="step-7"></a>
#### STEP 7 · Terminal 열기 (S07)

- **현재 화면**: …            ← 이 STEP이 시작될 때 화면
- **행동**: ① **Terminal**을 누릅니다.   ← UI 라벨 굵게, 번호는 클릭 표시 그림의 번호와 같게

![Terminal 위치](screenshots/s07-click-terminal.png)   ← 그 행동 바로 아래

- **결과**: …
- **성공 확인**: …
- **꼭 같아야 할 것**: … / **달라도 되는 것**: …   ← 비교하는 STEP

<details><summary>🎙️ 해설 대본 — STEP 7</summary>
…
</details>
```
- 앵커 `step-N`은 playbook `readme_anchor`, 괄호 `(SNN)`은 playbook `id`와 같다. 그림은 playbook `screenshots`에 적은 것이 **그 STEP 구역 안(또는 앞 STEP 구역 안)**에 있어야 한다(검사기 3b — 02 미리 보기에만 있는 그림은 인정하지 않는다).
- 그림을 찍지 못했으면 그림 자리에 playbook `not_captured`와 같은 문구를 그대로 쓴다(예: *촬영하지 않음: 콘솔은 로그인이 필요해 자동 촬영할 수 없다*).
- Terminal 명령은 코드 블록 + '명령 | 뜻' 표, '한 줄 입력 → Enter → 결과 확인 → 다음 줄'. 입력 전 '영문 입력 상태' 확인.
- 학습자가 틀리기 쉬운 곳은 ⚠️ 상자(이름 창의 함정, File 메뉴 Shut Down, Terminate), 반영 지연은 💡 상자, 비용은 💰, 다시 하는 경우는 🔁.
- 보충 촬영 그림 아래에는 *기울임*으로 무엇이 다른지 적는다. 다른 레슨의 폴더가 화면에 보이면 '달라도 되는 것'에 적는다.
- 노트북 STEP: 노트북 만들기(Launcher의 **Notebook** 구역 커널 카드 — 바로 아래 **Console** 구역과 헷갈리지 않게) → 첫 저장 이름 창 → 커널 상태(`Connecting` → `Idle`) → '셀 실행 방법'(맨 아래 빈 셀 클릭, `Ctrl+V`, `Shift+Enter`, `[*]` → 숫자) → 셀마다 STEP(현재 화면, 행동, 코드, 그림, 예상 결과). 틀은 `assets/readme-template.md` STEP 4·5, 실제 예는 `assets/example-lesson` STEP 16~23.

## 7. 코딩 블록 (코드 파일을 만드는 STEP은 반드시)
| 항목 | 내용 |
|---|---|
| **파일 위치** | Pod 안 전체 경로 |
| **현재 화면** | 예: JupyterLab 편집기(`untitled.py` 탭) |
| **수행할 행동** | 코드 상자 전체 복사 → 편집기 빈 곳 클릭 → `Ctrl+V`(Mac `⌘V`) |
| **파일 이름** | 첫 저장 때 정함, 입력은 확장자 없이 |
| **코드 입력** | 아래 코드 상자(`code/`의 파일과 같음) |
| **저장** | `Ctrl+S` → *Rename file* → 이름만 입력 → **Rename and Save** |
| **실행 환경** | 03절의 파이썬 환경(예: JupyterLab Terminal에서 `source <venv>/bin/activate` 뒤, 또는 시스템 `python`) |
| **실행 명령어** | 예: `python lMM_x.py` |
| **결과 확인** | 성공 줄 그대로 |
| **스크린샷** | 붙여 넣은 모습 → 이름 창 → 실행 결과 |

- 스크린샷 세 장은 `jlab.py`의 `new_file_paste()`(Launcher → Python File → 붙여 넣기 → 첫 `Ctrl+S` → 이름 창 → 저장)나 메인 세션의 Chrome 확장으로 학습자처럼 만들며 찍는다. 그러려면 그 파일이 챕터 폴더에 아직 없어야 한다(개발은 `/root/dev-<레슨>/`). 끝내 찍지 못한 장면은 `not_captured`로 이유를 적는다(다른 그림으로 대신하지 않는다).
- README의 실행 명령은 학습자 기준으로 쓰고, 제작 때의 SSH 명령(`/root/venvs/train/bin/python …`)은 쓰지 않는다.

## 8. 🎙️ 해설 대본
블록 제목 문자열은 검사기와 **글자 하나까지 같아야** 한다: `🎙️ 해설 대본 — 시작`, `🎙️ 해설 대본 — STEP N`, `🎙️ 해설 대본 — 마무리` (`🎙️` = U+1F399 U+FE0F, 줄표는 `—` U+2014, 앞뒤 공백 한 칸). 템플릿에서 복사해 쓴다.
```markdown
<details><summary>🎙️ 해설 대본 — STEP 9</summary>

> (말하듯 쓴 문장 3~6개)

</details>
```
- **위치**: 시작 = 머리말 표 바로 아래 / STEP N = 모든 STEP 구역의 끝(그 STEP의 그림·성공 확인 다음) / 마무리 = 12절 체크리스트 앞.
- **내용 순서**: 지금 화면이 어디인지 → 어디를 누르거나 무엇을 입력하는지 → 화면에 무엇이 나타나는지(실제 숫자 그대로) → 그 결과가 무슨 뜻인지(쉬운 비유) → 다음에 무엇을 하는지. 시작 = 무엇을 왜 하고 끝나면 무엇을 할 수 있는지, 마무리 = 한 일 요약 + 핵심 개념 2~3개 + 다음 강의 예고.
- **말투**: 강사가 화면을 가리키며 말하는 습니다체, 2~3문장마다 질문형('~일까요?', '~죠?'). 화면의 영어 라벨·명령은 그대로, 필요하면 읽는 법을 괄호로(예: `nvidia-smi`(엔비디아 에스엠아이)). 비밀값·IP는 말하지 않는다.
- 파일럿 예(STEP 9): "> 이제 핵심 명령 `nvidia-smi`(엔비디아 에스엠아이)를 입력합니다. 표가 하나 나오죠? GPU 이름은 NVIDIA A40, 메모리 칸은 `0MiB / 46068MiB`로 아직 아무도 쓰지 않는 상태입니다. …"

## 9. `LESSON_GUIDE.template.md` 채우기
`init_course.py`가 `{{COURSE_TITLE}}`, `{{DATE}}`, `{{REPO_PATH}}`, `{{REPO_GITBASH}}`, `{{POD_ROOT}}`, `{{POD_ROOT_REL}}`, `{{VENVS}}`, `{{KERNEL}}`, `{{KERNEL_LABEL}}`, `{{LOCKDIR}}`, `{{EXAMPLE_LESSON}}`을 채운다. 남은 `<…>`는 Phase 2 실측 뒤 메인 세션이 채운다: 1절 환경 표(2절 표 참고), 학습자 환경, 파일럿 경로, 자원 분배 표(레인), 모델 크기 상한. 템플릿에 적힌 LLM 과정 기본값은 **참고용**이다 — 표에는 이번 Pod에서 `setup.sh` 출력·lock 파일·`nvidia-smi`로 다시 확인한 값만 쓴다(같으면 그대로, 다르면 고친다). 비우거나 지어낸 값으로 두고 병렬 제작을 시작하지 않는다.

## 10. playbook.yaml 스키마
```yaml
lesson: {id, title, captured_at, environment: {gpu, image, driver, jupyterlab, python, pytorch, …}, start_condition, done_condition}
steps:
  - {id, part, screen, env, cwd, action, ui_target, file, command, code_file, change, save, run,
     result, success_check, screenshots, not_captured, logs, concept, readme_anchor, scene_id, troubleshooting, expected_output}
troubleshooting: {T01: "증상 → 해결", …}
```
| 필드 | 뜻 |
|---|---|
| `id` `part` `screen` `env` `result` `screenshots` `readme_anchor` `scene_id` | **필수**(비면 검사기 FAIL). `screenshots`는 `not_captured`가 있을 때만 비어도 된다 |
| `not_captured` | 그림을 찍지 못한 이유(예: "촬영하지 않음: 콘솔은 로그인이 필요해 자동 촬영할 수 없다"). README 그 STEP 구역에 같은 문구가 있어야 한다(검사기 3b). evidence-manifest에 들어간다 |
| `screen` | 이 STEP이 시작될 때 보이는 화면 |
| `env` | 브라우저 / 브라우저(JupyterLab) / Bash (JupyterLab Terminal) / Notebook 커널 |
| `cwd`, `command` | Terminal STEP의 현재 폴더와 입력 명령(여러 줄은 `|`) |
| `action`, `ui_target` | 화면에서 하는 행동, 누르는 라벨 목록(화면 그대로) |
| `file`, `code_file`, `change`, `save`, `run` | 만들거나 고치는 Pod 파일, 저장소 사본, new/modify, 저장 방법, 실행 방법 |
| `success_check` | 학습자가 확인할 기준 |
| `logs`, `expected_output` | 근거 로그, 성공 판별 파일 |
| `concept` | 이 STEP의 개념 한 줄 |
| `scene_id` | 짧은 구역 이름(예: `C-terminal`). 영상을 만들면 장면 ID가 된다 |
| `troubleshooting` | 이 STEP 관련 T 번호(아래 사전·README 10절·troubleshooting.md와 같은 ID) |

`lesson.id`, `lesson.captured_at`, `lesson.environment`는 evidence-manifest에 들어간다.

## 11. expected-output 형식
```text
# log: logs/terminal-commands.ssh-rerun.log
# after: $ python check_gpu.py
# 성공 판별 기준(정규식, 한 줄에 하나). 실제 출력은 맨 아래 주석.
^PyTorch: \d+\.\d+\.\d+
^CUDA Available: True$
# 실제 출력(날짜, GPU):
#   PyTorch: 2.8.0+cu128
```
`# log:`(레슨 기준 경로, 필수), `# after:`(선택, 이 글자 뒤부터 검사), 나머지 `#` 아닌 줄은 정규식(`re.M`). GPU·버전처럼 달라도 되는 부분은 패턴으로 넓힌다.

## 12. troubleshooting.md 형식
머리말(근거: 촬영 중 관찰 / 공식 문서 / README-only 점검) + 표 `| ID | 단계 | 증상 | 원인 | 해결 | 근거 |` + '보안 주의'. ID는 playbook·README 10절과 같다. 근거 칸에 실측 그림(`screenshots/…`)이나 문서 이름을 적는다.

## 13. 품질 게이트
1. `python tools/check_lesson.py <레슨폴더>` → 모두 PASS(항목과 고치는 법: `verification.md` 1절). 그림이 없는 것은 README에서 링크하지 않는다.
2. README를 처음부터 초보자 입장에서 다시 읽는다: 빠진 클릭·경로·명령·성공 기준, 정해지지 않은 파이썬 환경.
3. 실패한 단계는 원인을 고쳐 다시 실행. 끝내 못 하면 '실행하지 않음(이유)'.
4. Pod에서 자기가 띄운 서버·커널·Terminal·tmux와 dev·scratch 폴더를 모두 정리.
