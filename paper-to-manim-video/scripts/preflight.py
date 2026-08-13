"""Diagnose whether this machine can render a paper-to-manim-video project.

Read-only: reports, never installs or edits anything. Run with the system Python.

    python preflight.py [--root C:\\manimwork\\my-paper] [--json]

Exit code is 0 when nothing is blocking, 1 when at least one check FAILs.
WARN never blocks — those checks degrade a feature (e.g. no codex => the
generated-imagery node switches off and everything is drawn in Manim).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path


# Windows consoles default to cp949 here, and every one of these scripts prints
# Korean. Without this, a run dies with UnicodeEncodeError *after* it has already
# written its output files — the confusing failure mode of looking broken while
# actually having succeeded.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

FAIL, WARN, OK, SKIP = "FAIL", "WARN", "OK", "SKIP"


@dataclass
class Check:
    key: str
    label: str
    status: str
    detail: str = ""
    remedy: str = ""
    extra: dict = field(default_factory=dict)


def sh(cmd: list[str], timeout: int = 25) -> tuple[int, str]:
    """Run a command, return (returncode, combined output). Never raises.

    On Windows an npm-installed CLI is a `.cmd` shim. Passing the bare name to
    CreateProcess raises WinError 2, and even a resolved `.cmd` path is safest
    launched through the command interpreter — so resolve, then wrap.
    """
    exe = shutil.which(cmd[0])
    if exe is None:
        return 127, "not found"
    argv = [exe, *cmd[1:]]
    if os.name == "nt" and Path(exe).suffix.lower() in (".cmd", ".bat"):
        argv = [os.environ.get("COMSPEC", "cmd.exe"), "/c", *argv]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except OSError as exc:
        return 1, str(exc)


def venv_python(root: Path) -> Path:
    win = root / ".venv" / "Scripts" / "python.exe"
    return win if win.exists() else root / ".venv" / "bin" / "python"


# ---------------------------------------------------------------- host tooling

def check_python() -> Check:
    v = sys.version_info
    ok = (v.major, v.minor) == (3, 11)
    return Check("python", "Python 3.11 (system)",
                 OK if ok else WARN,
                 f"{platform.python_version()} at {sys.executable}",
                 "" if ok else "manim is pinned to a 3.11 venv; the system interpreter only "
                               "bootstraps uv, so a different version here is usually harmless.")


def check_on_path(key: str, label: str, exe: str, version_arg: str = "--version",
                  remedy: str = "", severity: str = FAIL) -> Check:
    path = shutil.which(exe)
    if not path:
        return Check(key, label, severity, "not on PATH", remedy)
    rc, out = sh([exe, version_arg])
    first = out.strip().splitlines()[0] if out.strip() else ""
    return Check(key, label, OK, f"{first or 'present'} ({path})")


def check_latex() -> Check:
    exe = shutil.which("pdflatex") or shutil.which("latex")
    if not exe:
        return Check("latex", "LaTeX (MathTex 렌더용)", FAIL, "pdflatex/latex not on PATH",
                     "winget install MiKTeX.MiKTeX  →  새 셸을 열거나 PATH를 갱신한 뒤 재검사. "
                     "설치 후 반드시 AutoInstall도 켤 것 (아래 항목 참고).")
    rc, out = sh([exe, "--version"])
    return Check("latex", "LaTeX (MathTex 렌더용)", OK,
                 out.strip().splitlines()[0] if out.strip() else exe)


def check_miktex_autoinstall() -> Check:
    """MiKTeX defaults to asking before fetching a missing package — that GUI
    prompt HANGS a non-interactive render instead of failing it."""
    if not shutil.which("initexmf"):
        return Check("miktex_autoinstall", "MiKTeX AutoInstall", SKIP,
                     "initexmf not found (MiKTeX 미설치이거나 TeX Live 사용 중)")
    rc, out = sh(["initexmf", "--show-config-value", "[MPM]AutoInstall"])
    val = out.strip().splitlines()[-1].strip() if out.strip() else ""
    if val == "1":
        return Check("miktex_autoinstall", "MiKTeX AutoInstall", OK, "1 (자동 설치 켜짐)")
    return Check("miktex_autoinstall", "MiKTeX AutoInstall", WARN,
                 f"현재값 {val!r} — 누락 패키지를 물어보므로 첫 MathTex 렌더가 멈출 수 있음",
                 'initexmf --set-config-value "[MPM]AutoInstall=1"')


def check_korean_font() -> Check:
    """Manim's Text() goes through Pango; a Korean-capable family must exist."""
    if platform.system() == "Windows":
        candidates = {"Malgun Gothic": Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "malgun.ttf"}
    else:
        candidates = {}
    found = {name: p for name, p in candidates.items() if p.exists()}
    if found:
        name = next(iter(found))
        return Check("korean_font", "한글 폰트", OK, f"{name} ({found[name]})",
                     extra={"font": name})
    return Check("korean_font", "한글 폰트", WARN,
                 "Malgun Gothic을 찾지 못함",
                 'Text(..., font="<설치된 한글 폰트>")로 명시하거나 나눔고딕 등을 설치할 것')


def check_codex() -> Check:
    """Capability gate for the generated-imagery node. Absence is not fatal."""
    if not shutil.which("codex"):
        return Check("codex_image", "Codex 이미지 생성", WARN, "codex CLI가 PATH에 없음",
                     "이미지 생성 노드를 끄고 전 구간 Manim 작도로 진행합니다.",
                     extra={"enabled": False})
    rc, out = sh(["codex", "features", "list"], timeout=60)
    if rc != 0:
        return Check("codex_image", "Codex 이미지 생성", WARN,
                     "`codex features list` 실패", "이미지 생성 노드를 끕니다.",
                     extra={"enabled": False})
    enabled = False
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == "image_generation":
            enabled = parts[-1].lower() == "true"
            break
    if enabled:
        return Check("codex_image", "Codex 이미지 생성", OK, "image_generation = true",
                     extra={"enabled": True})
    return Check("codex_image", "Codex 이미지 생성", WARN,
                 "image_generation 플래그가 꺼져 있음",
                 "codex features enable image_generation", extra={"enabled": False})


# ------------------------------------------------------------- project venv

def check_project_root(root: Path | None) -> Check:
    if root is None:
        return Check("root", "프로젝트 출력 루트", SKIP, "--root 미지정")
    detail = str(root)
    if not root.as_posix().isascii():
        return Check("root", "프로젝트 출력 루트", WARN, f"{detail} (비-ASCII 경로)",
                     r"MiKTeX 임시파일이 한글 경로에서 깨질 수 있음. C:\manimwork\<slug> 권장.")
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".preflight_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return Check("root", "프로젝트 출력 루트", FAIL, f"{detail} — 쓰기 불가: {exc}",
                     "쓰기 가능한 다른 경로를 --root로 지정하세요.")
    free_gb = shutil.disk_usage(root).free / 2**30
    if free_gb < 5:
        return Check("root", "프로젝트 출력 루트", WARN,
                     f"{detail} (여유 {free_gb:.1f}GB)",
                     "1080p60 렌더는 partial movie 파일을 많이 만듭니다. 5GB 이상 권장.")
    return Check("root", "프로젝트 출력 루트", OK, f"{detail} (여유 {free_gb:.1f}GB)")


def check_venv_imports(root: Path | None) -> list[Check]:
    if root is None:
        return [Check("venv", "프로젝트 venv", SKIP, "--root 미지정")]
    py = venv_python(root)
    if not py.exists():
        return [Check("venv", "프로젝트 venv", FAIL, f"{py} 없음",
                      f'python scripts/setup_env.py --root "{root}"')]

    probe = (
        "import json,sys\n"
        "r={}\n"
        "try:\n"
        "    import manim; r['manim']=manim.__version__\n"
        "except Exception as e: r['manim']='ERR: %s'%e\n"
        "try:\n"
        "    import noise; r['noise']='shim' if getattr(noise,'SHIM',False) else 'real'\n"
        "except Exception as e: r['noise']='ERR: %s'%e\n"
        "try:\n"
        "    from raenim import Scene2D, PythonCode, RaeTex, Tensor; r['raenim']='ok'\n"
        "except Exception as e: r['raenim']='ERR: %s'%e\n"
        "print(json.dumps(r))\n"
    )
    rc, out = sh([str(py), "-c", probe], timeout=120)
    payload = {}
    for line in out.strip().splitlines()[::-1]:
        try:
            payload = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if not payload:
        return [Check("venv", "프로젝트 venv", FAIL, f"probe 실패: {out.strip()[:300]}",
                      f'python scripts/setup_env.py --root "{root}" --force')]

    checks = [Check("venv", "프로젝트 venv", OK, str(py))]
    m = payload.get("manim", "")
    checks.append(Check("manim", "manim import", OK if not m.startswith("ERR") else FAIL, m,
                        "" if not m.startswith("ERR") else "setup_env.py를 --force로 다시 실행"))
    n = payload.get("noise", "")
    if n == "real":
        checks.append(Check("noise", "noise 패키지", OK, "실제 C 확장"))
    elif n == "shim":
        checks.append(Check("noise", "noise 패키지", OK, "순수 파이썬 shim (RWiggle만 사용, 정상)"))
    else:
        checks.append(Check("noise", "noise 패키지", FAIL, n,
                            "assets/noise_shim/noise.py를 venv site-packages에 복사"))
    r = payload.get("raenim", "")
    checks.append(Check("raenim", "raenim import", OK if r == "ok" else FAIL, r,
                        "" if r == "ok" else "uv pip install --no-deps git+https://github.com/CodingVillainKor/raenim.git"))
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description="paper-to-manim-video 환경 사전 검증")
    ap.add_argument("--root", help=r"프로젝트 루트 (예: C:\manimwork\my-paper)")
    ap.add_argument("--json", action="store_true", help="마지막 줄에 JSON 요약 출력")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else None

    checks: list[Check] = [
        check_python(),
        check_on_path("uv", "uv", "uv", remedy="https://docs.astral.sh/uv/ 에서 설치"),
        check_on_path("ffmpeg", "FFmpeg", "ffmpeg", "-version",
                      remedy="winget install Gyan.FFmpeg"),
        check_on_path("git", "git", "git", remedy="winget install Git.Git", severity=WARN),
        check_latex(),
        check_miktex_autoinstall(),
        check_korean_font(),
        check_codex(),
        check_project_root(root),
    ]
    checks.extend(check_venv_imports(root))

    width = max(len(c.label) for c in checks) + 2
    print("=" * (width + 60))
    for c in checks:
        print(f"  {c.status:<4} {c.label:<{width}} {c.detail}")
        if c.remedy and c.status in (FAIL, WARN):
            print(f"       {'':<{width}} → {c.remedy}")
    print("=" * (width + 60))

    fails = [c for c in checks if c.status == FAIL]
    warns = [c for c in checks if c.status == WARN]
    print(f"  FAIL {len(fails)} / WARN {len(warns)} / total {len(checks)}")
    if fails:
        print("  차단 항목이 있습니다. 위 → 안내를 따른 뒤 다시 실행하세요 (최대 3회 반복).")

    if args.json:
        print(json.dumps({
            "blocking": len(fails),
            "warnings": len(warns),
            "image_generation": next(
                (c.extra.get("enabled", False) for c in checks if c.key == "codex_image"), False),
            "korean_font": next(
                (c.extra.get("font") for c in checks if c.key == "korean_font"), None),
            "checks": [asdict(c) for c in checks],
        }, ensure_ascii=False))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
