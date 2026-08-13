"""Extract a paper PDF into paper.json + a readable text dump (Stage 1).

Text extraction, not page rasterisation — the pipeline needs the words, and
rendering pages to PNG would also require poppler, which may not be installed.
Figures are located separately by `crop_figure.py`.

    python parse_paper.py --pdf paper.pdf --out C:\\manimwork\\my-paper
    python parse_paper.py --pdf paper.pdf --out <root> --dump-text   # also write paper.txt

Run this with the PROJECT VENV python (PyMuPDF lives there).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import pymupdf  # PyMuPDF >= 1.24 exposes the modern name
except ImportError:  # pragma: no cover
    try:
        import fitz as pymupdf
    except ImportError:
        print("PyMuPDF가 필요합니다:  uv add PyMuPDF", file=sys.stderr)
        raise SystemExit(1)

# Numbered headings ("3 Method", "3.1 Soft neighborhood") and the usual
# unnumbered ones. Kept deliberately loose; a wrong split is cheap to fix, a
# missed section is not.
HEADING = re.compile(
    r"^\s*(?:(\d+(?:\.\d+)*)\s+)?"
    r"(Abstract|Introduction|Related\s+Work|Background|Preliminaries|Method(?:s|ology)?|"
    r"Approach|Model|Experiments?|Results?|Discussion|Ablation[^\n]*|Conclusions?|"
    r"Limitations?|Acknowledg\w+|References|Appendix[^\n]*)\s*$",
    re.IGNORECASE,
)
# Display equations: a line with real math operators and little prose.
EQUATION_HINT = re.compile(r"[=≈≤≥∑∏∫√∈∀∃⊤]|\\frac|\^\{|_\{")
CAPTION = re.compile(r"^\s*(Fig(?:ure)?\.?\s*\d+|Table\s*\d+)[.:\s]", re.IGNORECASE)


def page_lines(doc) -> list[tuple[int, str]]:
    out = []
    for pno in range(doc.page_count):
        for line in doc[pno].get_text("text").splitlines():
            out.append((pno + 1, line.rstrip()))
    return out


def split_sections(lines: list[tuple[int, str]]) -> list[dict]:
    sections: list[dict] = []
    current = {"number": None, "title": "Front matter", "page_start": 1, "lines": []}
    for pno, line in lines:
        m = HEADING.match(line)
        if m and len(line) < 80:
            if current["lines"]:
                sections.append(current)
            current = {"number": m.group(1), "title": m.group(2).strip(),
                       "page_start": pno, "lines": []}
        else:
            current["lines"].append((pno, line))
    if current["lines"]:
        sections.append(current)

    for sec in sections:
        text = "\n".join(l for _, l in sec["lines"]).strip()
        sec["text"] = text
        sec["char_count"] = len(text)
        sec["page_end"] = sec["lines"][-1][0] if sec["lines"] else sec["page_start"]
        del sec["lines"]
    return sections


def collect(lines: list[tuple[int, str]], pattern: re.Pattern, min_len: int = 0) -> list[dict]:
    hits = []
    for pno, line in lines:
        stripped = line.strip()
        if len(stripped) >= min_len and pattern.search(stripped):
            hits.append({"page": pno, "text": stripped})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="논문 PDF → paper.json (Stage 1)")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True, help="프로젝트 루트 (paper.json이 여기 생김)")
    ap.add_argument("--dump-text", action="store_true", help="paper.txt도 함께 저장")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.is_file():
        raise SystemExit(f"PDF가 없습니다: {pdf}")
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf)
    lines = page_lines(doc)
    sections = split_sections(lines)

    figures = []
    for pno in range(doc.page_count):
        page = doc[pno]
        for idx, img in enumerate(page.get_images(full=True)):
            info = doc.extract_image(img[0])
            rects = page.get_image_rects(img[0])
            figures.append({
                "page": pno + 1, "index": idx,
                "width_px": info.get("width"), "height_px": info.get("height"),
                "bbox": [round(v, 1) for v in rects[0]] if rects else None,
            })

    payload = {
        "source_pdf": str(pdf),
        "title_guess": (doc.metadata or {}).get("title") or pdf.stem,
        "page_count": doc.page_count,
        "sections": [{k: v for k, v in s.items() if k != "text"} | {"text": s["text"]}
                     for s in sections],
        "equations": collect(lines, EQUATION_HINT, min_len=6),
        "captions": collect(lines, CAPTION),
        "figures": figures,
    }

    paper_json = out_dir / "paper.json"
    paper_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dump_text:
        dump = out_dir / "paper.txt"
        with dump.open("w", encoding="utf-8") as fh:
            for sec in sections:
                num = f"{sec['number']} " if sec["number"] else ""
                fh.write(f"\n\n{'=' * 78}\n## {num}{sec['title']}  "
                         f"(p{sec['page_start']}-{sec['page_end']}, {sec['char_count']} chars)\n"
                         f"{'=' * 78}\n{sec['text']}\n")
        print(f"[parse_paper] {dump}")

    print(f"[parse_paper] {paper_json}")
    print(f"[parse_paper] {doc.page_count}쪽, 섹션 {len(sections)}개, "
          f"수식 후보 {len(payload['equations'])}줄, 캡션 {len(payload['captions'])}개, "
          f"임베드 그림 {len(figures)}개")
    for sec in sections:
        num = f"{sec['number']} " if sec["number"] else ""
        print(f"    p{sec['page_start']:>3}  {num}{sec['title']:<28} {sec['char_count']:>6} chars")

    if args.json:
        print(json.dumps({"paper_json": str(paper_json), "sections": len(sections),
                          "figures": len(figures)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
