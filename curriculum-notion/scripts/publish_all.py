# -*- coding: utf-8 -*-
"""publish_all.py — 완성된 유닛을 검증→발행→노트북 업로드까지 일괄 처리.

유닛 하나당 순서
  1. preflight_unit      규약 검사 (정답 누출·수식·언어·이미지)
  2. build_unit_notebook 노트북 생성 + 규약 검사
  3. verify_unit_nb      **검산 셀 실제 실행** (경고도 에러)
  4. 노션 발행           본문 비우고 청크 순차 1회 (누적·중복 방지)
  5. rclone 업로드       노트북 → 드라이브, `콜랩` 속성에 링크

멱등: publish_state.json 에 완료 유닛을 기록해 이어서 재개한다.
노션 호출은 **순차**로만 한다(레이트리밋 3req/s).

    python publish_all.py --check-only     # 검증만 (노션 안 건드림)
    python publish_all.py                  # 검증 통과분 전부 발행
    python publish_all.py W04U01 W04U02    # 특정 유닛만
    python publish_all.py --force          # 이미 발행한 것도 다시
"""
from __future__ import annotations

import os

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

def _need(name: str, hint: str):
    """없으면 트레이스백 대신 무엇을 먼저 하라고 알려 준다."""
    import json as _j
    import sys as _s
    p = HERE / name
    if not p.exists():
        print(f"[!] {name} 가 없습니다. 먼저 {hint} 를 실행하세요.", file=_s.stderr)
        _s.exit(2)
    return _j.loads(p.read_text(encoding="utf-8"))

sys.path.insert(0, str(HERE))


import blocks as B                       # noqa: E402
import notion_api as N                   # noqa: E402
import unitkit as K                      # noqa: E402
from build_unit_notebook import load     # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CUR = _need("curriculum.json", "curriculum.py --dump")
STATE = _need("state.json", "publish_skeleton.py")
PSTATE = HERE / "publish_state.json"
RCLONE = os.environ.get("RCLONE_BIN", "rclone")
DRIVE = "gdrive:메타코드 실습프로젝트/_코딩북_실습"


def pstate() -> dict:
    return json.loads(PSTATE.read_text(encoding="utf-8")) if PSTATE.exists() else {}


def save(s: dict) -> None:
    PSTATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def page_of(uid: str) -> str | None:
    ent = STATE["weeks"].get(str(int(uid[1:3]))) or {}
    return (ent.get("units") or {}).get(uid)


def sh(*cmd) -> tuple[int, str]:
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def check(path: Path) -> tuple[bool, str]:
    for script in ("preflight_unit.py", "build_unit_notebook.py", "verify_unit_nb.py"):
        rc, out = sh(str(HERE / script), str(path))
        if rc != 0:
            return False, f"{script}: {out[-500:]}"
    return True, "ok"


def upload_nb(uid: str, week: int) -> str | None:
    nb = HERE / "notebooks" / f"{uid}.ipynb"
    if not nb.exists():
        return None
    dest = f"{DRIVE}/{week:02d}주차/"
    r = subprocess.run([RCLONE, "copy", str(nb), dest], capture_output=True, timeout=900)
    if r.returncode != 0:
        print(f"    [!] 업로드 실패 rc={r.returncode}")
        return None
    r = subprocess.run([RCLONE, "lsjson", dest], capture_output=True, timeout=600)
    try:
        for it in json.loads(r.stdout.decode("utf-8")):
            if it["Name"] == nb.name:
                return f"https://colab.research.google.com/drive/{it['ID']}"
    except Exception:
        pass
    return None


def main() -> int:
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    check_only = "--check-only" in sys.argv
    force = "--force" in sys.argv
    ps = pstate()

    units = [u for u in CUR["units"] if (HERE / "units" / f"{u['id']}.py").exists()]
    if only:
        units = [u for u in units if u["id"] in only]
    if not force:
        units = [u for u in units if u["id"] not in ps]
    if not units:
        print("할 일 없음 (모두 발행됨 또는 유닛 파일 없음)")
        return 0

    print(f"대상 {len(units)}유닛" + ("  [검증만]" if check_only else ""))
    okc = badc = 0
    fails: list[str] = []

    for i, u in enumerate(units, 1):
        uid = u["id"]
        path = HERE / "units" / f"{uid}.py"
        print(f"\n[{i}/{len(units)}] {uid} — {u['raw_title'][:40]}")

        good, msg = check(path)
        if not good:
            print(f"   검증 실패: {msg[:300]}")
            fails.append(f"{uid}: {msg[:160]}")
            badc += 1
            continue
        print("   검증 통과 (preflight·build·검산실행)")
        if check_only:
            okc += 1
            continue

        pid = page_of(uid)
        if not pid:
            fails.append(f"{uid}: 노션 페이지 없음")
            badc += 1
            continue

        mod = load(path)
        plt = K.setup_mpl()
        if hasattr(mod, "figs"):
            mod.figs(plt)
        bs = mod.build(B, lambda k, c=None: B.image(k, c))
        bs, nimg = K.resolve_images(bs)
        got = K.publish(pid, bs)
        if got != len(bs):
            fails.append(f"{uid}: 블록 수 불일치 {got}≠{len(bs)}")
            badc += 1
            continue

        url = upload_nb(uid, u["week"])
        if url:
            N.update_page(pid, {"콜랩": {"url": url}})
        print(f"   발행 {got}블록 · 그림 {nimg} · 콜랩 {'OK' if url else '없음'}")
        ps[uid] = {"page": pid, "blocks": got, "colab": url}
        save(ps)
        okc += 1

    print(f"\n{'검증' if check_only else '발행'} 성공 {okc} / 실패 {badc}")
    for f in fails:
        print("  -", f)
    return 1 if badc else 0


if __name__ == "__main__":
    sys.exit(main())
