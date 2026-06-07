# 가이드북 spec JSON 스키마

각 노트북 → 가이드북 1개. `_guidebook/gb_<slug>.json` 에 저장.

```jsonc
{
  "title": "📘 가이드북 제목 (예: 6주차 실습2 — PyTorch 신경망 학습)",
  "blocks": [ {블록 spec}, ... ]
}
```

## 블록 spec 타입 (03_build_notion.py block_from_spec 과 동일)

| type | 필드 | 비고 |
|------|------|------|
| `h2` | `text` | 큰 섹션 제목 (파란 배경 자동) |
| `h3` | `text` | 소제목 |
| `p` | `text` | 본문. `**굵게**` `_이탤릭_` `` `코드` `` 지원 |
| `callout` | `text`, `emoji`, `color` | 강조 박스. color 기본 default_background, 팁은 `blue_background`, 핵심은 `orange_background`, 주의는 `red_background` |
| `num` | `items`[] | 번호 목록 |
| `bul` | `items`[] | 불릿 목록 |
| `code` | `code`, `language` | 코드 블록. language 기본 python |
| `eq` | `expression` | LaTeX 수식 |
| `quote` | `text` | 인용 |
| `divider` | - | 구분선 |
| `output` | `text` | **코드 실행 결과(출력)**. 회색 코드블록으로 렌더됨. 노트북 셀의 `outputs` 값을 그대로 넣어 "이 코드를 돌리면 이렇게 나와요"를 보여줄 때 |
| `image_ref` | `key` | **코드가 만든 그림**(matplotlib 등). 노트북 셀의 `output_images` 배열에 있는 key를 그대로 넣으면 구글드라이브 이미지로 자동 치환됨 |

## 출력·그림 사용 규칙 (중요)

노트북 cells의 각 code 셀에는 `outputs`(실행 결과 텍스트)와 `output_images`(그림 key 목록)가 들어있다.
- 코드를 설명한 직후, 그 셀에 `outputs`가 있으면 **`output` 블록으로 실제 결과를 보여주고** "이 결과는 ~를 의미해요" 해설을 붙인다.
- 그 셀에 `output_images`가 있으면 **각 key를 `image_ref` 블록으로** 넣어 그림을 보여주고, 그림이 무엇을 나타내는지 설명한다.
- key는 절대 지어내지 말 것. 노트북 데이터의 `output_images`에 있는 값만 사용.

## 가이드북 작성 원칙 (코드 0 기초자 대상, 전체 상세형)

1. **맨 위**: callout으로 "이 노트북으로 할 수 있게 되는 것" + 선수지식
2. **import 섹션**: 쓰인 라이브러리마다 "무엇을·왜" 한 줄 설명 (bul)
3. **코드 흐름을 의미 단위로 섹션화** (h2/h3). 노트북의 마크다운 셀을 길잡이로 활용.
4. **각 코드 조각마다**:
   - `code` 블록으로 실제 코드 제시 (노트북에서 발췌, 너무 길면 핵심만)
   - `p`로 **한 줄씩 무슨 뜻인지** 풀이 (코드 모르는 사람 눈높이)
   - 함수/메서드는 "`함수()` 는 ~를 한다" 식으로 문법 설명
5. **하이퍼파라미터/주요 인자**가 나오면:
   - `bul` 또는 표로 "인자 = 의미, 이 값이면 이렇게 됨, 권장 기준"
   - callout(blue_background)로 "⚙️ 실무 팁: 이 값을 어떻게 정하나"
6. **실무 적용**: callout으로 "💼 실무에서는 …" (언제 쓰나, 흔한 실수, 대안)
7. **맨 끝**: "✅ 핵심 체크리스트" (num) — 이 노트북에서 꼭 기억할 것

## 어투
친근하게 (~예요/~이야/~합니다). 전문용어는 쉬운 말 병기.
실제 코드 기반 — 노트북에 없는 내용 지어내지 말 것. 단 개념 보충 설명은 OK.
