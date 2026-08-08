# -*- coding: utf-8 -*-
"""verify_unit_nb.py — 유닛 노트북의 **검산 셀이 실제로 통과하는지** 돌려서 확인한다.

preflight 는 `allclose` 라는 글자가 있는지만 본다. 그건 "채점기가 있다"는 뜻이지
"채점을 통과한다"는 뜻이 아니다. 이 스크립트가 그 차이를 메운다.

돌리는 것:  setup → explore → SOLUTION(정답 구현) → check
`todo` 셀은 일부러 NotImplementedError 라서 건너뛰고, 그 자리를 SOLUTION 이 채운다.
SOLUTION 이 없으면 노션 '💻 직접 만들기' 섹션의 첫 코드 블록을 대신 쓴다.

    python verify_unit_nb.py units/W04U05.py
    python verify_unit_nb.py --all
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import blocks as B                       # noqa: E402
from build_unit_notebook import load     # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def solution_of(mod) -> tuple[str, str]:
    """(정답코드, 출처)"""
    if getattr(mod, "SOLUTION", None):
        return mod.SOLUTION, "SOLUTION"
    bs = mod.build(B, lambda k, c=None: B.image(k, c))
    codes = [("".join(r["text"]["content"] for r in b["code"]["rich_text"]))
             for b in bs if b.get("type") == "code"
             and b["code"]["language"] == "python"]
    if not codes:
        raise SystemExit("정답 코드가 없습니다 (SOLUTION 또는 python 코드 블록 필요)")
    return codes[0], "build()의 첫 python 코드블록"


def cells(mod, key: str) -> str:
    return "\n".join(b for k, b in (getattr(mod, "NB", {}).get(key) or []) if k == "code")


def run_one(path: Path) -> tuple[bool, str]:
    mod = load(path)
    sol, src = solution_of(mod)
    prog = "\n\n".join([cells(mod, "setup"), cells(mod, "explore"), sol, cells(mod, "check")])
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8", dir=HERE) as f:
        f.write(prog)
        tmp = Path(f.name)
    try:
        r = subprocess.run([sys.executable, "-W", "error::FutureWarning",
                            "-W", "error::DeprecationWarning", str(tmp)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
    finally:
        tmp.unlink(missing_ok=True)
    ok = r.returncode == 0
    out = (r.stdout or "") + (r.stderr or "")
    if ok and "✅" not in out:
        ok, out = False, out + "\n[!] 통과 표시(✅)가 출력되지 않았습니다"
    return ok, f"[정답출처: {src}]\n" + out.strip()[-1400:]


def main() -> int:
    if "--all" in sys.argv:
        paths = sorted((HERE / "units").glob("W*.py"))
    elif len(sys.argv) > 1:
        paths = [Path(sys.argv[1])]
    else:
        print(__doc__)
        return 2

    bad = 0
    for p in paths:
        print(f"\n=== {p.stem} ===")
        try:
            ok, out = run_one(p)
        except Exception as e:
            ok, out = False, f"실행 실패: {e}"
        print(out)
        print("→", "통과" if ok else "실패")
        bad += 0 if ok else 1

    print(f"\n{len(paths) - bad}/{len(paths)} 통과")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
