"""Task 8: TTS 모드(tts.py, cues.py --audio, assemble.py 음성 배치) 검사."""
import importlib.util
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

SK = Path(__file__).resolve().parents[1]
SCRIPTS = SK / "scripts"
TTS = SCRIPTS / "tts.py"
CUES = SCRIPTS / "cues.py"
ASSEMBLE = SCRIPTS / "assemble.py"
PY = sys.executable  # pytest 를 돌리는 파이썬(프로젝트 venv)


def _run(args, cwd=None, timeout=300):
    return subprocess.run([PY, *map(str, args)], cwd=cwd, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *map(str, args)],
                   check=True, capture_output=True)


def _online(host="speech.platform.bing.com", port=443) -> bool:
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _tts_shots():
    return {"episode": "ep", "mode": "tts", "scenes": [{"name": "A", "cues": [
        {"id": "c001", "t": "가중치는 그대로 두죠", "say": None, "key": None,
         "rel": "hook", "move": "fade", "hold": False},
        {"id": "c002", "t": "LoRA는 작은 행렬만 배워요", "say": "로라는 작은 행렬만 배워요",
         "key": "LoRA", "rel": "detail", "move": "fade", "hold": False},
    ]}]}


def test_tts_durs_written(tmp_path):
    if not _online():
        pytest.skip("network unavailable (edge-tts needs speech.platform.bing.com)")
    if importlib.util.find_spec("edge_tts") is None and shutil.which("uv") is None:
        pytest.skip("neither edge_tts nor uv available")
    ep = tmp_path / "ep"
    _write_json(ep / "shots.json", _tts_shots())

    proc = _run([TTS, "--episode", ep])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for cid in ("c001", "c002"):
        mp3 = ep / "tts" / f"{cid}.mp3"
        assert mp3.is_file() and mp3.stat().st_size > 0
    durs = json.loads((ep / "tts" / "durs.json").read_text(encoding="utf-8"))
    assert set(durs) == {"c001", "c002"}
    assert all(v > 0.3 for v in durs.values())

    # 두 번째 실행은 같은 대본이면 다시 합성하지 않는다
    before = (ep / "tts" / "c001.mp3").stat().st_mtime_ns
    proc2 = _run([TTS, "--episode", ep])
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    assert (ep / "tts" / "c001.mp3").stat().st_mtime_ns == before


def test_cues_audio_option(tmp_path):
    ep = tmp_path / "ep"
    _write_json(ep / "shots.json", _tts_shots())
    # durs.json 이 없으면 traceback 대신 FAIL 한 줄 + exit 1
    proc = _run([CUES, "--episode", ep])
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "FAIL" in proc.stdout and "tts.py" in proc.stdout

    _write_json(tmp_path / "voice" / "durs.json", {"c001": 2.4, "c002": 1.75})
    proc = _run([CUES, "--episode", ep, "--audio", tmp_path / "voice"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    timing = json.loads((ep / "timing.json").read_text(encoding="utf-8"))
    assert timing == {"c001": {"scene": "A", "dur": 2.4}, "c002": {"scene": "A", "dur": 1.75}}


def _audio_rms(mp4: Path, sr: int = 8000, win: float = 0.01):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-map", "0:a:0",
                          "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    n = int(sr * win)
    frames = x[: len(x) // n * n].reshape(-1, n)
    return np.sqrt((frames ** 2).mean(axis=1)), win


def test_assemble_places_audio(tmp_path):
    ep = tmp_path / "ep"
    shots = _tts_shots()
    _write_json(ep / "shots.json", shots)
    _write_json(ep / "timing.json", {"c001": {"scene": "A", "dur": 1.5},
                                     "c002": {"scene": "A", "dur": 1.5}})
    _write_json(ep / "cuelog" / "A.json", {"scene": "A", "cues": [
        {"id": "c001", "start": 0.0, "dur": 1.5, "elapsed": 0.5},
        {"id": "c002", "start": 1.5, "dur": 1.5, "elapsed": 0.5}]})
    (ep / "videos").mkdir()
    _ffmpeg("-f", "lavfi", "-i", "color=c=black:s=320x180:d=3:r=30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", ep / "videos" / "A.mp4")
    (ep / "tts").mkdir()
    for cid in ("c001", "c002"):
        _ffmpeg("-f", "lavfi", "-i", "sine=frequency=1000:duration=0.5:sample_rate=24000",
                "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k", ep / "tts" / f"{cid}.mp3")

    proc = _run([ASSEMBLE, "--episode", ep])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    final = ep / "ep_FINAL.mp4"
    assert final.is_file()

    streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                              "-of", "csv=p=0", str(final)],
                             capture_output=True, text=True, check=True).stdout.split()
    assert "audio" in streams and "video" in streams

    rms, win = _audio_rms(final)
    assert len(rms) * win == pytest.approx(3.0, abs=0.1)  # 영상 길이에 맞춘 음성
    thr = 0.5 * rms.max()
    loud = rms > thr
    first = np.argmax(loud) * win
    assert first == pytest.approx(0.0, abs=0.05)
    # 첫 소리(0~0.5초)가 끝나고 조용한 구간이 있다
    assert not loud[int(0.8 / win): int(1.4 / win)].any()
    after = int(1.0 / win)
    second = (after + np.argmax(loud[after:])) * win
    assert second == pytest.approx(1.5, abs=0.05), f"second onset at {second:.3f}s"
    # 2.0초 뒤는 다시 조용하다(apad)
    assert not loud[int(2.2 / win):].any()
