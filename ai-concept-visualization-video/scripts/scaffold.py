"""프로젝트와 에피소드 폴더를 만든다.

    python scaffold.py --root <proj> --episode <name> [--mode tts|silent]

- 프로젝트 루트: assets/project_template 의 pyproject.toml({{name}} 치환), custom_config.yml
- 에피소드 폴더 <proj>/<name>/:
  - main.py   (main_template.py 시작 틀)
  - shots.json(빈 스키마: {"episode": <name>, "mode": <mode>, "scenes": []})
    mode 기본값은 "tts"(스킬 기본값: edge-tts 음성 + 박힌 자막). 무음 영상이면 --mode silent.
  - vizkit.py (씬이 같은 폴더에서 `from vizkit import *` 한다)
- 이미 있는 파일은 건너뛴다(덮어쓰지 않는다).

렌더는 에피소드 폴더를 cwd로 돈다. manimgl은 cwd의 custom_config.yml만 읽으므로
render.py가 루트의 custom_config.yml을 --config_file로 넘긴다.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

MODES = ("tts", "silent")
DEFAULT_MODE = "tts"

SK = Path(__file__).resolve().parent.parent
TEMPLATE = SK / "assets" / "project_template"


def project_name(root: Path) -> str:
    """pyproject [project].name 으로 쓸 수 있는 이름(PEP 508: 영숫자와 -_.)."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", root.resolve().name).strip("-._").lower()
    return name or "concept-video"


def _write_new(path: Path, text: str, created: list, skipped: list) -> None:
    if path.exists():
        skipped.append(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    created.append(path)


def _copy_new(src: Path, dst: Path, created: list, skipped: list) -> None:
    if dst.exists():
        skipped.append(dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    created.append(dst)


def scaffold(root: Path, episode: str, mode: str = DEFAULT_MODE) -> tuple[list[Path], list[Path]]:
    if mode not in MODES:
        raise ValueError(f"mode는 {MODES} 중 하나다: {mode!r}")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", episode):
        raise ValueError(f"episode 이름은 ASCII 영숫자와 _.- 만 쓴다: {episode!r}")
    root = Path(root)
    ep = root / episode
    created: list[Path] = []
    skipped: list[Path] = []
    root.mkdir(parents=True, exist_ok=True)

    py = (TEMPLATE / "pyproject.toml").read_text(encoding="utf-8")
    _write_new(root / "pyproject.toml", py.replace("{{name}}", project_name(root)), created, skipped)
    _copy_new(TEMPLATE / "custom_config.yml", root / "custom_config.yml", created, skipped)

    ep.mkdir(parents=True, exist_ok=True)
    _copy_new(TEMPLATE / "main_template.py", ep / "main.py", created, skipped)
    _copy_new(TEMPLATE / "vizkit.py", ep / "vizkit.py", created, skipped)
    shots = {"episode": episode, "mode": mode, "scenes": []}
    _write_new(ep / "shots.json", json.dumps(shots, ensure_ascii=False, indent=1) + "\n", created, skipped)
    return created, skipped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ai-concept-visualization-video 프로젝트·에피소드 만들기")
    ap.add_argument("--root", required=True, help="프로젝트 루트(ASCII 경로 권장)")
    ap.add_argument("--episode", required=True, help="에피소드 폴더 이름")
    ap.add_argument("--mode", choices=MODES, default=DEFAULT_MODE,
                    help="shots.json의 mode(기본 tts: 음성 + 자막, silent: 무음 + 자막). "
                         "shots.json이 이미 있으면 건드리지 않는다")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    try:
        created, skipped = scaffold(Path(args.root), args.episode, args.mode)
    except ValueError as e:
        print(f"FAIL {e}")
        return 1
    for p in created:
        print(f"created {p}")
    for p in skipped:
        print(f"skipped {p} (already exists)")
    if any(ord(c) > 127 for c in str(Path(args.root).resolve())):
        print("WARN root path has non-ASCII characters; an ASCII path is safer for manimgl/latex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
