"""4단계 — 드라이브에 올라간 영상을 페이지에 채워 넣는다.

    python 04_sync_videos.py --work <폴더>              # 한 번 돌기
    python 04_sync_videos.py --work <폴더> --loop        # 다 채울 때까지 10분마다 (분리 실행 권장)
    python 04_sync_videos.py --work <폴더> --loop --detach
    python 04_sync_videos.py --work <폴더> --urls-only   # URL 표만 갱신

하는 일 두 가지
    (1) rclone lsjson 으로 파일 ID 수집 → _out/video_urls.json
    (2) 페이지의 "⏳ 영상 업로드 대기 중" callout 을 실제 embed 로 교체

임베드 URL 은 `https://drive.google.com/file/d/<ID>/preview`.
노션 `video` 블록은 Drive 링크를 거부하므로 반드시 `embed` 블록을 쓴다.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vt_common as C

PENDING = "영상 업로드 대기 중"
INTERVAL = 600


def refresh_urls() -> dict:
    """드라이브 파일 목록 → {unit key: {id, preview_url, view_url}}"""
    units = C.load_json("units.json") or []
    by_path = {u["video"]: u for u in units}
    urls: dict[str, dict] = {}
    unmatched = 0
    for path, meta in C.drive_listing().items():
        unit = by_path.get(path)
        if not unit:
            unmatched += 1
            continue
        fid = meta["ID"]
        urls[unit["key"]] = {
            "id": fid,
            "size": meta.get("Size", 0),
            "preview_url": f"https://drive.google.com/file/d/{fid}/preview",
            "view_url": f"https://drive.google.com/file/d/{fid}/view?usp=sharing",
        }
    C.save_json("video_urls.json", urls)
    return urls


def backfill(urls: dict, dry: bool = False) -> tuple[int, int]:
    state = C.load_json("pages.json", {}) or {}
    filled = pending = 0
    for key, info in state.items():
        if info.get("video_filled"):
            continue
        video = urls.get(key)
        if not video:
            pending += 1
            continue
        try:
            blocks = C.get_children(info["page_id"])
        except Exception as exc:
            print(f"  읽기 실패 {info['title'][:40]} — {exc}")
            continue

        slot = next((b for b in blocks
                     if b["type"] == "callout" and PENDING in C.rich_text_of(b)), None)
        if slot is None:
            info["video_filled"] = any(b["type"] == "embed" for b in blocks)
            continue
        if dry:
            filled += 1
            continue

        idx = blocks.index(slot)
        body = {"children": [C.embed(video["preview_url"])]}
        if idx > 0:
            body["after"] = blocks[idx - 1]["id"]
        C.api(f"https://api.notion.com/v1/blocks/{info['page_id']}/children", "PATCH", body)
        C.api(f"https://api.notion.com/v1/blocks/{slot['id']}", "PATCH", {"archived": True})
        info["video_filled"] = True
        filled += 1
        if filled % 10 == 0:
            C.save_json("pages.json", state)
            print(f"  … {filled}개 채움", flush=True)
    if not dry:
        C.save_json("pages.json", state)
    return filled, pending


def once(dry: bool = False) -> int:
    urls = refresh_urls()
    units = C.load_json("units.json") or []
    filled, pending = backfill(urls, dry)
    print(f"[{time.strftime('%H:%M:%S')}] 드라이브 {len(urls)}/{len(units)} · "
          f"{'(dry) ' if dry else ''}영상 채움 {filled} / 대기 {pending}")
    return pending


def main() -> None:
    C.init()
    argv = sys.argv
    if "--detach" in argv:
        extra = [a for a in ("--loop", "--urls-only") if a in argv]
        print(f"분리 실행 PID={C.detach('04_sync_videos.py', extra)}")
        return
    if "--urls-only" in argv:
        urls = refresh_urls()
        print(f"video_urls.json 갱신 — {len(urls)}개")
        return

    dry = "--dry" in argv
    if "--loop" not in argv:
        once(dry)
        return
    for _ in range(300):
        if once(dry) == 0:
            print("모든 차시에 영상이 붙었습니다 — 종료")
            return
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
