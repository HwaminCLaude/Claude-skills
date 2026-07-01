"""
upload_guidebook_images.py
<주차>/_guidebook/images/ 아래 모든 PNG를 구글드라이브에 업로드하고
key(파일명, 확장자 제외) -> 공개 임베드 URL 매핑을 gb_drive_urls.json 에 저장.

추가로, 각 노트북의 **원본 .ipynb 파일 자체**도 Drive(메타코드/가이드북자료파일/<주차>/<slug>/)에
그대로 올려 공유링크를 gb_drive_files.json 에 저장한다.
→ 노션 페이지의 'Files & media' 속성(기본 이름 "원본 파일")에 붙여서, DB에서 원본 노트북을
   바로 열람/다운로드할 수 있게 하기 위함. (속성 세팅은 Step 5 MCP 업로드에서 수행)

사용법:
  python upload_guidebook_images.py <주차폴더>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import os
ROOT = Path(os.environ.get("METACODE_ROOT", r"C:/Users/정화민/Desktop/메타코드"))
RCLONE_BIN = os.environ.get("RCLONE_BIN", r"C:\Users\정화민\rclone\rclone.exe")
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
DEST_ROOT = os.environ.get("GB_DRIVE_DEST", "메타코드/가이드북이미지")
FILES_DEST_ROOT = os.environ.get("GB_FILES_DRIVE_DEST", "메타코드/가이드북자료파일")


def run(*args, capture=False):
    print(f"[rclone] {' '.join(args)}")
    return subprocess.run([RCLONE_BIN, *args], check=True,
                          capture_output=capture, text=True, encoding="utf-8")


def normalize_drive_link(link: str) -> str:
    """rclone link 결과를 노션 Files 속성에 쓰기 좋은 /file/d/{ID}/view 형태로 정규화."""
    m = re.search(r"[?&]id=([A-Za-z0-9_-]+)", link) or re.search(r"/d/([A-Za-z0-9_-]+)", link)
    if m:
        return f"https://drive.google.com/file/d/{m.group(1)}/view?usp=sharing"
    return link


def upload_source_notebooks(week: str, week_dir: Path) -> dict[str, list[dict]]:
    """notebooks.json 의 각 노트북 원본 .ipynb 를 Drive에 그대로 업로드하고
    공유링크를 {nb_slug: [{"name":..., "url":...}]} 로 반환한다."""
    idx_path = week_dir / "_guidebook" / "notebooks.json"
    if not idx_path.exists():
        print(f"   [WARN] {idx_path} 없음 → 원본 노트북 업로드 건너뜀 "
              f"(extract_notebooks.py 먼저 실행)")
        return {}
    index = json.loads(idx_path.read_text(encoding="utf-8"))
    files_map: dict[str, list[dict]] = {}
    for slug, meta in index.items():
        nb_rel = meta.get("path")
        if not nb_rel:
            continue
        src = week_dir / nb_rel
        if not src.exists():
            print(f"   [WARN] 원본 없음: {src}")
            continue
        name = src.name
        remote_file = f"{FILES_DEST_ROOT}/{week}/{slug}/{name}"
        run("copyto", str(src), f"{RCLONE_REMOTE}:{remote_file}")
        try:
            link = run("link", "--expire", "0",
                       f"{RCLONE_REMOTE}:{remote_file}", capture=True).stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"   [WARN] link 실패 {remote_file}: {e}")
            continue
        files_map.setdefault(slug, []).append({"name": name,
                                               "url": normalize_drive_link(link)})
        print(f"   + {slug}: {name}")
    return files_map


def main():
    week = sys.argv[1]
    week_dir = ROOT / week
    img_dir = week_dir / "_guidebook" / "images"
    out_path = week_dir / "_guidebook" / "gb_drive_urls.json"
    files_out_path = week_dir / "_guidebook" / "gb_drive_files.json"

    if not img_dir.exists() or not any(img_dir.rglob("*.png")):
        print(f"[INFO] {week}: 업로드할 그림 없음")
        out_path.write_text("{}", encoding="utf-8")
    else:
        dest = f"{RCLONE_REMOTE}:{DEST_ROOT}/{week}"
        print(f"\n=== 그림 업로드: {img_dir} -> {dest} ===")
        run("copy", str(img_dir), dest, "--create-empty-src-dirs",
            "--transfers", "8", "--checkers", "8")

        print("\n=== 원격 목록 + ID ===")
        out = run("lsjson", dest, "--recursive", "--files-only", capture=True)
        files = json.loads(out.stdout)
        urls = {}
        for f in files:
            path = f["Path"]  # "<slug>/<key>.png"
            file_id = f.get("ID") or ""
            if not file_id:
                continue
            key = Path(path).stem  # 확장자 제외 = key
            urls[key] = f"https://lh3.googleusercontent.com/d/{file_id}"

        print("\n=== 공개 권한 부여 ===")
        for f in files:
            try:
                run("link", "--expire", "0", f"{dest}/{f['Path']}", capture=True)
            except subprocess.CalledProcessError as e:
                print(f"   [WARN] link 실패 {f['Path']}: {e}")

        out_path.write_text(json.dumps(urls, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[DONE] {out_path} ({len(urls)}개 그림 URL)")

    print(f"\n=== 원본 노트북(.ipynb) 업로드 → 공유링크 ===")
    files_map = upload_source_notebooks(week, week_dir)
    files_out_path.write_text(
        json.dumps(files_map, ensure_ascii=False, indent=2), encoding="utf-8")
    n_files = sum(len(v) for v in files_map.values())
    print(f"[DONE] {files_out_path} (노트북 {len(files_map)}개 / 파일 {n_files}개)")


if __name__ == "__main__":
    main()
