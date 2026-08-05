"""
config.py — book-outline-notion 파이프라인 공통 설정.

다른 PDF에 적용할 때 바꾸는 것은 **환경변수 2개**뿐이다.
    BOOK_ROOT     작업 폴더 (PDF가 들어있는 곳)
    BOOK_DB_ID    대상 Notion 데이터베이스 ID (URL 그대로 넣어도 됨)
    NOTION_TOKEN  없으면 <BOOK_ROOT>/.env 에서 읽는다

목차 쪽 범위·본문 범위는 00_preflight.py 가 자동 탐지해 알려주고,
확정한 값을 BOOK_TOC_FIRST/LAST, BOOK_BODY_FIRST/LAST 로 고정한다.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ── 경로 ────────────────────────────────────────────────────
ROOT = Path(os.environ.get("BOOK_ROOT", Path.cwd()))
OUT_DIR = ROOT / "_output"
FIG_DIR = ROOT / "_figures"
GEN_DIR = OUT_DIR / "gen"          # LLM 배치 산출물 (멱등 재개용)
SCHEMA_DIR = OUT_DIR / "schema"    # codex --output-schema 용 JSON Schema
PROMPT_DIR = OUT_DIR / "prompts"   # 서브에이전트 폴백용 프롬프트

TOC_JSON = OUT_DIR / "toc.json"
SECTIONS_JSON = OUT_DIR / "sections.json"
FIGURES_JSON = OUT_DIR / "figures.json"
FIGOCR_JSON = OUT_DIR / "figocr.json"
DRIVE_URLS = OUT_DIR / "drive_urls.json"
DRIVE_FILES = OUT_DIR / "drive_files.json"
SUMMARIES_JSON = OUT_DIR / "summaries.json"
PAGE_BLOCKS = OUT_DIR / "page_blocks.json"
QA_JSON = OUT_DIR / "qa.json"
STATE_JSON = OUT_DIR / "notion_state.json"

for _d in (OUT_DIR, GEN_DIR, SCHEMA_DIR, PROMPT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def find_pdf() -> Path:
    """작업 폴더의 대상 PDF. BOOK_PDF 로 강제 지정 가능."""
    env = os.environ.get("BOOK_PDF")
    if env:
        return Path(env)
    pdfs = sorted(ROOT.glob("*.pdf"))
    if not pdfs:
        print(f"[ERROR] {ROOT} 에 PDF가 없습니다. BOOK_ROOT 를 확인하세요.",
              file=sys.stderr)
        sys.exit(1)
    if len(pdfs) > 1:
        print(f"[WARN] PDF가 {len(pdfs)}개입니다. '{pdfs[0].name}' 을 씁니다. "
              f"다른 파일이면 BOOK_PDF 로 지정하세요.", file=sys.stderr)
    return pdfs[0]


PDF_PATH = find_pdf()

# ── PDF 구조 (00_preflight.py 가 탐지해 알려준 값을 고정한다) ──
TOC_PAGE_FIRST = int(os.environ.get("BOOK_TOC_FIRST", 0))     # 0 = 자동 탐지
TOC_PAGE_LAST = int(os.environ.get("BOOK_TOC_LAST", 0))
BODY_FIRST = int(os.environ.get("BOOK_BODY_FIRST", 0))
BODY_LAST = int(os.environ.get("BOOK_BODY_LAST", 0))
EXPECTED_NODES = int(os.environ.get("BOOK_EXPECTED_NODES", 0))  # 0 = 게이트 끔

# 머리말/쪽번호 제거용 y 경계. A4 보고서(높이 841)에서 머리말 y0≈56, 쪽번호 y0≈776.
HEADER_Y = float(os.environ.get("BOOK_HEADER_Y", 70))
FOOTER_Y = float(os.environ.get("BOOK_FOOTER_Y", 765))

FIG_DPI = int(os.environ.get("BOOK_FIG_DPI", 200))

# ── Notion ──────────────────────────────────────────────────
def clean_id(v: str) -> str:
    """URL이든 32자리든 하이픈 유무 관계없이 UUID 형태로 정규화."""
    m = re.findall(r"[0-9a-fA-F]{32}", (v or "").replace("-", ""))
    if not m:
        return v or ""
    h = m[-1].lower()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


NOTION_DB_ID = clean_id(os.environ.get("BOOK_DB_ID", ""))
NOTION_DS_ID = clean_id(os.environ.get("BOOK_DS_ID", ""))   # 비우면 DB에서 자동 조회
NOTION_VERSION = os.environ.get("NOTION_VERSION", "2025-09-03")
TITLE_PROP = os.environ.get("BOOK_TITLE_PROP", "이름")

# DB 행으로 만들 목차 깊이. 3 = Ⅰ → 1. → 1) 까지만 행, 그 아래는 본문 소제목.
# 논리적 계층을 그대로 옮기면 행이 수백 개가 돼 사람이 훑을 수 없다. 3이 기본값.
MAX_DB_LEVEL = int(os.environ.get("BOOK_MAX_DB_LEVEL", 3))


def load_token() -> str:
    """NOTION_TOKEN 환경변수 → <ROOT>/.env 순으로 토큰을 찾는다.

    .env 는 `NOTION_TOKEN=ntn_...` 형식과 **토큰 값만 적힌 형식**을 모두 지원한다.
    """
    env_tok = os.environ.get("NOTION_TOKEN")
    if env_tok and env_tok.strip():
        return env_tok.strip()
    envfile = ROOT / ".env"
    if not envfile.exists():
        print(f"[ERROR] Notion 토큰이 없습니다. NOTION_TOKEN 환경변수를 두거나 "
              f"{envfile} 에 토큰을 적으세요.", file=sys.stderr)
        sys.exit(1)
    for raw in envfile.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cand = line.split("=", 1)[1].strip() if "=" in line else line
        cand = cand.strip().strip('"').strip("'")
        if cand.startswith(("ntn_", "secret_")):
            return cand
    print(f"[ERROR] {envfile} 에서 Notion 토큰(ntn_/secret_)을 찾지 못했습니다.",
          file=sys.stderr)
    sys.exit(1)


# ── rclone / Google Drive (그림 호스팅) ─────────────────────
RCLONE_BIN = os.environ.get("RCLONE_BIN", "rclone")
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
RCLONE_IMG_DEST = os.environ.get("BOOK_DRIVE_IMG", "book-outline/images")
RCLONE_FILE_DEST = os.environ.get("BOOK_DRIVE_FILES", "book-outline/files")

# ── LLM 백엔드 ──────────────────────────────────────────────
# "auto"  = codex CLI 가 있으면 codex, 없으면 프롬프트 파일만 쓰고 서브에이전트에 위임
# "codex" = codex 강제 (없으면 실패)
# "agent" = 항상 서브에이전트 위임
LLM_BACKEND = os.environ.get("BOOK_LLM_BACKEND", "auto")


def resolve_codex() -> str | None:
    """Windows 의 codex 는 npm 배치파일(codex.CMD)이라 이름만으로는 실행되지 않는다."""
    import shutil
    env = os.environ.get("CODEX_BIN")
    if env:
        return shutil.which(env) or (env if Path(env).exists() else None)
    return shutil.which("codex") or shutil.which("codex.cmd")


CODEX_BIN = resolve_codex()
OCR_BATCH = int(os.environ.get("BOOK_OCR_BATCH", 6))       # 이미지 장/호출
SUM_BATCH = int(os.environ.get("BOOK_SUM_BATCH", 25))      # 절 개수/호출

# ── 목차 번호 체계 ──────────────────────────────────────────
# 긴 패턴부터 먼저 시도해야 `1.1.1)` 이 `1.1)` 로 오인되지 않는다.
# 번호 체계가 다른 문서는 여기만 고치면 된다.
LEVEL_PATTERNS = [
    (6, re.compile(r"^(\d+\.\d+\.\d+)\)\s*(.+)$")),
    (5, re.compile(r"^(\d+\.\d+)\)\s*(.+)$")),
    (7, re.compile(r"^([a-z])\)\s*(.+)$")),
    (4, re.compile(r"^\((\d+)\)\s*(.+)$")),
    (3, re.compile(r"^(\d+)\)\s*(.+)$")),
    (2, re.compile(r"^(\d+)\.\s+(.+)$")),
    (1, re.compile(r"^([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)\.\s*(.+)$")),
]


def match_level(line: str):
    """목차/본문 한 줄 → (level, num, title) 또는 None."""
    for lv, pat in LEVEL_PATTERNS:
        m = pat.match(line)
        if m:
            return lv, m.group(1), m.group(2).strip()
    return None


def prefix_for(level: int, num: str) -> str:
    """레벨·번호 → 본문에 실제로 인쇄되는 헤딩 접두사.

    L1 `Ⅰ.` / L2 `1.` / L3 `1)` / L4 `(1)` / L5 `1.1)` / L6 `4.2.1)` / L7 `a)`
    """
    if level in (1, 2):
        return f"{num}."
    if level == 4:
        return f"({num})"
    return f"{num})"


def display_title(level: int, num: str, title: str) -> str:
    """DB 행 제목 = 번호 + 제목.

    번호를 빼면 '향후 전망'처럼 수십 번 반복되는 제목이 서로 구분되지 않는다.
    """
    return f"{prefix_for(level, num)} {title}"


def norm(s: str) -> str:
    """공백을 모두 제거한 비교용 정규화."""
    return re.sub(r"\s+", "", s or "")
