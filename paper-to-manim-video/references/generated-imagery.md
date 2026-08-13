# 생성 이미지 노드 (Codex `image_generation`)

Manim 도형·수식으로 표현이 안 되는 컷만 채우는 **보조** 수단이다. 영상의 뼈대는 임커밋 구조이고 기본값은 언제나 Manim 작도다.

---

## 언제 쓰나

**편당 1~3컷 상한.** 그보다 많아지면 편성이 잘못된 것이니 Stage 2로 돌아간다.

| 쓴다 | 안 쓴다 |
|---|---|
| 개념적 은유 (고차원 공간에서 이웃 찾기) | 논문의 실제 그림 → `crop_figure.py` |
| 분위기·전환 배경 | 데이터·성능 그래프 → `crop_figure.py` |
| 실물 비유 (에너지 지형을 언덕으로) | 아키텍처 다이어그램 → Manim 작도 |
| 추상 개념의 정서적 이미지 | 텐서·레이어 도식 → raenim `Tensor`/`MLP` |

---

## 정확성 가드레일

이 영상은 사용자 **본인의 연구**를 설명한다. 생성 이미지가 연구 산출물처럼 보이면 그건 조작이다.

`gen_image.py`가 프롬프트를 검사해 다음을 **거부(exit 2)** 한다: 그래프·차트·plot, 성능·정확도·benchmark·결과표, 아키텍처 다이어그램, `figure N`·논문 그림, 산점도·히스토그램·히트맵.

`--override-guardrail`이 있지만 쓰지 않는 것이 기본이다. 쓴다면 그 컷은 반드시 사람이 확인해야 한다.

생성 이미지를 쓴 컷은 `shots.json`의 `asset.kind == "generated"`로 표시되고, **CP3 최종 검수 목록에 자동으로 올라간다.**

---

## 품질 규칙

**1. 이미지 안에 글자를 넣지 않는다.** 생성 텍스트는 깨지고 한글은 특히 심하다. 라벨·수식·캡션은 전부 Manim `Text`/`MathTex`로 위에 얹는다. 부수 효과로 영상 전체의 타이포가 일관된다.

**1-b. 가로 구도를 요구한다.** 무대는 16:9인데 기본 생성물은 세로에 가깝게 나오기 쉽다. `set_height()`로 맞추면 좌우가 크게 비어 컷이 작아 보인다. 프롬프트에 "wide 16:9 landscape composition, subject spanning the full width"를 넣거나, Manim에서 `set_width(config.frame_width * 0.8)`로 폭 기준으로 맞춘 뒤 상하 여백을 캡션에 쓴다. (실측: 첫 생성물이 3:4라 1080p 무대에서 좌우가 각각 25%씩 검게 남았다.)

**2. 스타일 프리픽스를 고정한다.** `gen_image.py`의 `STYLE_PREFIX`가 시리즈 전체에 같은 룩을 강제한다 — 순수 검정 `#000000` 배경, 플랫 벡터, 제한 팔레트(흰색·연한 파랑·틸 + 따뜻한 악센트 하나), 넉넉한 여백, 상단에 캡션 자리. 검정 배경이라 Manim 무대에 이어 붙어도 경계가 보이지 않는다.

**3. 자동 승인하지 않는다.** 결과가 비결정적이다. 부적합하면 프롬프트를 다듬어 재생성(최대 3회), 초과하면 그 컷을 Manim 작도로 폴백한다.

---

## 사용

```bash
# 능력 게이트만 확인
python scripts/gen_image.py --check

# 생성
python scripts/gen_image.py \
  --prompt "빽빽한 점들이 떠 있는 어두운 공간에서, 한 점 주위로 빛의 구가 퍼지며 가장 가까운 이웃만 밝게 감싸는 장면" \
  --out <episode>/assets/generated/intro_s04_neighborhood.png
```

프롬프트 원문은 `assets/generated/prompts.json`에 기록되어 재생성·감사 추적이 된다.

Manim에서:
```python
img = ImageMobject(str(ASSETS / "generated" / "intro_s04_neighborhood.png"))
img.set_height(6)
caption = kr("가까운 이웃만 강하게 끌어당깁니다", font_size=28).to_edge(UP)
self.playw(FadeIn(img), run_time=1.2, wait=1.0)
self.playw(Write(caption), run_time=1.0, wait=2.4)
```

---

## 능력 게이트

`codex`가 없거나 `image_generation` 플래그가 꺼져 있으면 이 노드는 **통째로 꺼지고** 전 구간 Manim 작도로 진행한다. 스킬은 codex 없이도 완전히 동작해야 한다 — 이미지 생성이 실패했다고 파이프라인이 멈추면 안 된다.

확인: `codex features list | findstr image_generation` → `stable  true`

---

## 알려진 함정

Windows에서 `codex`는 npm `.cmd` 셸이다. 프롬프트를 명령행 인자로 넘기면 `cmd.exe`가 재파싱하면서 괄호 `(#000000)` 같은 문자가 깨지고, codex가 *"Please send the image description"* 이라고 되묻는다. `gen_image.py`는 `codex exec -`로 **stdin에 넘겨** 이를 회피한다. 직접 호출할 일이 있다면 같은 방식을 쓸 것.
