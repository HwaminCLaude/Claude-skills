# 자막

자막은 `shots.json`의 큐 목록에서 만들고, ffmpeg libass로 영상에 굽는다. 큐 형식은 `shots-schema.md`를 본다.

## 원천

- 큐마다 `t`(화면에 보일 문구), `say`(TTS 발음, 없으면 `t`), `key`(노랑으로 칠할 부분 문자열), `rel`, `move`, `hold`.
- 표시용 `t`와 발음용 `say`를 나눠서 '로라', '비플로트 십육' 같은 발음 표기가 화면에 뜨지 않게 한다.

## 모양(린트 `C1`~`C4`, `C7`)

- 1줄, 공백 포함 26자 이하(`C1` ERROR). 편 중앙값 15~20자.
- 끝에 마침표를 찍지 않는다(`C2` ERROR). 물음표는 질문에만, 쉼표는 문장 중간에 끊을 때만.
- `·`, `—`, `→`, `:`, 부연 괄호는 쓰지 않는다(`C3` ERROR).
- `key`는 `t`의 부분 문자열이고 큐당 1개 이하(`C4` ERROR).
- `t`의 모든 글자는 Noto Sans KR cmap에 있어야 한다(`C7` ERROR). 2026-10-27 확인(`C:\Windows\Fonts\NotoSansKR-Bold.ttf`): 아래첨자 `₀`(U+2080)와 `✔ ✕ ✗ ✘`는 없고, `α`, `Δ`, `✓`, `−`(U+2212)는 있다. `W₀`는 자막에서 'W'만 쓰고 화면 Tex로 `W_0`를 보여 준다.

## 핵심어 노랑

- 큐당 한 구간 이하. 낱말 하나에서 절 하나(약 27자)까지.
- 새 용어, 대조, 숫자에 쓴다. 편 전체에서 칠한 큐는 10~30%.
- ASS 태그: `{\c&H0025CFEA&}핵심어{\c&H00DCDCDC&}`(`#EACF25` → BGR `&H0025CFEA`).

## 시간

- 무음 모드 큐 길이: `max(1.2, n_syll/5.5 + 0.25*쉼표수 + 0.55*물음표수)`초. n_syll = 한글 음절 수 + 라틴 단어 수 + 숫자 덩어리 수(`cues.py estimate`).
- 공백을 뺀 속도가 6.4자/초(참고 영상 중앙값)를 넘으면 큐를 쪼갠다.
- TTS 모드: 큐마다 합성한 음성의 실측 길이(`tts/durs.json`).
- 큐 사이 빈틈은 0. 다음 큐 시작이 이번 큐 끝이다(참고 영상 98.8%).
- 실제 시각은 렌더 중 `CueScene`이 남긴 `cuelog/<Scene>.json`의 `start`를 쓴다. 애니메이션이 큐를 넘어도 자막이 화면과 어긋나지 않는다. 0.3초 넘는 초과는 `CUE_OVERRUN`으로 보고된다.

## ASS 스타일

```
[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans KR Medium,64,&H00DCDCDC,&H00DCDCDC,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,2,60,60,103,1
```

- 글자 `&H00DCDCDC`(#DCDCDC), 외곽선·그림자 0, Alignment 2(하단 가운데), MarginV 103(줄 중심 약 947~948px), MarginL/R 60.
- 목표: 한글 잉크 약 40px, 획 약 4px(참고 영상 실측).
- 시각 형식은 `H:MM:SS.cc`.

### 글꼴: 설계 §5.6의 'Bold'를 이렇게 구현했다

- **Fontname `Noto Sans KR Medium`, Bold `0`**. 정적 `C:\Windows\Fonts\NotoSansKR-Medium.ttf`(굵기 500)만 legacy 가족 이름이 `Noto Sans KR Medium`이라, 이 이름이면 그 파일 하나로 정확히 떨어진다. 값은 `captions.py`의 `CAPTION_FONT`, `CAPTION_BOLD`에 있다.
- 'Noto Sans KR' + Bold `-1`(처음 값)은 쓰지 않는다. `NotoSansKR-VF.ttf`가 같은 가족 이름으로 등록되고 기본 인스턴스가 Thin이라, libass(DirectWrite)가 VF를 고르고 Bold 플래그는 듣지 않는다. 획 2px로 참고 영상의 절반이 된다(`troubleshooting.md`의 'VF Thin 함정').
- 정적 Bold 파일(subtitles `fontsdir`로 넘기고 'Noto Sans KR' Bold -1)은 획 6px로 참고 영상보다 눈에 띄게 무겁다. Medium + Bold -1(가짜 굵게)은 5px다. 'Noto Sans KR Bold'(전체 이름)나 'NotoSansKR-Bold'(PostScript 이름)는 DirectWrite에서 **Arial로 조용히 바뀐다**.
- 2026-10-27 실측(검정 1920×1080, libx264 crf 18을 거친 프레임, '학습하면 여기만 바뀌어요'): 잉크 높이 40px, 줄 중심 947.5px, 획 4px. 참고 영상 lora1 1:00 프레임은 잉크 42px, 중심 948.5px, 획 4px. 같은 문구('그래서 원래 weight는')로 나란히 놓은 눈 비교에서 Medium이 가장 가까웠다(Regular는 가늘고 Bold는 무겁다).
- 밝기: 참고 영상 글자 최대 밝기는 약 248, 우리(#DCDCDC)는 약 231이다. 색은 바꾸지 않았다.
- 확인: `preflight.py`의 `capfont` 줄이 이 ASS 헤더 그대로 한 줄을 구워 libass `fontselect`가 `NotoSansKR-Medium`을 골랐는지 본다. 아니면 FAIL. `assemble.py`도 굽기 로그에서 같은 검사를 해서 다른 글꼴로 바뀌었으면 FAIL로 멈춘다. 자막 글자 가운데 Medium에 없는 글자가 대체 글꼴로 그려지면 `WARN caption glyph 0x....`를 찍는다.

### 문구 이스케이프

- 큐 문구의 `{`, `}`는 `\{`, `\}`로 바꿔 재정의 블록(`{\...}`)이 되지 않게 한다.
- 백슬래시 뒤에는 보이지 않는 WORD JOINER(U+2060)를 끼워 `\N`, `\n`, `\h`가 줄바꿈이나 공백으로 읽히지 않게 한다. libass 0.17.5에서 글자 그대로 그려지는 것을 확인했다.

## 태우기

- `assemble.py`가 에피소드 폴더를 cwd로 두고 `subtitles=captions.ass`(상대 경로)로 굽는다. 경로에 공백이나 한글이 있어도 필터 인자가 깨지지 않게 하기 위해서다.
- 무음 모드: 음성 트랙 없이 박힌 자막만.
- TTS 모드: 음성 트랙 + 박힌 자막. 자막을 별도 SRT로도 내보낸다.
