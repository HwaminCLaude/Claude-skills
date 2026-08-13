# 사전 검증 · 렌더 오류 대응

Stage 0의 복구 가이드와 Stage 5의 자동 수정 패턴. 이 기계에서 실제로 겪은 것들이라 추측이 아니다.

---

## 1. Stage 0 preflight

```bash
python scripts/preflight.py --root C:\manimwork\<slug>
```

13개 항목을 검사하고 `FAIL`이 있으면 exit 1. **FAIL은 차단, WARN은 기능 축소**다. 실패 시 아래 조치 → 재검사, 최대 3회 반복하고 그래도 안 되면 사용자에게 보고하고 멈춘다.

| 항목 | FAIL 시 조치 |
|---|---|
| uv 없음 | https://docs.astral.sh/uv/ 설치 |
| FFmpeg 없음 | `winget install Gyan.FFmpeg` |
| **LaTeX 없음** | `winget install --id MiKTeX.MiKTeX --silent --accept-package-agreements --accept-source-agreements` |
| 프로젝트 venv 없음 | `python scripts/setup_env.py --root <root>` |
| manim/raenim import 실패 | `setup_env.py --root <root> --force` |
| 출력 루트 쓰기 불가 | 다른 `--root` 지정 |

WARN은 그대로 진행한다: codex 없음 → 이미지 생성 노드 off, `noise`가 shim → 정상(`RWiggle`만 사용).

### MiKTeX 설치 후 반드시 두 가지

1. **PATH가 현재 셸에 없다.** 설치는 사용자 PATH에 등록되지만 실행 중인 프로세스는 갱신되지 않는다. 새 셸을 열거나, 렌더할 때 경로를 직접 넘긴다:
   ```bash
   python scripts/render.py --episode ... --latex-bin "%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64"
   ```
2. **AutoInstall을 켠다.** 기본값이 "물어보기"라서 첫 `MathTex` 렌더가 누락 패키지 GUI 대화상자에서 **실패가 아니라 멈춘다.**
   ```bash
   initexmf --set-config-value "[MPM]AutoInstall=1"
   ```

### noise 패키지

`pip install noise`는 이 환경에서 **실패하는 것이 정상**이다 (`Microsoft Visual C++ 14.0 or greater is required`). 마지막 릴리스가 2015년이라 cp311 휠이 없다. `setup_env.py`가 자동으로 `assets/noise_shim/noise.py`(순수 파이썬 Perlin)를 venv에 넣는다. 유일한 소비처가 `RWiggle`(장식용 떨림)이라 실사용에 지장 없다.

굳이 진짜 패키지를 원하면 VS Build Tools(수 GB)를 설치한 뒤 `uv pip install noise`.

---

## 2. 렌더 오류 5종

`render.py`가 출력을 정규식으로 분류해 `error_kind`와 조치를 함께 낸다.

| kind | 증상 | 조치 |
|---|---|---|
| `latex` | `LaTeX Error`, `pdflatex not found` | MiKTeX PATH + AutoInstall (위 참조). 그래도 안 되면 해당 컷을 `Text`로 대체 |
| `font` | Pango 경고, 한글이 □□□ | `Text(..., font="Malgun Gothic")` 명시. `MONO_FONT`는 한글 폰트가 아니다 |
| `import` | `ModuleNotFoundError` | `setup_env.py --force`. `from raenim import *`가 `Path`를 덮어쓴 경우도 여기 해당 |
| `index` | `IndexError`/`KeyError` | `RaeTex`는 정수가 아니라 **원문 문자열**로 조각을 꺼낸다. `items=` 사용 시 매핑이 어긋날 수 있으니 조각을 더 잘게 나눠 넘길 것 |
| `fork_only` | `AttributeError ... method_names` | `SkewedAnimations`는 순정에서 못 쓴다. 다른 애니메이션으로 교체 |
| `code` | `NameError`/`TypeError`/`SyntaxError` | 생성된 씬 코드 버그. 트레이스백 위치를 고치고 다시 스모크 |
| `svg_race` | `ParseError: no element found` | **병렬 렌더 경합 #2 — 텍스트 SVG 캐시.** 여러 씬에 **똑같은 문자열의 `Text`** 가 들어 있으면(머리말, 배지, 공통 캡션) manimpango가 같은 캐시 SVG를 동시에 쓴다. 한쪽이 절반만 쓴 파일을 다른 쪽이 읽어 XML 파싱이 깨진다. `render.py`가 자동으로 직렬 재시도한다. **씬 코드를 고칠 필요 없다** — `t2f`에 더미 키를 넣어 해시를 흩는 우회는 쓰지 말 것 |
| `tex_race` | `WinError 32`, "다른 프로세스가 파일을 사용" | **병렬 렌더 경합 #1 — LaTeX.** 씬들이 `media/Tex/`를 공유해서, 한 워커가 지우려는 `.log`를 다른 워커가 잡고 있다. `render.py`가 해당 씬만 자동으로 직렬 재시도한다(그때는 LaTeX 출력이 이미 캐시돼 빠르다). 수동 렌더 중이라면 `--jobs 1`로 한 번 돌려 Tex 캐시를 채운 뒤 병렬로 가면 된다 |

자동 수정은 **최대 3회**. 초과하면 그 구간을 단순한 연출로 낮추거나 사용자에게 올린다.

---

## 3. 음성·자막 (Stage 7)

`tts_narrate.py` 는 **edge-tts** 를 쓴다. API 키가 없고 인터넷만 있으면 된다.

```bash
uv pip install edge-tts        # 프로젝트 venv에
python scripts/tts_narrate.py --episode <ep> --quality qh --fit
python scripts/mux_av.py     --episode <ep> --quality qh          # 자막 트랙
python scripts/mux_av.py     --episode <ep> --quality qh --burn   # 자막 태움
```

| 증상 | 원인·조치 |
|---|---|
| 음성이 화면보다 점점 밀린다 | 씬 스케일 보정이 안 된 것. `--quality` 를 실제 렌더한 품질과 맞춰야 ffprobe로 씬 길이를 잴 수 있다. 렌더 전에 TTS를 돌리면 보정이 불가능하다 |
| 특정 줄이 애니메이션보다 길다 | `--fit` 을 쓰면 그 줄만 말속도를 올려 재합성한다. 그래도 넘치면 `shots.json` 의 문장을 쪼갠다 |
| `Unknown decoder 'copy'` | ffmpeg 인자 순서 문제. 모든 `-i` 입력이 코덱 옵션보다 앞에 와야 한다 (`mux_av.py` 는 처리돼 있음) |
| 자막이 안 보인다 | 기본은 **선택 가능한 트랙**(mov_text)이라 플레이어에서 켜야 한다. 유튜브 업로드나 미리보기용이면 `--burn` |
| 한 줄만 다시 녹음하고 싶다 | `tts/<shot_id>.mp3` 를 지우고 `tts_narrate.py` 를 다시 돌린다 (나머지는 캐시됨) |

음성은 3종 중 고른다: `ko-KR-HyunsuMultilingualNeural`(기본, 한영 혼용에 강함), `ko-KR-InJoonNeural`(남), `ko-KR-SunHiNeural`(여).

## 4. 자주 밟는 함정

**cp949 UnicodeEncodeError** — Windows 콘솔 기본 인코딩이 cp949라, 한글이나 `—` 를 출력하는 순간 스크립트가 죽는다. 고약한 건 **출력 파일은 이미 다 쓴 뒤에 죽는다**는 점이라, 실패한 줄 알고 다시 돌리기 쉽다. 모든 스크립트가 시작할 때 `sys.stdout.reconfigure(encoding="utf-8")` 로 스스로 전환하므로 지금은 발생하지 않는다. 직접 만든 스크립트를 추가한다면 같은 가드를 넣을 것.

**대화형 프롬프트에서 멈춤** — 한 파일에 Scene 클래스가 여러 개인데 `manim main.py`를 그냥 실행하면 Manim이 어느 씬을 렌더할지 물어본다. `render.py`는 AST로 클래스를 찾아 항상 이름을 명시하므로 이 문제가 없다. 수동으로 돌릴 때만 주의.

**manim.cfg에 해상도** — `pixel_width`/`pixel_height`/`frame_rate`를 넣으면 `-ql`/`-qh`를 덮어써서 2단 렌더가 무력화된다. 템플릿 `manim.cfg`에 일부러 빼 두었으니 다시 넣지 말 것.

**Codex 프롬프트가 깨짐** — Windows에서 `codex`는 npm `.cmd` 셸이라 `cmd.exe`를 거치는데, 프롬프트의 괄호 `(#000000)` 같은 문자가 재파싱되어 인자가 망가진다. 증상은 codex가 *"Please send the image description"* 이라고 답하는 것. `gen_image.py`는 `codex exec -`로 stdin에 넘겨 회피한다.

**`subprocess`에서 WinError 2** — `shutil.which("codex")`는 `codex.CMD`를 찾지만 `CreateProcess`는 배치 파일을 이름만으로 실행하지 못한다. 해석된 전체 경로를 `cmd.exe /c`로 감싸야 한다.

**렌더가 너무 느림** — 스모크는 반드시 `-ql`. 본번은 `--jobs 3`으로 구간 병렬. 캐시(애니메이션 해시 = partial movie 파일명)는 켜 두어 수정한 구간만 다시 그려지게 한다.

**한글 경로** — 순정 manim은 shell을 거치지 않아 대체로 안전하지만, MiKTeX 임시 파일에서 사고가 난다. 프로젝트 루트는 `C:\manimwork\<slug>` 같은 ASCII 경로로 유지한다.
