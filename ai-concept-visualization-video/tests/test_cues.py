"""cues.py 테스트: 무음 큐 길이 공식과 timing.json 생성."""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cues  # noqa: E402


def _shots(mode="silent"):
    return {
        "episode": "lora",
        "mode": mode,
        "scenes": [
            {
                "name": "Hook",
                "cues": [
                    {"id": "c001", "t": "LoRA는요,", "say": None, "key": "LoRA",
                     "rel": "hook", "move": "montage", "hold": False},
                    {"id": "c002", "t": "왜 그럴까요?", "say": None, "key": None,
                     "rel": "point", "move": "dim", "hold": False},
                ],
            }
        ],
    }


def test_estimate_formula():
    # 'LoRA'는 라틴 1단어, '는요'는 2음절 → 3
    assert cues.syllables("LoRA는요,") == 3
    assert cues.syllables("왜 그럴까요?") == 5
    # 숫자 덩어리 1개(쉼표 자리 구분은 한 덩어리) + 한글 1음절
    assert cues.syllables("1,000개") == 2
    assert cues.estimate("LoRA는요,") == pytest.approx(max(1.2, (3 + 1) / 5.5 + 0.25))
    assert cues.estimate("LoRA는요,") == pytest.approx(max(1.2, 3 / 5.5 + 0.25))
    assert cues.estimate("왜 그럴까요?") == pytest.approx(max(1.2, 5 / 5.5 + 0.55))
    # 긴 문장은 하한 1.2에 걸리지 않는다
    t = "원래 가중치는 그대로 얼려 둡니다, 그렇죠?"
    n = cues.syllables(t)
    assert cues.estimate(t) == pytest.approx(n / 5.5 + 0.25 + 0.55)


def test_build_timing_silent():
    timing = cues.build_timing(_shots("silent"))
    assert list(timing.keys()) == ["c001", "c002"]
    for cid, v in timing.items():
        assert v["scene"] == "Hook"
        assert v["dur"] >= 1.2
    assert timing["c002"]["dur"] == pytest.approx(5 / 5.5 + 0.55, abs=1e-3)


def test_build_timing_tts_uses_audio():
    shots = _shots("tts")
    shots["scenes"][0]["cues"] = shots["scenes"][0]["cues"][:1]
    timing = cues.build_timing(shots, audio_durs={"c001": 2.4})
    assert timing["c001"]["dur"] == 2.4
    assert timing["c001"]["scene"] == "Hook"
    # tts 모드인데 음성 길이가 빠지면 조용히 넘어가지 않는다
    with pytest.raises((KeyError, ValueError)):
        cues.build_timing(shots, audio_durs={})
    with pytest.raises((KeyError, ValueError)):
        cues.build_timing(shots, audio_durs=None)
