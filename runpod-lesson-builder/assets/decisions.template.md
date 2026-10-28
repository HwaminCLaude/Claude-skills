---
# 시작 인터뷰 결정 — 이 앞머리는 tools/check_lesson.py와 워크플로가 읽는다. 키 이름을 바꾸지 말 것.
decided_at: "<YYYY-MM-DD HH:MM KST>"
scope: "<pilot-first | all | one | continue>"
deliverables: "<readme+narration | readme | readme+narration+video>"
narration: true             # deliverables가 readme면 false(검사기는 이 값만 읽는다, 따옴표 없이 true/false). false면 check_lesson이 해설 대본 항목을 건너뛰고 NOTE만 찍는다
video_lessons: []           # 영상을 만들 레슨 ID, 예: [C02-L02]
audience: "<non-developer | beginner-dev | developer>"
curriculum: "<propose | given>"
pods: "<connected:<A 이름>[,<B 이름>] | new:<GPU·개수> | two-pods>"
multi_gpu: "<deploy-when-needed | concept-only | none>"
budget: "<none | after-pilot | $<금액> | <시간>h>"
after_done: "<stop-all | keep-running>"
parallel_workflow: false    # true = 사용자가 Workflow(여러 에이전트 동시 실행)에 동의함
unattended_checks: "<cron-30min | manual | none>"
content_review: "<sample+consistency | full | gate-only>"
publish: "<private | public-planned | undecided>"
---

# 결정 사항 — {{COURSE_TITLE}}

시작 인터뷰(스킬 `references/intake-interview.md`)에서 정한 값이다. 레슨 제작 에이전트는 `docs/LESSON_GUIDE.md`와 함께 이 파일을 먼저 읽는다. 여기 적힌 결정이 기본값보다 우선한다.

| 결정 | 값 | 사용자 답(원문) 또는 근거 |
|---|---|---|
| 과정 이름·저장소 | <…> | <…> |
| 범위 | <…> | <…> |
| 산출물 | <README + 해설 대본 / README만 / + 영상(레슨)> | <…> |
| 대상 | <…> | <…> |
| 커리큘럼 | <초안 제안 / 목록 받음> | <…> |
| Pod | <연결된 Pod 이름 / 새 Pod 사양·시간당 요금 / Pod 2대> | <…> |
| GPU 2장 레슨 | <그때만 2-GPU Pod / 개념만 / 없음> | <…> |
| 예산 | <…> | <…> |
| 끝난 뒤 Pod | <모두 Stop / 켜 둠> | <…> |
| 병렬 제작 | <Workflow 사용 동의 / 차례로> | <…> |
| 자리 비움 점검 | <30분마다 cron / 직접 / 없음> | <…> |
| 내용 검토 | <표본 + 정합성 / 전 레슨 / 품질 검사만> | <…> |
| 공개 | <비공개 / 공개 예정 / 미정> | <…> |

## 사람이 직접 한 준비
| 준비물 | 상태 |
|---|---|
| RunPod 로그인(Chrome 확장 브라우저) | <…> |
| SSH 공개키 등록 | <…> |
| Pod Deploy(새 Pod일 때) | <…> |
| Hugging Face 토큰(gated 모델일 때만) | <해당 없음 / 사용자가 Pod에서 직접 입력> |
| TTS 라이선스(영상을 만들고 공개할 때만) | <해당 없음 / 정함: …> |

## 바뀐 기록
요구가 바뀌면 위 값을 고치고 여기에 한 줄을 남긴 뒤 진행 중인 작업을 멈추고 고쳐서 다시 시작한다(parallel-production 6절).

| 날짜·시각 | 무엇이 | 사용자 말(원문) | 다시 한 일 |
|---|---|---|---|
