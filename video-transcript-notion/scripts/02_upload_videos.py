"""2단계 — 영상을 구글드라이브에 올린다. 정체 감시 워치독이 내장돼 있다.

    python 02_upload_videos.py --work <폴더>            # 포그라운드
    python 02_upload_videos.py --work <폴더> --detach   # 분리 실행(권장, 수 시간)
    python 02_upload_videos.py --work <폴더> --status   # 남은 개수만
    python 02_upload_videos.py --work <폴더> --bw off   # 대역폭 상한 해제

## 왜 이렇게 짰는가 (70GB·546개를 올리며 실제로 겪은 것)

1. **그룹별로 돌리면 미완성 그룹을 건너뛴다.** 처음엔 주차마다 rclone 을 돌리고 N회
   재시도 후 다음으로 넘어가게 했는데, 미완성인 채로 넘어가 버렸다.
   → **전체를 한 번에 copy 하고 남은 파일이 0 이 될 때까지 라운드 반복.** copy 는 멱등이다.

2. **rclone 이 구글드라이브 업로드 중 자주 정체된다.** 수 GB 지점에서 전송량이 수백 B/s 로
   떨어져 몇 시간을 날린다(`--timeout` 으로 안 풀린다). 내장 워치독이 STALL_MIN 분간
   전송량이 안 늘면 rclone 을 죽이고, 상위 루프가 이어서 재개한다.

3. **대역폭 상한이 없으면 Notion API 호출이 굶어 죽는다.** 노션 작업과 병행할 땐 상한을
   걸고, 업로드만 남았으면 `--bw off` 로 푼다.
"""
from __future__ import annotations

import re
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vt_common as C

STALL_MIN = 3        # 이만큼 전송량이 그대로면 정체로 보고 rclone 을 죽인다
POLL_SEC = 60
MAX_ROUNDS = 60
STATS_RE = re.compile(r"([\d.]+)\s+([KMGT]?i?B)\s*/\s*[\d.]+\s+[KMGT]?i?B")
UNIT = {"B": 1, "KiB": 2**10, "MiB": 2**20, "GiB": 2**30, "TiB": 2**40}
_stop = threading.Event()


def log(msg: str) -> None:
    path = C.out_dir() / "upload.log"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")


def local_files() -> list[tuple[str, int]]:
    units = C.load_json("units.json") or []
    if units:
        return [(u["video"], u["size"]) for u in units]
    src = C.source_dir()
    return [(str(p.relative_to(src)).replace("\\", "/"), p.stat().st_size)
            for p in src.glob("*/*.mp4")]


def remaining() -> tuple[int, float]:
    have = set(C.drive_listing())
    left = [(p, s) for p, s in local_files() if p not in have]
    return len(left), sum(s for _, s in left) / 2**30


# ─────────────────────────────────────────────────────────── 워치독
def transferred() -> float | None:
    path = C.out_dir() / "upload.log"
    if not path.exists():
        return None
    try:
        tail = path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
    except Exception:
        return None
    for line in reversed(tail):
        m = STATS_RE.search(line)
        if m:
            return float(m[1]) * UNIT.get(m[2], 1)
    return None


def rclone_alive() -> bool:
    if sys.platform != "win32":
        return subprocess.run(["pgrep", "-x", "rclone"], capture_output=True).returncode == 0
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq rclone.exe"], capture_output=True)
    return b"rclone.exe" in out.stdout


def kill_rclone() -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/IM", "rclone.exe"], capture_output=True)
    else:
        subprocess.run(["pkill", "-9", "-x", "rclone"], capture_output=True)


def watchdog() -> None:
    last_val, last_change, kills = None, time.time(), 0
    while not _stop.is_set():
        time.sleep(POLL_SEC)
        if not rclone_alive():
            last_val, last_change = None, time.time()
            continue
        val = transferred()
        if val is None:
            continue
        if last_val is None or val > last_val + 1024:
            last_val, last_change = val, time.time()
            continue
        idle = (time.time() - last_change) / 60
        if idle >= STALL_MIN:
            kills += 1
            log(f"[WATCHDOG] 정체 {idle:.1f}분 ({val / 2**30:.2f} GiB) → rclone 종료 #{kills}")
            kill_rclone()
            last_val, last_change = None, time.time()


# ────────────────────────────────────────────────────────── 업로드
def build_cmd(bwlimit: str) -> list[str]:
    cmd = [
        C.rclone(), "copy", str(C.source_dir()), C.remote(),
        "--include", "/*/*.mp4",
        "--transfers", "4", "--checkers", "8",
        "--retries", "10", "--low-level-retries", "30",
        "--drive-chunk-size", "8M",       # 작게: 정체 시 재전송 손실이 적다
        "--tpslimit", "8",
        "--timeout", "90s", "--contimeout", "20s", "--expect-continue-timeout", "10s",
        "--log-file", str(C.out_dir() / "upload.log"), "--log-level", "INFO",
        "--stats", "1m", "--stats-one-line",   # 5m 이면 워치독이 정체를 못 읽는다
    ]
    if bwlimit and bwlimit != "off":
        cmd[4:4] = ["--bwlimit", bwlimit]
    return cmd


def make_public() -> None:
    """폴더 단위 공개 1회. 파일별 link 는 수십 분 걸리므로 절대 하지 말 것."""
    proc = subprocess.run([C.rclone(), "link", "--expire", "0", C.remote()],
                          capture_output=True, timeout=300)
    out = proc.stdout.decode("utf-8", "replace").strip()
    log(f"[PUBLIC] {out or proc.stderr.decode('utf-8', 'replace')[:120]}")
    print(f"폴더 공개 링크: {out}")


def run(bwlimit: str) -> int:
    n0, gb0 = remaining()
    log(f"[START] 남은 {n0}개 / {gb0:.1f}GiB (bwlimit={bwlimit})")
    print(f"업로드 시작 — 남은 {n0}개 / {gb0:.1f}GiB")
    if n0 == 0:
        return 0

    threading.Thread(target=watchdog, daemon=True).start()
    cmd = build_cmd(bwlimit)
    for round_no in range(1, MAX_ROUNDS + 1):
        rc = subprocess.call(cmd)
        left, gb = remaining()
        log(f"[ROUND {round_no}] rc={rc} 남은 {left}개 / {gb:.1f}GiB")
        print(f"[ROUND {round_no}] 남은 {left}개 / {gb:.1f}GiB", flush=True)
        if left == 0:
            _stop.set()
            make_public()
            log("[DONE] 전부 업로드 완료")
            print("전부 업로드 완료")
            return 0
        time.sleep(20)
    _stop.set()
    log(f"[STOP] {MAX_ROUNDS}라운드 소진")
    return 1


def main() -> None:
    C.init()
    argv = sys.argv
    bw = argv[argv.index("--bw") + 1] if "--bw" in argv else C.cfg("bandwidth_limit", "1600k")
    if "--status" in argv:
        n, gb = remaining()
        print(f"남은 {n}개 / {gb:.1f}GiB")
        return
    if "--public" in argv:
        make_public()
        return
    if "--detach" in argv:
        extra = ["--bw", bw]
        print(f"업로드 분리 실행 PID={C.detach('02_upload_videos.py', extra)}  bwlimit={bw}")
        print(f"로그: {C.out_dir() / 'upload.log'}")
        return
    sys.exit(run(bw))


if __name__ == "__main__":
    main()
