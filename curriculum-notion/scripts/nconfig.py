# -*- coding: utf-8 -*-
"""nconfig.py — Notion 토큰/버전만 담은 최소 설정 (이식용).

토큰 우선순위
  1. 환경변수 NOTION_TOKEN
  2. 환경변수 NOTION_ENV_FILE 이 가리키는 파일
  3. 이 폴더 또는 상위 폴더의 .env
.env 는 `NOTION_TOKEN=ntn_...` 형식과 **토큰 값만 한 줄** 형식을 모두 지원한다.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

NOTION_VERSION = os.environ.get("NOTION_VERSION", "2025-09-03")
TITLE_PROP = os.environ.get("NOTION_TITLE_PROP", "이름")


def _from_file(p: Path) -> str | None:
    if not p.exists():
        return None
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cand = line.split("=", 1)[1].strip() if "=" in line else line
        cand = cand.strip().strip('"').strip("'")
        if cand.startswith(("ntn_", "secret_")):
            return cand
    return None


def load_token() -> str:
    tok = os.environ.get("NOTION_TOKEN", "").strip()
    if tok:
        return tok
    envfile = os.environ.get("NOTION_ENV_FILE")
    if envfile:
        got = _from_file(Path(envfile))
        if got:
            return got
    here = Path(__file__).resolve().parent
    for d in (here, *here.parents[:3]):
        got = _from_file(d / ".env")
        if got:
            return got
    print("[ERROR] Notion 토큰을 찾지 못했습니다. NOTION_TOKEN 환경변수를 설정하거나 "
          ".env 에 ntn_ 토큰을 넣으세요.", file=sys.stderr)
    sys.exit(1)
