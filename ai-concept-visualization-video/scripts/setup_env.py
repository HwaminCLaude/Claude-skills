"""프로젝트 루트에서 uv 환경을 만든다.

    python setup_env.py --root <proj>

1. uv 가 PATH 에 있는지 확인한다.
2. `uv sync` (cwd=<proj>). pyproject.toml 이 Python ==3.10.18, ManimGL 포크, raenimgl, av 를 고정한다.
   Python 3.10.18 이 없으면 uv 가 내려받는다. 첫 실행은 git 저장소 두 개를 받으므로 몇 분 걸린다.
3. <proj>/.venv 파이썬으로 `import manimlib, raenimgl, av` 를 확인한다.
성공하면 exit 0, 아니면 exit 1.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def venv_python(root: Path) -> Path:
    win = root / ".venv" / "Scripts" / "python.exe"
    return win if os.name == "nt" or win.exists() else root / ".venv" / "bin" / "python"


def check_imports(py: Path, cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    code = ("import sys, manimlib, raenimgl, av; "
            "print('python', sys.version.split()[0]); print('av', av.__version__)")
    return subprocess.run([str(py), "-c", code], cwd=str(cwd), capture_output=True,
                          encoding="utf-8", errors="replace", env=env, timeout=600)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="uv sync + import 확인")
    ap.add_argument("--root", required=True, help="pyproject.toml 이 있는 프로젝트 루트")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    root = Path(args.root).resolve()
    if not (root / "pyproject.toml").exists():
        print(f"FAIL {root / 'pyproject.toml'} not found (run scaffold.py first)")
        return 1
    uv = shutil.which("uv")
    if not uv:
        print("FAIL uv not found on PATH (install: https://docs.astral.sh/uv/)")
        return 1

    print(f"$ uv sync  (cwd={root})", flush=True)
    proc = subprocess.run([uv, "sync"], cwd=str(root))
    if proc.returncode != 0:
        print(f"FAIL uv sync exit={proc.returncode}")
        return 1

    py = venv_python(root)
    if not py.exists():
        print(f"FAIL venv python not found: {py}")
        return 1
    proc = check_imports(py, root)
    if proc.returncode != 0:
        print("FAIL import manimlib, raenimgl, av")
        print((proc.stderr or proc.stdout)[-3000:])
        return 1
    print(proc.stdout.strip())
    print(f"PASS env ready: {py}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
