"""
03_render_figures.py — 그림 222장을 캡션 아래 영역만 크롭해 PNG로 렌더한다.

본문의 그림은 전부 래스터/벡터라 텍스트 레이어가 비어 있다(실측: 222/222 영역에서
추출 텍스트 0자). 그래서 이미지로 떠서 Notion에 넣고, 04단계에서 Codex 비전으로
도식 안 글자를 읽어 검색 가능하게 만든다.

산출: _figures/<fig_id>.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).parent))
import config as C


def main():
    figs = json.loads(C.FIGURES_JSON.read_text(encoding="utf-8"))
    C.FIG_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(C.PDF_PATH)
    zoom = C.FIG_DPI / 72.0
    mat = fitz.Matrix(zoom, zoom)

    made, skipped, blank = 0, 0, []
    for f in figs:
        out = C.FIG_DIR / f"{f['fig_id']}.png"
        if out.exists() and out.stat().st_size > 2000:
            skipped += 1
            continue
        page = doc[f["page"] - 1]
        rect = fitz.Rect(*f["rect"]) & page.rect
        pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
        # 완전 백지면 기록해 둔다 (크롭 좌표 오류 탐지)
        if pix.width < 20 or pix.height < 20:
            blank.append(f["fig_id"])
            continue
        pix.save(out)
        made += 1

    doc.close()
    files = sorted(C.FIG_DIR.glob("*.png"))
    sizes = [p.stat().st_size for p in files]
    print(f"렌더 {made}장 / 기존 재사용 {skipped}장 / 실패 {len(blank)}장")
    print(f"_figures/ 총 {len(files)}장, "
          f"평균 {sum(sizes) // max(len(sizes), 1) // 1024}KB, "
          f"최소 {min(sizes) // 1024 if sizes else 0}KB, "
          f"합계 {sum(sizes) // 1024 // 1024}MB")
    if blank:
        print(f"[WARN] 렌더 실패: {blank[:10]}", file=sys.stderr)
    if len(files) != len(figs):
        print(f"[ERROR] 그림 수 불일치: 기대 {len(figs)} vs 실제 {len(files)}", file=sys.stderr)
        sys.exit(1)
    # 너무 작은 파일 = 백지 의심
    tiny = [p.name for p, s in zip(files, sizes) if s < 3000]
    if tiny:
        print(f"[WARN] 백지 의심 {len(tiny)}장: {tiny[:10]}", file=sys.stderr)
    print(f"[DONE] {C.FIG_DIR}")


if __name__ == "__main__":
    main()
