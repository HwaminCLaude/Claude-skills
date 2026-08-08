"""
notion_api.py — Notion REST 얇은 래퍼.

Claude에 붙은 Notion MCP 토큰이 만료(401)라 MCP 대신 .env 토큰으로 직접 호출한다.
- 평균 3 req/s 한도 → 기본 0.34s 간격 스로틀
- 429/5xx/소켓에러 지수 백오프 재시도
- 깨진 lone surrogate 제거 (400 no low surrogate 방지)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from nconfig import NOTION_VERSION, load_token

API = "https://api.notion.com/v1/"
_TOKEN: str | None = None
_last_call = 0.0
MIN_INTERVAL = 0.34  # 초 — 평균 3 req/s


def token() -> str:
    global _TOKEN
    if _TOKEN is None:
        _TOKEN = load_token()
    return _TOKEN


def desurrogate(obj):
    """깨진 lone surrogate(U+D800–DFFF) 제거 → 노션 '400 no low surrogate' 방지."""
    if isinstance(obj, str):
        return "".join(c for c in obj if not (0xD800 <= ord(c) <= 0xDFFF))
    if isinstance(obj, list):
        return [desurrogate(x) for x in obj]
    if isinstance(obj, dict):
        return {k: desurrogate(v) for k, v in obj.items()}
    return obj


class NotionError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"Notion {status}: {body[:500]}")
        self.status = status
        self.body = body


def request(path: str, method: str = "GET", body: dict | None = None,
            retries: int = 6) -> dict:
    """Notion API 호출. 스로틀 + 재시도 포함."""
    global _last_call
    url = API + path.lstrip("/")
    data = None
    if body is not None:
        data = json.dumps(desurrogate(body), ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token()}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    delay = 1.0
    for attempt in range(retries):
        gap = time.monotonic() - _last_call
        if gap < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - gap)
        _last_call = time.monotonic()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            # 429(rate limit) / 5xx 는 재시도, 4xx 는 즉시 실패
            if e.code == 429:
                wait = float(e.headers.get("Retry-After", delay))
                time.sleep(wait)
                delay = min(delay * 2, 30)
                continue
            if 500 <= e.code < 600 and attempt < retries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            raise NotionError(e.code, raw) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if attempt >= retries - 1:
                raise NotionError(0, str(e)) from None
            time.sleep(delay)
            delay = min(delay * 2, 30)
    raise NotionError(0, "재시도 소진")


# ── 자주 쓰는 호출 ──────────────────────────────────────────
def me() -> dict:
    return request("users/me")


def get_database(db_id: str) -> dict:
    return request(f"databases/{db_id}")


def get_data_source(ds_id: str) -> dict:
    return request(f"data_sources/{ds_id}")


def update_data_source(ds_id: str, properties: dict) -> dict:
    return request(f"data_sources/{ds_id}", "PATCH", {"properties": properties})


def create_page(parent: dict, properties: dict, children: list | None = None) -> dict:
    body = {"parent": parent, "properties": properties}
    if children:
        body["children"] = children
    return request("pages", "POST", body)


def update_page(page_id: str, properties: dict) -> dict:
    return request(f"pages/{page_id}", "PATCH", {"properties": properties})


def append_children(block_id: str, children: list) -> dict:
    return request(f"blocks/{block_id}/children", "PATCH", {"children": children})


def get_children(block_id: str, page_size: int = 100) -> list:
    out, cursor = [], None
    while True:
        q = f"blocks/{block_id}/children?page_size={page_size}"
        if cursor:
            q += f"&start_cursor={cursor}"
        r = request(q)
        out.extend(r.get("results", []))
        if not r.get("has_more"):
            return out
        cursor = r.get("next_cursor")


def query_all(ds_id: str, page_size: int = 100) -> list:
    out, cursor = [], None
    while True:
        body = {"page_size": page_size}
        if cursor:
            body["start_cursor"] = cursor
        r = request(f"data_sources/{ds_id}/query", "POST", body)
        out.extend(r.get("results", []))
        if not r.get("has_more"):
            return out
        cursor = r.get("next_cursor")


def archive_block(block_id: str) -> dict:
    return request(f"blocks/{block_id}", "DELETE")


# ── 블록 크기 방어 ──────────────────────────────────────────
def count_blocks(b: dict) -> int:
    """블록 + 모든 중첩 children 재귀 카운트 (노션 요청당 블록 한계 계산용)."""
    n = 1
    t = b.get("type")
    payload = b.get(t) or {}
    for k in (payload.get("children") or []):
        n += count_blocks(k)
    return n


def chunked_append(page_id: str, blocks: list, limit: int = 85) -> int:
    """중첩 children까지 세어 ≤limit 블록씩 안전 분할 append. 보낸 청크 수 반환."""
    chunks, cur, cur_n = [], [], 0
    for b in blocks:
        n = count_blocks(b)
        if cur and cur_n + n > limit:
            chunks.append(cur)
            cur, cur_n = [], 0
        cur.append(b)
        cur_n += n
    if cur:
        chunks.append(cur)
    for c in chunks:
        append_children(page_id, c)
    return len(chunks)


def find_subitem_props(ds: dict, ds_id: str) -> tuple[str | None, str | None]:
    """데이터소스 스키마에서 자기참조 relation 2개(상위/하위 항목)를 찾는다.

    Notion '하위 항목(Sub-items)' 을 UI에서 켜면 자기 자신을 가리키는 dual relation
    한 쌍이 생긴다. 어느 쪽이 '상위'인지는 dual_property 의 synced_property_name 으로
    판별할 수 없어서, 이름 힌트(상위/부모/parent)로 고른다.
    """
    self_rel = []
    for name, spec in (ds.get("properties") or {}).items():
        if spec.get("type") != "relation":
            continue
        rel = spec.get("relation") or {}
        target = rel.get("data_source_id") or rel.get("database_id") or ""
        if target.replace("-", "") in (ds_id.replace("-", ""),
                                       (ds.get("parent", {}).get("database_id") or "").replace("-", "")):
            self_rel.append(name)
        elif not target:
            self_rel.append(name)
    if len(self_rel) < 2:
        return (None, None)
    parent_hints = ("상위", "부모", "parent")
    parent = next((n for n in self_rel if any(h in n.lower() for h in parent_hints)), None)
    child = next((n for n in self_rel if n != parent), None)
    if parent is None:
        parent, child = self_rel[0], self_rel[1]
    return (parent, child)
