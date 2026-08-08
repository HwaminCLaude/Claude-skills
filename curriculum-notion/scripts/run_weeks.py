# -*- coding: utf-8 -*-
"""run_weeks.py — 주차별 Codex 저작을 병렬로 돌린다.

각 주차마다 `_prompts/W<NN>.md` 를 Codex 에 물려 그 주차 유닛을 전부 작성시킨다.
Codex 는 노션을 건드리지 않는다(발행은 publish_all.py 가 한다).

    python run_weeks.py 1 2 3          # 특정 주차
    python run_weeks.py --rest         # 아직 유닛 파일이 없는 주차 전부
    python run_weeks.py --rest -j 3    # 동시 3개
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Windows 에서 codex 는 npm 셔임(.CMD)이라 이름만으론 subprocess 가 못 찾는다.
CODEX = shutil.which("codex") or "codex"

HERE = Path(__file__).parent
LOGS = HERE / "_logs"
CUR = json.loads((HERE / "curriculum.json").read_text(encoding="utf-8"))
DL = str(HERE)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def missing(week: int) -> list[str]:
    return [u["id"] for u in CUR["units"]
            if u["week"] == week and not (HERE / "units" / f"{u['id']}.py").exists()]


def run_week(week: int) -> tuple[int, int, str]:
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"W{week:02d}.log"
    prompt = (HERE / "_prompts" / f"W{week:02d}.md")
    if not prompt.exists():
        return week, 1, "프롬프트 없음"
    txt = prompt.read_text(encoding="utf-8")
    t0 = time.time()
    try:
        r = subprocess.run(
            [CODEX, "exec", "-C", str(HERE), "--add-dir", DL,
             "-s", "workspace-write", "--skip-git-repo-check", "-"],
            input=txt, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=7200)
        log.write_text((r.stdout or "") + "\n--- stderr ---\n" + (r.stderr or ""),
                       encoding="utf-8")
        rc = r.returncode
    except subprocess.TimeoutExpired:
        log.write_text("TIMEOUT", encoding="utf-8")
        rc = 124
    left = missing(week)
    dt = int(time.time() - t0)
    msg = f"{dt//60}분 / 남은유닛 {len(left)}" + (f" {left}" if left else "")
    return week, rc, msg


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    jobs = 3
    if "-j" in sys.argv:
        jobs = int(sys.argv[sys.argv.index("-j") + 1])
    if "--rest" in sys.argv:
        weeks = [w["week"] for w in CUR["weeks"] if missing(w["week"])]
    else:
        weeks = [int(a) for a in args]
    if not weeks:
        print("할 일 없음 — 모든 주차의 유닛 파일이 이미 있습니다.")
        return 0

    print(f"대상 주차 {weeks}  (동시 {jobs})")
    for w in weeks:
        print(f"  W{w:02d} 남은유닛 {len(missing(w))}")
    print()

    ok = bad = 0
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for week, rc, msg in ex.map(run_week, weeks):
            tag = "OK " if rc == 0 else f"rc={rc}"
            print(f"  [{tag}] W{week:02d}  {msg}", flush=True)
            ok += rc == 0
            bad += rc != 0
    print(f"\n완료 {ok} / 실패 {bad}")
    print(f"로그: {LOGS}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
