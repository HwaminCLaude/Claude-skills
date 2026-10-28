"""박자 없는 큐(plays == 0) 판정 테스트: render.py no_beat_cues와 cuelog 소비자 호환."""
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import captions  # noqa: E402
import render  # noqa: E402


def _log(*cues):
    return {"scene": "Hook", "cues": list(cues)}


def _cue(cid, plays, start=0.0, dur=1.0, elapsed=0.5):
    e = {"id": cid, "start": start, "dur": dur, "elapsed": elapsed}
    if plays is not ...:
        e["plays"] = plays
    return e


def test_no_beat_flags_only_zero_plays_in_order():
    log = _log(_cue("c1", 2), _cue("c2", 0), _cue("c3", 1), _cue("c4", 0))
    assert render.no_beat_cues(log) == ["c2", "c4"]


def test_no_beat_none_when_every_cue_plays():
    assert render.no_beat_cues(_log(_cue("c1", 1), _cue("c2", 3))) == []


def test_no_beat_skips_old_cuelog_without_plays_key():
    # 옛 키트가 쓴 cuelog(plays 없음)는 판정하지 않는다(거짓 경고 방지)
    log = _log(_cue("c1", ...), _cue("c2", 0))
    assert render.no_beat_cues(log) == ["c2"]
    assert render.no_beat_cues(_log(_cue("c1", ...))) == []


def test_no_beat_accepts_list_and_empty():
    assert render.no_beat_cues([_cue("a", 0), _cue("b", 1)]) == ["a"]
    assert render.no_beat_cues(None) == []
    assert render.no_beat_cues({}) == []
    assert render.no_beat_cues(_log()) == []


def test_read_cuelog(tmp_path):
    ep = tmp_path / "ep"
    (ep / "cuelog").mkdir(parents=True)
    log = _log(_cue("c1", 0))
    (ep / "cuelog" / "Hook.json").write_text(json.dumps(log), encoding="utf-8")
    assert render.read_cuelog(ep, "Hook") == log
    assert render.read_cuelog(ep, "Missing") is None
    assert render.no_beat_cues(render.read_cuelog(ep, "Missing")) == []


def test_plays_key_does_not_break_captions_reader():
    """새 키 plays가 captions.py(그리고 이를 쓰는 assemble.py)의 cuelog 읽기를 깨지 않는다."""
    shots = {"scenes": [{"name": "Hook", "cues": [
        {"id": "c1", "t": "하나"}, {"id": "c2", "t": "둘"}]}]}
    timing = {"c1": {"scene": "Hook", "dur": 1.0}, "c2": {"scene": "Hook", "dur": 1.5}}
    log = _log(_cue("c1", 1, start=0.0, dur=1.0, elapsed=0.6),
               _cue("c2", 0, start=1.0, dur=1.5, elapsed=0.0))
    items = captions.cue_times(shots, timing, {"Hook": log})
    assert [round(s, 3) for _, s, _ in items] == [0.0, 1.0]
