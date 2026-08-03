"""화질 진단 — "왜 어떤 영상은 720p 로 보이고 어떤 건 320p 고정인가?" 에 답한다.

    python probe_quality.py --work <폴더>            # 드라이브 변환 상태
    python probe_quality.py --work <폴더> --local    # 로컬 원본 해상도

두 가지가 겹쳐 있어 헷갈리기 쉽다. 반드시 구분해서 답할 것:

  (A) **드라이브 변환 대기** — 노션은 드라이브 미리보기를 그대로 띄운다. 드라이브는 업로드 후
      백그라운드로 360p → 480p → 720p → 1080p 순서로 변환하는데, 끝나기 전에는 낮은 화질만
      고를 수 있다. **기다리면 저절로 해결된다.** 대량 업로드 직후엔 대기열이 밀린다.
      판별법: Drive API 의 `videoMediaMetadata` 는 **변환이 끝나야 채워진다**.

  (B) **원본이 애초에 저화질** — 변환이 끝나도 그 이상 안 올라간다. 영구적이다.
      판별법: 로컬 파일을 ffprobe 로 재면 된다(`--local`).
"""
from __future__ import annotations

import collections
import json
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vt_common as C

FIELDS = "id,name,size,videoMediaMetadata,hasThumbnail"


def tier(height: int | None) -> str:
    h = height or 0
    return "4K" if h >= 2000 else "QHD" if h >= 1400 else "FHD" if h >= 1000 else "저화질"


def probe_local() -> None:
    ffprobe = C.cfg("ffprobe_bin", "ffprobe")
    units = C.load_json("units.json") or []
    src = C.source_dir()
    print(f"로컬 원본 {len(units)}개 조사 중...")

    def one(unit: dict) -> dict:
        path = src / unit["video"]
        try:
            proc = subprocess.run(
                [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                 "stream=width,height:format=duration,size", "-of", "json", str(path)],
                capture_output=True, timeout=60)
            d = json.loads(proc.stdout.decode("utf-8", "replace"))
            st = (d.get("streams") or [{}])[0]
            fm = d.get("format") or {}
            dur = float(fm.get("duration") or 0)
            size = int(fm.get("size") or 0)
            return {**unit, "w": st.get("width"), "h": st.get("height"),
                    "mbps": round(size * 8 / dur / 1e6, 2) if dur else 0}
        except Exception as exc:
            return {**unit, "w": None, "h": None, "err": str(exc)[:60]}

    with ThreadPoolExecutor(max_workers=12) as pool:
        res = list(pool.map(one, units))
    C.save_json("local_probe.json", [{k: v for k, v in r.items() if k != "segments"}
                                     for r in res])

    print(f"\n{'해상도':<14}{'개수':>6}{'총GB':>9}{'평균Mbps':>10}")
    for key, n in sorted(collections.Counter((r["w"], r["h"]) for r in res).items(),
                         key=lambda x: -(x[0][1] or 0)):
        sub = [r for r in res if (r["w"], r["h"]) == key]
        gb = sum(r.get("size", 0) for r in sub) / 2**30
        mb = sum(r.get("mbps", 0) for r in sub) / len(sub)
        label = f"{key[0]}x{key[1]}" if key[0] else "조사실패"
        print(f"{label:<14}{n:>6}{gb:>8.1f}{mb:>10.2f}")

    low = [r for r in res if (r["h"] or 0) < 1000]
    print(f"\n화질 좋음(1080p+) {len(res) - len(low)}개 / 낮음(720p 이하) {len(low)}개")
    if low:
        print("\n저화질 목록 — 원본이 그래서 개선 불가:")
        for r in sorted(low, key=lambda r: r["video"]):
            print(f"  {r['w']}x{r['h']:<5} {r.get('mbps', 0):>5.1f}Mbps  {r['video'][:64]}")
        per = collections.Counter(r["group"] for r in low)
        print(f"\n  그룹별: {dict(per)}")


def probe_drive() -> None:
    headers = {"Authorization": "Bearer " + C.drive_access_token()}
    files = list(C.drive_listing().items())
    print(f"드라이브 파일 {len(files)}개 — 변환 상태 조회 중...")

    def one(item) -> dict:
        path, meta = item
        url = (f"https://www.googleapis.com/drive/v3/files/{meta['ID']}"
               f"?fields={FIELDS}&supportsAllDrives=true")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
            vm = data.get("videoMediaMetadata") or {}
            return {"path": path, "size": int(meta.get("Size") or 0),
                    "h": vm.get("height"), "w": vm.get("width")}
        except Exception as exc:
            return {"path": path, "err": str(exc)[:80]}

    with ThreadPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, files))
    C.save_json("drive_probe.json", res)

    done = [r for r in res if r.get("h")]
    pending = [r for r in res if not r.get("h") and "err" not in r]
    errors = [r for r in res if "err" in r]

    print(f"\n변환 완료 (원본 화질까지 선택 가능) : {len(done)}")
    print(f"변환 대기 (저화질 고정, 기다리면 해결) : {len(pending)}")
    print(f"조회 실패                              : {len(errors)}")
    if errors:
        print(f"  예: {errors[0].get('err')}")

    if done:
        print("\n드라이브가 인식한 해상도")
        for h, n in sorted(collections.Counter(r["h"] for r in done).items(), reverse=True):
            print(f"  {h:>5}p  {n:>4}개")

    if pending:
        gb = sum(r.get("size", 0) for r in pending) / 2**30
        print(f"\n변환 대기 {len(pending)}개 ({gb:.1f} GB) — 그룹별")
        per = collections.Counter(r["path"].split("/")[0] for r in pending)
        for group, n in sorted(per.items(), key=lambda x: -x[1]):
            print(f"  {group:<14} {n:>4}개")
        print("\n→ 로컬에서 할 일 없음. 구글 서버가 알아서 처리하며 몇 시간~하루 걸립니다.")


def main() -> None:
    C.init()
    if "--local" in sys.argv:
        probe_local()
    else:
        probe_drive()


if __name__ == "__main__":
    sys.exit(main())
