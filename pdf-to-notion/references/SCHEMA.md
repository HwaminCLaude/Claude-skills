# Explanation JSON 스키마

`_output/explanations.json` 의 구조.

```jsonc
{
  "<deck_slug>": {
    // 페이지 번호 -> 노션 블록 배열. 우측 column 안에 그대로 들어감.
    "page_explanations": {
      "1": [
        { "type": "callout", "text": "이 자료는 ~를 다룹니다.", "emoji": "💡", "color": "orange_background" },
        { "type": "p", "text": "본문은 **굵게** 표시할 수 있어요." }
      ],
      "2": [
        { "type": "h3", "text": "이번 장에서 다룰 것" },
        { "type": "num", "items": ["수집은 데이터를 모으는 것,", "요약은 데이터를 정리하는 것"] },
        { "type": "p", "text": "" }
      ]
    },
    // (선택) 페이지 번호 -> 새 H2 섹션 시작 제목. 없으면 페이지 식별자(p001) 사용.
    "section_titles": {
      "3": "What is Regression?",
      "7": "Linear Regression"
    }
  }
}
```

## 지원 블록 타입

| type   | 필드                                | 비고                                 |
|--------|-------------------------------------|--------------------------------------|
| `p`    | `text`                              | 일반 paragraph. `**굵게**` 지원      |
| `h3`   | `text`                              | 소제목 (페이지 내부)                 |
| `callout` | `text`, `emoji`(기본 💡), `color`(기본 default_background) | 강조 박스 |
| `quote` | `text`                              | 인용                                 |
| `num`  | `items` (str 리스트)                | 번호 매김                            |
| `bul`  | `items` (str 리스트)                | 불릿                                 |
| `mermaid` | `code`                           | code 블록 (mermaid)                  |
| `code` | `code`, `language`(기본 python)     | 일반 코드 블록                       |
| `divider` | -                                | 구분선                               |
| `eq`   | `expression`                        | LaTeX 수식 (equation 블록)           |

`text` 안에서 `**...**` 를 굵게, `_..._` 를 이탤릭, `` `...` `` 를 코드로 변환.

## 작성 가이드 (참조 노션 스타일)

- 친근한 어투 (~이야 / ~입니다 / ~에요)
- **핵심 용어는 굵게**
- 한 줄 요약은 callout(orange_background)으로 강조
- 개념 분류/흐름은 mermaid `flowchart`
- 정의 = 설명 형태일 때 번호 매김 (수집은 ~, 요약은 ~)
- 페이지가 표지/목차/간지면 짧은 안내 1~2줄
