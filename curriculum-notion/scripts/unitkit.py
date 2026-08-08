# -*- coding: utf-8 -*-
"""unitkit.py — 유닛 저작·발행 공용 키트.

제공하는 것
  * 그림: matplotlib 한글 폰트 세팅, `save(fig, key)`
  * 이미지: Notion **File Upload API** 업로드 (Drive lh3 는 이 계정에서 작동 안 함)
  * 블록: `__IMG__:key` 자리표시자를 file_upload 블록으로 치환
  * 발행: 유닛 페이지 본문을 청크 단위로 **순차 1회** append + 블록 수 검증

유닛 저작 모듈(units/WxxUyy.py)이 지켜야 할 규약은 AUTHORING_CONTRACT.md 참조.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
IMG = HERE / "images"


import notion_api as N   # noqa: E402
import blocks as B       # noqa: E402

API = "https://api.notion.com/v1"


# ── 그림 ────────────────────────────────────────────────────────────────
def setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # 한글 폰트. monospace 까지 지정해야 `family="monospace"` 로 그린 글자가
    # DejaVu Sans Mono 로 떨어져 한글이 네모(두부)로 깨지는 걸 막는다.
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["font.sans-serif"] = ["Malgun Gothic", "AppleGothic", "NanumGothic",
                                       "DejaVu Sans"]
    plt.rcParams["font.monospace"] = ["D2Coding", "Malgun Gothic", "DejaVu Sans Mono"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140
    plt.rcParams["savefig.bbox"] = "tight"
    return plt


def figs_with_glyph_check(mod, plt) -> list[str]:
    """figs() 를 돌리면서 '글리프 없음' 경고를 잡아낸다.

    이 경고가 나면 그림 속 한글이 네모로 깨진 채 발행된다. 눈으로 안 보면 못 잡으므로
    경고를 수집해 preflight 에서 실패시킨다.
    """
    import warnings
    if not hasattr(mod, "figs"):
        return []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        mod.figs(plt)
    return [str(w.message) for w in caught
            if "missing from font" in str(w.message) or "Glyph" in str(w.message)]


def save(fig, key: str) -> str:
    """images/{key}.png 로 저장. 블록에서는 B.image(key) 로 참조한다."""
    IMG.mkdir(parents=True, exist_ok=True)
    p = IMG / f"{key}.png"
    fig.savefig(p)
    try:
        fig.clf()
    except Exception:
        pass
    return str(p)


# ── 이미지 업로드 (Notion 자체 호스팅) ───────────────────────────────────
def _auth() -> dict:
    return {"Authorization": f"Bearer {N.token()}", "Notion-Version": "2022-06-28"}


def upload_png(path: Path) -> str | None:
    """file_upload id 반환. id 는 **1회용**(블록 첨부 시 소모)."""
    a = _auth()
    r = None
    for i in range(4):
        r = requests.post(f"{API}/file_uploads",
                          headers={**a, "Content-Type": "application/json"},
                          data=json.dumps({"filename": path.name,
                                           "content_type": "image/png"}))
        if r.status_code == 200:
            break
        time.sleep(1.5 * (i + 1))
    else:
        print(f"  [실패 create] {path.name}: {r.status_code} {r.text[:120]}")
        return None
    fid = r.json()["id"]
    for i in range(4):
        with open(path, "rb") as f:
            r2 = requests.post(f"{API}/file_uploads/{fid}/send", headers=a,
                               files={"file": (path.name, f, "image/png")})
        if r2.status_code == 200 and r2.json().get("status") == "uploaded":
            return fid
        time.sleep(1.5 * (i + 1))
    print(f"  [실패 send] {path.name}: {r2.status_code} {r2.text[:120]}")
    return None


def resolve_images(blocks: list) -> tuple[list, int]:
    """블록 안의 `__IMG__:key` 를 file_upload 로 치환. (블록, 치환수)"""
    n = 0
    for b in blocks:
        if b.get("type") != "image":
            continue
        ext = (b.get("image") or {}).get("external") or {}
        url = ext.get("url", "")
        if not url.startswith("__IMG__:"):
            continue
        key = url.split(":", 1)[1]
        p = IMG / f"{key}.png"
        if not p.exists():
            raise FileNotFoundError(f"이미지 없음: {p}")
        fid = upload_png(p)
        if not fid:
            raise RuntimeError(f"업로드 실패: {key}")
        cap = b["image"].get("caption") or []
        b["image"] = {"type": "file_upload", "file_upload": {"id": fid}, "caption": cap}
        n += 1
        time.sleep(0.25)
    return blocks, n


# ── 발행 ────────────────────────────────────────────────────────────────
def count_children(page_id: str) -> int:
    n, cur = 0, None
    while True:
        q = f"blocks/{page_id}/children?page_size=100" + (f"&start_cursor={cur}" if cur else "")
        r = N.request(q)
        n += len(r.get("results") or [])
        if not r.get("has_more"):
            return n
        cur = r.get("next_cursor")


def clear_page(page_id: str) -> int:
    """본문 전체 삭제(재발행용). 부분 업로드된 페이지는 이어붙이지 말고 비우고 다시."""
    killed = 0
    while True:
        r = N.request(f"blocks/{page_id}/children?page_size=100")
        kids = r.get("results") or []
        if not kids:
            return killed
        for k in kids:
            N.archive_block(k["id"])
            killed += 1


def publish(page_id: str, blocks: list, *, replace: bool = True) -> int:
    """유닛 본문 발행. 청크 1개씩 **순차 1회** append (누적·중복 방지)."""
    if replace:
        had = clear_page(page_id)
        if had:
            print(f"  기존 블록 {had}개 정리")
    total = 0
    for i in range(0, len(blocks), 85):
        chunk = blocks[i:i + 85]
        N.request(f"blocks/{page_id}/children", "PATCH", {"children": chunk})
        total += len(chunk)
        print(f"    청크 {i // 85 + 1}: {len(chunk)}블록")
    got = count_children(page_id)
    print(f"  발행 {total} / 실제 {got}", "OK" if got == total else "⚠ 불일치")
    return got
