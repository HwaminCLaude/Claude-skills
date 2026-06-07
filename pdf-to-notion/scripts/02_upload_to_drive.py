"""
02_upload_to_drive.py
_split_images/* 폴더 전체를 rclone으로 Google Drive에 업로드하고,
각 파일의 외부 공개 URL을 drive_urls.json 에 저장한다.

흐름:
  1. rclone copy _split_images/ gdrive:메타코드/노션이미지/ --create-empty-src-dirs
  2. rclone lsjson gdrive:메타코드/노션이미지 --recursive  로 파일 ID 수집
  3. 공개 권한 부여 (rclone link 또는 anyone-with-link 권한)
  4. URL 매핑 저장

권한 설정:
  rclone backend(drive)는 기본적으로 비공개 업로드.
  공개 링크는 Drive API의 권한 변경 필요 → rclone link --expire 0 gdrive:path/p001.png

대안: rclone copy 시점에 --drive-shared-with-me 또는 별도 권한 부여 단계.
간단하게: 업로드 후 `rclone link` 로 각 파일의 webViewLink 생성.

본 스크립트는 lsjson 으로 ID 수집 → 외부 임베드 URL 패턴
`https://lh3.googleusercontent.com/d/{ID}` 를 사용.
이 URL은 공개 권한이 있어야 작동하므로, 먼저 공개 권한을 일괄 부여.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (DRIVE_URLS, IMG_DIR, RCLONE_BIN, RCLONE_DEST_ROOT,
                    RCLONE_REMOTE)


def run(*args, capture=False) -> subprocess.CompletedProcess:
    print(f"[rclone] {' '.join(args)}")
    return subprocess.run(
        [RCLONE_BIN, *args],
        check=True,
        capture_output=capture,
        text=True,
        encoding="utf-8",
    )


def upload():
    src = str(IMG_DIR)
    dst = f"{RCLONE_REMOTE}:{RCLONE_DEST_ROOT}"
    run("copy", src, dst, "--create-empty-src-dirs", "--progress",
        "--transfers", "8", "--checkers", "8")


def list_remote() -> list[dict]:
    """리모트 파일 목록 + Drive ID 추출."""
    dst = f"{RCLONE_REMOTE}:{RCLONE_DEST_ROOT}"
    out = run("lsjson", dst, "--recursive", "--files-only", capture=True)
    return json.loads(out.stdout)


def grant_public(remote_path: str) -> str:
    """rclone link로 공개 링크 발급 (anyone with link viewer)."""
    out = run("link", "--expire", "0",
              f"{RCLONE_REMOTE}:{RCLONE_DEST_ROOT}/{remote_path}",
              capture=True)
    return out.stdout.strip()


def to_embed_url(file_id: str) -> str:
    """노션에서 이미지로 임베드 가능한 URL."""
    return f"https://lh3.googleusercontent.com/d/{file_id}"


def main():
    if not IMG_DIR.exists():
        print(f"[ERROR] {IMG_DIR} 가 없습니다. 01_split_and_extract.py 먼저 실행.")
        sys.exit(1)

    print("\n=== Step 1: 업로드 ===")
    upload()

    print("\n=== Step 2: 원격 파일 목록 + ID 추출 ===")
    files = list_remote()
    print(f"   원격 파일 {len(files)}개")

    # ID 추출 정규식: rclone lsjson 결과의 ID 필드는 백엔드별로 다름.
    # Google Drive는 'ID' 키에 fileId가 들어옴.
    urls: dict[str, dict[str, str]] = {}
    for f in files:
        path = f["Path"]  # 예: "Sam_이론_5_..._Regression_Model/p001.png"
        file_id = f.get("ID") or ""
        if not file_id:
            print(f"   [WARN] ID 없음: {path}")
            continue
        parts = Path(path).parts
        if len(parts) < 2:
            continue
        deck_slug, png_name = parts[0], Path(parts[-1]).stem  # "p001"
        urls.setdefault(deck_slug, {})[png_name] = to_embed_url(file_id)

    # 공개 권한 일괄 부여
    print("\n=== Step 3: 공개 권한 부여 ===")
    for f in files:
        try:
            grant_public(f["Path"])
        except subprocess.CalledProcessError as e:
            print(f"   [WARN] link 실패: {f['Path']}: {e}")

    DRIVE_URLS.write_text(
        json.dumps(urls, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[DONE] URL 매핑 저장: {DRIVE_URLS}")
    print(f"   강의자료 {len(urls)}개 / 총 URL {sum(len(v) for v in urls.values())}개")


if __name__ == "__main__":
    main()
