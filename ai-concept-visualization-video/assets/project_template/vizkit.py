"""vizkit: ai-concept-visualization-video 키트.

씬 파일에서 `from vizkit import *`로 쓴다. 이 모듈은 manimlib와 raenimgl의
이름을 그대로 다시 내보내고, 그 위에 다음을 더한다.

- 디자인 토큰(색, 글자 크기, 간격, 배치 한계). 씬 코드에는 hex를 쓰지 않는다.
- 글자 함수 label/title/source/mono/tex. FS는 설계 크기이고, 실제 font_size는
  Text가 FS×TEXT_SCALE, Tex가 TEX_FS(=FS×1.5)다(1080p 잉크 높이 보정).
- 강조 함수 tint/dim_others/undim/dimmed, 인용 카드 덮개 focus_cover.
- CueScene: 자막 큐 단위 박자 계약. `with self.cue(id):` 블록이 끝나면
  timing.json의 큐 길이까지 기다리고, 실제 시작 시각과 블록 안 play 횟수(plays)를
  cuelog/<Scene>.json에 남긴다.
- 카메라와 흐름 헬퍼(zoom_in/zoom_out, pan_to, tilt/untilt, orbit, carry, aside,
  quote_card, quote_focus, clear_to)와 stand_up/lay_down.
"""
from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path

from manimlib import *  # noqa: F401,F403
from raenimgl import *  # noqa: F401,F403
from manimlib import (
    BLUE, GREEN, RED, ORANGE, WHITE, BLACK, GREY_B, GREY_C, GREY_D,
    DEG, FRAME_HEIGHT, FRAME_WIDTH, LEFT, RIGHT, UP, DOWN, UL, ORIGIN,
    FadeIn, FadeOut, Group, ImageMobject, InteractiveScene, Mobject,
    Rectangle, Restore, SurroundingRectangle, Tex, Text, Transform, VGroup, VMobject,
)
from raenimgl import Scene2D
import numpy as np

# ---------------------------------------------------------------------------
# 디자인 토큰(설계 §5.4)
# ---------------------------------------------------------------------------
BG = "#000000"
PANEL = "#0A0A0A"
OVERLAY_OPACITY = 0.75

TEXT = WHITE
TEXT_2 = GREY_B
LINE = GREY_D
ARROW = GREY_C
DIM = 0.25

OBJ = [BLUE, GREEN, RED, ORANGE]

# FS는 '설계 크기'다(린트와 문서가 이 숫자를 쓴다). 그대로 font_size로 쓰면 1080p 한글
# 잉크가 목표의 약 70%라서 키트가 Text에는 TEXT_SCALE을 곱해 그린다.
# 1080p '학습합니다' 잉크 높이 실측: S 34, M 40, T 44, L 53, XL 66px
# (설계 목표 34/41/44/54/68px).
FS = {"S": 20, "M": 24, "T": 26, "L": 32, "XL": 40}
TEXT_SCALE = 1.44
# Tex 크기 토큰: FS×1.5(S 30, M 36, T 39, L 48, XL 60). TEX_FS["L"]에서 대문자·숫자
# 높이가 약 48px로 같은 토큰 한글 잉크(54px)의 약 0.9배다.
TEX_FS = {k: v * 1.5 for k, v in FS.items()}
BUFF = (0.25, 0.5, 1.0)

CAPTION_SAFE_Y = -2.7
CONTENT_X = 4.3
CONTENT_X_WIDE = 5.7

FONT_SANS = "Noto Sans KR"
FONT_SERIF = "Noto Serif KR"
FONT_MONO = "Consolas"

CUE_OVERRUN_TOL = 0.3

# ---------------------------------------------------------------------------
# 글자
# ---------------------------------------------------------------------------


def _fs(size: str) -> float:
    """Text용 실제 font_size(FS[size] × TEXT_SCALE)."""
    if size not in FS:
        raise KeyError(f"글자 크기 토큰은 {list(FS)} 중 하나다: {size!r}")
    return FS[size] * TEXT_SCALE


def label(text: str, size: str = "M", color=TEXT, *, prop: bool = False) -> Text:
    """해설 라벨(Noto Sans KR). font_size = FS[size] × TEXT_SCALE.

    prop=True는 화면 효과가 없는 린트 표지다. 채팅 프롬프트나 화면 속 UI처럼
    의도해서 넣은 극 안 문장임을 lint에 알린다.
    """
    return Text(text, font=FONT_SANS, font_size=_fs(size)).set_color(color)


def title(text: str) -> Text:
    """좌상단 구간 제목(T, 흰색)."""
    return label(text, "T", TEXT).to_corner(UL, buff=0.2)


def source(text: str) -> Text:
    """출처 표기(Noto Serif KR, S, TEXT_2)."""
    return Text(text, font=FONT_SERIF, font_size=_fs("S")).set_color(TEXT_2)


def mono(text: str, size: str = "M") -> Text:
    """코드 소품 글자(Consolas)."""
    return Text(text, font=FONT_MONO, font_size=_fs(size)).set_color(TEXT)


def tex(*parts: str, size: str = "L", color=TEXT, **kwargs) -> Tex:
    """수식(Tex). font_size = TEX_FS[size](= FS[size] × 1.5).

    조각을 여러 개 넘기면 Tex(*parts)와 같아서 `m["BA"].set_color(OBJ[1])`처럼 고를 수 있다.
    나머지 키워드는 Tex에 그대로 넘긴다. t2c(tex_to_color_map)를 주면 color를 칠한 뒤 그 색을 다시 입힌다.
    """
    if size not in TEX_FS:
        raise KeyError(f"Tex 크기 토큰은 {list(TEX_FS)} 중 하나다: {size!r}")
    m = Tex(*parts, font_size=TEX_FS[size], **kwargs).set_color(color)
    cmap = {**kwargs.get("tex_to_color_map", {}), **kwargs.get("t2c", {})}
    if cmap:
        m.set_color_by_tex_to_color_map(cmap)
    return m


# ---------------------------------------------------------------------------
# 강조
# ---------------------------------------------------------------------------


def tint(mob, color, opacity: float = 0.3) -> SurroundingRectangle:
    """대상 영역을 면 색으로 덮는 반투명 틴트(테두리 없음)."""
    rect = SurroundingRectangle(mob, buff=0, color=color)
    rect.set_fill(color, opacity=opacity)
    rect.set_stroke(width=0, opacity=0)
    return rect


def _has_points(mob) -> bool:
    return any(sm.has_points() for sm in mob.get_family())


def _scene_content(scene) -> list:
    """씬에 올라와 있는 내용 객체(카메라 프레임과 InteractiveScene 보조 객체 제외)."""
    skip = {id(scene.frame)}
    for m in getattr(scene, "unselectables", []) or []:
        skip.add(id(m))
    out = []
    for m in scene.mobjects:
        if id(m) in skip or type(m) is Mobject:
            continue
        if not _has_points(m):
            continue
        out.append(m)
    return out


def _split_others(mobs, keep_ids: set, keep_family_ids: set) -> list:
    """keep에 들지 않는 객체를 가능한 한 큰 덩어리로 모은다."""
    others = []
    for m in mobs:
        if id(m) in keep_ids:
            continue
        if id(m) in keep_family_ids:
            # keep을 품은 묶음: 안으로 들어가 나머지만 고른다
            others.extend(_split_others(m.submobjects, keep_ids, keep_family_ids))
        elif _has_points(m):
            others.append(m)
    return others


def _others(scene, keep) -> list:
    keep = list(keep or [])
    keep_ids = {id(sm) for k in keep for sm in k.get_family()}
    # keep을 품고 있는 조상(묶음) id
    keep_anc = set()
    for top in _scene_content(scene):
        for sm in top.get_family():
            if id(sm) in keep_ids:
                continue
            if any(id(x) in keep_ids for x in sm.get_family()):
                keep_anc.add(id(sm))
    return _split_others(_scene_content(scene), keep_ids, keep_anc)


def _data_names(sm) -> tuple:
    dtype = getattr(getattr(sm, "data", None), "dtype", None)
    return tuple(dtype.names or ()) if dtype is not None else ()


def _opacity_snapshot(mob) -> list:
    """객체 가족마다 원래 불투명도를 적어 둔다."""
    snap = []
    for sm in mob.get_family():
        names = _data_names(sm)
        if isinstance(sm, VMobject):
            snap.append(("v", float(sm.get_fill_opacity()), float(sm.get_stroke_opacity())))
        elif "opacity" in names:
            snap.append(("i", np.array(sm.data["opacity"]).copy()))
        elif "rgba" in names:
            snap.append(("m", np.array(sm.data["rgba"][:, 3]).copy()))
        else:
            snap.append(None)
    return snap


def _apply_snapshot(target, snap) -> None:
    for sm, s in zip(target.get_family(), snap):
        if s is None:
            continue
        if s[0] == "v" and isinstance(sm, VMobject):
            sm.set_fill(opacity=s[1], recurse=False)
            sm.set_stroke(opacity=s[2], recurse=False)
        elif s[0] == "i":
            sm.set_opacity(float(np.mean(s[1])) if len(s[1]) else 1.0, recurse=False)
        elif s[0] == "m":
            sm.set_opacity(float(np.mean(s[1])) if len(s[1]) else 1.0, recurse=False)


def _apply_dim(target, snap, opacity: float) -> None:
    """snap(원래 불투명도)의 opacity배로 target 가족을 칠한다."""
    for sm, s in zip(target.get_family(), snap):
        if s is None:
            continue
        if s[0] == "v":
            sm.set_fill(opacity=s[1] * opacity, recurse=False)
            sm.set_stroke(opacity=s[2] * opacity, recurse=False)
        else:
            base = float(np.mean(s[1])) if len(s[1]) else 1.0
            sm.set_opacity(base * opacity, recurse=False)


def _dim_registry(scene) -> dict:
    reg = getattr(scene, "_viz_dimmed", None)
    if reg is None:
        reg = {}
        scene._viz_dimmed = reg
    return reg


def _live_ids(scene) -> set:
    """지금 장면에 올라와 있는 모든 객체(가족 포함)의 id."""
    return {id(sm) for top in scene.mobjects for sm in top.get_family()}


def _live_parts(mob, live: set):
    """장면에서 빠진 묶음 안에서 아직 장면에 남은 가장 큰 조각들."""
    for sm in mob.submobjects:
        if id(sm) in live:
            yield sm
        else:
            yield from _live_parts(sm, live)


def _prune_registry(scene) -> dict:
    """장면에서 빠진(FadeOut, remove 등) 객체를 흐리기 등록부에서 지운다.

    묶음 일부만 뺀 경우(Scene.remove는 남은 조각을 장면 목록에 풀어 놓는다) 남은 조각은
    원래 불투명도와 함께 따로 다시 등록해 undim이 되돌릴 수 있게 한다.
    """
    reg = _dim_registry(scene)
    live = _live_ids(scene)
    for key, (mob, snap) in list(reg.items()):
        if id(mob) in live:
            continue
        del reg[key]
        per = {id(sm): s for sm, s in zip(mob.get_family(), snap)}
        for sub in _live_parts(mob, live):
            reg[id(sub)] = (sub, [per.get(id(x)) for x in sub.get_family()])
    return reg


def _restore_anim(mob, snap):
    target = mob.copy()
    _apply_snapshot(target, snap)
    return Transform(mob, target)


def dim_others(scene, keep: list, opacity: float = DIM) -> list:
    """keep 밖의 내용을 흐리는 애니메이션 목록(색은 두고 불투명도만 opacity배).

    이미 흐린 객체는 원래 불투명도를 기억해 두므로 두 번 흐려도 undim으로 돌아온다.
    keep 안에 전에 흐렸던 객체가 있으면 원래대로 되돌리는 애니메이션도 넣는다.
    """
    reg = _prune_registry(scene)
    anims = []
    keep = list(keep or [])
    keep_ids = {id(sm) for k in keep for sm in k.get_family()}
    for key in list(reg):
        mob, snap = reg[key]
        if id(mob) in keep_ids:
            anims.append(_restore_anim(mob, snap))
            del reg[key]
    for mob in _others(scene, keep):
        if id(mob) in reg:
            continue
        snap = _opacity_snapshot(mob)
        reg[id(mob)] = (mob, snap)
        target = mob.copy()
        _apply_dim(target, snap, opacity)
        anims.append(Transform(mob, target))
    return anims


def undim(scene) -> list:
    """dim_others(또는 dimmed(..., scene=))로 흐린 객체를 원래 불투명도로 되돌리는 애니메이션 목록.

    지금 장면에 남아 있는 객체만 되돌린다. 그 사이 FadeOut 등으로 빠진 객체는
    등록부에서 지우기만 한다(되돌리는 Transform이 그 객체를 다시 화면에 올리지 않게).
    """
    reg = _prune_registry(scene)
    anims = [_restore_anim(mob, snap) for mob, snap in reg.values()]
    reg.clear()
    return anims


def dimmed(mob, k: float = DIM, scene=None):
    """mob을 dim_others로 흐린 것과 같은 모양(불투명도 k배)으로 바로 바꾸고 돌려준다.

    앞 씬 끝 화면을 흐린 채로 이어받을 때 쓴다(애니메이션 아님). scene을 넘기면
    원래 불투명도를 흐리기 등록부에 적어 두어 나중에 undim(scene)이 되돌린다.
        self.add(dimmed(ctx, scene=self))
    """
    snap = _opacity_snapshot(mob)
    _apply_dim(mob, snap, k)
    if scene is not None:
        _dim_registry(scene)[id(mob)] = (mob, snap)
    return mob


def _cover_strip(x0: float, x1: float, y0: float, y1: float) -> Rectangle:
    r = Rectangle(width=max(x1 - x0, 1e-4), height=max(y1 - y0, 1e-4))
    r.set_fill(BLACK, opacity=OVERLAY_OPACITY).set_stroke(width=0, opacity=0)
    r.move_to(np.array([(x0 + x1) / 2, (y0 + y1) / 2, 0.0]))
    return r


def focus_cover(card, keep) -> VGroup:
    """card에서 keep 밖을 덮는 BLACK(OVERLAY_OPACITY) 띠 4개(위, 아래, 왼쪽, 오른쪽).

    keep: 카드 안 비율 상자 (x0, y0, x1, y1). (0, 0)이 카드 왼쪽 위, (1, 1)이 오른쪽 아래다.
    Mobject를 넘기면 그 경계 상자(카드 밖은 잘라 냄)를 쓴다. 띠는 늘 4개라서 두 덮개
    사이를 Transform으로 옮길 수 있다(쓰지 않는 띠는 폭이나 높이가 0).
    """
    L, R = card.get_left()[0], card.get_right()[0]
    T, B = card.get_top()[1], card.get_bottom()[1]
    if isinstance(keep, Mobject):
        kx0, kx1 = keep.get_left()[0], keep.get_right()[0]
        ky_top, ky_bot = keep.get_top()[1], keep.get_bottom()[1]
    else:
        fx0, fy0, fx1, fy1 = [float(v) for v in keep]
        if not (0 <= fx0 < fx1 <= 1 and 0 <= fy0 < fy1 <= 1):
            raise ValueError(f"keep은 0~1 비율 (x0, y0, x1, y1)이고 x0<x1, y0<y1이다: {keep!r}")
        kx0, kx1 = L + fx0 * (R - L), L + fx1 * (R - L)
        ky_top, ky_bot = T - fy0 * (T - B), T - fy1 * (T - B)
    kx0, kx1 = max(L, kx0), min(R, kx1)
    ky_top, ky_bot = min(T, ky_top), max(B, ky_bot)
    return VGroup(
        _cover_strip(L, R, ky_top, T),           # 위
        _cover_strip(L, R, B, ky_bot),           # 아래
        _cover_strip(L, kx0, ky_bot, ky_top),    # 왼쪽
        _cover_strip(kx1, R, ky_bot, ky_top),    # 오른쪽
    )


# ---------------------------------------------------------------------------
# 함수
# ---------------------------------------------------------------------------


def stand_up(mob, phi: float = 60):
    """판 위의 객체를 RIGHT축으로 phi도 돌려 세운다(기울인 카메라와 같은 각도).

    - 객체를 넘기면 바로 돌리고 그 객체를 돌려준다(애니메이션 아님): `self.add(stand_up(m))`
    - `m.animate`를 넘기면 애니메이션 빌더를 돌려준다: `self.play(stand_up(m.animate))`
    - 다시 눕힐 때는 `lay_down(m.animate)`(= phi를 음수로).
    """
    return mob.rotate(phi * DEG, axis=RIGHT)


def lay_down(mob, phi: float = 60):
    """stand_up의 반대(RIGHT축으로 -phi도). `self.play(lay_down(m.animate))`."""
    return stand_up(mob, -phi)


def _point(target) -> np.ndarray:
    if isinstance(target, Mobject):
        return target.get_center()
    return np.array(target, dtype=float)


# ---------------------------------------------------------------------------
# CueScene
# ---------------------------------------------------------------------------


class CueNotFound(KeyError):
    """self.cue(id)의 id가 timing.json에 없다."""

    def __str__(self) -> str:  # KeyError 기본 str은 repr이라 한글 문장이 읽기 어렵다
        return str(self.args[0]) if self.args else ""


class CueScene(InteractiveScene, Scene2D):
    """자막 큐 단위로 박자를 맞추는 기본 씬.

    - setup(): 에피소드 폴더(씬 파일이 있는 폴더)의 timing.json을 읽는다.
    - cue(id): 큐 블록. 끝나면 남은 시간만큼 기다린다. 블록 안 play 횟수를 plays로 적는다.
    - tear_down(): cuelog/<SceneName>.json을 쓴다.
    """

    def _episode_dir(self) -> Path:
        mod = sys.modules.get(type(self).__module__)
        f = getattr(mod, "__file__", None)
        if f:
            return Path(f).resolve().parent
        return Path.cwd()

    def setup(self):
        super().setup()
        self._viz_dir = self._episode_dir()
        tpath = self._viz_dir / "timing.json"
        if not tpath.exists():
            tpath = Path.cwd() / "timing.json"
        self._timing = (
            json.loads(tpath.read_text(encoding="utf-8")) if tpath.exists() else {}
        )
        self._timing_path = tpath
        self._cuelog = []
        self._cue_slip = 0.0
        self._frame_stack = []
        self._viz_dimmed = {}
        self._play_count = 0

    def play(self, *args, **kwargs):
        # 큐마다 박자 수(plays)를 세려고 play만 센다(wait도 num_plays를 올리므로 그것은 쓰지 않는다).
        # raenimgl의 playw/playwl/playwlfin/clear/play_camera도 self.play를 거치므로 여기서 센다.
        if args:
            self._play_count = getattr(self, "_play_count", 0) + 1
        return super().play(*args, **kwargs)

    # -- 큐 ---------------------------------------------------------------
    @contextmanager
    def cue(self, cue_id: str):
        if cue_id not in self._timing:
            if not self._timing:
                why = (f"timing.json({self._timing_path})이 없거나 비어 있다. "
                       "shots.json에 큐를 쓰고 cues.py --episode <ep>로 timing.json을 만든다.")
            else:
                have = list(self._timing)
                shown = ", ".join(have[:8]) + (" ..." if len(have) > 8 else "")
                why = (f"timing.json({self._timing_path})에 없다(있는 큐: {shown}). "
                       "main.py의 self.cue(id)가 shots.json의 큐 id와 같은지 보고, "
                       "cues.py --episode <ep>로 timing.json을 다시 만든다.")
            raise CueNotFound(f"큐 id {cue_id!r}가 shots.json/timing.json에 없다: {why}")
        dur = float(self._timing[cue_id]["dur"])
        start = float(self.get_time())
        entry = {"id": cue_id, "start": round(start, 4), "dur": dur, "elapsed": None, "plays": 0}
        self._cuelog.append(entry)
        plays0 = self._play_count
        yield
        entry["plays"] = self._play_count - plays0
        elapsed = float(self.get_time()) - start
        entry["elapsed"] = round(elapsed, 4)
        remain = dur - elapsed
        if remain < -CUE_OVERRUN_TOL:
            print("CUE_OVERRUN", cue_id, round(-remain, 3), flush=True)
        # 프레임 단위로 끊으며 생기는 오차(_cue_slip)를 다음 큐에서 갚아
        # 큐가 많아도 씬 길이가 큐 길이 합에서 벌어지지 않게 한다.
        fps = float(getattr(self.camera, "fps", 60) or 60)
        n = int(round((remain - self._cue_slip) * fps))
        if n > 0:
            # get_time_progression은 arange(0, d, 1/fps)라 (n-0.5)/fps면 정확히 n프레임
            self.wait((n - 0.5) / fps)
        spent = float(self.get_time()) - start
        self._cue_slip = 0.0 if remain < 0 else self._cue_slip + (spent - dur)

    def tear_down(self):
        try:
            out_dir = self._viz_dir / "cuelog"
            out_dir.mkdir(parents=True, exist_ok=True)
            data = {"scene": type(self).__name__, "cues": self._cuelog}
            (out_dir / f"{type(self).__name__}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        except AttributeError:
            pass  # setup()이 돌기 전에 실패한 경우
        super().tear_down()

    # -- 카메라 상태 스택 ------------------------------------------------------
    def _push_frame(self):
        self.frame.save_state()
        self._frame_stack.append(self.frame.saved_state)

    def _pop_frame(self, run_time: float):
        if not self._frame_stack:
            raise RuntimeError("되돌릴 카메라 상태가 없다(zoom_in/tilt 없이 zoom_out/untilt 호출)")
        self.frame.saved_state = self._frame_stack.pop()
        self.play(Restore(self.frame), run_time=run_time)

    # -- 카메라와 흐름 헬퍼 ------------------------------------------------------
    def zoom_in(self, target, scale: float = 0.4, run_time: float = 1.0):
        """rel=detail: 2D 확대. zoom_out()으로 돌아온다."""
        self._push_frame()
        self.play(self.frame.animate.move_to(_point(target)).scale(scale), run_time=run_time)

    def zoom_out(self, run_time: float = 1.0):
        self._pop_frame(run_time)

    def pan_to(self, target, run_time: float = 1.0):
        """rel=next: 카메라를 옆 내용으로 옮긴다."""
        self.play(self.frame.animate.move_to(_point(target)), run_time=run_time)

    def tilt(self, center, phi: float = 60, height: float | None = None,
             run_time: float = 1.0):
        """rel=structure: 판을 눕혀 보도록 카메라를 phi도 기울인다. untilt()로 돌아온다."""
        self._push_frame()
        self.play(
            self.frame.animate.reorient(0, phi, 0, _point(center), height),
            run_time=run_time,
        )

    def untilt(self, run_time: float = 1.0):
        self._pop_frame(run_time)

    def orbit(self, degrees: float):
        """기울인 판을 세로축으로 degrees도 돌려 보는 카메라 애니메이션(재생하지 않고 돌려준다).

        tilt() 안에서만 쓴다. untilt()가 tilt 전 상태로 되돌리므로 따로 되감지 않는다.
            self.play(lay_down(m.animate), self.orbit(-14), run_time=0.9)
        """
        # 카메라 상태 스택이 비면(tilt/zoom_in 밖) 되돌릴 길이 없으므로 막는다.
        # zoom_in 안에서는 막지 못하니 tilt 안에서만 쓴다.
        if not self._frame_stack:
            raise RuntimeError("orbit은 tilt() 안에서만 쓴다(untilt가 되돌릴 카메라 상태가 없다)")
        return self.frame.animate.increment_theta(degrees * DEG)

    def _frame_scale(self) -> float:
        return self.frame.get_height() / FRAME_HEIGHT

    def carry(self, group, edge=LEFT, scale: float = 0.6, run_time: float = 1.0):
        """rel=carry: 앞 결과를 줄여 옆으로 밀고 빈자리를 비운다."""
        edge = np.array(edge, dtype=float)
        k = self._frame_scale()
        c = self.frame.get_center()
        w = group.get_width() * scale
        h = group.get_height() * scale
        target = group.get_center().copy()
        if abs(edge[0]) > 0:
            target[0] = c[0] + np.sign(edge[0]) * (CONTENT_X * k - w / 2)
        if edge[1] > 0:
            target[1] = c[1] + (FRAME_HEIGHT / 2 - 1.0) * k - h / 2
        elif edge[1] < 0:
            target[1] = c[1] + CAPTION_SAFE_Y * k + h / 2
        self.play(group.animate.scale(scale).move_to(target), run_time=run_time)

    def aside(self, group, angle_deg: float = 80, direction=LEFT, run_time: float = 1.0):
        """rel=aside: 앞 묶음을 통째로 옆으로 돌려 치운다(CLIP/main.py:436-438)."""
        direction = np.array(direction, dtype=float)
        sign = -1.0 if direction[0] < 0 else 1.0
        self.play(
            group.animate.rotate(sign * angle_deg * DEG, axis=UP).shift(
                direction * CONTENT_X * self._frame_scale()
            ),
            run_time=run_time,
        )

    def quote_card(self, image_path: str, run_time: float = 1.0) -> Mobject:
        """rel=quote: 뒤를 BLACK 0.75로 덮고 논문 크롭 카드를 오른쪽에서 들인다.

        반환한 Group(덮개, 카드)을 나중에 FadeOut하거나 clear_to로 치운다.
        밝은 카드는 카메라로 확대하지 않는다(자막 띠를 덮는다). 강조는 quote_focus로 한다.
        """
        k = self._frame_scale()
        c = self.frame.get_center()
        cover = Rectangle(width=FRAME_WIDTH * k * 1.02, height=FRAME_HEIGHT * k * 1.02)
        cover.set_fill(BLACK, opacity=OVERLAY_OPACITY).set_stroke(width=0, opacity=0)
        cover.move_to(c)
        p = Path(image_path)
        if not p.is_absolute() and (self._viz_dir / p).exists():
            p = self._viz_dir / p  # 에피소드 폴더 기준 상대 경로
        card = ImageMobject(str(p), height=FRAME_HEIGHT * k * 0.6)
        card.move_to(c + RIGHT * (FRAME_WIDTH * k / 2 + card.get_width() / 2 + 0.2))
        self.play(
            FadeIn(cover),
            card.animate.move_to(c),
            run_time=run_time,
        )
        return Group(cover, card)

    def quote_focus(self, card, keep=None, cover=None, run_time: float = 0.6):
        """rel=quote/point: 인용 카드에서 keep만 남기고 나머지를 BLACK 덮개로 가린다(재생함).

        밝은 카드는 카메라로 확대하지 않고 이 덮개로 강조한다(확대하면 카드가 자막 띠를 덮는다).
        - keep: 카드 안 비율 상자 (x0, y0, x1, y1), (0, 0)=왼쪽 위. 또는 Mobject(그 경계 상자).
        - cover: 앞서 이 메서드가 돌려준 덮개. 넘기면 그 덮개를 새 자리로 Transform한다(초점 옮기기).
        - keep=None이고 cover를 넘기면 덮개를 FadeOut하고 None을 돌려준다.
        돌려준 덮개(VGroup, 띠 4개)는 장면에 따로 올라가 있다. 카드를 치울 때 함께 FadeOut한다.

            q = self.quote_card("assets/fig1.png"); card = q[1]
            cov = self.quote_focus(card, (0, 0, 0.53, 1))        # 왼쪽 53%만 남김
            cov = self.quote_focus(card, (0.5, 0, 1, 1), cov)    # 오른쪽 절반으로 옮김
            self.play(FadeOut(q), FadeOut(cov))
        """
        if keep is None:
            if cover is not None:
                self.play(FadeOut(cover), run_time=run_time)
            return None
        new = focus_cover(card, keep)
        if cover is None:
            self.play(FadeIn(new), run_time=run_time)
            return new
        self.play(Transform(cover, new), run_time=run_time)
        return cover

    def clear_to(self, keep: list, run_time: float = 0.6):
        """rel=new: keep만 남기고 나머지를 FadeOut."""
        others = _others(self, keep)
        reg = _dim_registry(self)
        for m in others:
            reg.pop(id(m), None)
        if others:
            self.play(*[FadeOut(m) for m in others], run_time=run_time)
