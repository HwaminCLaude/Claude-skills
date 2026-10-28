"""captions.py 테스트: ASS 헤더, 핵심어 색, cuelog 실제 시각 반영."""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import captions  # noqa: E402

WJ = chr(0x2060)  # WORD JOINER


def _dialogues(ass: str):
    return [ln for ln in ass.splitlines() if ln.startswith("Dialogue:")]


def test_ass_header_values():
    ass = captions.to_ass([("안녕하세요", 0.0, 1.5)], {})
    assert "PlayResX: 1920" in ass
    assert "PlayResY: 1080" in ass
    assert "WrapStyle: 2" in ass
    assert "Noto Sans KR Medium,64,&H00DCDCDC" in ass
    style = [ln for ln in ass.splitlines() if ln.startswith("Style:")][0]
    fields = style[len("Style:"):].split(",")
    # Format 순서: Name, Fontname, Fontsize, Primary, Secondary, Outline, Back, Bold, ...
    # 'Noto Sans KR' + Bold -1 은 VF Thin 에 떨어진다. 정적 Medium 을 가족 이름으로 고르고 Bold 0.
    assert fields[1].strip() == "Noto Sans KR Medium"
    assert fields[7].strip() == "0"
    # BorderStyle 1, Outline 0, Shadow 0, Alignment 2, MarginL/R 60, MarginV 103
    assert ",1,0,0,2,60,60,103," in style
    dl = _dialogues(ass)
    assert len(dl) == 1
    assert dl[0].startswith("Dialogue: 0,0:00:00.00,0:00:01.50,")


def test_key_color_tag():
    t = "원래 W를 그대로 얼려 둡니다"
    ass = captions.to_ass([(t, 0.0, 2.0)], {t: "그대로 얼려"})
    dl = _dialogues(ass)
    assert len(dl) == 1
    assert r"{\c&H0025CFEA&}그대로 얼려{\c&H00DCDCDC&}" in dl[0]
    assert dl[0].endswith(r"원래 W를 {\c&H0025CFEA&}그대로 얼려{\c&H00DCDCDC&} 둡니다")


def test_cuelog_overrides_timing():
    shots = {
        "episode": "ep", "mode": "silent",
        "scenes": [
            {"name": "A", "cues": [
                {"id": "c1", "t": "첫 큐", "key": None, "rel": "hook", "move": "x", "hold": False},
                {"id": "c2", "t": "둘째 큐", "key": None, "rel": "build", "move": "x", "hold": False},
            ]},
            {"name": "B", "cues": [
                {"id": "c3", "t": "셋째 큐", "key": None, "rel": "new", "move": "x", "hold": False},
            ]},
        ],
    }
    timing = {"c1": {"scene": "A", "dur": 1.2},
              "c2": {"scene": "A", "dur": 1.3},
              "c3": {"scene": "B", "dur": 2.0}}

    # cuelog 없음: timing 누적
    items = captions.cue_times(shots, timing, None)
    assert [round(s, 3) for _, s, _ in items] == [0.0, 1.2, 2.5]
    assert items[-1][2] == pytest.approx(4.5)

    # cuelog 있음: c1이 0.3초 밀려 c2가 1.5에 시작
    cuelogs = {"A": {"scene": "A", "cues": [
        {"id": "c1", "start": 0.0, "dur": 1.2, "elapsed": 1.5},
        {"id": "c2", "start": 1.5, "dur": 1.3, "elapsed": 0.5},
    ]}}
    items = captions.cue_times(shots, timing, cuelogs)
    assert items[0] == ("첫 큐", pytest.approx(0.0), pytest.approx(1.5))
    assert items[1][1] == pytest.approx(1.5)
    # 씬 A 길이 = 1.5 + max(1.3, 0.5) = 2.8 → 씬 B 시작
    assert items[2][1] == pytest.approx(2.8)

    # scene_durs(실제 영상 길이)가 있으면 씬 오프셋은 그 합이다
    items = captions.cue_times(shots, timing, cuelogs, scene_durs={"A": 2.85, "B": 2.0})
    assert items[1][2] == pytest.approx(2.85)
    assert items[2][1] == pytest.approx(2.85)
    assert items[2][2] == pytest.approx(4.85)

    ass = captions.to_ass(items, {})
    dl = _dialogues(ass)
    assert dl[1].startswith("Dialogue: 0,0:00:01.50,0:00:02.85,")
    assert dl[0].startswith("Dialogue: 0,0:00:00.00,0:00:01.50,")


def _two_scene_shots():
    return {
        "episode": "ep", "mode": "silent",
        "scenes": [
            {"name": "A", "cues": [
                {"id": "c1", "t": "첫 큐", "key": None},
                {"id": "c2", "t": "둘째 큐", "key": None},
            ]},
            {"name": "B", "cues": [{"id": "c3", "t": "셋째 큐", "key": None}]},
        ],
    }


_TIMING = {"c1": {"scene": "A", "dur": 1.2}, "c2": {"scene": "A", "dur": 1.3},
           "c3": {"scene": "B", "dur": 2.0}}


def test_style_font_and_no_outline_shadow():
    ass = captions.to_ass([("자막", 0.0, 1.0)], {})
    style = [ln for ln in ass.splitlines() if ln.startswith("Style:")][0]
    assert style == ("Style: Default,Noto Sans KR Medium,64,&H00DCDCDC,&H00DCDCDC,&H00000000,"
                     "&H00000000,0,0,0,0,100,100,0,0,1,0,0,2,60,60,103,1")
    # Format 순서상 BorderStyle 1, Outline 0, Shadow 0, Alignment 2, MarginL/R 60, MarginV 103
    assert ",0,0,2,60,60,103," in style
    assert captions.CAPTION_FONT == "Noto Sans KR Medium"
    assert captions.CAPTION_FONT_PS == "NotoSansKR-Medium"


def test_cuelog_null_elapsed_names_scene_and_cue():
    cuelogs = {"A": {"scene": "A", "cues": [
        {"id": "c1", "start": 0.0, "dur": 1.2, "elapsed": None},
    ]}}
    with pytest.raises(ValueError) as ei:
        captions.cue_times(_two_scene_shots(), _TIMING, cuelogs)
    msg = str(ei.value)
    assert "A" in msg and "c1" in msg and "elapsed" in msg and "render" in msg


def test_cuelog_null_start_names_scene_and_cue():
    cuelogs = {"A": {"scene": "A", "cues": [{"id": "c2", "start": None, "dur": 1.3}]}}
    with pytest.raises(ValueError, match=r"c2.*start"):
        captions.cue_times(_two_scene_shots(), _TIMING, cuelogs)


def test_cuelog_missing_elapsed_key_is_ok():
    cuelogs = {"A": {"scene": "A", "cues": [{"id": "c1", "start": 0.0, "dur": 1.2}]}}
    items = captions.cue_times(_two_scene_shots(), _TIMING, cuelogs)
    assert [round(s, 3) for _, s, _ in items] == [0.0, 1.2, 2.5]


def test_cuelog_unknown_keys_ignored():
    base = {"A": {"scene": "A", "cues": [
        {"id": "c1", "start": 0.0, "dur": 1.2, "elapsed": 1.5},
        {"id": "c2", "start": 1.5, "dur": 1.3, "elapsed": 0.5},
    ]}}
    extra = {"A": {"scene": "A", "version": 2, "cues": [
        {"id": "c1", "start": 0.0, "dur": 1.2, "elapsed": 1.5,
         "plays": [{"t0": 0.0, "t1": 1.0, "anims": ["FadeIn"]}], "foo": "bar"},
        {"id": "c2", "start": 1.5, "dur": 1.3, "elapsed": 0.5, "plays": []},
    ]}}
    a = captions.cue_times(_two_scene_shots(), _TIMING, base)
    b = captions.cue_times(_two_scene_shots(), _TIMING, extra)
    assert a == b


def test_zero_length_caption_warns(capsys):
    cuelogs = {"A": {"scene": "A", "cues": [
        {"id": "c1", "start": 0.0, "dur": 1.2, "elapsed": 1.0},
        {"id": "c2", "start": 1.2, "dur": 1.3, "elapsed": 1.0},
    ]}}
    # 씬 A 영상이 마지막 큐 시작(1.2초)보다 짧다 → c2 길이 0
    items = captions.cue_times(_two_scene_shots(), _TIMING, cuelogs, scene_durs={"A": 1.1, "B": 2.0})
    assert items[1][2] - items[1][1] == pytest.approx(0.0)
    out = capsys.readouterr().out
    assert "WARN caption zero-length" in out and "c2" in out and "scene A" in out
    assert "c1" not in out and "c3" not in out


def test_no_warn_for_normal_lengths(capsys):
    captions.cue_times(_two_scene_shots(), _TIMING, None, scene_durs={"A": 2.5, "B": 2.0})
    assert "WARN" not in capsys.readouterr().out


def test_escape_blocks_ass_control_sequences():
    t = r"a\Nb c\hd e\n {\b1}굵게{x}"
    ass = captions.to_ass([(t, 0.0, 1.0)], {})
    body = _dialogues(ass)[0].split("Default,,0,0,0,,", 1)[1]
    BS = chr(0x5C)
    # 백슬래시 바로 뒤에 N, n, h, b 가 오지 않는다(WORD JOINER 가 끼어 있다)
    for seq in (r"\N", r"\n", r"\h", r"\b"):
        assert seq not in body
    assert BS + WJ + "N" in body and BS + WJ + "h" in body and BS + WJ + "n" in body
    # 중괄호는 \{ \} 로 막혀 재정의 블록이 되지 않는다
    assert "{" not in body.replace(r"\{", "")
    assert "}" not in body.replace(r"\}", "")
    # 원문 '{\b1}' → '\{' + '\' + WJ + 'b1\}': 백슬래시 처리를 먼저 하므로 \{ 의 백슬래시는 그대로다
    assert r"\{" + BS + WJ + r"b1\}" in body
    assert body.count(r"\{") == 2 and body.count(r"\}") == 2
    # WJ 와 이스케이프를 걷어 내면 원문 그대로다
    assert body.replace(WJ, "").replace(r"\{", "{").replace(r"\}", "}") == t


def test_escape_inside_key_coloring():
    t = r"값 \N 이 {x}"
    ass = captions.to_ass([(t, 0.0, 1.0)], {t: r"\N"})
    dl = _dialogues(ass)[0]
    assert r"{\c&H0025CFEA&}" + chr(0x5C) + WJ + r"N{\c&H00DCDCDC&}" in dl
    assert dl.endswith(r" 이 \{x\}")


def test_check_fontselect():
    ok_log = ("[Parsed_subtitles_0 @ 0] fontselect: (Noto Sans KR Medium, 400, 0) -> "
              "NotoSansKR-Medium, 0, NotoSansKR-Medium\n"
              "[Parsed_subtitles_0 @ 0] Glyph 0x2080 not found, selecting one more font for "
              "(Noto Sans KR Medium, 400, 0)\n"
              "[Parsed_subtitles_0 @ 0] fontselect: (Noto Sans KR Medium, 400, 0) -> "
              "SegoeUI-Semibold, 0, SegoeUI-Semibold\n")
    err, warns = captions.check_fontselect(ok_log)
    assert err is None
    assert len(warns) == 1 and "0x2080" in warns[0]

    thin = "fontselect: (Noto Sans KR Medium, 400, 0) -> NotoSansKR-Thin, 0, NotoSansKR-Thin\n"
    err, _ = captions.check_fontselect(thin)
    assert err and "NotoSansKR-Thin" in err

    arial = "fontselect: (Noto Sans KR Medium, 400, 0) -> ArialMT, 0, ArialMT\n"
    assert captions.check_fontselect(arial)[0]
    assert captions.check_fontselect("no libass lines here")[0]
