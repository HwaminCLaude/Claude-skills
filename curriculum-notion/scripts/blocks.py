# -*- coding: utf-8 -*-
"""blocks.py — 딥러닝 구성요소 교과서용 Notion 블록 빌더.

모든 챕터 빌드 스크립트가 import 해서 쓰는 공용 라이브러리.
목표: 에이전트가 raw JSON을 손으로 쓰지 않고, 파이썬 함수 호출만으로
      구조가 항상 유효한 Notion 블록(수식/표/mermaid/이미지/코드)을 만든다.

인라인 미니 마크업(문자열 안에서 그대로 사용):
  **굵게**      -> bold
  `코드`        -> inline code (annotation)
  $x^2+1$       -> KaTeX 인라인 수식 (equation rich_text)
  [라벨](url)   -> 링크
  ~~취소선~~    -> strikethrough
  (그 외 텍스트는 평문)

핵심 규칙(검증된 함정 회피):
  - code 블록 language 는 반드시 유효값("python","bash","json","mermaid","plain text").
  - rich_text 1개 content 는 2000자 한도 -> dump_chunks 가 자동 분할.
  - 이미지는 외부 URL만 가능 -> image(key) 는 "__IMG__:key" 자리표시자를 넣고
    drive_sync 가 업로드 후 실제 lh3 URL 로 치환한다.
  - 한 append 요청 100블록 한도 -> dump_chunks 가 90개씩 청크로 나눈다.
  - 중첩은 2단계까지(toggle 안에 표/토글 넣지 말 것).
"""
from __future__ import annotations
import json, os, re
from pathlib import Path

MAXLEN = 1900  # rich_text content 안전 한도

# ---------------------------------------------------------------------------
# 인라인 파서: 문자열 -> rich_text 배열
# ---------------------------------------------------------------------------
_INLINE = re.compile(
    r"\$(?P<eq>[^$]+?)\$"
    r"|\*\*(?P<bold>.+?)\*\*"
    r"|~~(?P<strike>.+?)~~"
    r"|`(?P<code>[^`]+?)`"
    r"|\[(?P<ltext>[^\]]+?)\]\((?P<lurl>[^)]+?)\)"
)


def _txt(content, ann=None, link=None):
    o = {"type": "text", "text": {"content": content}}
    if link:
        o["text"]["link"] = {"url": link}
    if ann:
        o["annotations"] = ann
    return o


def rich(s):
    """인라인 마크업 문자열 -> Notion rich_text 배열. (이미 dict/list면 그대로 통과)"""
    if s is None:
        return []
    if isinstance(s, dict):
        return [s]
    if isinstance(s, list):
        out = []
        for e in s:
            out.extend(rich(e))
        return out
    if not isinstance(s, str):
        s = str(s)
    out, pos = [], 0
    for m in _INLINE.finditer(s):
        if m.start() > pos:
            out.append(_txt(s[pos:m.start()]))
        if m.group("eq") is not None:
            out.append({"type": "equation", "equation": {"expression": m.group("eq")}})
        elif m.group("bold") is not None:
            out.append(_txt(m.group("bold"), {"bold": True}))
        elif m.group("strike") is not None:
            out.append(_txt(m.group("strike"), {"strikethrough": True}))
        elif m.group("code") is not None:
            out.append(_txt(m.group("code"), {"code": True, "color": "default"}))
        elif m.group("ltext") is not None:
            out.append(_txt(m.group("ltext"), link=m.group("lurl")))
        pos = m.end()
    if pos < len(s):
        out.append(_txt(s[pos:]))
    return out or [_txt("")]


def _block(t, payload):
    return {"object": "block", "type": t, t: payload}


# ---------------------------------------------------------------------------
# 텍스트 계열
# ---------------------------------------------------------------------------
def h1(s):
    return _block("heading_1", {"rich_text": rich(s), "color": "default"})


def h2(s, color="default"):
    return _block("heading_2", {"rich_text": rich(s), "color": color})


def h3(s, color="default"):
    return _block("heading_3", {"rich_text": rich(s), "color": color})


def p(s):
    return _block("paragraph", {"rich_text": rich(s)})


def bullet(s):
    return _block("bulleted_list_item", {"rich_text": rich(s)})


def numbered(s):
    return _block("numbered_list_item", {"rich_text": rich(s)})


def todo(s, checked=False):
    return _block("to_do", {"rich_text": rich(s), "checked": checked})


def quote(s):
    return _block("quote", {"rich_text": rich(s)})


def callout(s, emoji="💡", color="gray_background"):
    return _block("callout", {
        "rich_text": rich(s),
        "icon": {"type": "emoji", "emoji": emoji},
        "color": color,
    })


def divider():
    return _block("divider", {})


def toc():
    return _block("table_of_contents", {"color": "default"})


# ---------------------------------------------------------------------------
# 수식 / 코드 / mermaid
# ---------------------------------------------------------------------------
def equation(expr):
    """디스플레이 수식 블록($$...$$). expr 에 $ 기호 넣지 말 것."""
    return _block("equation", {"expression": expr.strip()})


def _split(src):
    return [src[i:i + MAXLEN] for i in range(0, len(src), MAXLEN)] or [""]


def code(src, lang="python", caption=None):
    payload = {
        "rich_text": [_txt(c) for c in _split(src)],
        "language": lang,
    }
    if caption:
        payload["caption"] = rich(caption)
    return _block("code", payload)


def mermaid(diagram, caption=None):
    return code(diagram.strip(), lang="mermaid", caption=caption)


# ---------------------------------------------------------------------------
# 표
# ---------------------------------------------------------------------------
def _cell(v):
    return rich(v)


def table(headers, rows, has_row_header=False):
    """headers: [str...], rows: [[cell,...],...]. 셀은 인라인 마크업 지원."""
    width = len(headers)
    children = [_block("table_row", {"cells": [_cell(h) for h in headers]})]
    for r in rows:
        cells = [_cell(c) for c in r]
        while len(cells) < width:
            cells.append(rich(""))
        children.append(_block("table_row", {"cells": cells[:width]}))
    return _block("table", {
        "table_width": width,
        "has_column_header": True,
        "has_row_header": has_row_header,
        "children": children,
    })


# ---------------------------------------------------------------------------
# 토글 / 이미지
# ---------------------------------------------------------------------------
def toggle(summary, children):
    return _block("toggle", {"rich_text": rich(summary), "children": children})


def image(key, caption=None):
    """key = images/{key}.png 의 stem. drive_sync 가 URL로 치환."""
    return _block("image", {
        "type": "external",
        "external": {"url": f"__IMG__:{key}"},
        "caption": rich(caption) if caption else [],
    })


# ---------------------------------------------------------------------------
# 청크 저장 (2000자 분할 + 90블록/파일)
# ---------------------------------------------------------------------------
def _sanitize_rt(rt):
    out = []
    for e in rt or []:
        if e.get("type", "text") == "text":
            c = e["text"].get("content", "")
            if len(c) > MAXLEN:
                for i in range(0, len(c), MAXLEN):
                    seg = {"type": "text", "text": {"content": c[i:i + MAXLEN]}}
                    if e["text"].get("link"):
                        seg["text"]["link"] = e["text"]["link"]
                    if e.get("annotations"):
                        seg["annotations"] = e["annotations"]
                    out.append(seg)
                continue
        out.append(e)
    return out


def _sanitize_block(b):
    t = b.get("type")
    payload = b.get(t)
    if isinstance(payload, dict):
        if isinstance(payload.get("rich_text"), list):
            payload["rich_text"] = _sanitize_rt(payload["rich_text"])
        if isinstance(payload.get("caption"), list):
            payload["caption"] = _sanitize_rt(payload["caption"])
        if isinstance(payload.get("children"), list):
            for c in payload["children"]:
                _sanitize_block(c)
        if isinstance(payload.get("cells"), list):
            payload["cells"] = [_sanitize_rt(c) for c in payload["cells"]]
    return b


def dump_chunks(blocks, prefix, outdir, size=90):
    """blocks(list) -> outdir/prefix_c01.json ... 로 저장. (파일목록, 총블록수) 반환."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for b in blocks:
        _sanitize_block(b)
    files = []
    n = 0
    for i in range(0, len(blocks), size):
        n += 1
        fp = outdir / f"{prefix}_c{n:02d}.json"
        chunk = blocks[i:i + size]
        json.dump(chunk, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
        files.append(str(fp))
    return files, len(blocks)


# 자주 쓰는 색상 상수(콜아웃/헤딩)
BLUE = "blue_background"
GREEN = "green_background"
YELLOW = "yellow_background"
ORANGE = "orange_background"
RED = "red_background"
PURPLE = "purple_background"
GRAY = "gray_background"
BROWN = "brown_background"
PINK = "pink_background"

if __name__ == "__main__":
    # 스모크 테스트
    bs = [
        h1("테스트"),
        p("이건 **굵게**, `코드`, 그리고 인라인 수식 $e^{i\\pi}+1=0$ 입니다."),
        equation("\\mathcal{L} = -\\sum_i y_i \\log \\hat{y}_i"),
        callout("팁입니다", "💡", YELLOW),
        table(["A", "B"], [["1", "**2**"], ["$x$", "y"]]),
        code("import torch\nx = torch.randn(3)\nprint(x)", "python"),
        mermaid("graph LR\n  A-->B"),
        image("demo", "그림 캡션"),
        toggle("더 보기", [p("숨겨진 내용")]),
    ]
    files, total = dump_chunks(bs, "smoke", "._smoke")
    print("OK", total, files)
    print(json.dumps(bs[1], ensure_ascii=False))
