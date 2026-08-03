"""공통 유틸 — 설정 로딩, Notion API(레이트리밋 내장), rclone 헬퍼.

모든 스크립트가 이 모듈을 import 한다. 작업 폴더(`--work`)에 `config.json` 이 있어야 한다.
스키마는 references/CONFIG.md 참조.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────── 설정
_CFG: dict = {}
_WORK: Path = Path.cwd()


def init(work: str | Path | None = None) -> dict:
    """작업 폴더를 정하고 config.json 을 읽는다. 모든 스크립트가 맨 처음 호출한다."""
    global _CFG, _WORK
    argv = sys.argv
    if work is None and "--work" in argv:
        work = argv[argv.index("--work") + 1]
    _WORK = Path(work or os.environ.get("VTN_WORK") or Path.cwd()).resolve()
    path = _WORK / "config.json"
    if not path.exists():
        sys.exit(f"config.json 없음: {path}\nreferences/CONFIG.md 를 보고 만드세요.")
    _CFG = json.loads(path.read_text(encoding="utf-8"))
    out_dir().mkdir(parents=True, exist_ok=True)
    return _CFG


def cfg(key: str, default=None):
    cur = _CFG
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def work_dir() -> Path:
    return _WORK


def out_dir() -> Path:
    return _WORK / "_out"


def source_dir() -> Path:
    return Path(cfg("source_dir", str(_WORK)))


def rclone() -> str:
    return cfg("rclone_bin", "rclone")


def remote() -> str:
    return cfg("drive_remote", "")


def save_json(name: str, obj) -> Path:
    path = out_dir() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def load_json(name: str, default=None):
    path = out_dir() / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


# ────────────────────────────────────────────────────── Notion API
# 공개 API 는 통합앱당 평균 3 req/s. 넘기면 429 가 나고 **한 번 걸리면 몇 분간 전체가 막힌다**.
# 그래서 넉넉히 아래로 잡고, 429 면 길게 쉰다. 병렬 호출은 하지 말 것.
_RATE = threading.Semaphore(1)
_MIN_INTERVAL = 0.42          # ≈2.4 req/s
_last_call = [0.0]
_headers: dict = {}


def notion_token() -> str:
    """토큰 우선순위: config.notion.token → NOTION_TOKEN → ~/.claude.json 의 MCP 헤더."""
    token = cfg("notion.token") or os.environ.get("NOTION_TOKEN")
    if token:
        return token if token.startswith("Bearer ") else "Bearer " + token
    path = Path.home() / ".claude.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            hdr = json.loads(data["mcpServers"]["notion"]["env"]["OPENAPI_MCP_HEADERS"])
            return hdr["Authorization"]
        except Exception:
            pass
    sys.exit("Notion 토큰을 찾지 못했습니다. config.json 의 notion.token 이나 NOTION_TOKEN 환경변수를 설정하세요.")


def _hdrs() -> dict:
    global _headers
    if not _headers:
        _headers = {
            "Authorization": notion_token(),
            "Notion-Version": cfg("notion.version", "2022-06-28"),
            "Content-Type": "application/json",
        }
    return _headers


def _throttle() -> None:
    with _RATE:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()


def api(url: str, method: str = "GET", body: dict | None = None, retries: int = 6):
    """Notion REST 호출. 레이트리밋·429·5xx 를 알아서 처리한다."""
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        _throttle()
        try:
            req = urllib.request.Request(url, data=data, headers=_hdrs(), method=method)
            with urllib.request.urlopen(req, timeout=120) as fh:
                return json.loads(fh.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            if exc.code == 429:
                delay = max(int(exc.headers.get("Retry-After") or 0), 30 * (attempt + 1))
                print(f"  [429] {delay}초 대기 후 재시도 ({attempt + 1}/{retries})", flush=True)
                time.sleep(delay)
                continue
            if exc.code in (500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise RuntimeError(f"{method} {url} -> {exc.code} {detail}") from exc
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise
    raise RuntimeError(f"{method} {url} -> 재시도 {retries}회 실패")


def create_page(db_id: str, title: str, props: dict | None = None) -> str:
    body = {
        "parent": {"database_id": db_id},
        "properties": {
            cfg("notion.title_prop", "이름"): {"title": [{"text": {"content": title[:1900]}}]},
            **(props or {}),
        },
    }
    return api("https://api.notion.com/v1/pages", "POST", body)["id"]


def get_children(block_id: str) -> list[dict]:
    out, cursor = [], None
    while True:
        url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        res = api(url)
        out.extend(res["results"])
        if not res.get("has_more"):
            return out
        cursor = res["next_cursor"]


def query_db(db_id: str) -> list[dict]:
    out, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        res = api(f"https://api.notion.com/v1/databases/{db_id}/query", "POST", body)
        out.extend(res["results"])
        if not res.get("has_more"):
            return out
        cursor = res["next_cursor"]


def rich_text_of(block: dict) -> str:
    """블록의 텍스트. API 응답(plain_text)과 우리가 만든 요청 블록(text.content) 둘 다 처리한다."""
    body = block.get(block.get("type", ""), {})
    if not isinstance(body, dict) or "rich_text" not in body:
        return ""
    out = []
    for part in body["rich_text"]:
        out.append(part.get("plain_text") or (part.get("text") or {}).get("content", ""))
    return "".join(out)


def title_of(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop["type"] == "title":
            return "".join(x["plain_text"] for x in prop["title"])
    return ""


# ─────────────────────────────────────────────── 블록 조립 헬퍼
_INLINE = re.compile(r"(\*\*.+?\*\*|_.+?_|`.+?`)")


def to_rich_text(text: str) -> list[dict]:
    """**굵게** _이탤릭_ `코드` 를 노션 rich_text 로. 2000자에서 자른다."""
    if not text:
        return []
    out = []
    for part in _INLINE.split(text[:2000]):
        if not part:
            continue
        ann = {"bold": False, "italic": False, "code": False}
        content = part
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            ann["bold"], content = True, part[2:-2]
        elif part.startswith("_") and part.endswith("_") and len(part) > 2:
            ann["italic"], content = True, part[1:-1]
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            ann["code"], content = True, part[1:-1]
        if content:
            out.append({
                "type": "text", "text": {"content": content},
                "annotations": {"bold": False, "italic": False, "strikethrough": False,
                                "underline": False, "code": False, "color": "default", **ann},
            })
    return out


def para(text: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": to_rich_text(text)}}


def heading(text: str, level: int = 2, color: str = "default") -> dict:
    key = f"heading_{level}"
    return {"object": "block", "type": key,
            key: {"rich_text": to_rich_text(text), "is_toggleable": False, "color": color}}


def callout(text: str, emoji: str = "💡", color: str = "default") -> dict:
    return {"object": "block", "type": "callout",
            "callout": {"rich_text": to_rich_text(text),
                        "icon": {"type": "emoji", "emoji": emoji}, "color": color}}


def divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def embed(url: str) -> dict:
    """구글드라이브 영상은 반드시 embed 블록. video 블록은 Drive 링크를 거부한다."""
    return {"object": "block", "type": "embed", "embed": {"url": url}}


def desurrogate(obj):
    """깨진 lone surrogate 제거 — 노션이 '400 no low surrogate' 로 거부하는 걸 막는다."""
    if isinstance(obj, str):
        return "".join(c for c in obj if not 0xD800 <= ord(c) <= 0xDFFF)
    if isinstance(obj, list):
        return [desurrogate(x) for x in obj]
    if isinstance(obj, dict):
        return {k: desurrogate(v) for k, v in obj.items()}
    return obj


def count_blocks(block: dict) -> int:
    n = 1
    for kid in (block.get(block.get("type", ""), {}) or {}).get("children") or []:
        n += count_blocks(kid)
    return n


def append_blocks(page_id: str, blocks: list[dict], after: str | None = None,
                  limit: int = 85) -> None:
    """노션 100블록/요청 제한을 중첩까지 세어 안전 분할 append."""
    chunk, size = [], 0
    anchor = after
    for block in blocks:
        n = count_blocks(block)
        if chunk and size + n > limit:
            anchor = _flush(page_id, chunk, anchor)
            chunk, size = [], 0
        chunk.append(block)
        size += n
    if chunk:
        _flush(page_id, chunk, anchor)


def _flush(page_id: str, chunk: list[dict], anchor: str | None) -> str | None:
    body = {"children": desurrogate(chunk)}
    if anchor:
        body["after"] = anchor
    res = api(f"https://api.notion.com/v1/blocks/{page_id}/children", "PATCH", body)
    return res["results"][-1]["id"] if anchor and res.get("results") else anchor


# ──────────────────────────────────────────────────────── 시간 표기
def hhmmss(seconds: float | int | None) -> str:
    if seconds is None:
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ───────────────────────────────────────────────────────── rclone
def rclone_json(args: list[str], timeout: int = 300):
    proc = subprocess.run([rclone(), *args], capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout.decode("utf-8", "replace"))
    except Exception:
        return None


def drive_listing() -> dict[str, dict]:
    """원격 파일 목록. {상대경로: {ID, Size}}"""
    data = rclone_json(["lsjson", "-R", remote(), "--files-only"]) or []
    return {f["Path"].replace("\\", "/"): f for f in data}


def drive_access_token() -> str:
    """rclone 이 들고 있는 Drive 액세스 토큰. 만료면 rclone 을 한 번 돌려 갱신시킨다."""
    subprocess.run([rclone(), "lsd", remote().split(":")[0] + ":", "--max-depth", "1"],
                   capture_output=True, timeout=120)
    dump = subprocess.run([rclone(), "config", "dump"], capture_output=True)
    cfgd = json.loads(dump.stdout.decode("utf-8", "replace"))
    name = remote().split(":")[0]
    return json.loads(cfgd[name]["token"])["access_token"]


def detach(script: str, extra: list[str] | None = None) -> int:
    """스크립트를 콘솔과 분리된 프로세스로 띄운다(장시간 작업용). PID 반환."""
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    args = [sys.executable, str(Path(__file__).parent / script), "--work", str(_WORK)]
    args += extra or []
    proc = subprocess.Popen(args, creationflags=flags, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.pid
