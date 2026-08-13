"""Run a project's analysis code and validate the facts.json it produces.

Why this exists
---------------
When a video quotes numbers — a correlation, a fit index, a p-value — those
numbers must come from a computation, not from a model writing plausible digits.
This runner enforces one rule: **`analysis/` computes, `facts.json` records, and
the scenes read only from `facts.json`.** Nothing is transcribed by hand.

The project supplies `analysis/run_analysis.py`; this wrapper executes it with
the project venv, checks the output is well-formed, and reports what a scene
author is allowed to quote.

    python compute_facts.py --root C:\\manimwork\\my-project
    python compute_facts.py --root ... --check      # 계산은 건너뛰고 검증만

`facts.json` 권장 최상위 키:
    source      어떤 데이터인지 한 줄 (영상에 표시할 출처)
    criteria    논문·계획서가 정한 판정 기준 (계산값과 구분해서 보여주기 위함)
    invariants  {검증이름: bool} — 하나라도 false면 이 러너가 실패한다
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def venv_python(root: Path) -> Path:
    for cand in (root / ".venv" / "Scripts" / "python.exe",
                 root / ".venv" / "bin" / "python"):
        if cand.exists():
            return cand
    return Path(sys.executable)


def walk_numbers(node, path="") -> list[tuple[str, float]]:
    """Every numeric leaf, with its dotted path — the quotable set."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            out += walk_numbers(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += walk_numbers(v, f"{path}[{i}]")
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out.append((path, float(node)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="분석 실행 + facts.json 검증")
    ap.add_argument("--root", required=True, help="프로젝트 루트")
    ap.add_argument("--script", default="run_analysis.py",
                    help="analysis/ 안의 실행 파일 (기본 run_analysis.py)")
    ap.add_argument("--check", action="store_true", help="실행하지 않고 검증만")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    analysis = root / "analysis"
    facts_path = analysis / "facts.json"

    if not args.check:
        runner = analysis / args.script
        if not runner.is_file():
            raise SystemExit(f"분석 스크립트가 없습니다: {runner}")
        py = venv_python(root)
        print(f"[compute] {py.name} {runner.name}")
        proc = subprocess.run([str(py), str(runner)], cwd=analysis,
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        for line in (proc.stdout or "").splitlines():
            print(f"  {line}")
        if proc.returncode != 0:
            for line in (proc.stderr or "").splitlines()[-20:]:
                print(f"  ! {line}")
            raise SystemExit(f"분석 실패 (exit {proc.returncode})")

    if not facts_path.is_file():
        raise SystemExit(f"facts.json이 없습니다: {facts_path}")
    facts = json.loads(facts_path.read_text(encoding="utf-8"))

    problems = []
    if "source" not in facts:
        problems.append("`source` 없음 — 영상에 표시할 데이터 출처를 넣으세요")
    if "criteria" not in facts:
        problems.append("`criteria` 없음 — 판정 기준을 계산값과 분리해 두세요")

    invariants = facts.get("invariants")
    if not isinstance(invariants, dict) or not invariants:
        problems.append("`invariants` 없음 — 수학적 검산을 최소 하나는 넣으세요")
        failed = []
    else:
        failed = [k for k, v in invariants.items() if not v]

    numbers = walk_numbers(facts)
    print(f"\n[facts] {facts_path}")
    print(f"[facts] 출처: {facts.get('source', '(미기재)')}")
    print(f"[facts] 인용 가능한 수치 {len(numbers)}개 · 최상위 키 {len(facts)}개")
    if invariants:
        print(f"[facts] 불변량 {len(invariants) - len(failed)}/{len(invariants)} 통과")
        for k, v in invariants.items():
            print(f"         {'OK  ' if v else 'FAIL'} {k}")
    for p in problems:
        print(f"[facts] ⚠ {p}")
    if failed:
        print(f"[facts] ⚠ 불변량 실패: {failed} — 이 상태로 영상을 만들지 마세요")

    if args.json:
        print(json.dumps({"facts": str(facts_path), "numbers": len(numbers),
                          "failed_invariants": failed, "problems": problems},
                         ensure_ascii=False))
    return 1 if (failed or problems) else 0


if __name__ == "__main__":
    sys.exit(main())
