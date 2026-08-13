"""Pull figures out of the paper PDF as PNGs for use as Manim ImageMobjects.

The paper's own figures are the honest way to show real data and real results —
never a generated image. Two modes:

  list    every embedded raster on a page, with size and position, so you can
          pick the one you want
  crop    render a page region at high DPI (works for vector figures too, which
          `list` cannot extract because they aren't embedded images)

    python crop_figure.py --pdf paper.pdf --list --pages 1-8
    python crop_figure.py --pdf paper.pdf --page 4 --extract 0 --out fig2.png
    python crop_figure.py --pdf paper.pdf --page 4 --bbox 72,120,520,430 --out fig2.png --dpi 300

Coordinates are PDF points (72 per inch), origin at the TOP-LEFT of the page,
which is what `--list` reports — so you can copy numbers straight across.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    print("PyMuPDF가 필요합니다:  uv add PyMuPDF   (프로젝트 venv의 python으로 실행하세요)",
          file=sys.stderr)
    raise SystemExit(1)


def parse_pages(spec: str, total: int) -> list[int]:
    """'1-8', '3', '2,5,9' -> zero-based page indices."""
    pages: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            lo, hi = chunk.split("-", 1)
            pages.extend(range(int(lo) - 1, min(int(hi), total)))
        elif chunk:
            pages.append(int(chunk) - 1)
    return [p for p in pages if 0 <= p < total]


def list_figures(doc, pages: list[int]) -> list[dict]:
    found = []
    for pno in pages:
        page = doc[pno]
        for idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            rects = page.get_image_rects(xref)
            rect = rects[0] if rects else None
            info = doc.extract_image(xref)
            found.append({
                "page": pno + 1,
                "index": idx,
                "xref": xref,
                "width_px": info.get("width"),
                "height_px": info.get("height"),
                "ext": info.get("ext"),
                "bbox": [round(v, 1) for v in (rect.x0, rect.y0, rect.x1, rect.y1)] if rect else None,
            })
    return found


def extract_embedded(doc, page_no: int, index: int, out: Path) -> Path:
    page = doc[page_no]
    images = page.get_images(full=True)
    if index >= len(images):
        raise SystemExit(f"{page_no + 1}쪽에 인덱스 {index}의 이미지가 없습니다 "
                         f"(총 {len(images)}개). --list로 확인하세요.")
    info = doc.extract_image(images[index][0])
    out = out.with_suffix("." + info["ext"]) if out.suffix.lower() != f".{info['ext']}" else out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(info["image"])
    return out


def render_region(doc, page_no: int, bbox: tuple[float, ...] | None, out: Path, dpi: int) -> Path:
    page = doc[page_no]
    clip = fitz.Rect(*bbox) if bbox else None
    pix = page.get_pixmap(dpi=dpi, clip=clip, alpha=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="논문 PDF에서 figure 추출")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--list", action="store_true", help="페이지의 임베드 이미지 목록")
    ap.add_argument("--pages", default="1-9999", help="--list 대상 페이지 (예: 1-8)")
    ap.add_argument("--page", type=int, help="추출할 페이지 (1부터)")
    ap.add_argument("--extract", type=int, help="임베드 이미지 인덱스")
    ap.add_argument("--bbox", help="영역 렌더 x0,y0,x1,y1 (PDF 포인트, 좌상단 원점)")
    ap.add_argument("--dpi", type=int, default=300, help="영역 렌더 해상도 (기본 300)")
    ap.add_argument("--out", help="출력 PNG 경로")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.is_file():
        raise SystemExit(f"PDF가 없습니다: {pdf}")
    doc = fitz.open(pdf)

    if args.list:
        figures = list_figures(doc, parse_pages(args.pages, doc.page_count))
        if args.json:
            print(json.dumps({"pdf": str(pdf), "page_count": doc.page_count,
                              "figures": figures}, ensure_ascii=False))
        else:
            print(f"{pdf.name} — {doc.page_count}쪽, 임베드 이미지 {len(figures)}개")
            for f in figures:
                print(f"  p{f['page']:>3} #{f['index']}  {f['width_px']}x{f['height_px']} "
                      f"{f['ext']}  bbox={f['bbox']}")
            if not figures:
                print("  (임베드 이미지 없음 — 벡터 그림일 가능성이 큽니다. "
                      "--page/--bbox 영역 렌더를 쓰세요.)")
        return 0

    if args.page is None or not args.out:
        ap.error("--list 이거나, --page 와 --out 이 필요합니다")

    page_no = args.page - 1
    if not 0 <= page_no < doc.page_count:
        raise SystemExit(f"페이지 범위를 벗어났습니다 (1..{doc.page_count})")
    out = Path(args.out).resolve()

    if args.extract is not None:
        saved = extract_embedded(doc, page_no, args.extract, out)
    else:
        bbox = tuple(float(v) for v in args.bbox.split(",")) if args.bbox else None
        if bbox and len(bbox) != 4:
            raise SystemExit("--bbox는 x0,y0,x1,y1 네 개 값이어야 합니다")
        saved = render_region(doc, page_no, bbox, out, args.dpi)

    size_kb = round(saved.stat().st_size / 1024, 1)
    print(f"[crop_figure] {saved}  ({size_kb} KB)")
    print(f"[crop_figure] Manim에서: ImageMobject(r\"{saved}\")")
    if args.json:
        print(json.dumps({"out": str(saved), "size_kb": size_kb}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
