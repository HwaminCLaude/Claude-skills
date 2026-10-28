# 실측 버전 기록 — {{COURSE_TITLE}}

마지막 검증: <YYYY-MM-DD>. 버전이 바뀌면 이 파일과 해당 레슨 README 머리말을 함께 고친다.
고정 버전의 원본은 `environment/setup.sh`(TRAIN_PKGS·SERVE_PKGS)이고, Pod에 실제로 깔린 버전은 lock 파일(`{{LOCKDIR}}/*.lock`)이다.
여기에는 Pod에서 확인한 값만 적는다(값을 공개해도 되는 환경변수만 — 키·비밀번호·토큰 값은 적지 않는다).

## Pod 이미지
| 항목 | 값 |
|---|---|
| 템플릿 | `<이미지 태그>` (콘솔 표시 "<…>") |
| OS | |
| GPU / Driver | |
| Python | <버전 (`python`·`which python`)> |
| PyTorch (시스템) | |
| JupyterLab | <버전 (jupyter_server, ipykernel)> |
| 기타 | <uv, git, tmux, runpodctl> |
| 환경변수(값 공개 가능한 것) | <예: `HF_HOME=…`, `RUNPOD_CPU_COUNT=…`> |

## venv (`setup.sh` 실행 결과, `{{VENVS}}`)
| venv | 설치 명령 | 결과 버전(lock) | 설치 시간 | 크기(`du -sh`) |
|---|---|---|---|---|
| train | | | | |
| serve | | | | |

## 동작 확인
- <stackcheck.sh 등으로 확인한 라이브러리 동작과 근거 로그 경로(`verification/…`)>

## Pod에서 실측한 UI 라벨·동작
| 항목 | 결과 | 확인한 레슨·날짜 |
|---|---|---|
