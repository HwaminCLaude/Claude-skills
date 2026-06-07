"""
extract_notebooks.py
주차 폴더 안의 모든 .ipynb를 찾아 코드/마크다운/출력 텍스트를 JSON으로 추출한다.

사용법:
  python extract_notebooks.py <주차폴더>
  예: python extract_notebooks.py 6주차

출력:
  <주차폴더>/_guidebook/notebooks.json
    { "<nb_slug>": {
        "path": "상대경로",
        "name": "노트북 파일명(확장자 제외)",
        "cells": [
           {"type":"markdown"|"code", "source":"...", "outputs":"..."}
        ],
        "n_code": N, "n_md": M
      }, ... }
"""
from __future__ import annotations

import base64
import json
import re
import sys
import unicodedata
from pathlib import Path

import os
ROOT = Path(os.environ.get("METACODE_ROOT", r"C:/Users/정화민/Desktop/메타코드"))
IMG_DIR_NAME = "images"  # _guidebook/images/ 아래 그림 PNG 저장


def slugify(name: str) -> str:
    name = unicodedata.normalize("NFC", name)
    name = name.replace(" ", "_").replace("/", "-").replace("\\", "-")
    name = re.sub(r"\.ipynb$", "", name, flags=re.IGNORECASE)
    # 대괄호 등 정리
    name = name.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def extract_cell_outputs(outputs: list, img_dir: Path, slug: str, cell_idx: int) -> tuple[str, list]:
    """코드 셀 출력에서 (텍스트, 이미지키목록) 추출.
    이미지(image/png|jpeg base64)는 PNG로 저장하고 키를 반환한다.
    """
    parts = []
    img_keys = []
    for j, out in enumerate(outputs or []):
        ot = out.get("output_type")
        if ot == "stream":
            txt = out.get("text", "")
            if isinstance(txt, list):
                txt = "".join(txt)
            parts.append(txt)
        elif ot in ("execute_result", "display_data"):
            data = out.get("data", {})
            if "text/plain" in data:
                txt = data["text/plain"]
                if isinstance(txt, list):
                    txt = "".join(txt)
                parts.append(txt)
            for fmt, ext in (("image/png", "png"), ("image/jpeg", "jpg")):
                if fmt in data:
                    b64 = data[fmt]
                    if isinstance(b64, list):
                        b64 = "".join(b64)
                    key = f"{slug}__c{cell_idx:03d}_{j}"
                    try:
                        (img_dir / f"{key}.{ext}").write_bytes(base64.b64decode(b64))
                        img_keys.append(key)
                    except Exception as e:
                        print(f"   [WARN] 이미지 저장 실패 {key}: {e}")
        elif ot == "error":
            tb = out.get("traceback", [])
            parts.append("[에러] " + " ".join(tb)[:200])
    text = "\n".join(parts).strip()
    # 출력 텍스트는 800자까지 보존 (가이드북에 표시)
    if len(text) > 800:
        text = text[:800] + " …(출력 생략)"
    return text, img_keys


def extract_notebook(nb_path: Path, img_dir: Path, slug: str) -> dict:
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cells_out = []
    n_code = n_md = n_img = 0
    for idx, cell in enumerate(nb.get("cells", [])):
        ct = cell.get("cell_type")
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        src = src.strip()
        if not src and ct != "code":
            continue
        if ct == "markdown":
            n_md += 1
            src = re.sub(r"!\[[^\]]*\]\(data:image/[^)]+\)", "[그림]", src)
            src = re.sub(r"data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=\s]+", "[그림]", src)
            cells_out.append({"type": "markdown", "source": src,
                              "outputs": "", "output_images": []})
        elif ct == "code":
            n_code += 1
            out_text, img_keys = extract_cell_outputs(
                cell.get("outputs", []), img_dir, slug, idx)
            n_img += len(img_keys)
            cells_out.append({"type": "code", "source": src,
                              "outputs": out_text, "output_images": img_keys})
    return {"cells": cells_out, "n_code": n_code, "n_md": n_md, "n_img": n_img}


def main():
    if len(sys.argv) < 2:
        print("사용법: python extract_notebooks.py <주차폴더>")
        sys.exit(1)
    week = sys.argv[1]
    week_dir = ROOT / week
    out_dir = week_dir / "_guidebook"
    out_dir.mkdir(parents=True, exist_ok=True)
    img_root = out_dir / IMG_DIR_NAME
    img_root.mkdir(parents=True, exist_ok=True)

    nbs = sorted(week_dir.rglob("*.ipynb"))
    nbs = [p for p in nbs if ".ipynb_checkpoints" not in str(p)]
    print(f"[INFO] {week}: 노트북 {len(nbs)}개 발견")

    result = {}
    used_slugs = set()
    for nb in nbs:
        rel = nb.relative_to(week_dir)
        slug = slugify(nb.stem)
        # 중복 슬러그 방지 (부모 폴더 추가)
        if slug in used_slugs:
            slug = slugify(nb.parent.name) + "_" + slug
        used_slugs.add(slug)
        nb_img_dir = img_root / slug
        nb_img_dir.mkdir(parents=True, exist_ok=True)
        try:
            data = extract_notebook(nb, nb_img_dir, slug)
        except Exception as e:
            print(f"  [ERR] {nb.name}: {e}")
            continue
        data["path"] = str(rel).replace("\\", "/")
        data["name"] = nb.stem.strip()
        data["slug"] = slug
        result[slug] = data
        # 노트북별 개별 파일 저장 (agent가 자기 것만 읽도록)
        (out_dir / f"nb_{slug}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  + {slug}: code {data['n_code']}, md {data['n_md']}, 그림 {data['n_img']}")

    out_path = out_dir / "notebooks.json"
    # 인덱스용 (cells 제외, 가벼운 메타만)
    index = {k: {"name": v["name"], "path": v["path"],
                 "n_code": v["n_code"], "n_md": v["n_md"]}
             for k, v in result.items()}
    out_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DONE] {out_path} ({len(result)}개 노트북) + 개별 nb_*.json")


if __name__ == "__main__":
    main()
