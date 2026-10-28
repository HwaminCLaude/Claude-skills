# 검증: 품질 게이트 · README만 보고 재현 · 교차 리뷰

세 겹으로 본다. ① 결정적 게이트(`check_lesson.py`)는 레슨마다 반드시, ② README-only 재현은 파일럿은 반드시·이후는 챕터마다 1개 이상(또는 전부), ③ Codex 읽기 전용 리뷰는 선택. 고친 뒤에는 ①을 다시 돌린다. 저장소 문서(environment/, verification/, REPORT.md)는 `check_lesson.py --repo`로 따로 스캔한다.

## 1. `check_lesson.py` 게이트

```bash
python tools/check_lesson.py "chapters/chapter-NN/lesson-MM-slug"    # 저장소 루트에서, 이 PC의 python(PyYAML 필요)
python tools/check_lesson.py --repo                                   # 저장소 전체 비밀값 스캔
```
출력은 `PASS|FAIL <항목> — <자세히>` 줄, `evidence-manifest.json: N images`, 마지막 `N PASS / M FAIL`(FAIL이 있으면 종료 코드 1). 파일럿 기준 13개 항목(노트북·기대 출력 파일 수에 따라 달라짐).

| 항목 | 무엇을 보나 | FAIL이면 |
|---|---|---|
| 1 playbook 필수 필드 | 모든 step의 `id, part, screen, env, result, screenshots, readme_anchor, scene_id`가 비어 있지 않음(`not_captured`가 있는 step은 `screenshots`가 비어도 됨) | 빈 필드를 채운다(지어내지 말고 실행·촬영 기록에서). 정말 찍지 못했으면 `not_captured: "<이유>"` |
| (2 전) `screenshots/_masking.json` | 파일이 있어야 함 | `python tools/redact.py <레슨>`을 먼저 |
| 2 스크린샷 존재·마스킹 | playbook이 가리키는 그림이 `screenshots/`에 있고, `_masking.json`에 있거나(redact 산출물) 마스킹본 위 주석(annotate-spec의 src가 마스킹본) | 그림을 찍어 redact-spec에 넣고 redact → 필요하면 annotate |
| 2b 공개 폴더에 마스킹 경로 밖 이미지 없음 | `screenshots/*.png` 중 redact·annotate가 만들지 않은 것 | 손으로 넣은 그림을 지우거나 명세에 넣고 다시 생성 |
| 3 README 단계 앵커 | 각 `readme_anchor`에 `<a id="…"></a>` | 앵커 추가(오타 확인) |
| 3b 단계 이미지 배치 | 그 STEP의 그림이 STEP 구역 안 또는 **앞 STEP 구역 안**(02 미리 보기 같은 STEP 밖 절은 인정 안 함). `not_captured`가 있으면 그 문구가 그 STEP 구역에 그대로 있어야 함. 구역 = 다음 STEP 앵커 또는 코드 블록 밖의 다음 `## ` 제목까지 | 그림을 그 행동 바로 아래로 옮긴다 / 이유 문구를 playbook과 같게 쓴다 |
| 3-1 해설 대본 | `🎙️ 해설 대본 — 시작`, `— 마무리`, 모든 STEP 구역 안의 `🎙️ 해설 대본` 블록 | 블록 추가(문자열은 템플릿에서 복사, `lesson-guide.md` 8절) |
| 4 README 참조 파일 | `](경로)` 링크·그림이 레슨 기준으로 존재(http, `#앵커`는 제외, `파일#절`은 파일만) | 경로 수정 또는 링크 삭제. http 링크는 검사하지 않으므로 직접 열어 확인 |
| 5 노트북 | `notebooks/*.ipynb`마다 실행 번호 1..n, 코드 셀마다 출력(셀 태그 `no-output` 또는 첫 줄 `# no-output` 예외) | nbconvert로 처음부터 다시 실행해 가져온다(손으로 숫자 고치지 않기) |
| 6 기대 출력 | `expected-output/*.txt`의 `# log:` 로그에서 정규식 줄이 모두 맞음 | 패턴을 실제 출력에 맞게(달라도 되는 부분만 넓힘) 또는 로그 경로 수정. 출력이 틀렸으면 코드를 고쳐 다시 실행 |
| 7 비밀값 스캔 | 레슨 폴더의 공개 파일 전부(하위 폴더 포함; `_raw/`, 점 폴더, `__pycache__`, 이미지·모델 같은 바이너리 제외)에서 `token=…`, `RUNPOD_API_KEY=`, `JUPYTER_PASSWORD=`, `hf_…`, `rpa_…`, IPv4, 프록시 SSH 사용자(`-xxxxxxxx@ssh.runpod.io`), SSH 키 지문(`SHA256:` + 43글자), `.env.local`의 `POD_<글자>_ID`·`POD_<글자>_HOST` 값, `POD_<글자>_PORT` 값(4~5자리 숫자일 때 `-p`·`-P`·`port`·`포트` 바로 뒤에 올 때만) | 그 값을 파일에서 지우거나 `<POD_IP>` 같은 자리 표시로 바꾼다(로그면 `# edited:` 줄). 검사기를 고치지 않는다 |
| 8 storyboard | `storyboard.md`가 있을 때만: 모든 `scene_id` 포함 | (영상을 만들 때만 해당) |

- `.env.local`은 `tools/`의 부모 → 레슨 기준 저장소 루트 순서로 찾는다. 못 찾으면 `NOTE` 줄을 찍고 기본 패턴으로만 스캔한다(이때 Pod ID·주소·포트는 못 잡는다 → 제작 중에는 반드시 `.env.local`이 있어야 한다).
- IPv4 패턴은 `4.15.4.0` 같은 네 마디 버전 문자열과 `0.0.0.0`·`127.0.0.1`에도 걸린다. 설치 로그를 붙일 때는 필요한 줄만 남긴다(`# edited:`). 명령에 꼭 필요하면 `localhost`를 쓰거나 설명으로 바꾼다(LLM 과정 C10-L05는 `--host 0.0.0.0`을 뺐다: vLLM 0.32.0은 `--host`가 없으면 모든 주소에서 접속을 받는다).
- `POD_<X>_PORT` 패턴은 SSH 포트가 서비스 포트(8888·8000 등)와 같은 숫자일 때 `Port 8888`, `--port 8000` 같은 정상 문장에도 걸린다(오탐 — 가짜 값 8888·8000으로 시험하면 파일럿에서도 걸린다). 그런 줄은 SSH 포트가 아님을 확인해 사용자에게 알리고, 검사기는 고치지 않는다. LLM 과정의 실제 포트 값으로는 레슨 17개(공개 파일 587개)에서 오탐 0건이었다(2026-10-28).
- 검사기가 보지 못하는 것: 그림 속 글자(마스킹은 결과 그림을 열어 눈으로 확인), Pod 이름(비밀값 아님), http 링크가 실제로 열리는지.
- 검사는 결정적이다: 같은 폴더면 같은 결과. 매번 `evidence-manifest.json`을 다시 쓴다(`not_captured`가 있으면 그것도 넣는다).
- `--repo` 모드: 저장소 전체(`.git/`·`_raw/`·점 폴더·`__pycache__`·`tools/`(스킬과 같은 도구 사본)·`.env.local`·바이너리 제외)를 같은 패턴으로 본다. 루프백(127.x)과 `0.0.0.0`은 주소 비밀값으로 보지 않는다. `environment/preflight-report.md`·`versions.md`·`verification/*`·`REPORT.md`를 쓴 뒤 돌린다.

## 2. README만 보고 재현 (README-only)

목적: 'README 말고는 아무것도 모르는 사람'이 따라 할 수 있는지. 서로 모르는 두 에이전트를 돌리고, 그 결과를 메인 세션이 실제 Pod에서 그대로 실행한다. 에이전트 두 개를 띄우므로 계획 단계(`workflow.md` 0-4)에서 사용자 동의를 받는다.

1. **워크플로 실행** — `assets/readme-only-check-template.js`를 그대로 쓰고 `args`로 레슨을 준다.
   ```text
   Workflow({ script: <assets/readme-only-check-template.js 내용>,
              args: { lesson: "D:/<과정>/chapters/chapter-02/lesson-02-xxx",
                      start: "the RunPod console Pods page", end: "STEP 25" } })
   ```
   - `end`는 결제·삭제·Pod 상태를 바꾸는 STEP(Stop, Terminate, Deploy, Restart Pod …) 바로 앞 STEP으로 고른다(파일럿은 STEP 26이 Stop이라 `STEP 25`).
   - **행동 목록(action list)** 에이전트: README와 그 안의 그림만 읽고, 로봇이 해석 없이 실행할 수 있는 원자 행동(클릭 하나, 입력 한 줄 + Enter, 키 조합 하나, 대기/확인 하나)과 각 행동의 기대 결과를 README 문구 그대로 만든다. README만으로 정할 수 없으면 `underivable=true` + 이유, 막히는 곳은 `blocking_gaps`. 결제·삭제·Pod 상태 변경 행동(Deploy, Start, Stop, Terminate, Restart Pod, Edit Pod, File → Shut Down, Delete, Web terminal 토글, 계정 설정)은 `do_not_execute=true`.
   - **초보자 비평(beginner critic)** 에이전트: 터미널을 써 본 적 없는 비개발자 편에서 STEP마다 막히거나 틀릴 곳(모호한 말, 쓰이지 않은 필요한 행동, 글과 그림의 라벨 불일치, 행동에서 먼 그림, 설명 전에 나온 용어, 확인할 수 없는 성공 기준, 경고 없는 위험, 숫자·파일 이름·STEP 참조 불일치, 정해지지 않은 파이썬 환경)을 `blocker / major / minor`로. 그림을 열어 글이 말하는 것이 실제로 보이는지 확인한다.
   - 두 에이전트 모두 다른 파일(playbook, 로그, 코드)·브라우저·SSH를 쓰지 않는다.
   - Workflow 도구가 없으면 템플릿의 `RULES` + 각 Task 문장을 그대로 서브에이전트 두 개에게 따로 준다.
2. **실행 대조** — 메인 세션이 행동 목록을 **해석 없이 그대로** 실행한다. RunPod 콘솔 단계는 Chrome 확장(메인 세션만), JupyterLab 단계는 Chrome 확장 또는 `jlab.py`의 `j.page`. `do_not_execute=true` 행동은 누르지 않고 그 버튼·창이 보이는지만 확인한다. 기대 결과와 다르면 기록한다. 재현 환경 규칙:
   - (1) **공유 볼륨이 아닌 Pod**(Network Volume 없음 또는 별도 볼륨)를 우선 쓴다. 그 Pod의 venv·모델 캐시는 README 03 준비물과 같게 맞춘다(README가 앞 레슨의 venv를 전제하면 그것만 만들고, 모델을 미리 받아 두지 않는다 — 학습자처럼 첫 다운로드부터).
   - (2) (아직 실행해 보지 않은 절차) 제작 Pod와 같은 볼륨밖에 없으면, 그 챕터를 쓰는 레인이 없을 때 `tools/pod.sh A 'mv <과정폴더>/chNN <과정폴더>/chNN.prod-backup'`으로 비켜 두고 재현한 뒤, 재현 폴더를 `/root/scratch-<레슨>-repro/`로 옮기고 `mv <과정폴더>/chNN.prod-backup <과정폴더>/chNN`으로 되돌린다.
   - (3) 위 둘 다 어려워 경로를 바꿔 실행하면(예: `/workspace/<과정폴더>` → `/root/scratch-<레슨>-repro`), 바꾼 경로 표를 결과 기록에 남기고 그 밖에는 해석하지 않는다.
3. **판정** — `underivable`, `blocking_gaps`, 실행 불일치, `blocker`·`major` 비평은 모두 **README 결함**이다. 고치고 1로 돌아간다. 끝나면 임시 폴더를 지우고 커널·서버를 정리한다.
4. 결과(행동 수, underivable 수, 고친 것, 재현 환경과 경로 치환 표)를 `verification/<레슨>-readme-only.md`에 남긴다(선택) → `check_lesson.py --repo`.
5. 파일럿 뒤 레슨의 표본: 챕터마다 1개 이상, 콘솔·서버·학습 STEP이 있는 레슨 우선. Pod를 Stop하기 전에 한다.

## 3. Codex 읽기 전용 교차 리뷰 (선택)

수정은 Claude가 한다. Codex에게는 읽기만 시킨다(쓰기 모드 금지).
```bash
cd "<스크래치 폴더>"     # 레슨 폴더 밖에서 실행(도구 상태 폴더가 레슨에 생기지 않게)
codex exec -s read-only --skip-git-repo-check -o out.md - < prompt.txt
```
- `-s read-only`: 읽기 전용 샌드박스, `--skip-git-repo-check`: git 저장소 밖에서도 실행, `-o out.md`: 마지막 답을 파일로, `-`: 지시를 표준입력(`prompt.txt`)에서 읽음. (codex-cli 0.164.0에서 확인한 옵션)
- `prompt.txt`에 쓸 것: 리뷰할 파일의 절대 경로(README, code/, notebooks/, logs/, expected-output/), 볼 것(README의 명령·코드·숫자가 로그·노트북 출력과 맞는지, 코드 버그, 초보자가 막힐 곳, 비밀값), 답 형식(항목마다 파일·위치·문제·근거·고칠 방법, 심각도), '파일을 고치지 말 것'.

## 4. 지적 반영하는 법
1. 모든 지적을 표로 모은다(출처: action-list / critic / 실행 대조 / codex, 심각도, STEP).
2. **사실 확인 먼저**: 지적이 맞는지 그림·로그·노트북 출력으로 확인한다. 비평 에이전트가 틀릴 수도 있다. 맞지 않으면 '반영 안 함(근거)'으로 남긴다.
3. `blocker`·`major`와 실행 불일치는 모두 고친다. `minor`는 README가 더 나빠지지 않으면 고친다.
4. 같은 사실을 담은 곳을 함께 고친다: README ↔ playbook.yaml ↔ troubleshooting.md ↔ expected-output. 새로 겪은 증상은 10절 오류 해결과 troubleshooting.md에 근거와 함께 추가한다.
5. 화면이 모자라면 다시 촬영(또는 보충 촬영)해 redact부터 다시. 숫자를 손으로 바꾸지 않는다.
6. `check_lesson.py` 다시 → 구조가 크게 바뀌었으면 README-only를 한 번 더.
