# 예시 레슨 — LLM 과정 파일럿 C02-L02 (형식 참고용)

LLM 과정의 파일럿 레슨 「C02-L02 JupyterLab 접속하고 GPU 확인하기」(2026-10-28 촬영, `check_lesson.py` 13 PASS)의 **글 파일 사본**이다. 과정에 아직 파일럿이 없을 때 README·playbook·명세 파일의 형식을 볼 때 쓴다. 원본(그림 포함)은 작성자의 LLM 과정 저장소(비공개)의 `chapters/chapter-02/lesson-02-first-gpu-check`에 있고, 이 사본에는 그림이 없다.

## 들어 있는 것
| 파일 | 볼 것 |
|---|---|
| `README.md` | 머리말 표, 🎙️ 해설 대본 위치(시작·STEP별·마무리), 14절, Part·STEP 형식, 코딩 블록(STEP 13), 노트북 STEP(16~23), '꼭 같아야 할 것 / 달라도 되는 것', 보충 촬영 그림 아래 설명, 10절 오류 해결 |
| `playbook.yaml` | 단일 원본 스키마(필수 필드, `readme_anchor`·`scene_id`·`troubleshooting` 연결), 촬영하지 못한 STEP의 주석(S26) |
| `troubleshooting.md` | ID·단계·증상·원인·해결·근거 표, 보안 주의 |
| `expected-output/*.txt` | `# log:`·`# after:`·정규식 줄·실제 출력 주석 |
| `logs/terminal-commands.ssh-rerun.log` | Terminal 화면을 SSH로 다시 실행한 로그 |
| `notebooks/` | 실행 결과가 담긴 노트북(실행 번호 1..4)과 셀별 코드(`cells/cellN.py` = README·playbook의 `code_file`) |
| `_raw/redact-spec.json`, `_raw/annotate-spec.json` | 마스킹 상자·클릭 번호 좌표(탭 캡처 원본 1568폭 픽셀 기준) |
| `_raw/capture-log.jsonl` | 촬영 기록 한 줄 형식(`file`은 `_raw` 안의 파일 이름) |
| `screenshots/_masking.json`, `evidence-manifest.json` | `redact.py`·`check_lesson.py`가 만든 결과 |

## 들어 있지 않은 것
- 그림(`screenshots/*.png`, `_raw/*.jpg`·`*.png`)과 `shared/diagrams/` — 그래서 이 폴더는 `check_lesson.py`를 통과하지 않는다. 그림을 지어내 넣지 않는다.
- `storyboard.md`, `narration.md`(영상이 범위에 있던 때의 산출물), 도구 상태 폴더 `.omx/`.

## 바꾼 것
- Pod 이름은 `<POD_A_NAME>`·`<POD_B_NAME>`, 컨테이너 호스트 이름은 `<컨테이너>`로 바꿨다. playbook의 영상용 필드 `video_episode`는 뺐다. 그 밖의 글자는 원본 그대로다.

## 지금 규칙과 다른 점 (이 레슨이 규칙보다 먼저 만들어져서)
- 보충 촬영을 `/workspace/c02l02-fix`(공유 볼륨)에서 했다 → 지금은 컨테이너 디스크 `/root/scratch-<레슨>/`.
- S26의 Stop 확인 창을 찍지 못한 것을 playbook 주석과 README 문장으로만 적었다 → 지금은 그 부분만 다룬 STEP이면 `screenshots: []` + `not_captured: "<이유>"`(README에 같은 문구).
- ssh-rerun 로그 첫 줄에 `# source: ssh-rerun (Pod A, <날짜>, 화면 STEP N)`이 없다 → 새 레슨은 붙인다.
- 파이썬 환경은 시스템 Python(`Python 3 (ipykernel)`)이라 03절 '추가 설치: 없습니다'로 끝났다 → venv를 쓰는 레슨은 `lesson-guide.md` 5절의 '03 준비물' 규칙대로 환경을 만드는 곳을 적는다.
