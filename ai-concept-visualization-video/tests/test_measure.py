"""measure_motion.py, measure_design.py, sweep_frames.py를 합성 영상으로 확인한다."""
import json
import os
import subprocess
import sys
from pathlib import Path

SK = Path(__file__).resolve().parents[1]
SCRIPTS = SK / "scripts"
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def _ffmpeg(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True)


def _moving_rect(out: Path):
    """검정 10초, 흰 사각형이 1초마다 자리를 옮긴다(자막 띠 위쪽)."""
    _ffmpeg(["-f", "lavfi", "-i", "color=black:s=1920x1080:r=30:d=10",
             "-f", "lavfi", "-i", "color=white:s=200x200:r=30:d=10",
             "-filter_complex", "[0][1]overlay=x='100+mod(floor(t),8)*200':y=300:shortest=1",
             "-pix_fmt", "yuv420p", str(out)])


def _static_rect(out: Path, secs=10):
    """검정 바탕, 하단 띠 밖 흰 사각형 1개, 완전 정지."""
    _ffmpeg(["-f", "lavfi", "-i", f"color=black:s=1920x1080:r=30:d={secs}",
             "-vf", "drawbox=x=860:y=340:w=200:h=200:color=white:t=fill",
             "-pix_fmt", "yuv420p", str(out)])


def _run(script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def test_motion_static_video(tmp_path):
    mv, st = tmp_path / "moving.mp4", tmp_path / "static.mp4"
    _moving_rect(mv)
    _static_rect(st)

    _run("measure_motion.py", "--video", mv, "--json", tmp_path / "mv.json")
    m = json.loads((tmp_path / "mv.json").read_text(encoding="utf-8"))
    assert m["hold_median_s"] < 1.5, m
    assert m["short_hold_share"] > 0.5, m

    r = _run("measure_motion.py", "--video", st, "--json", tmp_path / "st.json")
    s = json.loads((tmp_path / "st.json").read_text(encoding="utf-8"))
    assert s["hold_median_s"] >= 9, s
    assert "A1 FAIL" in r.stdout
    for k in ("hold_median_s", "short_hold_share", "big_changes_per_min"):
        assert k in s


def test_motion_ignores_caption_band(tmp_path):
    """아래 16% 띠에서만 바뀌는 영상은 정지로 잰다."""
    v = tmp_path / "band.mp4"
    _ffmpeg(["-f", "lavfi", "-i", "color=black:s=1920x1080:r=30:d=10",
             "-f", "lavfi", "-i", "color=white:s=300x80:r=30:d=10",
             "-filter_complex", "[0][1]overlay=x='100+mod(floor(t),5)*300':y=960:shortest=1",
             "-pix_fmt", "yuv420p", str(v)])
    _run("measure_motion.py", "--video", v, "--json", tmp_path / "b.json")
    b = json.loads((tmp_path / "b.json").read_text(encoding="utf-8"))
    assert b["hold_median_s"] >= 9, b


def test_design_black_bg(tmp_path):
    v = tmp_path / "design.mp4"
    _static_rect(v, secs=6)
    r = _run("measure_design.py", "--video", v, "--json", tmp_path / "d.json")
    d = json.loads((tmp_path / "d.json").read_text(encoding="utf-8"))
    assert d["bg_hex"] == "#000000", d
    assert d["caption_band_content_frames"] == 0, d
    for k in ("outline_boxes_median", "outline_boxes_ge3_share", "xspan_median", "clusters_median"):
        assert k in d
    assert "A2 " in r.stdout


def test_design_detects_band_and_outline(tmp_path):
    """자막 띠 안의 내용과 테두리만 있는 상자 3개를 잡는다."""
    v = tmp_path / "bad.mp4"
    boxes = ",".join(f"drawbox=x={200 + i * 500}:y=200:w=300:h=200:color=white:t=4" for i in range(3))
    _ffmpeg(["-f", "lavfi", "-i", "color=black:s=1920x1080:r=30:d=4",
             "-vf", boxes + ",drawbox=x=700:y=980:w=500:h=60:color=white:t=fill",
             "-pix_fmt", "yuv420p", str(v)])
    r = _run("measure_design.py", "--video", v, "--json", tmp_path / "d.json")
    d = json.loads((tmp_path / "d.json").read_text(encoding="utf-8"))
    assert d["caption_band_content_frames"] > 0, d
    assert d["outline_boxes_median"] >= 3, d
    assert "A2 FAIL" in r.stdout


def test_sweep_frames_sheet(tmp_path):
    v = tmp_path / "mv.mp4"
    _moving_rect(v)
    out = tmp_path / "sweep"
    _run("sweep_frames.py", "--video", v, "--every", 1, "--out", out)
    sheets = sorted(out.glob("sheet_*.jpg"))
    assert len(sheets) == 2, list(out.iterdir())
