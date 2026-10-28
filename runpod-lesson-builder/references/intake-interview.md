# 시작 인터뷰 — 사람만 정할 수 있는 것을 먼저 묻기

제작을 시작하기 전에 **자동 조사 → 질문 → 준비물 확인 → 요약 확인 → 기록** 순서로 결정을 한 번에 모은다. 요청에 이미 답이 있는 항목은 다시 묻지 않는다.

왜 먼저 하나: 2026-10-28 LLM 과정에서 '영상은 만들지 않는다', 'STEP마다 해설 대본', '전 챕터로 확대'가 실행 도중에 정해져 병렬 워크플로를 세 번 다시 시작했다. GPU 2장 레슨용 Pod, 사용자가 자는 동안의 진행, 끝난 뒤 Pod 처리도 도중에 따로 물어야 했다.

## 1. 자동 조사 (질문 전에, 읽기 전용)
알아낼 수 있는 것은 묻지 않고 조사한다. 결과는 짧은 표로 보여 준다. 접속값·토큰 같은 값은 출력하지 않는다.

| 조사 | 방법 | 알게 되는 것 |
|---|---|---|
| 과정 저장소 | 작업 폴더와 사용자가 말한 경로에서 `docs/LESSON_GUIDE.md`, `tools/check_lesson.py`, `curriculum.md`, `docs/DECISIONS.md`, `REPORT.md`를 찾는다 | 새 과정인지 이어 만들기인지 |
| 이전 결정 | `docs/DECISIONS.md` 앞머리(YAML)를 읽는다 | 다시 묻지 않아도 되는 항목(바뀐 것만 묻는다) |
| Pod 접속값 | `.env.local`에서 `POD_<X>_HOST`가 채워진 Pod 수만 센다 → 있으면 `tools/pod.sh A 'nvidia-smi -L'` | 바로 쓸 수 있는 Pod 수와 GPU |
| 브라우저 | `claude-in-chrome` 스킬을 먼저 호출 → 탭 정보 → RunPod 콘솔 Pods 목록을 보기만 한다(아무것도 누르지 않음, 메인 세션만) | 로그인 여부, Running Pod 이름·GPU·시간당 요금 |
| 로컬 도구 | `python --version`, Git Bash, `python -c "import playwright, yaml, PIL, nbformat"`, `codex --version`(선택) | 캡처·마스킹·검사가 돌아가는지 |
| Claude 쪽 도구 | 이 세션에 Workflow, CronCreate, AskUserQuestion이 있는지 | 병렬 제작·자리 비움 점검이 가능한지 |

조사로 정해지는 기본값:
- 연결해 둔 Running Pod가 있으면 그 Pod를 쓰는 것을 권장안으로 둔다. 연결된 Pod를 두고 Stop이나 새 Pod를 먼저 제안하지 않는다.
- `docs/DECISIONS.md`가 있으면 그 값을 기본값으로 두고, 이번 요청과 달라 보이는 것만 묻는다.
- AskUserQuestion이 없으면 같은 질문을 번호 목록으로 한 번에 보여 주고 답을 받는다.

## 2. 질문 (AskUserQuestion)
- 한 번에 1~4개씩, 2~3번에 나눈다. 앞 묶음의 답으로 다음 묶음을 줄인다. 예를 들어 레슨 하나만이면 병렬·자리 비움 질문을 뺀다.
- 커리큘럼이 아직 없으면 'GPU 2장'·'병렬'의 건너뛰는 조건은 요청과 주제로 판단한다(애매하면 묻는다). curriculum 초안을 확인받을 때 다시 맞춘다.
- 선택지는 2~4개다. 권장안을 첫째에 두고 이름 끝에 '(권장)'을 붙인다. header는 12자 이내로 쓴다. '기타'는 자동으로 붙으니 직접 만들지 않는다.
- 금액·시간 한도처럼 숫자가 필요한 답은 '기타'로 받는다.
- 이미 답이 나온 항목은 질문에서 빼고, 4절 요약 확인 때 그 값을 보여 준다.

### 묶음 1 — 무엇을 만드나
| header | 질문 | 선택지(첫째가 권장) | 건너뛰는 때 |
|---|---|---|---|
| 범위 | 이번에 어디까지 만들까요? | 파일럿 1개를 먼저 만들고 검토 뒤 나머지 / 과정 전체를 끝까지 / 레슨 하나만 / 기존 과정 이어 만들기 | 요청에 범위가 분명할 때 |
| 산출물 | 레슨마다 무엇을 만들까요? | README + STEP별 🎙️ 해설 대본 / README만 / README + 해설 대본 + 영상(레슨을 지정) | |
| 대상 | 누가 따라 하나요? | 코딩을 모르는 비개발자 / 개발 입문자 / 실무 개발자 | 레슨 하나(아래 기본값) |
| 커리큘럼 | 레슨 목록은 어떻게 정할까요? | 주제를 받아 초안을 제안하고 확인받기 / 직접 목록 제공 | 레슨 하나, 이어 만들기 |

영상을 고르면 이어서 묻는다: header '영상 레슨'(5자), multiSelect. 레슨 후보가 4개 이하일 때만 그 레슨을 선택지로 보인다(레슨 하나면 묻지 않고 그 레슨). 더 많거나 커리큘럼이 아직 없으면 질문에 '지금 정하려면 레슨 ID를 기타에 적어 주세요(예: C02-L02)'를 넣고 선택지 '커리큘럼이 정해진 뒤 고르기(권장) / 파일럿 레슨만'으로 묻는다. '커리큘럼이 정해진 뒤'면 `video_lessons: []`로 두고, curriculum을 확인받을 때 다시 묻는다('바뀐 기록'에 남김). '파일럿 레슨만'이면 파일럿 ID가 정해진 뒤 `video_lessons`에 적는다. 영상은 `ai-concept-visualization-video`로 따로 만든다.

### 묶음 2 — Pod와 비용
| header | 질문 | 선택지(첫째가 권장) | 건너뛰는 때 |
|---|---|---|---|
| Pod | 어떤 Pod를 쓸까요? | 연결해 둔 `<조사한 Pod 이름>` / 새 Pod를 만들기(사양·가격을 보여 드리고 승인받은 뒤) / 레슨이 많으니 Pod 2대(가격 확인 뒤) | |
| GPU 2장 | GPU 2장 이상이 필요한 레슨(예: Tensor Parallel)은 어떻게 할까요? | 그 레슨 때만 2-GPU Pod를 띄우고 끝나면 Stop(가격 확인 뒤) / 개념만 설명하고 실행하지 않음 | 커리큘럼에 그런 레슨이 없을 때 |
| 예산 | 비용 한도가 있나요? 금액·시간 한도는 '기타'에 적어 주세요(예: $30, 10h). | 한도 없음 — 가격과 추정 비용만 알려 줌 / 파일럿 비용을 본 뒤 정하기 | 레슨 하나(아래 기본값) |
| 끝난 뒤 | 작업이 모두 끝나면 Pod는 어떻게 할까요? | 이번에 쓴 Pod를 모두 Stop / 켜 둔 채로 두기 | |

Terminate와 Network Volume 삭제는 선택지에 넣지 않는다. 되돌릴 수 없으므로 사용자가 따로 분명히 요청할 때만 한다.

### 묶음 3 — 진행 방식
| header | 질문 | 선택지(첫째가 권장) | 건너뛰는 때 |
|---|---|---|---|
| 병렬 | 레슨 여러 개를 동시에 만들까요? | 예 — 워크플로로 여러 에이전트가 동시에(빠르지만 토큰을 많이 씀) / 아니요 — 한 레슨씩 차례로 | 레슨 1~2개 |
| 자리 비움 | 자리를 비우시는 동안은 어떻게 할까요? | 30분마다 자동 점검 예약(이 세션 창이 열려 있어야 함) / 제가 진행하고 직접 확인 / 필요 없음 | 레슨 하나 |
| 내용 검토 | 다 만든 뒤 내용 검토는 어디까지 할까요? | 표본 몇 개 + 레슨 사이 정합성 / 모든 레슨 내용 검토(시간·토큰 더 듦) / 품질 검사(check_lesson)만 | 레슨 하나(그 레슨 전체를 검토) |
| 공개 | 결과물을 공개할 계획인가요? | 비공개(로컬 git만) / GitHub 등에 공개 예정 / 아직 모름 | 레슨 하나(아래 기본값) |

- '병렬 = 예'는 Workflow 도구를 쓰는 데 대한 사용자 동의다. 이 답이나 같은 뜻의 요청 없이 Workflow를 돌리지 않는다. '예'는 큰 과정의 읽기 전용 사전 조사(workflow.md 0-3)에도 Workflow를 쓴다는 뜻이므로 선택지 설명(description)에 적는다. README-only 검증 Workflow는 0-4 승인 때 따로 동의를 받는다.
- '공개 예정'이면 공개 전 준비를 미리 알린다: Pod·볼륨 이름까지 가릴지, Jupyter 토큰 교체(Pod 재배포), RunPod 계정 MFA.

### 따로 묻지 않는 기본값
요청에서 다르게 말하지 않으면 다음을 쓴다: 한국어, 해설 대본은 강사가 말하는 습니다체, 토큰이 필요 없는 공개 모델, git은 로컬만(push는 요청할 때만).

### 레슨 하나만일 때
묻는 것은 산출물·Pod·끝난 뒤(+ 과정 이름)뿐이다. 나머지는 요청에 답이 없으면 이렇게 적는다: `scope: one`, `curriculum: given`, `audience: non-developer`, `budget: none`(가격·추정 비용은 알린다), `multi_gpu: none`(그 레슨이 GPU 2장을 쓰면 가격을 보여 주고 따로 묻는다), `parallel_workflow: false`, `unattended_checks: none`, `content_review: full`, `publish: private`.

## 3. 사람이 직접 해야 하는 준비물
자동 조사에서 빠진 것만 짧게 안내하고, 해 두었는지 묻는다. header는 '준비물', 선택지는 '다 해 두었음 / 일부 남음 — 같이 하기 / 지금은 못 함'. 같은 호출에 과정 이름 질문(이 절 끝)을 두 번째로 넣는다.
- RunPod 로그인(Chrome 확장이 쓰는 그 브라우저): 콘솔 화면 촬영과 Pod 끄기에 필요하다.
- SSH 공개키 등록(RunPod 콘솔 → Credentials → SSH Public Keys): 계정 설정이라 사용자가 한다.
- 새 Pod: 인터뷰를 마친 뒤 workflow.md 0-5에서 사양·가격을 보여 드린다. Deploy는 사용자가 누르거나 명시적으로 승인한다.
- gated 모델을 쓸 때만: Hugging Face 토큰은 사용자가 Pod에서 `hf auth login`으로 직접 넣는다.
- 영상을 만들고 공개할 때: TTS 라이선스를 먼저 정한다.

'지금은 못 함'이면 그 준비물이 필요 없는 단계까지만 진행하고, 무엇을 기다리는지 말한다.

'일부 남음 — 같이 하기'는 4절 기록을 마친 뒤 한다. RunPod 로그인은 사용자가 직접 한다. SSH 공개키 등록과 새 Pod Deploy·멈춘 Pod Start는 workflow.md 0-5대로 한다(품목과 화면 가격을 보여 주고 명시적 승인을 받는다. `Deploy Pod`는 기본적으로 사용자가 누른다).

과정 이름: 준비물 질문과 같은 AskUserQuestion 호출에 두 번째 질문으로 넣는다(빠진 준비물이 없으면 이 질문만). header '과정 이름'(5자), 질문 '과정 이름과 저장소 폴더를 어떻게 할까요?', 선택지 '`<요청 주제로 지은 이름>` · `D:/<영문-kebab>`(권장) / 폴더 이름을 과정 이름으로'. 다른 이름·경로는 '기타'로 받는다. 새 과정과 레슨 하나일 때만 묻는다(이어 만들기는 조사로 안다).

## 4. 요약 확인과 기록
1. 결정 표(조사 결과 + 답 + 기본값)를 보여 주고 AskUserQuestion으로 확인한다. header는 '확인', 선택지는 '이대로 시작(권장) / 고칠 것이 있음'.
2. 과정 저장소의 `docs/DECISIONS.md`에 적는다.
   - 틀은 `assets/decisions.template.md`다. 새 과정은 `init_course.py`가 이 틀을 `docs/DECISIONS.md`로 만들어 두므로 그것을 채운다. 이 파일이 없는 기존 저장소는 `python "<SK>/scripts/init_course.py" "<저장소>" --init-decisions --title "<과정 이름>"`으로 이 파일만 만든다(`--force`는 쓰지 않는다).
   - 저장소가 아직 없으면 결정을 대화에 붙들어 두었다가, Phase 1에서 저장소를 만든 직후 바로 쓴다.
   - 앞머리(YAML)는 검사기와 워크플로가 읽는다. 키 이름을 바꾸지 않는다. 표에는 사용자 답 원문을 적는다.
3. 레슨 에이전트는 LESSON_GUIDE와 함께 DECISIONS를 먼저 읽는다(`assets/lesson-workflow-template.js` 프롬프트에 들어 있다).

## 5. 답이 바꾸는 것
| 결정(앞머리 키) | 바뀌는 곳 |
|---|---|
| 범위(`scope`) | 파일럿 먼저 → Phase 3·4 뒤에 멈추고 보고 / 전체 → Phase 5까지 / 레슨 하나 → SKILL.md '레슨 하나만' / 이어 만들기 → workflow.md '이어 만들기' 점검부터 |
| 산출물(`deliverables`, `narration`, `video_lessons`) | 'README + 해설 대본' → `deliverables: readme+narration`, `narration: true` / 'README만' → `deliverables: readme`, `narration: false`(check_lesson이 해설 대본 항목을 건너뛰고 NOTE를 찍는다) / '+ 영상' → `deliverables: readme+narration+video`, `narration: true`, `video_lessons: [레슨 ID]`(README가 끝난 뒤 `ai-concept-visualization-video`로 따로). 검사기는 `narration`만 읽는다 |
| 대상(`audience`) | README 말투·설명 깊이와 레슨 프롬프트의 대상 문구(LESSON_GUIDE 3행). 묻지 않았으면 `non-developer` |
| 커리큘럼(`curriculum`) | `propose` → 0-4 보고 때 curriculum.md 초안(챕터·레슨 수)을 보여 확인받는다 / `given` → 받은 목록 그대로 쓴다 |
| 기록 시각(`decided_at`) | 질문하지 않는다. 4절 '확인'을 받은 시각(KST). 결정이 바뀌면 이 값은 두고 '바뀐 기록'에 줄을 더한다 |
| Pod·GPU 2장(`pods`, `multi_gpu`) | 레인 수와 배치(parallel-production 1절). 2-GPU 레슨은 따로 띄운 Pod의 레인 하나로 하고 끝나면 바로 Stop |
| 예산(`budget`) | 시간당 요금 × 예상 시간을 처음에 보고한다. 한도의 80%에 가까우면 멈추고 묻는다. `after-pilot`이면 파일럿 뒤 보고 때 다시 묻는다 |
| 끝난 뒤(`after_done`) | Phase 7 |
| 병렬(`parallel_workflow`) | true → Workflow로 레인 병렬(큰 과정의 0-3 사전 조사 Workflow 포함) / false → 레인마다 서브에이전트 하나를 차례로 |
| 자리 비움(`unattended_checks`) | CronCreate 점검 예약(parallel-production 7절의 점검 프롬프트) |
| 내용 검토(`content_review`) | parallel-production '끝난 뒤 내용 검토'의 범위 |
| 공개(`publish`) | 마스킹 범위(Pod·볼륨 이름까지 가릴지), 공개 전 토큰 교체·MFA 안내. push는 여전히 요청할 때만 |

## 6. 묻지 않는 것 (스킬 규칙으로 고정)
비밀값 규칙, 실제로 실행한 결과만 쓰기, Windows 데스크톱 캡처 금지, 결제 전 품목·가격 확인, Terminate·볼륨 삭제는 명시적 요청 때만. 사용자가 비밀값·실측 규칙을 풀자고 하면 이유를 설명하고 따르지 않는다. Terminate는 대상과 되돌릴 수 없다는 점을 확인한 뒤에만 한다.

## 7. 도중에 다시 묻는 때
- 결정에 없는 비용·계정 행동이 필요할 때: 새 Pod, 멈춘 Pod Start, 볼륨 증설, 계정 설정.
- 실측이 결정과 부딪힐 때: 저장 용량 부족, GPU 메모리 부족, 모델 라이선스 문제, 예산 한도에 가까움.
- 사용자가 요구를 바꿀 때: `docs/DECISIONS.md`의 값과 '바뀐 기록'을 먼저 고친 뒤 parallel-production 6절(멈춤 → 고침 → 재개)을 따른다.
