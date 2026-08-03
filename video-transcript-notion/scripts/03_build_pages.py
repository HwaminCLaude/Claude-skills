"""3단계 — 차시마다 노션 페이지를 만든다. **영상이 맨 위, 대본이 그 바로 밑.**

    python 03_build_pages.py --work <폴더> --dry
    python 03_build_pages.py --work <폴더> --group 7주차
    python 03_build_pages.py --work <폴더>

페이지 구조
    🎓 정보 callout   (그룹 · 차시 · 길이 · 부제)
    [영상 embed]                     ← 아직 업로드 전이면 ⏳ 대기 callout 을 대신 넣는다
    ─────
    H2 🎙 강의 대본 (N문장)
    [00:00] 문장 …                   ← 타임스탬프를 붙여 영상에서 찾아가기 쉽게

영상 업로드는 몇 시간 걸리므로 **페이지를 먼저 만들고 영상은 나중에 채운다**(04_sync_videos.py).
노션 블록 append 가 `after` 파라미터를 지원하기 때문에 가능한 설계다.

산출물 _out/pages.json — 멱등 재개용 상태파일(이미 만든 차시는 건너뜀)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vt_common as C

PARA_CHARS = 1800     # 노션 rich_text 는 블록당 2000자 제한
PENDING = "영상 업로드 대기 중"


def target_db(group: str) -> str | None:
    """그룹 → 실제로 페이지를 만들 DB id.

    mode=flat      : 전부 한 DB 에
    mode=child_db  : group_db_map 이 그룹마다 child DB id 를 알려준다
    """
    if C.cfg("notion.mode", "flat") == "flat":
        return C.cfg("notion.database_id")
    return (C.cfg("notion.group_db_map") or {}).get(group)


def transcript_blocks(segments: list[dict]) -> list[dict]:
    out, buf, size = [], [], 0
    for seg in segments:
        line = f"[{C.hhmmss(seg['t'])}] {seg['text']}"
        if buf and size + len(line) + 1 > PARA_CHARS:
            out.append(C.para("\n".join(buf)))
            buf, size = [], 0
        buf.append(line)
        size += len(line) + 1
    if buf:
        out.append(C.para("\n".join(buf)))
    return out


def build(unit: dict, video: dict | None) -> list[dict]:
    seq = unit["key"].split("/")[-1]
    info = f"{unit['group']} · {seq}차시 · {C.hhmmss(unit['duration'])}"
    if unit.get("subtitle"):
        info += f" · {unit['subtitle']}"
    blocks = [C.callout(info, "🎓", "gray_background")]

    if video and video.get("preview_url"):
        blocks.append(C.embed(video["preview_url"]))
    else:
        blocks.append(C.callout(f"{PENDING} — 업로드가 끝나면 자동으로 채워집니다.",
                                "⏳", "gray_background"))
    blocks.append(C.divider())

    segs = unit.get("segments") or []
    label = f"🎙 강의 대본 ({len(segs)}문장)" if segs else "🎙 강의 대본 — 없음"
    blocks.append(C.heading(label, 2, "blue_background"))
    if segs:
        blocks.extend(transcript_blocks(segs))
    else:
        blocks.append(C.callout("이 차시는 자막이 없어 대본을 넣지 못했습니다.",
                                "▫️", "gray_background"))
    return blocks


def page_title(unit: dict) -> str:
    seq = unit["key"].split("/")[-1]
    tmpl = C.cfg("page_title_format", "{seq}. {subtitle} — {title}")
    text = tmpl.format(seq=seq, group=unit["group"], title=unit["title"],
                       subtitle=unit.get("subtitle", ""))
    return text.replace(" — ", " — ").replace(".  — ", ". ").strip(" —")


def main() -> None:
    C.init()
    argv = sys.argv
    dry = "--dry" in argv
    only = argv[argv.index("--group") + 1] if "--group" in argv else None

    units = C.load_json("units.json")
    if not units:
        sys.exit("units.json 없음 — 01_scan.py 를 먼저 돌리세요")
    if only:
        units = [u for u in units if u["group"] == only]
    videos = C.load_json("video_urls.json", {}) or {}
    state = C.load_json("pages.json", {}) or {}

    print(f"차시 {len(units)}개 / 이미 만든 페이지 {len(state)}\n")
    made = skipped = no_text = 0

    for n, unit in enumerate(units, start=1):
        if unit["key"] in state and not dry:
            skipped += 1
            continue
        if not unit["segments"]:
            no_text += 1
        db_id = target_db(unit["group"])
        if not db_id:
            print(f"[{n}] 대상 DB 없음 — group={unit['group']} (config 의 group_db_map 확인)")
            continue

        video = videos.get(unit["key"])
        blocks = build(unit, video)
        total = sum(C.count_blocks(b) for b in blocks)
        title = page_title(unit)

        if dry:
            if n <= 6 or n % 50 == 0:
                print(f"[{n}/{len(units)}] DRY {unit['group']} 블록 {total:>3} "
                      f"대본 {len(unit['segments']):>4}문장 "
                      f"{'영상O' if video else '영상-'}  {title[:44]}")
            continue

        page_id = C.create_page(db_id, title)
        C.append_blocks(page_id, blocks)
        state[unit["key"]] = {
            "page_id": page_id, "title": title, "group": unit["group"],
            "segments": len(unit["segments"]), "source": unit["source"],
            "blocks": total, "video_filled": bool(video),
        }
        made += 1
        if made % 10 == 0:
            C.save_json("pages.json", state)
        print(f"[{n}/{len(units)}] OK {unit['group']} 블록 {total:>3} "
              f"대본 {len(unit['segments']):>4}문장 "
              f"{'영상O' if video else '영상-'}  {title[:44]}", flush=True)

    if dry:
        print(f"\n(dry) 총 {len(units)}차시 / 대본없음 {no_text}")
    else:
        C.save_json("pages.json", state)
        print(f"\n생성 {made} / 건너뜀 {skipped} / 대본없음 {no_text}")
        print(f"상태: {C.out_dir() / 'pages.json'}")


if __name__ == "__main__":
    sys.exit(main())
