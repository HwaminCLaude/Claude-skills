"""Task 1: vizkit.py 키트와 CueScene 렌더 테스트.

실제 ManimGL 렌더(-w -l)를 돌린다. 한 테스트에 수십 초가 걸릴 수 있다.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SK = Path(__file__).resolve().parents[1]
TEMPLATE = SK / "assets" / "project_template"
VIZKIT = TEMPLATE / "vizkit.py"
CONFIG = TEMPLATE / "custom_config.yml"
# 렌더용 파이썬: 기본은 pytest를 돌리는 파이썬(프로젝트 venv). 다른 venv를 쓰려면 VIZ_TEST_PYTHON.
DEVPY = Path(os.environ.get("VIZ_TEST_PYTHON") or sys.executable)
pytestmark = pytest.mark.skipif(not DEVPY.is_file(), reason=f"렌더용 파이썬 없음: {DEVPY}")

RENDER_TIMEOUT = 600


def _make_episode(tmp: Path, main_src: str, timing: dict) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    shutil.copy(VIZKIT, tmp / "vizkit.py")
    shutil.copy(CONFIG, tmp / "custom_config.yml")
    (tmp / "timing.json").write_text(json.dumps(timing, ensure_ascii=False), encoding="utf-8")
    (tmp / "main.py").write_text(main_src, encoding="utf-8")
    return tmp


def _render(ep: Path, scene: str, *flags: str) -> subprocess.CompletedProcess:
    """기본은 `-w -l`(480p 영상). flags를 주면 `-w` 뒤에 그것을 쓴다(예: "-s", "--hd")."""
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [str(DEVPY), "-m", "manimlib", "main.py", scene, "-w", *(flags or ("-l",))],
        cwd=str(ep),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=RENDER_TIMEOUT,
    )


def _duration(mp4: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(mp4)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _fail_msg(proc: subprocess.CompletedProcess) -> str:
    return f"exit={proc.returncode}\nSTDOUT:\n{proc.stdout[-3000:]}\nSTDERR:\n{proc.stderr[-3000:]}"


def test_config_ascii_and_imports_without_utf8_mode(tmp_path):
    """custom_config.yml must load under the default locale encoding (cp949, utf8_mode 0)."""
    CONFIG.read_bytes().decode("ascii")
    ep = tmp_path / "ep"
    ep.mkdir()
    shutil.copy(CONFIG, ep / "custom_config.yml")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env["PYTHONUTF8"] = "0"
    proc = subprocess.run(
        [str(DEVPY), "-c", "import sys, manimlib; print(sys.flags.utf8_mode)"],
        cwd=str(ep), capture_output=True, text=True, errors="replace",
        env=env, timeout=RENDER_TIMEOUT,
    )
    assert proc.returncode == 0, _fail_msg(proc)
    assert proc.stdout.strip().endswith("0"), _fail_msg(proc)


TIMING_SRC = '''from vizkit import *


class T(CueScene):
    def construct(self):
        with self.cue("c1"):
            a = label("가나")
            self.play(FadeIn(a), run_time=0.5)
        with self.cue("c2"):
            self.play(FadeIn(tint(a, BLUE)), run_time=1.0)
'''


def test_cue_scene_timing(tmp_path):
    ep = _make_episode(
        tmp_path / "ep",
        TIMING_SRC,
        {"c1": {"scene": "T", "dur": 1.5}, "c2": {"scene": "T", "dur": 2.0}},
    )
    proc = _render(ep, "T")
    assert proc.returncode == 0, _fail_msg(proc)

    mp4 = ep / "videos" / "T.mp4"
    assert mp4.exists(), _fail_msg(proc)
    assert abs(_duration(mp4) - 3.5) <= 0.1

    log = json.loads((ep / "cuelog" / "T.json").read_text(encoding="utf-8"))
    assert log["scene"] == "T"
    ids = [c["id"] for c in log["cues"]]
    assert ids == ["c1", "c2"]
    starts = [c["start"] for c in log["cues"]]
    for got, want in zip(starts, [0.0, 1.5]):
        assert abs(got - want) <= 0.05, starts
    for c in log["cues"]:
        assert set(c) >= {"id", "start", "dur", "elapsed", "plays"}
    assert [c["plays"] for c in log["cues"]] == [1, 1]
    assert "CUE_OVERRUN" not in proc.stdout


OVERRUN_SRC = '''from vizkit import *


class T(CueScene):
    def construct(self):
        with self.cue("c1"):
            self.play(FadeIn(label("길다")), run_time=1.5)
'''


def test_cue_overrun_reported(tmp_path):
    ep = _make_episode(tmp_path / "ep", OVERRUN_SRC, {"c1": {"scene": "T", "dur": 0.5}})
    proc = _render(ep, "T")
    assert proc.returncode == 0, _fail_msg(proc)
    assert "CUE_OVERRUN c1" in proc.stdout, _fail_msg(proc)

    log = json.loads((ep / "cuelog" / "T.json").read_text(encoding="utf-8"))
    c1 = log["cues"][0]
    assert c1["dur"] == 0.5
    assert abs(c1["elapsed"] - 1.5) <= 0.05


TILT_SRC = '''from vizkit import *


class T(CueScene):
    def construct(self):
        with self.cue("c1"):
            board = VGroup(*[Square(0.8).set_fill(OBJ[i], 0.7).set_stroke(width=0)
                             for i in range(4)]).arrange(RIGHT, buff=0.25)
            self.play(FadeIn(board), run_time=0.5)
        with self.cue("c2"):
            self.tilt(ORIGIN, 60)
            self.play(stand_up(board[1].copy()).animate.shift(OUT * 0.5), run_time=0.5)
            self.untilt()
'''


def test_tilt_untilt_renders(tmp_path):
    ep = _make_episode(
        tmp_path / "ep",
        TILT_SRC,
        {"c1": {"scene": "T", "dur": 1.2}, "c2": {"scene": "T", "dur": 3.0}},
    )
    proc = _render(ep, "T")
    assert proc.returncode == 0, _fail_msg(proc)
    assert (ep / "videos" / "T.mp4").exists()


# ---------------------------------------------------------------------------
# 글자 크기 보정: 1080p 정지 화면에서 잉크 높이를 잰다(설계 §5.4 목표 ±8%)
# ---------------------------------------------------------------------------

INK_TARGET = {"S": 34, "M": 41, "T": 44, "L": 54, "XL": 68}  # 1080p 한글 잉크(px)
TEX_CAP_TARGET = 48  # tex("BA", size="L") 대문자 높이(px). L 한글 잉크의 약 0.9배
INK_TOL = 0.08

INK_SRC = '''from vizkit import *


class Ink(CueScene):
    def construct(self):
        rows = VGroup(*[label("학습합니다", s) for s in ("S", "M", "T", "L", "XL")])
        rows.add(tex("BA", size="L"))
        rows.arrange(DOWN, buff=0.5)
        self.add(rows)
'''


def _ink_bands(png: Path, thresh: int = 100, gap: int = 12) -> list:
    """밝은 픽셀이 있는 행을 띠로 묶어 띠마다 높이(px)를 위에서부터 돌려준다."""
    import numpy as np
    from PIL import Image

    a = np.asarray(Image.open(png).convert("L"))
    assert a.shape == (1080, 1920), a.shape
    rows = np.where((a > thresh).any(axis=1))[0]
    assert len(rows), "빈 화면"
    bands = []
    start = prev = int(rows[0])
    for r in rows[1:]:
        r = int(r)
        if r - prev > gap:
            bands.append(prev - start + 1)
            start = r
        prev = r
    bands.append(prev - start + 1)
    return bands


def test_text_ink_heights_match_design_targets(tmp_path):
    ep = _make_episode(tmp_path / "ep", INK_SRC, {})
    proc = _render(ep, "Ink", "-s", "--hd")
    assert proc.returncode == 0, _fail_msg(proc)
    png = ep / "videos" / "Ink.png"
    assert png.exists(), _fail_msg(proc)
    bands = _ink_bands(png)
    assert len(bands) == 6, bands
    for (size, want), got in zip(INK_TARGET.items(), bands[:5]):
        assert abs(got - want) <= want * INK_TOL, f"{size}: 잉크 {got}px, 목표 {want}px ({bands})"
    got = bands[5]
    assert abs(got - TEX_CAP_TARGET) <= TEX_CAP_TARGET * INK_TOL, f"tex L: {got}px ({bands})"


# ---------------------------------------------------------------------------
# undim: 장면에서 빠진 객체는 되살리지 않는다 / dimmed(scene=) / 큐마다 plays
# ---------------------------------------------------------------------------

UNDIM_SRC = '''from vizkit import *


class T(CueScene):
    def construct(self):
        with self.cue("c1"):
            a = Square(1).set_fill(OBJ[0], 0.7).set_stroke(width=0).shift(LEFT * 2)
            b = Square(1).set_fill(OBJ[1], 0.7).set_stroke(width=0)
            c = Square(1).set_fill(OBJ[2], 0.7).set_stroke(width=0).shift(RIGHT * 2)
            self.playw(FadeIn(VGroup(a, b, c)), wait=0, run_time=0.3)
            self.play(*dim_others(self, [c]), run_time=0.3)
            print("DIMMED %.3f %.3f" % (a.get_fill_opacity(), b.get_fill_opacity()), flush=True)
        with self.cue("c2"):
            self.play(FadeOut(a), run_time=0.3)
            anims = undim(self)
            self.play(*anims, run_time=0.3)
            print("UNDIM n=%d a_in=%s b=%.3f" % (
                len(anims), any(m is a for m in self.mobjects), b.get_fill_opacity()), flush=True)
        with self.cue("c3"):
            self.wait(0.2)
        with self.cue("c4"):
            d = dimmed(Square(1).set_fill(TEXT, 0.8).set_stroke(width=0).shift(DOWN * 2), scene=self)
            self.add(d)
            before = d.get_fill_opacity()
            self.play(*undim(self), run_time=0.3)
            print("DIMMED_SCENE %.3f %.3f" % (before, d.get_fill_opacity()), flush=True)
            self.zoom_in(b, scale=0.5, run_time=0.3)
            self.zoom_out(run_time=0.3)
        with self.cue("c5"):
            # 묶음째 흐린 뒤 한 조각만 빼도, 남은 조각은 undim으로 돌아온다
            e1 = Square(0.5).set_fill(OBJ[3], 0.6).set_stroke(width=0).shift(UP * 2 + LEFT)
            e2 = Square(0.5).set_fill(OBJ[3], 0.6).set_stroke(width=0).shift(UP * 2 + RIGHT)
            self.add(dimmed(VGroup(e1, e2), scene=self))
            self.play(FadeOut(e1), run_time=0.3)
            self.play(*undim(self), run_time=0.3)
            print("PART e1_in=%s e2=%.3f" % (
                any(m is e1 for top in self.mobjects for m in top.get_family()),
                e2.get_fill_opacity()), flush=True)
'''


def test_undim_skips_removed_and_counts_plays(tmp_path):
    ep = _make_episode(
        tmp_path / "ep",
        UNDIM_SRC,
        {"c1": {"scene": "T", "dur": 1.0}, "c2": {"scene": "T", "dur": 1.0},
         "c3": {"scene": "T", "dur": 0.5}, "c4": {"scene": "T", "dur": 1.5},
         "c5": {"scene": "T", "dur": 1.0}},
    )
    proc = _render(ep, "T")
    assert proc.returncode == 0, _fail_msg(proc)
    out = proc.stdout
    assert "DIMMED 0.175 0.175" in out, _fail_msg(proc)
    assert "PART e1_in=False e2=0.600" in out, _fail_msg(proc)
    # 뺀 a는 undim 뒤에도 장면에 없고, 남은 b는 원래 불투명도(0.7)로 돌아온다
    assert "UNDIM n=1 a_in=False b=0.700" in out, _fail_msg(proc)
    # dimmed(scene=)로 흐린 객체도 undim이 되돌린다
    assert "DIMMED_SCENE 0.200 0.800" in out, _fail_msg(proc)

    log = json.loads((ep / "cuelog" / "T.json").read_text(encoding="utf-8"))
    plays = {c["id"]: c["plays"] for c in log["cues"]}
    # playw도 센다, wait만 있는 큐는 0, zoom_in/zoom_out 헬퍼도 각각 1
    assert plays == {"c1": 2, "c2": 2, "c3": 0, "c4": 3, "c5": 2}, plays


# ---------------------------------------------------------------------------
# quote_focus, stand_up(m.animate), lay_down, orbit
# ---------------------------------------------------------------------------

QUOTE_SRC = '''from vizkit import *


class T(CueScene):
    def construct(self):
        with self.cue("c1"):
            q = self.quote_card("card.png", run_time=0.4)
            card = q[1]
            print("CARD_BOTTOM %.3f" % card.get_bottom()[1], flush=True)
        with self.cue("c2"):
            cov = self.quote_focus(card, (0, 0, 0.53, 1), run_time=0.3)
            w = [r.get_width() / card.get_width() for r in cov]
            print("COVER1 %.2f %.2f" % (w[2], w[3]), flush=True)
            cov2 = self.quote_focus(card, (0.5, 0, 1, 1), cov, run_time=0.3)
            w = [r.get_width() / card.get_width() for r in cov2]
            print("COVER2 same=%s %.2f %.2f" % (cov2 is cov, w[2], w[3]), flush=True)
        with self.cue("c3"):
            gone = self.quote_focus(card, None, cov2, run_time=0.3)
            print("COVER3", gone is None, any(m is cov2 for m in self.mobjects), flush=True)
            self.play(FadeOut(q), run_time=0.3)
        with self.cue("c4"):
            board = VGroup(*[Square(0.8).set_fill(OBJ[i], 0.7).set_stroke(width=0)
                             for i in range(4)]).arrange(RIGHT, buff=0.25)
            self.add(board)
            self.tilt(ORIGIN, 60, run_time=0.4)
            self.play(stand_up(board[1].animate), run_time=0.3)
            self.play(lay_down(board[1].animate), self.orbit(-14), run_time=0.3)
            self.untilt(run_time=0.4)
            print("FRAME_BACK %.3f %.3f" % (self.frame.get_phi(), self.frame.get_theta()), flush=True)
'''


def test_quote_focus_and_structure_helpers(tmp_path):
    from PIL import Image

    ep = _make_episode(
        tmp_path / "ep",
        QUOTE_SRC,
        {"c1": {"scene": "T", "dur": 0.6}, "c2": {"scene": "T", "dur": 0.8},
         "c3": {"scene": "T", "dur": 0.8}, "c4": {"scene": "T", "dur": 1.6}},
    )
    Image.new("RGB", (400, 300), (255, 255, 255)).save(ep / "card.png")
    proc = _render(ep, "T")
    assert proc.returncode == 0, _fail_msg(proc)
    out = proc.stdout
    assert "CARD_BOTTOM " in out, _fail_msg(proc)
    bottom = float(out.split("CARD_BOTTOM ")[1].split()[0])
    assert bottom >= -2.7, bottom  # 인용 카드는 자막 띠 위
    assert "COVER1 0.00 0.47" in out, _fail_msg(proc)            # 오른쪽 47%를 덮음
    assert "COVER2 same=True 0.50 0.00" in out, _fail_msg(proc)  # 왼쪽 절반으로 옮김
    assert "COVER3 True False" in out, _fail_msg(proc)
    assert "FRAME_BACK 0.000 0.000" in out, _fail_msg(proc)
    log = json.loads((ep / "cuelog" / "T.json").read_text(encoding="utf-8"))
    assert [c["plays"] for c in log["cues"]] == [1, 2, 2, 4]


# ---------------------------------------------------------------------------
# 큐 id가 timing.json에 없을 때 원인이 보이는 오류
# ---------------------------------------------------------------------------


def test_missing_cue_id_error_names_cause(tmp_path):
    ep = _make_episode(tmp_path / "ep", TIMING_SRC, {"x1": {"scene": "T", "dur": 1.0}})
    proc = _render(ep, "T")
    assert proc.returncode != 0
    err = proc.stderr + proc.stdout
    assert "CueNotFound" in err, _fail_msg(proc)
    assert "'c1'" in err and "shots.json" in err and "cues.py" in err, _fail_msg(proc)
    assert "x1" in err, _fail_msg(proc)  # 있는 큐 id를 보여 준다


def test_tex_keeps_t2c_colors(tmp_path):
    """tex(..., t2c=...)는 color를 칠한 뒤 t2c 색을 다시 입힌다(t2c 색이 지워지지 않는다)."""
    shutil.copy(VIZKIT, tmp_path / "vizkit.py")
    shutil.copy(CONFIG, tmp_path / "custom_config.yml")
    (tmp_path / "probe.py").write_text(
        "import json\n"
        "from vizkit import *\n"
        "from manimlib.utils.color import color_to_hex\n"
        "def cols(m):\n"
        "    return sorted({s.get_color().upper() for s in m.family_members_with_points()})\n"
        "m = tex('W_0', '+', 'BA', t2c={'BA': OBJ[1]})\n"
        "n = tex('W_0', color=OBJ[2])\n"
        "print('RESULT ' + json.dumps({'m': cols(m), 'n': cols(n),\n"
        "    'want_m': sorted({color_to_hex(TEXT).upper(), color_to_hex(OBJ[1]).upper()}),\n"
        "    'want_n': [color_to_hex(OBJ[2]).upper()]}))\n",
        encoding="utf-8",
    )
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.run([str(DEVPY), "probe.py"], cwd=str(tmp_path), capture_output=True,
                          encoding="utf-8", errors="replace", env=env, timeout=RENDER_TIMEOUT)
    assert proc.returncode == 0, _fail_msg(proc)
    line = [ln for ln in proc.stdout.splitlines() if "RESULT " in ln][-1]
    got = json.loads(line.split("RESULT ", 1)[1])
    assert got["m"] == got["want_m"]
    assert got["n"] == got["want_n"]
