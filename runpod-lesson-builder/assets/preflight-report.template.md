# 사전 점검 보고서 — {{COURSE_TITLE}}

- 점검일: <YYYY-MM-DD> (KST)
- 방식: 읽기 전용 점검 → 사용자 보고·승인 → (승인 뒤) 쓰기 점검. 명령은 runpod-lesson-builder 스킬 `references/workflow.md` Phase 0.
- 이 파일은 공개 저장소에 들어간다. IP·포트·Pod ID·토큰·키·SSH 지문·계정 잔액은 적지 않는다. 다 쓴 뒤 `python tools/check_lesson.py --repo`.

| 항목 | 상태 | 확인 결과 | 제약 사항 / 대응 |
|---|---|---|---|
| Chrome 연결 | <성공/실패> | <사용자가 고른 브라우저(이름·OS), 쓸 수 있는 동작> | |
| RunPod 콘솔 | | <GPU 종류·개수, 템플릿, Cloud, Cost 열 값, HTTP services Ready, SSH 방식> | 잔액·아바타·Pod ID·IP는 마스킹 대상 |
| 스크린샷 | | <탭 캡처·zoom 캡처를 파일로 저장해 다시 열어 본 결과(크기·판독성)> | Windows 화면 캡처는 쓰지 않는다 |
| SSH | | <`tools/pod.sh A 'nvidia-smi -L'` 종료 코드> | |
| GPU | | <이름, 메모리, 드라이버, CUDA Version> | |
| OS·Python | | <OS, `python --version`, `which python`, 시스템 PyTorch> | |
| JupyterLab | | <버전, `jlab.py` 자가 점검 그림> | |
| 저장소(Pod) | | <컨테이너 디스크 크기, `/workspace`가 Network Volume인지·두 Pod 공유인지> | |
| 자원 표시 | | <`nproc`·`free` 값과 `RUNPOD_CPU_COUNT`> | |
| 다른 과정·세션 | | <`<과정폴더>`가 비었는지, `/root/venvs`, tmux, GPU 프로세스> | 쓰고 있으면 멈추고 묻는다 |
| 도구(Pod) | | <uv, tmux, git 버전> | |
| 도구(Claude 쪽) | | <Workflow·CronCreate 도구, workflow-authoring·claude-in-chrome 스킬, Git Bash 버전> | 없으면 대안(서브에이전트, 직접 마무리) |
| Codex(선택) | | <`codex --version`> | 읽기 전용 교차 리뷰에만 |
| 로컬 PC | | <playwright·PIL·yaml·nbformat, chromium> | |

## 보안 관찰
- <비밀값이 보일 수 있는 곳(환경변수, 링크의 `?token=` 등)과 대응 — 값은 적지 않는다>

## 실측 체크리스트 (조사·미확인 항목)
| 항목 | 확인 방법 | 결과 | 상태 |
|---|---|---|---|
| <예: 노트북을 연 상태의 Kernel 메뉴 라벨> | <리허설에서 화면 확인> | | 미확인 |
| <예: Stop 뒤 kernelspec이 남는지> | <승인 뒤, 아무도 그 Pod를 쓰지 않을 때만(workflow.md 0-6)> | | 확인하지 않음 |

## 사용자 결정
- <저장 용량·비용, 모델·라이선스, 두 번째 Pod, 공개 범위, README-only 검증 워크플로 실행>
