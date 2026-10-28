"""에피소드 씬을 ManimGL로 렌더한다.

    python render.py --episode <dir> --quality l|hd [--jobs N] [--scenes A,B] [--python <exe>]

- main.py 를 AST로 읽어 CueScene(또는 Scene2D) 하위 클래스를 찾는다(같은 파일 안의 간접 상속 포함).
- 씬마다 `<python> -m manimlib main.py <S> -w (-l|--hd)` 를 에피소드 폴더에서 실행한다.
  - <python> 기본값: <proj>/.venv/Scripts/python.exe (proj = 에피소드 폴더의 부모)
  - 에피소드 폴더에 custom_config.yml 이 없으면 <proj>/custom_config.yml 을 --config_file 로 넘긴다.
  - 렌더 전에 videos/<S>.mp4, videos/<S>_temp.mp4, cuelog/<S>.json 을 지운다.
    렌더가 실패하면 남은 videos/<S>*.mp4 도 지운다(옛 파일로 이어 붙이지 않게).
- 실패한 씬은 stderr 를 latex, font, attribute, import, other 로 분류해 보고한다.
- stdout 의 CUE_OVERRUN 줄(0.3초 넘는 큐 초과)을 모아 WARN 으로 보고한다.
- 렌더가 끝난 씬의 cuelog/<S>.json 을 읽어 plays == 0 인 큐(박자 없는 큐, 설계 A5)를
  WARN CUE_NO_BEAT 로 보고한다. plays 키가 없는 옛 cuelog 는 판정하지 않는다.
- 씬마다 전체 로그를 <ep>/logs/render_<S>.log 에 남긴다.
- 하나라도 실패하면 exit 1.

보고 줄 형식:
    OK   <S> <렌더초>s video=<길이>s
    FAIL <S> kind=<kind> <마지막 오류 줄>
    WARN CUE_OVERRUN <S> <cue_id> <초과초>
    WARN CUE_NO_BEAT <S> <cue_id>
    SUMMARY ok=<n> fail=<n> overrun=<n> no_beat=<n>
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCENE_BASES = {"CueScene", "Scene2D"}
QUALITY_FLAGS = {"l": "-l", "hd": "--hd"}
KINDS = ("latex", "font", "attribute", "import", "other")

_EXC_LINE = re.compile(r"^\s*(?:[\w.]+\.)?(\w*(?:Error|Exception|Exit))\b[:\s]?(.*)$")
_OVERRUN = re.compile(r"CUE_OVERRUN\s+(\S+)\s+([0-9.eE+-]+)")


# ---------------------------------------------------------------------------
# 씬 찾기
# ---------------------------------------------------------------------------


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def find_scenes(main_py: Path) -> list[str]:
    """CueScene/Scene2D 를 (같은 파일 안에서 간접으로라도) 상속한 클래스 이름, 파일 정의 순."""
    tree = ast.parse(main_py.read_text(encoding="utf-8"), filename=str(main_py))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    scene_like = set(SCENE_BASES)
    changed = True
    while changed:
        changed = False
        for c in classes:
            if c.name in scene_like:
                continue
            if any(_base_name(b) in scene_like for b in c.bases):
                scene_like.add(c.name)
                changed = True
    return [c.name for c in classes if c.name in scene_like and c.name not in SCENE_BASES]


def order_scenes(found: list[str], ep: Path) -> list[str]:
    """shots.json 씬 순서를 먼저, 나머지는 파일 순서로."""
    shots_path = ep / "shots.json"
    if not shots_path.exists():
        return found
    shots = json.loads(shots_path.read_text(encoding="utf-8"))
    order = [s["name"] for s in shots.get("scenes", [])]
    head = [n for n in order if n in found]
    return head + [n for n in found if n not in head]


# ---------------------------------------------------------------------------
# 오류 분류
# ---------------------------------------------------------------------------


def last_error_line(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    for ln in reversed(lines):
        if _EXC_LINE.match(ln):
            return ln.strip()
    return lines[-1].strip() if lines else ""


def classify(stderr: str, stdout: str = "") -> str:
    """실패 로그 → latex | font | attribute | import | other.

    마지막 예외 줄(과 바로 앞 몇 줄)만 본다. 일반 로그에 섞인 낱말로 잘못 분류하지 않게.
    """
    text = stderr if stderr.strip() else stdout
    lines = [ln for ln in text.splitlines() if ln.strip()]
    exc_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if _EXC_LINE.match(lines[i]):
            exc_idx = i
            break
    if exc_idx is None:
        tail = "\n".join(lines[-5:])
        exc = ""
    else:
        tail = "\n".join(lines[max(0, exc_idx - 4): exc_idx + 1])
        exc = _EXC_LINE.match(lines[exc_idx]).group(1)

    if exc in ("ModuleNotFoundError", "ImportError"):
        return "import"
    if "latex" in exc.lower() or re.search(r"latex|dvisvgm|\.tex\b|xelatex", tail, re.I):
        return "latex"
    if re.search(r"\bfonts?\b|pango|manimpango", tail, re.I):
        return "font"
    if exc == "AttributeError":
        return "attribute"
    return "other"


def parse_overruns(stdout: str) -> list[tuple[str, float]]:
    out = []
    for m in _OVERRUN.finditer(stdout):
        try:
            out.append((m.group(1), float(m.group(2))))
        except ValueError:
            out.append((m.group(1), float("nan")))
    return out


def no_beat_cues(cuelog) -> list[str]:
    """cuelog(<ep>/cuelog/<S>.json 내용 또는 큐 목록) → plays == 0 인 큐 id 목록(순서 유지).

    plays 키가 없는 항목(옛 키트가 쓴 cuelog)은 판정하지 않는다.
    """
    if not cuelog:
        return []
    entries = cuelog.get("cues", []) if isinstance(cuelog, dict) else cuelog
    out = []
    for e in entries:
        plays = e.get("plays") if isinstance(e, dict) else None
        if plays is None:
            continue
        try:
            if int(plays) == 0:
                out.append(str(e.get("id")))
        except (TypeError, ValueError):
            continue
    return out


def read_cuelog(ep: Path, scene: str) -> dict | None:
    p = ep / "cuelog" / f"{scene}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 렌더
# ---------------------------------------------------------------------------


def default_python(ep: Path) -> Path:
    proj = ep.resolve().parent
    win = proj / ".venv" / "Scripts" / "python.exe"
    return win if os.name == "nt" or win.exists() else proj / ".venv" / "bin" / "python"


def _remove_outputs(ep: Path, scene: str) -> None:
    vids = ep / "videos"
    for p in [vids / f"{scene}.mp4", vids / f"{scene}_temp.mp4", ep / "cuelog" / f"{scene}.json"]:
        try:
            p.unlink()
        except FileNotFoundError:
            pass


def _probe_duration(mp4: Path) -> float | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(mp4)],
            capture_output=True, text=True, timeout=60,
        )
        return float(out.stdout.strip())
    except Exception:
        return None


def render_scene(ep: Path, scene: str, python: Path, quality: str,
                 config_file: Path | None, timeout: float | None) -> dict:
    _remove_outputs(ep, scene)
    cmd = [str(python), "-m", "manimlib", "main.py", scene, "-w", QUALITY_FLAGS[quality]]
    if config_file is not None:
        cmd += ["--config_file", str(config_file)]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(ep), capture_output=True, encoding="utf-8",
                              errors="replace", env=env, timeout=timeout)
        rc, out, err = proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as e:
        rc = -1
        out = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "replace")
        err = (e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode("utf-8", "replace"))
        err += f"\nTimeoutError: render exceeded {timeout}s"
    secs = time.time() - t0

    logs = ep / "logs"
    logs.mkdir(exist_ok=True)
    (logs / f"render_{scene}.log").write_text(
        f"$ {' '.join(cmd)}\n# exit={rc} secs={secs:.1f}\n\n--- STDOUT ---\n{out}\n--- STDERR ---\n{err}",
        encoding="utf-8",
    )

    mp4 = ep / "videos" / f"{scene}.mp4"
    res = {"scene": scene, "rc": rc, "secs": secs, "overruns": parse_overruns(out)}
    if rc == 0 and mp4.exists():
        res.update(ok=True, duration=_probe_duration(mp4),
                   no_beat=no_beat_cues(read_cuelog(ep, scene)))
    else:
        if rc == 0:
            kind, line = "other", f"exit 0 but {mp4.relative_to(ep)} was not written"
        else:
            kind, line = classify(err, out), last_error_line(err or out)
        _remove_outputs(ep, scene)
        res.update(ok=False, kind=kind, error=line)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="에피소드 씬 렌더(ManimGL -w)")
    ap.add_argument("--episode", required=True)
    ap.add_argument("--quality", required=True, choices=sorted(QUALITY_FLAGS))
    ap.add_argument("--jobs", type=int, default=2, help="동시에 돌릴 렌더 수(기본 2: GPU 컨텍스트 경합 방지)")
    ap.add_argument("--scenes", default=None, help="쉼표로 구분한 씬 이름(기본: 전부)")
    ap.add_argument("--python", default=None, help="렌더 파이썬(기본: <proj>/.venv/Scripts/python.exe)")
    ap.add_argument("--timeout", type=float, default=None, help="씬 하나당 제한 시간(초)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    ep = Path(args.episode).resolve()
    main_py = ep / "main.py"
    if not main_py.exists():
        print(f"FAIL setup kind=other {main_py} not found")
        return 1
    if not (ep / "timing.json").exists():
        print(f"FAIL setup kind=other {ep / 'timing.json'} not found (run cues.py --episode first)")
        return 1
    python = Path(args.python) if args.python else default_python(ep)
    if not python.exists():
        print(f"FAIL setup kind=other python not found: {python} (run setup_env.py or pass --python)")
        return 1

    try:
        found = find_scenes(main_py)
    except SyntaxError as e:
        print(f"FAIL main.py kind=other SyntaxError: {e}")
        return 1
    scenes = order_scenes(found, ep)
    if args.scenes:
        wanted = [s.strip() for s in args.scenes.split(",") if s.strip()]
        missing = [s for s in wanted if s not in found]
        if missing:
            print(f"FAIL setup kind=other scenes not found in main.py: {','.join(missing)}")
            return 1
        scenes = wanted
    if not scenes:
        print("FAIL setup kind=other no CueScene/Scene2D subclasses in main.py")
        return 1

    shots_path = ep / "shots.json"
    if shots_path.exists() and not args.scenes:
        shots = json.loads(shots_path.read_text(encoding="utf-8"))
        for s in shots.get("scenes", []):
            if s["name"] not in found:
                print(f"WARN missing-scene {s['name']} is in shots.json but not in main.py")

    config_file = None
    if not (ep / "custom_config.yml").exists() and (ep.parent / "custom_config.yml").exists():
        config_file = ep.parent / "custom_config.yml"

    print(f"render {len(scenes)} scene(s) quality={args.quality} jobs={args.jobs} python={python}", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futs = [pool.submit(render_scene, ep, s, python, args.quality, config_file, args.timeout)
                for s in scenes]
        results = []
        for f in futs:
            r = f.result()
            results.append(r)
            if r["ok"]:
                d = r.get("duration")
                print(f"OK   {r['scene']} {r['secs']:.1f}s video={d:.2f}s" if d is not None
                      else f"OK   {r['scene']} {r['secs']:.1f}s", flush=True)
            else:
                print(f"FAIL {r['scene']} kind={r['kind']} {r['error']}", flush=True)

    n_over = 0
    for r in results:
        for cue_id, sec in r["overruns"]:
            n_over += 1
            print(f"WARN CUE_OVERRUN {r['scene']} {cue_id} {sec:.3f}")
    n_no_beat = 0
    for r in results:
        for cue_id in r.get("no_beat", []):
            n_no_beat += 1
            print(f"WARN CUE_NO_BEAT {r['scene']} {cue_id}")
    n_fail = sum(1 for r in results if not r["ok"])
    print(f"SUMMARY ok={len(results) - n_fail} fail={n_fail} overrun={n_over} "
          f"no_beat={n_no_beat} logs={ep / 'logs'}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
