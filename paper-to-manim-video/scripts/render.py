"""Render an episode's Manim scenes: low-quality smoke first, then the final pass.

Two rules this script exists to enforce:

1. Never invoke `manim main.py` bare. With several scene classes in one file
   Manim stops and asks interactively, which hangs an automated run. Scene
   classes are discovered by parsing the AST and always passed explicitly.
2. Smoke before final. A 480p15 pass surfaces NameErrors, missing LaTeX
   packages and bad indices in seconds instead of after a 20-minute 1080p60
   render.

Segments render in parallel processes — the vanilla-ManimCE equivalent of the
--parallel flag in the imcommit fork, without needing the fork.

    python render.py --episode C:\\manimwork\\my-paper\\ep01_problem --quality ql
    python render.py --episode ... --quality qh --jobs 3 --json
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
from dataclasses import dataclass, asdict
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

QUALITY_DIR = {"ql": "480p15", "qm": "720p30", "qh": "1080p60", "qk": "2160p60"}

# Ordered: first match wins, so put the specific patterns above the generic ones.
ERROR_SIGNATURES: list[tuple[str, str, str]] = [
    # Must precede the generic `latex` rule: this is a concurrency race, not a
    # LaTeX failure. Parallel scenes share media/Tex/, and on Windows one worker
    # unlinking a .log another still holds raises WinError 32.
    (r"WinError 32|PermissionError.*Tex|다른 프로세스가 파일을 사용",
     "tex_race",
     "병렬 렌더가 공유 media/Tex/에서 경합했습니다. 해당 씬만 직렬로 재시도합니다."),
    (r"latex error|LaTeX Error|pdflatex.*not found|No such file.*\.tex",
     "latex",
     "LaTeX 실패. MiKTeX 설치와 PATH를 확인하고 "
     'initexmf --set-config-value "[MPM]AutoInstall=1" 을 켜세요.'),
    (r"Pango|font.*not found|Invalid font",
     "font",
     '한글 폰트 문제. Text(..., font="Malgun Gothic")로 명시했는지 확인하세요.'),
    (r"ModuleNotFoundError|ImportError",
     "import",
     "venv에 패키지가 없습니다. setup_env.py --force로 환경을 다시 만드세요."),
    (r"IndexError|KeyError",
     "index",
     "mobject 인덱싱 오류. RaeTex는 정수가 아니라 원문 문자열로 조각을 꺼냅니다."),
    (r"AttributeError.*method_names|SkewedAnimations",
     "fork_only",
     "포크 전용 API입니다. 순정 ManimCE에서는 SkewedAnimations를 쓸 수 없습니다."),
    (r"NameError|AttributeError|TypeError|SyntaxError",
     "code",
     "생성된 씬 코드의 버그입니다. 트레이스백 위치를 고치고 다시 스모크 렌더하세요."),
]


@dataclass
class SceneResult:
    scene: str
    ok: bool
    seconds: float
    mp4: str | None = None
    error_kind: str | None = None
    remedy: str | None = None
    tail: str = ""


def discover_scenes(main_py: Path) -> list[str]:
    """Scene classes in source order, without importing the module."""
    tree = ast.parse(main_py.read_text(encoding="utf-8"), filename=str(main_py))
    scenes = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {b.id if isinstance(b, ast.Name) else getattr(b, "attr", "") for b in node.bases}
        if bases & {"Scene2D", "Scene3D", "Scene", "MovingCameraScene", "ThreeDScene"}:
            scenes.append(node.name)
    return scenes


def classify(output: str) -> tuple[str | None, str | None]:
    for pattern, kind, remedy in ERROR_SIGNATURES:
        if re.search(pattern, output, re.IGNORECASE):
            return kind, remedy
    return None, None


def venv_python(episode: Path) -> Path:
    """The project venv lives at the project root, one level above the episode."""
    for base in (episode, episode.parent, episode.parent.parent):
        for cand in (base / ".venv" / "Scripts" / "python.exe", base / ".venv" / "bin" / "python"):
            if cand.exists():
                return cand
    return Path(sys.executable)


def render_one(episode: Path, python: Path, scene: str, quality: str, env: dict) -> SceneResult:
    started = time.time()
    cmd = [str(python), "-m", "manim", f"-{quality}", "main.py", scene]
    proc = subprocess.run(cmd, cwd=episode, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)
    elapsed = round(time.time() - started, 1)
    combined = (proc.stdout or "") + (proc.stderr or "")

    mp4 = episode / "media" / "videos" / "main" / QUALITY_DIR[quality] / f"{scene}.mp4"
    if proc.returncode == 0 and mp4.exists():
        return SceneResult(scene, True, elapsed, str(mp4))

    kind, remedy = classify(combined)
    tail = "\n".join(combined.strip().splitlines()[-20:])
    return SceneResult(scene, False, elapsed, None, kind or "unknown",
                       remedy or "출력 전문을 확인하세요.", tail)


def main() -> int:
    ap = argparse.ArgumentParser(description="에피소드 Manim 렌더 (스모크 → 본번)")
    ap.add_argument("--episode", required=True, help="main.py가 있는 에피소드 폴더")
    ap.add_argument("--quality", default="ql", choices=list(QUALITY_DIR),
                    help="ql=480p15 스모크, qh=1080p60 본번")
    ap.add_argument("--scenes", nargs="*", help="렌더할 씬 클래스 (기본: 전부)")
    ap.add_argument("--jobs", type=int, default=1,
                    help="동시 렌더 프로세스 수. 본번에서 3~4 권장")
    ap.add_argument("--latex-bin", help="PATH에 없을 때 MiKTeX bin 디렉터리를 앞에 붙임")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    episode = Path(args.episode).resolve()
    main_py = episode / "main.py"
    if not main_py.is_file():
        raise SystemExit(f"main.py를 찾을 수 없습니다: {main_py}")

    scenes = args.scenes or discover_scenes(main_py)
    if not scenes:
        raise SystemExit(f"{main_py}에 Scene 클래스가 없습니다.")

    env = os.environ.copy()
    if args.latex_bin:
        env["PATH"] = f"{args.latex_bin}{os.pathsep}{env.get('PATH', '')}"

    python = venv_python(episode)
    print(f"[render] {episode.name} — {len(scenes)} scenes @ -{args.quality} "
          f"(jobs={args.jobs})", flush=True)
    print(f"[render] python: {python}", flush=True)

    started = time.time()
    if args.jobs > 1:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(
                lambda s: render_one(episode, python, s, args.quality, env), scenes))
    else:
        results = [render_one(episode, python, s, args.quality, env) for s in scenes]

    # Scenes that lost the media/Tex/ race get one serial retry. By now the other
    # workers have exited and the LaTeX output they compiled is cached, so the
    # retry is both uncontended and fast.
    racers = [r for r in results if r.error_kind == "tex_race"]
    if racers:
        print(f"[render] {len(racers)} scene(s) hit the LaTeX race — retrying serially",
              flush=True)
        for i, r in enumerate(results):
            if r.error_kind == "tex_race":
                results[i] = render_one(episode, python, r.scene, args.quality, env)

    total = round(time.time() - started, 1)

    for r in results:
        mark = "OK  " if r.ok else "FAIL"
        print(f"  {mark} {r.scene:<20} {r.seconds:>6.1f}s  {r.mp4 or r.error_kind}", flush=True)
        if not r.ok:
            print(f"       → {r.remedy}", flush=True)
            for line in r.tail.splitlines()[-8:]:
                print(f"       | {line}", flush=True)

    failed = [r for r in results if not r.ok]
    print(f"[render] {len(results) - len(failed)}/{len(results)} succeeded in {total}s", flush=True)

    if args.json:
        print(json.dumps({
            "episode": str(episode), "quality": args.quality, "elapsed_sec": total,
            "failed": len(failed), "results": [asdict(r) for r in results],
        }, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
