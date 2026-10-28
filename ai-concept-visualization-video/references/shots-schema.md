# shots.json 스키마

대본은 에피소드 폴더의 `shots.json` 하나다. 자막 큐(1줄, 약 2초)의 목록이고, 씬 코드의 박자와 자막 시각이 모두 여기서 나온다.

```json
{"episode": "lora", "mode": "tts",
 "scenes": [{"name": "Hook", "cues": [
   {"id": "c001", "t": "LoRA는요,", "say": null, "key": "LoRA", "rel": "hook", "move": "montage", "hold": false}
 ]}]}
```

## 최상위 필드

| 필드 | 형식 | 뜻 |
|---|---|---|
| `episode` | str | 에피소드 이름. 최종 파일 `<episode>_FINAL.mp4`에 쓴다. |
| `mode` | `"tts"` \| `"silent"` | `tts`(스킬 기본값): edge-tts 음성 + 박힌 자막. `silent`: 음성 없이 박힌 자막만. `scaffold.py`는 기본으로 `"tts"`를 쓰고, 무음 영상이면 `scaffold.py --mode silent`로 만든다(이미 만든 뒤면 이 값을 고친다). 필드가 빠진 옛 파일은 `cues.py`·`assemble.py`가 `silent`로 본다. |
| `scenes` | list | **이 순서가 영상 순서다.** 렌더 결과를 이어 붙이는 순서도 이 목록을 따른다(파일 정의 순서, 알파벳 순서가 아니다). |

## 씬 필드

| 필드 | 형식 | 뜻 |
|---|---|---|
| `name` | str | `main.py`의 `CueScene` 하위 클래스 이름과 같아야 한다. |
| `cues` | list | 이 씬의 자막 큐. 순서대로 화면에 나온다. |

## 큐 필드

| 필드 | 형식 | 뜻 |
|---|---|---|
| `id` | str | 에피소드 전체에서 유일(`c001`, `c002` …). 씬 코드에서 `with self.cue("c001"):`로 쓴다. 중복이면 `cues.py`가 오류를 낸다. |
| `t` | str | 화면에 보일 자막 문구. 1줄, 공백 포함 26자 이하, 끝 마침표 없음. `·—→:`와 부연 괄호 금지. Noto Sans KR에 있는 글자만(린트 C7). 없는 글자: 아래 첨자 숫자 `₀`~`₉`, `ⁿ`, 이모지, `✔✕✗`. 그리스 문자 `α`, `Δ`는 있다. |
| `say` | str \| null | TTS 발음용 문구('로라', '비플로트 십육'). null이면 `t`를 읽는다. 화면에는 나오지 않는다. |
| `key` | str \| null | 노랑(`#EACF25`)으로 칠할 `t`의 부분 문자열. 큐당 1개 이하, 첫 등장 1곳만 칠한다. 편 전체에서 칠한 큐는 10~30%. |
| `rel` | str | 직전과의 관계. 다음 12개 중 하나: `detail` `next` `structure` `carry` `aside` `change` `build` `point` `new` `hook` `quote` `chapter`. 뜻과 연출은 `flow-grammar.md`. 같은 값이 4큐 넘게 이어지면 린트 WARN. |
| `move` | str | 그 큐의 박자(연출) 이름. 자유 문자열이지만 `rel`에 맞는 키트 헬퍼 이름을 쓴다(`zoom_in`, `pan_to`, `tilt`, `carry`, `aside`, `tint`, `dim_others`, `quote_card`, `clear_to`, `montage` 등). |
| `hold` | bool | 답이나 수식을 읽게 하려는 멈춤 표시. **표식일 뿐 큐 길이(timing)에는 반영하지 않는다.** 길게 보여 줘야 하면 큐를 하나 더 두거나 `t`를 늘린다. 편당 횟수는 린트·측정(A1)으로 관리한다. |

## 큐 길이(`cues.py`)

- silent: `max(1.2, n_syll/5.5 + 0.25*쉼표수 + 0.55*물음표수)`초.
  - `n_syll` = 한글 음절 수 + 라틴 단어 수(`[A-Za-z]+`) + 숫자 덩어리 수.
  - 숫자 덩어리: `1,000`, `3.14`처럼 자리 구분 쉼표·소수점으로 이어진 숫자는 한 덩어리다. 이 쉼표는 쉼으로 세지 않는다.
  - 쉼표는 `,` `，` `、`, 물음표는 `?` `？`를 센다.
  - 예: `LoRA는요,` → 3(LoRA 1 + 는요 2) → `max(1.2, 3/5.5+0.25)` = 1.2초. `왜 그럴까요?` → 5 → 5/5.5+0.55 ≈ 1.459초.
  - 공백 뺀 글자 속도가 6.4자/초를 넘으면 `cues.py`가 `WARN rate`를 찍는다. 그 큐는 쪼갠다.
- tts: `tts/durs.json`(`{id: 초}`)의 실측 길이를 그대로 쓴다. 빠진 큐가 있으면 오류. `durs.json`이 없으면 FAIL이므로 `tts.py`를 먼저 돌린다.

```
python scripts/cues.py --episode <dir>
```
→ `<dir>/timing.json`: `{"c001": {"scene": "Hook", "dur": 1.2}, ...}`(shots.json 큐 순서). `CueScene.setup()`이 읽는다.

## 자막 시각(`captions.py`)

- 렌더 중 `CueScene`이 `cuelog/<Scene>.json`(`{"scene", "cues": [{"id", "start", "dur", "elapsed", "plays"}]}`)에 실제 큐 시작 시각을 남긴다. `plays`는 큐 블록 안 `self.play` 횟수다(0이면 `render.py`가 `WARN CUE_NO_BEAT`). `captions.py`는 `plays` 같은 모르는 키를 무시하고, `start`·`dur`·`elapsed`가 null이면(렌더가 그 큐를 끝내지 못함) 오류를 낸다.
- `cue_times(shots, timing, cuelogs=None, scene_durs=None)` → `[(t, start, end)]`(이어 붙인 영상 기준 초).
  - 씬 오프셋 = 앞 씬들의 `scene_durs` 합(ffprobe 실측, `assemble.py`가 `scene_durs.json`으로 넘김). 없으면 큐 길이 합.
  - 큐 시작 = cuelog `start`. cuelog에 없는 큐는 앞 큐 시작 + 길이로 이어 간다. 큐 길이 = `max(dur, elapsed)`.
  - 큐 끝 = 다음 큐 시작(빈틈 0). 씬 마지막 큐 끝 = 씬 경계.
- `to_ass(items, keys)`의 `keys`는 **`t` → `key`** 사전이다(`items`에 큐 id가 없기 때문). 같은 `t`가 두 큐에 나오면 같은 `key`를 쓴다. `keys_from_shots(shots)`가 이 사전을 만든다.
- ASS: PlayRes 1920×1080, WrapStyle 2, `Noto Sans KR Medium` 64, Bold 0(가족 이름 `Noto Sans KR` + Bold면 libass가 VF Thin을 고른다), 글자 `&H00DCDCDC`, 외곽선·그림자 0, Alignment 2, MarginL/R 60, MarginV 103. 핵심어는 `{\c&H0025CFEA&}…{\c&H00DCDCDC&}`. 시각 형식 `H:MM:SS.cc`.

```
python scripts/captions.py --episode <dir> [--scene-durs <dir>/scene_durs.json]
```
→ `<dir>/captions.ass`. `timing.json`이 없으면 silent 공식으로 계산한다. `--scene-durs`는 파일 경로나 JSON 문자열을 받는다.
