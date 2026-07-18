#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_figures.py — trace 그림(figures/*.png)을 Google Drive에 올려 Notion 임베드 URL을 만든다.

rclone로 Drive 폴더에 복사한 뒤, 파일별 rclone link로 공개(anyone-with-link) + 파일 ID 추출 →
임베드 URL `https://lh3.googleusercontent.com/d/{FILE_ID}` → drive_urls.json {figkey: url}.
(그림 소수 개면 파일별 link도 빠름. 수백 개면 폴더 단위 공개 권장 — memory drive_folder_public_embed)

사용: python upload_figures.py <trace.json> <figures_dir> <out_drive_urls.json> --remote gdrive --folder NMFC_코드가이드북_그림
"""
import os, sys, json, re, subprocess, argparse

RCLONE = os.environ.get("RCLONE_BIN", "rclone")

def run(args):
    return subprocess.run([RCLONE]+args, capture_output=True, text=True)

def file_id(url):
    m = re.search(r"[?&]id=([\w-]+)", url) or re.search(r"/d/([\w-]+)", url) or re.search(r"/file/d/([\w-]+)", url)
    return m.group(1) if m else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace"); ap.add_argument("figdir"); ap.add_argument("out")
    ap.add_argument("--remote", default="gdrive"); ap.add_argument("--folder", default="NMFC_코드가이드북_그림")
    a = ap.parse_args()
    trace = json.load(open(a.trace, encoding="utf-8"))
    figures = trace.get("figures", {})   # {figkey: basename}
    dest = f"{a.remote}:{a.folder}"
    # 1) 업로드
    r = run(["copy", a.figdir, dest, "--drive-chunk-size", "8M"])
    if r.returncode != 0: print("copy 경고:", r.stderr.strip()[:200])
    # 2) 파일별 공개 링크 → ID → 임베드 URL
    urls = {}
    for figkey, base in figures.items():
        remote_path = f"{dest}/{base}"
        lr = run(["link", remote_path])
        if lr.returncode != 0:
            print(f"  link 실패 {base}: {lr.stderr.strip()[:120]}"); continue
        fid = file_id(lr.stdout.strip())
        if not fid:
            print(f"  ID 추출 실패 {base}: {lr.stdout.strip()[:120]}"); continue
        urls[figkey] = f"https://lh3.googleusercontent.com/d/{fid}"
    json.dump(urls, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"drive_urls.json: {len(urls)}/{len(figures)} 그림 URL -> {a.out}")
    for k, v in urls.items(): print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
