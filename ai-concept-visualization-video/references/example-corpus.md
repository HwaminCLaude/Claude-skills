# 예시 코퍼스(참고 전용)

씬 코드를 쓸 때 연출 예시를 찾아보는 자료다. 실행하지 않는다. 에피소드 폴더에 복사하지 않는다.

이 스킬에는 코퍼스 파일이 들어 있지 않다. 원본 공개 저장소에 라이선스 파일이 없어서 다시 배포하지 않고, 쓰는 사람이 직접 받는다. 스킬 작성자는 원작자에게 코드를 참고해 써도 된다는 확인을 받았다. 다만 원본 저장소에 라이선스 파일이 없으므로, 받은 코드를 공개·상업용 영상에 그대로 빌려 쓰려면 원작자에게 직접 확인한다.

## 받기

```powershell
python "SK\scripts\fetch_examples.py"            # git 필요. 이미 있으면 건너뜀
python "SK\scripts\fetch_examples.py" --force    # 다시 받아 바꿔 끼우기(받기에 실패하면 있던 코퍼스는 그대로)
```

받으면 `references/example_corpus/`가 아래 구조로 생긴다. `flow-grammar.md`와 `design-system.md`의 `파일:줄`은 이 구조를 가리킨다.

- `<topic>.py`(33개): 원본 `src/<topic>/main.py`를 그대로 복사한 것. 줄 번호가 원본과 같다.
  - bondinterest, CFMvsDiffusion, clco_autohistory, clco2, clco3, CLIP, curseofknowledge, dunder_all, floatingpoint, gen_model, gqa, imcoming_leverage, jev1, jev2, justgrpo, justgrpo2, linearAttn, linearAttn2, linearAttn3, lmSampling1, lora1, lora2, mdlm, MLA, pagedAttn, preln, RvsBquiz, siglip, synthid1, turboquant1, turboquant2, turboquant3, uniformSum
  - 각 파일의 `class X(InteractiveScene, Scene2D)` 하나가 영상 한 토막이다. `## 주석` 한 줄이 박자 하나에 해당한다.
- `raenimgl/*.py`: raenimgl 패키지 소스(`Scene2D`, `playw`, `Words`, `Overlay` 등). 시그니처 요약은 `raenimgl-api.md`.
- 이미지, 영상, SVG 같은 에셋은 받지 않는다. 코드가 `ImageMobject("...png")`로 부르는 파일은 없다.

## 출처

| 내용 | 저장소 | 커밋 |
|---|---|---|
| 장면 코드 33편 | https://github.com/CodingVillainKor/manimgl-imcommit | `4c5cf5cb96a1e8f0be66410f1e95bc4871fe9ea0` |
| raenimgl | https://github.com/CodingVillainKor/raenimgl.git | `089d4ffec3cae45877cecd68ab143a5ab47190b3` |

- 이 스킬의 문서와 코드 주석에 나오는 **참고 영상**은 이 장면 코드로 만든 원작 공개 영상이고, **참고 코퍼스**는 이 장면 코드 묶음이다. 자막 속도, 어미 비율, 자막 획 굵기 같은 목표치는 참고 영상에서 잰 값이다.
- 코드는 연출을 참고하고 빌려 쓰는 데만 쓴다. 원작 채널의 로고와 이름 같은 브랜드 요소는 화면과 자막에 쓰지 않는다.
- 렌더에 쓰는 ManimGL 포크와 raenimgl은 이 코퍼스와 별개로, 프로젝트를 만들 때 `uv sync`가 받는다(`assets/project_template/pyproject.toml`).

## 쓰지 않는 것

- raenimgl의 `Logo` 클래스(원작 채널 로고). 린트 `T9`가 ERROR로 막는다.
- `self.embed()`, `_mhelper.py`, `_mupdater.py` 같은 대화형 편집 보조.
- raenimgl `constant.py`의 `X_STRING "✘"`, `CHECK_STRING "✔"`: Noto Sans KR에 없는 글리프다. `✓`를 쓴다.

## 찾아보는 법

- 연출별 대표 예시는 `flow-grammar.md`에 `파일:줄`로 정리돼 있다.
- 직접 찾을 때(Git Bash): `grep -n "cf.animate.reorient" references/example_corpus/*.py`
