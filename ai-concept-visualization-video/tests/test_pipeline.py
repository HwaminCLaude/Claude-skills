"""Task 3: scaffold -> render -> assemble 파이프라인 테스트.

실제 ManimGL 렌더(-w -l)와 ffmpeg 굽기를 돌린다. 몇 분이 걸릴 수 있다.
렌더 환경은 DEVPY(기본: pytest를 돌리는 파이썬, 바꾸려면 VIZ_TEST_PYTHON)를 render.py --python 으로 넘겨 쓴다.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

SK = Path(__file__).resolve().parents[1]
SCRIPTS = SK / "scripts"
DEVPY = Path(os.environ.get("VIZ_TEST_PYTHON") or sys.executable)
pytestmark = pytest.mark.skipif(not DEVPY.is_file(), reason=f"렌더용 파이썬 없음: {DEVPY}")

TIMEOUT = 900


def _run(args, cwd=None) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [str(DEVPY), *[str(a) for a in args]],
        cwd=str(cwd) if cwd else None,
        capture_output=True, encoding="utf-8", errors="replace",
        env=env, timeout=TIMEOUT,
    )


def _msg(proc) -> str:
    return f"exit={proc.returncode}\nSTDOUT:\n{proc.stdout[-4000:]}\nSTDERR:\n{proc.stderr[-4000:]}"


def _scaffold(root: Path, episode: str = "ep", *extra) -> subprocess.CompletedProcess:
    return _run([SCRIPTS / "scaffold.py", "--root", root, "--episode", episode, *extra])


def _duration(mp4: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(mp4)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _has_audio(mp4: Path) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(mp4)],
        capture_output=True, text=True, check=True,
    )
    return bool(out.stdout.strip())


def _gray_frame(mp4: Path, t: float) -> np.ndarray:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(mp4)],
        capture_output=True, text=True, check=True,
    )
    w, h = (int(x) for x in probe.stdout.strip().split(",")[:2])
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", str(mp4), "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.uint8)[: w * h].reshape(h, w)


# 파일 정의 순서는 B, A. shots.json 순서는 A, B.
TWO_SCENE_SRC = '''from vizkit import *


class B(CueScene):
    def construct(self):
        with self.cue("b1"):
            self.play(FadeIn(Square(1.0).set_fill(OBJ[1], 0.8).set_stroke(width=0)), run_time=0.5)


class A(CueScene):
    def construct(self):
        with self.cue("a1"):
            self.play(FadeIn(Square(1.0).set_fill(OBJ[0], 0.8).set_stroke(width=0)), run_time=0.5)
'''

TWO_SCENE_SHOTS = {
    "episode": "ep",
    "mode": "silent",
    "scenes": [
        {"name": "A", "cues": [
            {"id": "a1", "t": "먼저 나오는 장면", "say": None, "key": "먼저",
             "rel": "hook", "move": "fade", "hold": False}]},
        {"name": "B", "cues": [
            {"id": "b1", "t": "그다음 장면", "say": None, "key": None,
             "rel": "next", "move": "fade", "hold": False}]},
    ],
}

TWO_SCENE_TIMING = {"a1": {"scene": "A", "dur": 1.5}, "b1": {"scene": "B", "dur": 1.5}}


def _make_two_scene_project(root: Path) -> Path:
    proc = _scaffold(root, "ep", "--mode", "silent")
    assert proc.returncode == 0, _msg(proc)
    ep = root / "ep"
    (ep / "main.py").write_text(TWO_SCENE_SRC, encoding="utf-8")
    (ep / "shots.json").write_text(json.dumps(TWO_SCENE_SHOTS, ensure_ascii=False), encoding="utf-8")
    (ep / "timing.json").write_text(json.dumps(TWO_SCENE_TIMING), encoding="utf-8")
    return ep


def _render(ep: Path, *extra) -> subprocess.CompletedProcess:
    return _run([SCRIPTS / "render.py", "--episode", ep, "--quality", "l",
                 "--python", DEVPY, *extra])


def _assemble(ep: Path) -> subprocess.CompletedProcess:
    return _run([SCRIPTS / "assemble.py", "--episode", ep, "--silent"])


def _check_render_and_assemble(ep: Path):
    proc = _render(ep)
    assert proc.returncode == 0, _msg(proc)
    assert (ep / "videos" / "A.mp4").exists()
    assert (ep / "videos" / "B.mp4").exists()
    assert "CUE_OVERRUN" not in proc.stdout

    proc = _assemble(ep)
    assert proc.returncode == 0, _msg(proc)

    durs = json.loads((ep / "scene_durs.json").read_text(encoding="utf-8"))
    assert list(durs.keys()) == ["A", "B"]

    final = ep / "ep_FINAL.mp4"
    assert final.exists(), _msg(proc)
    assert abs(_duration(final) - 3.0) <= 0.15
    assert not _has_audio(final)

    ass = (ep / "captions.ass").read_text(encoding="utf-8")
    assert "나오는 장면" in ass and "그다음 장면" in ass

    # 1.0초(장면 A, 큐 a1) 프레임의 아래 15% 띠에 자막 글자(밝은 화소)가 있다
    g = _gray_frame(final, 1.0)
    band = g[int(g.shape[0] * 0.85):, :]
    assert int((band > 150).sum()) > 30, int(band.max())
    return final


def test_scaffold_creates_files(tmp_path):
    root = tmp_path / "proj"
    proc = _scaffold(root, "ep")
    assert proc.returncode == 0, _msg(proc)
    for rel in ["pyproject.toml", "custom_config.yml", "ep/main.py", "ep/shots.json", "ep/vizkit.py"]:
        assert (root / rel).exists(), rel

    py = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "{{name}}" not in py
    shots = json.loads((root / "ep" / "shots.json").read_text(encoding="utf-8"))
    assert shots["episode"] == "ep"
    assert shots["mode"] == "tts"  # --mode 없이 부르면 스킬 기본값
    assert shots["scenes"] == []
    assert "from vizkit import *" in (root / "ep" / "main.py").read_text(encoding="utf-8")

    # 이미 있는 파일은 건너뛴다
    (root / "ep" / "main.py").write_text("# mine\n", encoding="utf-8")
    proc = _scaffold(root, "ep")
    assert proc.returncode == 0, _msg(proc)
    assert (root / "ep" / "main.py").read_text(encoding="utf-8") == "# mine\n"


def test_scaffold_mode_option(tmp_path):
    root = tmp_path / "proj"
    proc = _scaffold(root, "quiet", "--mode", "silent")
    assert proc.returncode == 0, _msg(proc)
    shots_path = root / "quiet" / "shots.json"
    assert json.loads(shots_path.read_text(encoding="utf-8"))["mode"] == "silent"

    proc = _scaffold(root, "voiced", "--mode", "tts")
    assert proc.returncode == 0, _msg(proc)
    assert json.loads((root / "voiced" / "shots.json").read_text(encoding="utf-8"))["mode"] == "tts"

    # 이미 있는 shots.json은 다른 --mode로 다시 불러도 바꾸지 않는다
    before = shots_path.read_text(encoding="utf-8")
    proc = _scaffold(root, "quiet", "--mode", "tts")
    assert proc.returncode == 0, _msg(proc)
    assert shots_path.read_text(encoding="utf-8") == before

    # 모르는 모드는 거부하고 에피소드를 만들지 않는다
    proc = _scaffold(root, "bad", "--mode", "voice")
    assert proc.returncode != 0, _msg(proc)
    assert not (root / "bad").exists()


def test_scaffold_function_mode(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("viz_scaffold", SCRIPTS / "scaffold.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.DEFAULT_MODE == "tts"
    mod.scaffold(tmp_path / "p", "ep")
    assert json.loads((tmp_path / "p" / "ep" / "shots.json").read_text(encoding="utf-8"))["mode"] == "tts"
    mod.scaffold(tmp_path / "p", "ep2", "silent")
    assert json.loads((tmp_path / "p" / "ep2" / "shots.json").read_text(encoding="utf-8"))["mode"] == "silent"
    try:
        mod.scaffold(tmp_path / "q", "ep", "voice")
    except ValueError:
        pass
    else:
        raise AssertionError("scaffold(mode='voice')가 ValueError를 내지 않았다")
    assert not (tmp_path / "q").exists()


def test_render_and_assemble_order(tmp_path):
    ep = _make_two_scene_project(tmp_path / "proj")
    _check_render_and_assemble(ep)


def test_assemble_path_with_space(tmp_path):
    ep = _make_two_scene_project(tmp_path / "with space" / "proj")
    assert " " in str(ep)
    _check_render_and_assemble(ep)


BROKEN_SRC = '''from vizkit import *


class A(CueScene):
    def construct(self):
        with self.cue("a1"):
            self.play(FadeIn(not_defined_anywhere), run_time=0.5)
'''


def test_render_removes_stale_and_fails_loudly(tmp_path):
    root = tmp_path / "proj"
    proc = _scaffold(root, "ep", "--mode", "silent")
    assert proc.returncode == 0, _msg(proc)
    ep = root / "ep"
    (ep / "main.py").write_text(BROKEN_SRC, encoding="utf-8")
    shots = {"episode": "ep", "mode": "silent", "scenes": [
        {"name": "A", "cues": [{"id": "a1", "t": "깨진 장면", "say": None, "key": None,
                                 "rel": "hook", "move": "fade", "hold": False}]}]}
    (ep / "shots.json").write_text(json.dumps(shots, ensure_ascii=False), encoding="utf-8")
    (ep / "timing.json").write_text(json.dumps({"a1": {"scene": "A", "dur": 1.5}}), encoding="utf-8")
    stale = ep / "videos" / "A.mp4"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_bytes(b"old render")

    proc = _render(ep)
    assert proc.returncode == 1, _msg(proc)
    assert not stale.exists()
    assert "kind=other" in proc.stdout, _msg(proc)

    # 옛 파일로 이어 붙이지 않는다
    proc = _assemble(ep)
    assert proc.returncode != 0, _msg(proc)
    assert not (ep / "ep_FINAL.mp4").exists()
