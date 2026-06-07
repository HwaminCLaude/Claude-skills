"""
01_split_and_extract.py
PDF -> 페이지별 PNG 분할 + 페이지별 텍스트 추출.

입력:
  - C:/Users/정화민/Desktop/메타코드/9주차_*/**/*.pdf  (재귀 탐색)
출력:
  - _split_images/{deck_slug}/p{NNN}.png
  - _output/content_cache.json
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

import os
ROOT = Path(os.environ.get("METACODE_ROOT", r"C:/Users/정화민/Desktop/메타코드"))
OUT_IMG = ROOT / "_split_images"
OUT_DIR = ROOT / "_output"
DPI = 200  # PNG 해상도
CACHE_PATH = OUT_DIR / "content_cache.json"


def slugify(name: str) -> str:
    """파일명을 디렉토리/슬러그용으로 안전 변환."""
    # NFC 정규화 후 확장자 제거
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE)
    # 영숫자·한글 이외 문자는 모두 _ 로 (공백·+·괄호·하이픈 등) → 연속 _ 축약
    name = re.sub(r"[^0-9A-Za-z가-힣]+", "_", name).strip("_")
    return name


def find_pdfs(root: Path) -> list[Path]:
    """루트 폴더 아래 모든 PDF 재귀 탐색 (_split_images 등 작업 폴더 제외)."""
    skip_dirs = {"_split_images", "_output", "_scripts"}
    pdfs: list[Path] = []
    for p in root.rglob("*.pdf"):
        if any(part in skip_dirs for part in p.parts):
            continue
        pdfs.append(p)
    return sorted(pdfs)


def split_pdf_to_images(pdf_path: Path, out_dir: Path, dpi: int = DPI) -> int:
    """PDF를 페이지별 PNG로 저장. 반환: 생성된 페이지 수."""
    out_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72  # PyMuPDF 기본 72dpi 대비 비율
    mat = fitz.Matrix(zoom, zoom)
    doc = fitz.open(pdf_path)
    try:
        for i, page in enumerate(doc, start=1):
            png_path = out_dir / f"p{i:03d}.png"
            if png_path.exists():
                continue  # 이미 있으면 스킵 (재실행 안전)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pix.save(png_path)
        return doc.page_count
    finally:
        doc.close()


def extract_text(pdf_path: Path) -> list[dict]:
    """pdfplumber로 페이지별 텍스트 추출.
    반환: [{page: 1, text: "...", char_count: N}, ...]
    """
    pages_out: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            pages_out.append({
                "page": i,
                "text": text,
                "char_count": len(text),
            })
    return pages_out


def main():
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pdfs = find_pdfs(ROOT)
    print(f"[INFO] PDF {len(pdfs)}개 발견")
    for p in pdfs:
        print(f"  - {p.relative_to(ROOT)}")

    cache = {}
    for pdf in pdfs:
        # deck slug: 부모 폴더의 마지막 의미있는 이름 + 파일명
        rel = pdf.relative_to(ROOT)
        parts = list(rel.parts)
        # 강사 식별자 추출 (한국어/영문 모두)
        instructor = "unknown"
        for p in parts:
            if "Sam" in p:
                instructor = "Sam"; break
            if "Liam" in p:
                instructor = "Liam"; break
            if "Bob" in p:
                instructor = "Bob"; break
            if "김동환" in p:
                instructor = "Kim"; break
            if "머신러닝" in p:
                instructor = "ML"; break
            if "통계" in p:
                instructor = "Stat"; break
            if "배상민" in p:
                instructor = "Bae"; break
            if "김도형" in p:
                instructor = "Koh"; break
            if "Jason" in p:
                instructor = "Jason"; break
            if "선형대수" in p:
                instructor = "LinAlg"; break
            if "한상태" in p or "대학원" in p:
                instructor = "Han"; break
            if "마케팅" in p:
                instructor = "Mkt"; break
            if "파이썬" in p:
                instructor = "Py"; break
        # 중간 분류 (이론/실습/lesson8) 등
        category = parts[-2] if len(parts) >= 2 else ""
        deck_name = slugify(pdf.stem)
        slug = f"{instructor}_{category}_{deck_name}" if category else f"{instructor}_{deck_name}"
        slug = slugify(slug)

        deck_img_dir = OUT_IMG / slug
        print(f"\n[SPLIT] {pdf.name} -> {deck_img_dir.name}/")
        n_pages = split_pdf_to_images(pdf, deck_img_dir)
        print(f"   {n_pages} 페이지 PNG 저장 완료")

        print(f"[EXTRACT] 텍스트 추출 중...")
        page_texts = extract_text(pdf)
        total_chars = sum(p["char_count"] for p in page_texts)
        print(f"   총 {total_chars}자")

        cache[slug] = {
            "pdf_path": str(rel).replace("\\", "/"),
            "deck_name": pdf.stem,
            "instructor": instructor,
            "category": category,
            "n_pages": n_pages,
            "images_dir": f"_split_images/{slug}",
            "pages": page_texts,
        }

    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[DONE] 캐시 저장: {CACHE_PATH}")
    print(f"[SUMMARY] 강의자료 {len(cache)}개, 총 페이지 {sum(v['n_pages'] for v in cache.values())}")


if __name__ == "__main__":
    main()
