"""렌더 전에 환경을 검사한다.

    python preflight.py --root <proj> [--python <exe>]

검사 항목(줄마다 PASS/WARN/FAIL <item> <detail>):
- python      프로젝트 venv 파이썬이 3.10.18 인지                       (FAIL)
- import      manimlib, raenimgl, av                                   (FAIL)
- ffmpeg      ffmpeg·ffprobe 실행 가능, `ffmpeg -filters` 에 subtitles  (FAIL)
- latex       latex, dvisvgm 실행 가능(Tex 수식에 필요)                  (WARN)
- font        manimpango 글꼴 목록(ManimGL Text 용): Noto Sans KR(FAIL), Noto Serif KR·Consolas(WARN)
- capfont     자막 글꼴: captions.py 의 ASS 헤더 그대로 한 줄을 ffmpeg subtitles 로 구워 보고,
              libass fontselect 가 'Noto Sans KR Medium' → NotoSansKR-Medium 을 골랐는지 본다.
              다른 글꼴(VF Thin, Arial 등)로 바뀌었거나 확인할 수 없으면                (FAIL)
- config      <proj>/custom_config.yml 이 있음                           (WARN)
FAIL 이 하나라도 있으면 exit 1.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import captions as _captions  # noqa: E402

PY_VERSION = "3.10.18"
FONTS_REQUIRED = ["Noto Sans KR"]
FONTS_OPTIONAL = ["Noto Serif KR", "Consolas"]

PROBE = r"""
import json, sys
out = {"version": sys.version.split()[0], "imports": {}, "fonts": None}
for m in ("manimlib", "raenimgl", "av"):
    try:
        __import__(m)
        out["imports"][m] = "ok"
    except BaseException as e:
        out["imports"][m] = f"{type(e).__name__}: {e}"
try:
    import manimpango
    out["fonts"] = sorted(set(manimpango.list_fonts()))
except BaseException as e:
    out["fonts_error"] = f"{type(e).__name__}: {e}"
print("PREFLIGHT_JSON " + json.dumps(out))
"""


def venv_python(root: Path) -> Path:
    win = root / ".venv" / "Scripts" / "python.exe"
    return win if os.name == "nt" or win.exists() else root / ".venv" / "bin" / "python"


class Report:
    def __init__(self):
        self.rows: list[tuple[str, str, str]] = []

    def add(self, status: str, item: str, detail: str = "") -> None:
        self.rows.append((status, item, detail))
        print(f"{status} {item} {detail}".rstrip(), flush=True)

    @property
    def n_fail(self) -> int:
        return sum(1 for s, _, _ in self.rows if s == "FAIL")

    @property
    def n_warn(self) -> int:
        return sum(1 for s, _, _ in self.rows if s == "WARN")


def _run(cmd, cwd=None, timeout=120) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run(cmd, cwd=cwd, capture_output=True, encoding="utf-8",
                          errors="replace", env=env, timeout=timeout)


def check_python(rep: Report, py: Path, root: Path) -> dict | None:
    if not py.exists():
        rep.add("FAIL", "python", f"{py} not found (run setup_env.py)")
        rep.add("FAIL", "import", "skipped: no venv python")
        return None
    try:
        proc = _run([str(py), "-c", PROBE], cwd=str(root), timeout=600)
    except subprocess.TimeoutExpired:
        rep.add("FAIL", "python", "probe timed out")
        return None
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("PREFLIGHT_JSON ")), None)
    if line is None:
        rep.add("FAIL", "python", f"probe failed: {(proc.stderr or proc.stdout).strip()[-500:]}")
        return None
    info = json.loads(line[len("PREFLIGHT_JSON "):])
    v = info["version"]
    rep.add("PASS" if v == PY_VERSION else "FAIL", "python", f"{v} (need {PY_VERSION}) {py}")
    for m, st in info["imports"].items():
        rep.add("PASS" if st == "ok" else "FAIL", "import", m if st == "ok" else f"{m}: {st}")
    return info


def check_ffmpeg(rep: Report) -> None:
    ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ff:
        rep.add("FAIL", "ffmpeg", "ffmpeg not found on PATH")
        return
    rep.add("PASS" if fp else "FAIL", "ffprobe", fp or "ffprobe not found on PATH")
    proc = _run([ff, "-hide_banner", "-filters"])
    has_subs = any(len(ln.split()) >= 2 and ln.split()[1] == "subtitles" for ln in proc.stdout.splitlines())
    rep.add("PASS" if has_subs else "FAIL", "ffmpeg",
            f"subtitles filter (libass) {'found' if has_subs else 'missing'} {ff}")


def check_latex(rep: Report) -> None:
    for exe in ("latex", "dvisvgm"):
        path = shutil.which(exe)
        if not path:
            rep.add("WARN", "latex", f"{exe} not found on PATH (Tex formulas will fail; Text still works)")
            continue
        try:
            proc = _run([path, "--version"], timeout=60)
            first = (proc.stdout or proc.stderr).strip().splitlines()[:1]
            ok = proc.returncode == 0
            rep.add("PASS" if ok else "WARN", "latex", f"{exe}: {first[0] if first else path}")
        except (subprocess.TimeoutExpired, OSError) as e:
            rep.add("WARN", "latex", f"{exe} not runnable: {e}")


def check_fonts(rep: Report, info: dict | None) -> None:
    if not info or info.get("fonts") is None:
        why = (info or {}).get("fonts_error", "no font list (venv probe failed)")
        rep.add("FAIL", "font", f"manimpango: {why}")
        return
    fonts = set(info["fonts"])
    for f in FONTS_REQUIRED:
        rep.add("PASS" if f in fonts else "FAIL", "font", f)
    for f in FONTS_OPTIONAL:
        rep.add("PASS" if f in fonts else "WARN", "font", f if f in fonts else f"{f} missing (fallback font)")


def check_caption_font(rep: Report) -> None:
    """자막에 쓰는 바로 그 글꼴을 libass 가 고르는지 실제로 구워 확인한다."""
    ff = shutil.which("ffmpeg")
    if not ff:
        rep.add("FAIL", "capfont", "ffmpeg not found on PATH (cannot check caption font)")
        return
    line = "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,자막 글꼴 검사 Aa1\n"
    with tempfile.TemporaryDirectory() as td:
        Path(td, "probe.ass").write_text(_captions.ASS_HEADER + line, encoding="utf-8")
        try:
            proc = _run([ff, "-hide_banner", "-nostats", "-loglevel", "info",
                         "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=0.1",
                         "-vf", "subtitles=probe.ass", "-frames:v", "1", "-f", "null", "-"],
                        cwd=td, timeout=120)
        except (subprocess.TimeoutExpired, OSError) as e:
            rep.add("FAIL", "capfont", f"ffmpeg probe failed: {e}")
            return
    if proc.returncode != 0:
        rep.add("FAIL", "capfont", f"ffmpeg probe exit {proc.returncode}: {proc.stderr.strip()[-300:]}")
        return
    err, warns = _captions.check_fontselect(proc.stderr)
    if err:
        rep.add("FAIL", "capfont", err)
        return
    rep.add("PASS", "capfont", f"'{_captions.CAPTION_FONT}' -> {_captions.CAPTION_FONT_PS} (libass)")
    for w in warns:
        rep.add("WARN", "capfont", w.removeprefix("WARN ").strip())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="렌더 환경 사전 검사")
    ap.add_argument("--root", required=True, help="프로젝트 루트")
    ap.add_argument("--python", default=None, help="검사할 파이썬(기본: <root>/.venv 파이썬)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    root = Path(args.root).resolve()
    py = Path(args.python) if args.python else venv_python(root)
    rep = Report()
    info = check_python(rep, py, root)
    check_ffmpeg(rep)
    check_latex(rep)
    check_fonts(rep, info)
    check_caption_font(rep)
    cfg = root / "custom_config.yml"
    rep.add("PASS" if cfg.exists() else "WARN", "config", str(cfg) if cfg.exists() else f"{cfg} missing")
    print(f"SUMMARY fail={rep.n_fail} warn={rep.n_warn}")
    return 1 if rep.n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
