"""
upload_guidebook_images.py
<주차>/_guidebook/images/ 아래 모든 PNG를 구글드라이브에 업로드하고
key(파일명, 확장자 제외) -> 공개 임베드 URL 매핑을 gb_drive_urls.json 에 저장.

사용법:
  python upload_guidebook_images.py <주차폴더>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import os
ROOT = Path(os.environ.get("METACODE_ROOT", r"C:/Users/정화민/Desktop/메타코드"))
RCLONE_BIN = os.environ.get("RCLONE_BIN", r"C:\Users\정화민\rclone\rclone.exe")
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
DEST_ROOT = os.environ.get("GB_DRIVE_DEST", "메타코드/가이드북이미지")


def run(*args, capture=False):
    print(f"[rclone] {' '.join(args)}")
    return subprocess.run([RCLONE_BIN, *args], check=True,
                          capture_output=capture, text=True, encoding="utf-8")


def main():
    week = sys.argv[1]
    img_dir = ROOT / week / "_guidebook" / "images"
    out_path = ROOT / week / "_guidebook" / "gb_drive_urls.json"
    if not img_dir.exists() or not any(img_dir.rglob("*.png")):
        print(f"[INFO] {week}: 업로드할 그림 없음")
        out_path.write_text("{}", encoding="utf-8")
        return

    dest = f"{RCLONE_REMOTE}:{DEST_ROOT}/{week}"
    print(f"\n=== 업로드: {img_dir} -> {dest} ===")
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


if __name__ == "__main__":
    main()
