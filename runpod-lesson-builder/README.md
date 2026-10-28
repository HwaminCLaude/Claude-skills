# runpod-lesson-builder

**RunPod GPU Pod에서 실제로 실행한 결과로, 비개발자가 혼자 따라 하는 실습 교재(README)를 만드는** Claude Code 스킬.

화면 캡처·로그·숫자를 모두 실제 Pod에서 얻습니다. 예상 출력이나 그린 화면으로 대신하지 않습니다.
레슨 하나 = 폴더 하나이고, README 하나만 보고 처음부터 끝까지 따라 할 수 있게 쓰는 것이 목표입니다.

2026-10-28 하룻밤에 **56개 레슨짜리 LLM 실습 과정**(Hugging Face 로딩 → 모델 내부 → LoRA·QLoRA → vLLM 서빙 → Tool Calling → 성능 → FastAPI 서비스 → 처음부터 재구축)을 이 방식으로 만들었고, 그때 쓴 도구·순서·함정을 그대로 정리했습니다.

---

## 무엇이 나오나

레슨 폴더 하나당:

| 파일 | 내용 |
|---|---|
| `README.md` | 14절 형식. STEP마다 "지금 화면 → 누를 곳 → 입력 → 저장·실행 → 기대 결과"와 그 바로 아래 **실제 화면**(민감정보는 모자이크) |
| 🎙️ 해설 대본 | STEP마다 강사가 말하듯 풀어 쓴 접는 블록(시작·마무리 포함). 영상은 원하는 레슨만 따로 |
| `playbook.yaml` | 단계별 단일 원본(화면, 행동, 파일, 명령, 성공 판별, 근거 그림·로그) |
| `troubleshooting.md` | 실제로 겪었거나 문서에 있는 오류와 해결 |
| `logs/`, `expected-output/` | 실제 실행 로그, 로그와 맞춰 보는 기대 출력(정규식) |
| `code/`, `notebooks/`, `scripts/` | 실행한 코드와 실행이 끝난 노트북 |
| `screenshots/` | 마스킹한 실화면만(원본은 git에서 빠지는 `_raw/`) |
| `evidence-manifest.json` | 그림마다 어느 STEP·어떤 촬영인지 |

과정 저장소 전체로는 `curriculum.md`, 제작 계약서 `docs/LESSON_GUIDE.md`, 시작 인터뷰 기록 `docs/DECISIONS.md`, 끝난 뒤 `REPORT.md`가 생깁니다.

## 어떻게 진행되나

0. **시작 인터뷰** — 알아낼 수 있는 것은 먼저 조사하고(저장소, 이전 결정, Pod 접속, Chrome의 RunPod 로그인, 로컬 도구), 사람만 정할 수 있는 것은 선택지 대화창으로 묻습니다.
   - 범위, 산출물(README / 해설 대본 / 영상), 대상, 커리큘럼
   - 쓸 Pod, GPU 2장 레슨, 예산, 끝난 뒤 Pod
   - 병렬 제작 여부, 자리 비움 점검, 내용 검토 깊이, 공개 계획
   - 결정은 `docs/DECISIONS.md`에 남기고, 검사기와 제작 에이전트가 그 값을 따릅니다.
1. **사전 점검**(읽기 전용) → 보고 → 승인
2. **Pod 환경** — 버전을 고정한 `setup.sh`로 venv를 만들고 실측 버전을 기록
3. **파일럿 레슨 1개** — 실제 실행 → 헤드리스 JupyterLab 실화면 캡처 → 마스킹 → README·해설 대본 → 품질 검사(`check_lesson.py`)
4. **README만 보고 재현 검증** — README만 읽은 별도 에이전트가 행동 목록을 뽑고, 초보자 시각으로 비평
5. **병렬 제작** — Pod·GPU 메모리·포트를 레인으로 나눠 여러 레슨을 동시에(Workflow, 사용자 동의 시)
6. **끝난 뒤 내용 검토** — 표본 검토 + 레슨 사이 정합성(다음 강의 예고, 색인 문서, 고정값) → 수정 → 전체 재검사
7. **REPORT.md** → 이번에 쓴 **Pod Stop**(Terminate는 사용자가 따로 요청할 때만)

## 요구 환경

| 항목 | 용도 | 비고 |
|---|---|---|
| **RunPod 계정**과 크레딧 | 실습 Pod | Pod Deploy와 결제는 사용자가 확인·승인 |
| **SSH 공개키 등록**(RunPod 콘솔 → Credentials → SSH Public Keys) | `pod.sh`로 Pod에 명령, 로그 수집 | 계정 설정이라 사용자가 직접 |
| **Claude in Chrome** 확장 + RunPod 로그인 | 콘솔 화면 촬영, Pod 끄기 | 메인 세션만 사용 |
| **Git Bash**(Windows) | `pod.sh`, `pod_get.sh` | |
| **Python 3.10+** + `python -m pip install pyyaml pillow playwright nbformat` + `python -m playwright install chromium` | 캡처(`jlab.py`, `webshot.py`), 마스킹, 품질 검사 | |
| Claude Code의 **Workflow** 도구 | 여러 레슨 병렬 제작 | 사용자가 요청할 때만. 없으면 레슨을 차례로 |
| **codex CLI**(선택) | 읽기 전용 교차 리뷰 | |

## 설치

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force .\runpod-lesson-builder "$env:USERPROFILE\.claude\skills\"
```

## 쓰는 법

스킬이 시작 인터뷰로 나머지를 물어봅니다. 짧게 이렇게 시작하면 됩니다.

```text
/runpod-lesson-builder 레슨 하나만 만들어줘: Hugging Face 토크나이저로 한국어 문장 토큰 수 세기. 연결해 둔 Pod 써줘.
```

```text
runpod-lesson-builder 스킬로 {{주제}} 실습 과정을 만들어줘.
- 대상: {{예: 코딩을 모르는 비개발자}}
- 범위: {{챕터·레슨 목록, 또는 "커리큘럼부터 제안"}}
- Pod: {{연결해 둔 Pod 이름 / "A40 1장 새로" — 새로 만들 땐 가격 보여 주고 확인받기}}
- 산출물: 레슨별 README + STEP별 해설 대본. 영상은 {{만들지 않음 / 요청한 레슨만}}
- 진행: 파일럿 1개를 먼저 보여 주고, 승인하면 나머지는 워크플로로 병렬 제작
- 끝나면: REPORT.md를 쓰고 쓴 Pod는 모두 Stop
```

이미 만든 과정을 이어서 할 때는 "이 과정 다음 레슨 이어서 만들어줘", "남은 챕터 README 전부 만들어줘"처럼 말하면 `docs/DECISIONS.md`를 읽고 바뀐 것만 묻습니다.

## 폴더 구성

```
runpod-lesson-builder/
├── SKILL.md                 ← 스킬 본문(절차·규칙). Claude가 읽고 따라 함
├── README.md                ← (이 파일)
├── scripts/                 ← init_course · pod/pod_get · jlab · webshot · redact · annotate ·
│                               check_lesson · setup.sh · stackcheck.sh (과정 저장소 tools/로 복사해 씀)
├── references/              ← intake-interview(시작 인터뷰) · workflow · lesson-guide ·
│                               runpod-jupyterlab-facts · pitfalls · verification · parallel-production
└── assets/                  ← README·playbook·결정 기록 틀, LESSON_GUIDE 틀, 병렬 제작·재현 검증 워크플로 틀,
                                예시 레슨(글 파일만)
```

## 지키는 규칙

- 실제로 실행·촬영한 결과만 씁니다. 못 한 것은 README에 '실행하지 않음(이유)'로 밝힙니다.
- API 키·토큰·IP·포트·Pod ID는 어떤 파일·그림에도 남기지 않습니다. `env`·`printenv`·필터 없는 `ps`를 쓰지 않고, 토큰이 든 주소창은 찍지 않습니다. Windows 데스크톱 전체는 캡처하지 않습니다.
- 새 Pod·Start·볼륨 증설 같은 결제는 품목과 가격을 보여 주고 승인받은 뒤에만 합니다. 끝나면 이번에 쓴 Pod만 Stop합니다.
- 커밋·푸시는 요청할 때만 합니다.

## 알아 둘 점

- 하룻밤 제작에서 나온 도구와 규칙을 정리한 것입니다. 다른 과정에서는 버전·화면 라벨을 다시 실측합니다(시작 인터뷰와 사전 점검이 그 일을 합니다).
- `jlab.py`에 새로 넣은 일부 기능(새 파일 붙여 넣기, Terminal 정리)은 로컬 JupyterLab 4.5.1에서만 시험했습니다.
- 품질 검사를 모두 통과해도 내용 오류는 남을 수 있습니다. 56개 레슨 제작 때 표본 4개에서 레슨당 약 5건이 나와, 끝난 뒤 내용 검토 단계를 넣었습니다.
- 규모가 큰 과정은 시간·토큰·Pod 비용이 큽니다. 56개 레슨에 Pod 3대 약 19시간, 약 $24(추정)가 들었습니다.
- 스킬 검사기(skill-creator 스킬의 `quick_validate.py`)를 Windows에서 돌릴 때는 `PYTHONUTF8=1`을 붙입니다.
