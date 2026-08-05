"""
02_extract_sections.py — 본문을 목차 725개 절로 정확히 쪼개고 블록 spec으로 변환한다.

이 PDF의 특성 (실측):
  * 물리적 한 줄이 각각 하나의 block → 블록 경계로는 문단을 못 나눈다.
    문단 시작 신호는 `▣` 마커뿐이고, 나머지 줄은 앞 문단의 이어짐이다.
  * HWP가 문단을 줄 단위로 자르며 **음절 중간에서도 끊는다**
    ("…기술이 아" + "니라 컴퓨팅…") → 한글끼리는 공백 없이, 그 외는 공백으로 이어붙인다.
  * 머리말 y0≈56.5 / 쪽번호 y0≈776 → HEADER_Y~FOOTER_Y 밖은 버린다.
  * 표는 find_tables() 로 구조를 뽑고, 표 안의 줄은 텍스트 스트림에서 제외한다.
  * 그림은 벡터/래스터라 텍스트가 없다 → 캡션 아래 영역의 크롭 좌표만 기록한다.

산출: _output/sections.json, _output/figures.json
게이트: 헤딩 725개를 모두 찾지 못하거나 본문 줄 커버리지가 100%가 아니면 중단.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).parent))
import config as C

CAP_RE = re.compile(r"^\[(그림|표)([ⅠⅡⅢⅣ])-(\d+)\]\s*(.*)$")
SRC_RE = re.compile(r"^자료\s*[:：]")
UNIT_RE = re.compile(r"^[(（][^)）]{0,30}[)）]$")   # (단위: 억 달러) 같은 캡션 부속 주석
BULLET = "▣"
SUB_BULLET = ("-", "·", "•", "※", "◦")


def join_line(prev: str, nxt: str, space: bool) -> str:
    """HWP 줄바꿈 복원.

    PDF 원본 줄은 **줄 끝 공백으로 단어 경계를 보존**한다 (실측: 줄끝 공백 있음 393 /
    없음 2267, 후자의 대부분은 '…기술이 아' + '니라…' 처럼 음절 중간 끊김).
    따라서 앞 줄의 trailing space 또는 뒤 줄의 leading space 유무를 그대로 따른다.
    """
    if not prev:
        return nxt
    if not nxt:
        return prev
    # 예외: 양쪽 정렬 때문에 구두점 뒤 공백이 줄바꿈에 삼켜지는 경우가 있다
    # (p99 '어렵다.'+'실제', p160 '측정하고,'+'또한').
    # 구두점 다음에 글자가 오면 항상 띄어야 하므로 공백을 넣는다.
    # 숫자가 이어지는 경우(3.5, 1,850)는 nxt 가 글자가 아니라 자동으로 제외된다.
    if not space and prev[-1] in ".,!?;:" and (nxt[0].isalpha() or is_hangul(nxt[0])):
        space = True
    return prev + (" " if space else "") + nxt


def is_hangul(ch: str) -> bool:
    return 0xAC00 <= ord(ch) <= 0xD7A3


def squeeze(s: str) -> str:
    """양쪽 정렬로 벌어진 다중 공백을 하나로."""
    return re.sub(r"[ \t ]+", " ", s).strip()


# ── 페이지 → 아이템 스트림 ──────────────────────────────────
def cell_text(page, bbox) -> str:
    """표 셀 하나를 좌표로 다시 읽어 줄바꿈을 올바르게 복원한다.

    find_tables().extract() 는 셀 안 줄을 `\\n` 으로 이어 붙여 주는데, 그러면
    '학습 성능\\n향상'(공백 필요)과 '성능 제\\n공'(공백 불가)을 구분할 수 없다.
    본문과 같은 줄끝 공백 신호를 써야 정확하다.
    """
    if bbox is None:
        return ""
    d = page.get_text("dict", clip=fitz.Rect(bbox))
    out, trail = "", False
    for blk in d.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for ln in blk.get("lines", []):
            raw = "".join(sp.get("text", "") for sp in ln.get("spans", []))
            piece = squeeze(raw)
            if not piece:
                continue
            space = trail or raw != raw.lstrip()
            # 좁은 셀에서는 영어 단어 사이 공백이 줄바꿈에 삼켜지기도 한다
            # ('Deep Neural' + 'Network'). 한글과 달리 영문은 단어 중간에서 끊기지
            # 않으므로 영문+영문이면 공백을 넣는다.
            if not space and out and out[-1].isascii() and out[-1].isalpha() \
                    and piece[0].isascii() and piece[0].isalpha():
                space = True
            out = join_line(out, piece, space)
            trail = raw != raw.rstrip()
    return out


def page_items(doc, pno: int) -> list[dict]:
    """한 쪽을 y 순서의 아이템 목록으로. kind: line | table"""
    page = doc[pno - 1]
    try:
        tables = page.find_tables().tables
    except Exception:
        tables = []

    trects = []
    for t in tables:
        try:
            rows = [[cell_text(page, cb) for cb in row.cells] for row in t.rows]
        except Exception:
            try:
                rows = [[squeeze(c or "") for c in row] for row in t.extract()]
            except Exception:
                rows = []
        rows = [r for r in rows if any(c.strip() for c in r)]
        if not rows:
            continue
        trects.append((fitz.Rect(t.bbox), rows))

    events: list[dict] = []
    for rect, rows in trects:
        events.append({"kind": "table", "page": pno, "y0": rect.y0, "y1": rect.y1,
                       "rows": rows})

    d = page.get_text("dict")
    for blk in d.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for ln in blk.get("lines", []):
            bbox = ln.get("bbox")
            if not bbox:
                continue
            y0, y1 = bbox[1], bbox[3]
            if y0 < C.HEADER_Y or y0 > C.FOOTER_Y:
                continue
            raw = "".join(sp.get("text", "") for sp in ln.get("spans", []))
            text = squeeze(raw)
            if not text:
                continue
            cy = (y0 + y1) / 2
            cx = (bbox[0] + bbox[2]) / 2
            if any(r.y0 - 1 <= cy <= r.y1 + 1 and r.x0 - 1 <= cx <= r.x1 + 1
                   for r, _ in trects):
                continue  # 표 내부 줄 → 표 구조로 이미 담겼다
            # 줄 끝/시작 공백 = 원문 띄어쓰기 정답 (join_line 참조). squeeze 전에 본다.
            events.append({"kind": "line", "page": pno, "y0": y0, "y1": y1,
                           "x0": bbox[0], "text": text,
                           "trail": raw != raw.rstrip(),
                           "lead": raw != raw.lstrip()})

    events.sort(key=lambda e: (round(e["y0"], 1), e.get("x0", 0)))
    return events


def build_stream(doc) -> list[dict]:
    stream: list[dict] = []
    for pno in range(C.BODY_FIRST, C.BODY_LAST + 1):
        stream.extend(page_items(doc, pno))
    return stream


# ── 헤딩 위치 확정 ──────────────────────────────────────────
def locate_headings(stream: list[dict], nodes: list[dict]) -> tuple[dict, list[dict]]:
    """노드 id → stream 인덱스. 목차 순서대로 커서를 전진시켜 중복 제목 오인을 막는다."""
    pos: dict[str, int] = {}
    fails: list[dict] = []
    cursor = 0
    for n in nodes:
        want = C.norm(n["prefix"] + n["title"])
        found = -1
        for k in range(cursor, len(stream)):
            e = stream[k]
            if e["kind"] != "line":
                continue
            if e["page"] < n["page"]:
                continue
            if e["page"] > n["page"]:
                break
            t = C.norm(e["text"])
            if t.startswith(want) or want in t:
                found = k
                break
            # 긴 제목이 두 줄로 접힌 경우: 다음 줄까지 이어 붙여 재시도
            if k + 1 < len(stream) and stream[k + 1]["kind"] == "line":
                if C.norm(e["text"] + stream[k + 1]["text"]).startswith(want):
                    found = k
                    break
        if found < 0:
            fails.append(n)
        else:
            pos[n["id"]] = found
            cursor = found + 1
    return pos, fails


# ── 아이템 → 블록 spec ──────────────────────────────────────
def to_blocks(items: list[dict], fig_seq: list[dict], node_id: str) -> list[dict]:
    """한 절의 아이템들을 Notion 블록 spec 배열로. 이어지는 줄은 앞 블록에 병합."""
    out: list[dict] = []
    cur: dict | None = None       # 진행 중인 p / bul 블록

    def flush():
        nonlocal cur
        if cur is not None:
            cur["text"] = squeeze(cur["text"])
            if cur["text"]:
                out.append(cur)
            cur = None

    pending_fig: dict | None = None   # 캡션은 나왔고 크롭 영역을 기다리는 그림
    prev_trail = False                # 직전에 소비한 줄이 공백으로 끝났는가
    skip: set[int] = set()            # 캡션에 흡수돼 따로 처리하지 않을 아이템

    for idx, it in enumerate(items):
        if idx in skip:
            continue
        # 앞 줄 끝 공백 또는 이번 줄 앞 공백 → 이어붙일 때 공백 하나를 넣는다
        space = prev_trail or bool(it.get("lead"))
        if it["kind"] == "table":
            flush()
            pending_fig = None
            prev_trail = False
            rows = it["rows"]
            # 직전 블록이 [표..] 캡션이면 표의 캡션으로 흡수
            caption = ""
            if out and out[-1].get("type") == "caption" and out[-1].get("cat") == "표":
                caption = out.pop()["text"]

            # 쪽 경계에서 잘린 표 이어붙이기.
            # 캡션이 없는 표가 직전 표 바로 뒤(같거나 다음 쪽)에 같은 열 수로 나오면
            # 원래 한 표가 find_tables() 에 의해 둘로 쪼개진 것이다.
            if not caption and out and out[-1].get("type") == "table":
                prev = out[-1]
                pcols = max(len(r) for r in prev["rows"])
                ncols = max(len(r) for r in rows)
                if pcols == ncols and 0 <= it["page"] - prev["page"] <= 1:
                    if rows and prev["rows"] and rows[0] == prev["rows"][0]:
                        rows = rows[1:]      # 이어지는 쪽에 반복된 머리행 제거
                    prev["rows"].extend(rows)
                    prev["page_end"] = it["page"]
                    continue

            out.append({"type": "table", "caption": caption, "rows": rows,
                        "page": it["page"]})
            continue

        text = it["text"]
        m = CAP_RE.match(text)
        if m:
            flush()
            prev_trail = False
            cat, part, num, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            label = f"[{cat}{part}-{num}]"

            # 캡션 아래 빈 공간 = 이미지/벡터로 그려진 도식.
            # 진짜 표는 캡션 바로 아래(≈10pt)에 셀 텍스트가 오므로 자연히 구분된다.
            # 「표」 캡션인데 아래가 텅 비어 있으면 **이미지로 그려진 표**다(11건).
            top = it["y1"] + 2
            # 캡션 바로 밑 '(단위: 억 달러)' 같은 짧은 괄호 주석은 캡션의 일부다.
            # 그냥 두면 여백 계산이 막혀 도식을 못 잘라낸다.
            nxt = idx + 1
            while (nxt < len(items) and items[nxt]["kind"] == "line"
                   and items[nxt]["page"] == it["page"]
                   and UNIT_RE.match(items[nxt]["text"])):
                tail = f'{tail} {items[nxt]["text"]}'.strip()
                top = items[nxt]["y1"] + 2
                skip.add(nxt)
                nxt += 1
            nxt_y = None
            for j in range(nxt, len(items)):
                if items[j]["page"] == it["page"]:
                    nxt_y = items[j]["y0"]
                    break
            bottom = (nxt_y - 2) if nxt_y else (C.FOOTER_Y - 5)

            if bottom - top >= 40:
                # 그림은 기존 id 체계를 유지한다(이미 렌더·업로드·판독된 222장).
                fig_id = (f"fig_{it['page']:03d}_{num}" if cat == "그림"
                          else f"tab_{it['page']:03d}_{num}")
                fig_seq.append({"fig_id": fig_id, "page": it["page"],
                                "rect": [40.0, top, 555.0, bottom],
                                "label": label, "caption": squeeze(tail),
                                "node": node_id})
                out.append({"type": "figure", "fig_id": fig_id, "label": label,
                            "caption": squeeze(tail), "page": it["page"]})
                pending_fig = out[-1]
            else:
                out.append({"type": "caption", "cat": cat,
                            "text": squeeze(f"{label} {tail}")})
            continue

        if SRC_RE.match(text):
            flush()
            target = pending_fig if pending_fig else (out[-1] if out else None)
            if target is not None and target.get("type") in ("figure", "table"):
                target["source"] = join_line(target.get("source", ""), text, space) \
                    if target.get("source") else text
                prev_trail = bool(it.get("trail"))
                cur = None
                # 자료 줄이 두 줄로 이어질 수 있어 계속 이어붙이도록 표시
                out.append({"type": "_srccont", "ref": target})
            else:
                out.append({"type": "source", "text": text})
            continue

        # 자료 줄 바로 다음 줄이 이어짐이면 자료에 붙인다
        if out and out[-1].get("type") == "_srccont":
            ref = out[-1]["ref"]
            prev_src = ref.get("source", "")
            if prev_src and not prev_src.rstrip().endswith((".", "다", ")", "성")):
                ref["source"] = join_line(prev_src, text, space)
                prev_trail = bool(it.get("trail"))
                continue
            out.pop()

        if text.startswith(BULLET):
            flush()
            pending_fig = None
            cur = {"type": "bul", "text": text[len(BULLET):].strip()}
            prev_trail = bool(it.get("trail"))
            continue

        if text[:1] in SUB_BULLET and len(text) > 1 and text[1:2] in (" ", " ") or \
           (text[:1] in SUB_BULLET and len(text) > 2 and not text[1:2].isdigit()):
            flush()
            pending_fig = None
            cur = {"type": "sub", "text": text[1:].strip()}
            prev_trail = bool(it.get("trail"))
            continue

        # 그 외 = 이어지는 줄 (또는 절 첫 문단)
        pending_fig = None
        if cur is None:
            cur = {"type": "p", "text": text}
        else:
            cur["text"] = join_line(cur["text"], text, space)
        prev_trail = bool(it.get("trail"))

    flush()
    return [b for b in out if b.get("type") != "_srccont"]


def plain_text(blocks: list[dict]) -> str:
    """요약·검수용 평문 (Codex 입력)."""
    parts = []
    for b in blocks:
        t = b.get("type")
        if t in ("p", "bul", "sub", "source", "caption"):
            parts.append(b.get("text", ""))
        elif t == "figure":
            parts.append(f'{b["label"]} {b.get("caption","")}')
        elif t == "table":
            cap = b.get("caption", "")
            rows = b.get("rows", [])
            head = " | ".join(rows[0]) if rows else ""
            parts.append(f'{cap} (표 {len(rows)}행) {head}')
    return "\n".join(p for p in parts if p)


def main():
    nodes = json.loads(C.TOC_JSON.read_text(encoding="utf-8"))
    doc = fitz.open(C.PDF_PATH)
    stream = build_stream(doc)
    n_lines = sum(1 for e in stream if e["kind"] == "line")
    n_tables = sum(1 for e in stream if e["kind"] == "table")
    print(f"본문 아이템: 줄 {n_lines}개 + 표 {n_tables}개")

    pos, fails = locate_headings(stream, nodes)
    print(f"헤딩 확정 {len(pos)}/{len(nodes)} (실패 {len(fails)})")
    if fails:
        for n in fails[:15]:
            print(f"   MISS L{n['level']} {n['display'][:50]} p{n['page']}", file=sys.stderr)
        print("[ERROR] 헤딩을 모두 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    order = sorted(nodes, key=lambda n: pos[n["id"]])
    if [n["id"] for n in order] != [n["id"] for n in nodes]:
        print("[ERROR] 헤딩 순서가 목차 순서와 다릅니다.", file=sys.stderr)
        sys.exit(1)

    first = pos[nodes[0]["id"]]
    dropped_before = sum(1 for e in stream[:first] if e["kind"] == "line")

    sections: dict[str, dict] = {}
    figures: list[dict] = []
    used_lines = 0
    for i, n in enumerate(nodes):
        start = pos[n["id"]] + 1
        end = pos[nodes[i + 1]["id"]] if i + 1 < len(nodes) else len(stream)
        items = stream[start:end]
        used_lines += sum(1 for e in items if e["kind"] == "line")
        blocks = to_blocks(items, figures, n["id"])
        pages = [e["page"] for e in items] or [n["page"]]
        sections[n["id"]] = {
            "id": n["id"], "seq": n["seq"], "level": n["level"],
            "display": n["display"], "title": n["title"], "num": n["num"],
            "path": n["path"], "part": n["part"], "parent": n["parent"],
            "children": n["children"],
            "page_start": min(min(pages), n["page"]),
            "page_end": max(max(pages), n["page"]),
            "n_table": sum(1 for b in blocks if b["type"] == "table"),
            "n_figure": sum(1 for b in blocks if b["type"] == "figure"),
            "blocks": blocks,
            "text": plain_text(blocks),
        }

    covered = used_lines + len(nodes)          # 본문 줄 = 헤딩 + 절 내용
    print(f"커버리지: {covered}/{n_lines} 줄 ({100 * covered / n_lines:.2f}%) "
          f"| 첫 헤딩 이전 버려진 줄 {dropped_before}")
    if covered != n_lines or dropped_before:
        print("[ERROR] 본문 줄 커버리지가 100%가 아닙니다.", file=sys.stderr)
        sys.exit(1)

    tot_tbl = sum(s["n_table"] for s in sections.values())
    tot_fig = sum(s["n_figure"] for s in sections.values())
    print(f"블록 집계: 표 {tot_tbl}개 / 그림 {tot_fig}개 / "
          f"총 블록 {sum(len(s['blocks']) for s in sections.values())}개")

    C.SECTIONS_JSON.write_text(json.dumps(sections, ensure_ascii=False, indent=1),
                               encoding="utf-8")
    C.FIGURES_JSON.write_text(json.dumps(figures, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print(f"[DONE] {C.SECTIONS_JSON}\n[DONE] {C.FIGURES_JSON} ({len(figures)}장)")

    s = sections[nodes[4]["id"]]
    print(f"\n샘플 — {s['display']} (p{s['page_start']}-{s['page_end']})")
    for b in s["blocks"][:4]:
        print(f"   {b['type']:8s} {str(b.get('text') or b.get('label') or '')[:78]}")


if __name__ == "__main__":
    main()
