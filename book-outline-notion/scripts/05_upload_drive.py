"""
05_upload_drive.py — 그림 PNG 222장과 원본 PDF를 Google Drive에 올려 공개 URL을 만든다.

노션 image 블록은 external URL 만 받으므로 Drive 파일 ID로
`https://lh3.googleusercontent.com/d/{ID}` 임베드 URL을 만든다.
(이 URL은 '링크가 있는 모든 사용자' 권한이 있어야 보이므로 rclone link 로 일괄 부여)

산출: _output/drive_urls.json {fig_id: url}, _output/drive_files.json [{name,url}]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as C


def run(*args, capture=False, check=True) -> subprocess.CompletedProcess:
    return subprocess.run([C.RCLONE_BIN, *args], check=check, capture_output=capture,
                          text=True, encoding="utf-8", errors="replace")


def upload_images():
    dst = f"{C.RCLONE_REMOTE}:{C.RCLONE_IMG_DEST}"
    print(f"[rclone] copy {C.FIG_DIR} → {dst}")
    run("copy", str(C.FIG_DIR), dst, "--transfers", "8", "--checkers", "8",
        "--progress", "--stats", "10s")


def list_remote(dest: str) -> list[dict]:
    out = run("lsjson", f"{C.RCLONE_REMOTE}:{dest}", "--recursive", "--files-only",
              capture=True)
    return json.loads(out.stdout)


def grant_public(remote_path: str) -> bool:
    try:
        run("link", "--expire", "0", f"{C.RCLONE_REMOTE}:{remote_path}",
            capture=True)
        return True
    except subprocess.CalledProcessError:
        return False


def normalize_drive_link(link: str) -> str:
    m = re.search(r"[?&]id=([A-Za-z0-9_-]+)", link) or re.search(r"/d/([A-Za-z0-9_-]+)", link)
    return f"https://drive.google.com/file/d/{m.group(1)}/view?usp=sharing" if m else link


def main():
    figs = json.loads(C.FIGURES_JSON.read_text(encoding="utf-8"))
    pngs = sorted(C.FIG_DIR.glob("*.png"))
    if len(pngs) != len(figs):
        print(f"[ERROR] PNG {len(pngs)}장 != 그림 {len(figs)}개 — 03단계 먼저", file=sys.stderr)
        sys.exit(1)

    upload_images()

    print("\n[rclone] 원격 파일 목록 + ID 수집")
    remote = list_remote(C.RCLONE_IMG_DEST)
    print(f"   원격 {len(remote)}개")

    print("[rclone] 공개 권한 부여 (병렬 8)")
    ok = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(grant_public, f"{C.RCLONE_IMG_DEST}/{f['Path']}"): f
                for f in remote}
        for i, fut in enumerate(as_completed(futs), 1):
            ok += bool(fut.result())
            if i % 50 == 0:
                print(f"   {i}/{len(remote)}")
    print(f"   공개 권한 {ok}/{len(remote)}")

    urls = {}
    for f in remote:
        fid = f.get("ID")
        stem = Path(f["Path"]).stem
        if fid:
            urls[stem] = f"https://lh3.googleusercontent.com/d/{fid}"
    C.DRIVE_URLS.write_text(json.dumps(urls, ensure_ascii=False, indent=1),
                            encoding="utf-8")

    missing = [f["fig_id"] for f in figs if f["fig_id"] not in urls]
    print(f"\n이미지 URL {len(urls)}개 → {C.DRIVE_URLS}")
    if missing:
        print(f"[ERROR] URL 누락 {len(missing)}장: {missing[:10]}", file=sys.stderr)
        sys.exit(1)

    # 원본 PDF
    print("\n[rclone] 원본 PDF 업로드")
    remote_pdf = f"{C.RCLONE_FILE_DEST}/{C.PDF_PATH.name}"
    run("copyto", str(C.PDF_PATH), f"{C.RCLONE_REMOTE}:{remote_pdf}", "--progress")
    link = run("link", "--expire", "0", f"{C.RCLONE_REMOTE}:{remote_pdf}",
               capture=True).stdout.strip()
    files = [{"name": C.PDF_PATH.name, "url": normalize_drive_link(link)}]
    C.DRIVE_FILES.write_text(json.dumps(files, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    print(f"[DONE] 원본 PDF: {files[0]['url']}")


if __name__ == "__main__":
    main()
