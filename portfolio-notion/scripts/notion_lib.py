"""Shared helpers for the portfolio-notion scripts.

Configuration
- Working directory (default: cwd, or $PORTFOLIO_DIR) holds portfolio.config.json, schema.json,
  items.json, highlights.json, pages_custom/, pages/, backup/, logs/, state.json.
- Notion token: $NOTION_TOKEN, else the Notion MCP header in ~/.claude.json (OPENAPI_MCP_HEADERS).
- API versions: 2025-09-03 for data sources / pages / blocks, 2026-03-11 for views and page move.
"""
import json
import os
import re
import sys
import time
import datetime
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("PORTFOLIO_DIR") or os.getcwd()
CONFIG_PATH = os.environ.get("PORTFOLIO_CONFIG") or os.path.join(ROOT, "portfolio.config.json")
V_NEW = "2026-03-11"   # views, page move
V_STD = "2025-09-03"   # data sources, pages, blocks


def load_json(relpath):
    p = relpath if os.path.isabs(relpath) else os.path.join(ROOT, relpath)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, relpath):
    p = relpath if os.path.isabs(relpath) else os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return p


def load_state():
    try:
        return load_json("state.json")
    except FileNotFoundError:
        return {}


def save_state(state):
    return save_json(state, "state.json")


if not os.path.exists(CONFIG_PATH):
    raise SystemExit(f"portfolio.config.json not found at {CONFIG_PATH}. Copy assets/portfolio.config.example.json and fill main_page_id.")
CFG = load_json(CONFIG_PATH)
MAIN_PAGE = CFG["main_page_id"]
SCHEMA = load_json(CFG.get("schema", "schema.json"))


def _find_headers(o):
    if isinstance(o, dict):
        if "OPENAPI_MCP_HEADERS" in o:
            return o["OPENAPI_MCP_HEADERS"]
        for v in o.values():
            r = _find_headers(v)
            if r:
                return r
    elif isinstance(o, list):
        for v in o:
            r = _find_headers(v)
            if r:
                return r
    return None


def load_token():
    tok = os.environ.get("NOTION_TOKEN")
    if tok:
        return tok if tok.lower().startswith("bearer ") else "Bearer " + tok
    cj = os.path.join(os.path.expanduser("~"), ".claude.json")
    if os.path.exists(cj):
        with open(cj, encoding="utf-8") as f:
            h = _find_headers(json.load(f))
        if h:
            return json.loads(h)["Authorization"]
    raise SystemExit("No Notion token: set NOTION_TOKEN or configure the Notion MCP server in ~/.claude.json")


TOKEN = load_token()


def log(msg):
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    with open(os.path.join(ROOT, "logs", "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def api(method, path, body=None, ver=V_STD, headers=None, data=None):
    """Return parsed JSON. On HTTP error return {'error': code, 'body': text}. Retries 429/5xx."""
    payload = data if data is not None else (json.dumps(body).encode() if body is not None else None)
    for attempt in range(8):
        req = urllib.request.Request("https://api.notion.com/v1" + path, method=method, data=payload)
        req.add_header("Authorization", TOKEN)
        req.add_header("Notion-Version", ver)
        if data is None:
            req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = r.read()
                return json.loads(txt) if txt else {}
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="replace")
            if e.code == 429 or e.code >= 500:
                time.sleep(float(e.headers.get("Retry-After", "2")) + 0.5 * attempt)
                continue
            return {"error": e.code, "body": txt}
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 + attempt)
    return {"error": "retries_exhausted", "body": path}


def api_ok(method, path, body=None, ver=V_STD, **kw):
    r = api(method, path, body, ver, **kw)
    if isinstance(r, dict) and "error" in r:
        raise RuntimeError(f"{method} {path} -> {r['error']}: {str(r.get('body'))[:500]}")
    return r


def paginate(method, path, body=None, ver=V_STD):
    out, cursor = [], None
    while True:
        if method == "GET":
            p = path + ((("&" if "?" in path else "?") + f"start_cursor={cursor}") if cursor else "")
            r = api_ok("GET", p, ver=ver)
        else:
            b = dict(body or {})
            b.setdefault("page_size", 100)
            if cursor:
                b["start_cursor"] = cursor
            r = api_ok(method, path, b, ver=ver)
        out.extend(r.get("results", []))
        if not r.get("has_more"):
            return out
        cursor = r.get("next_cursor")


def children(block_id):
    return paginate("GET", f"/blocks/{block_id}/children?page_size=100")


def walk_blocks(block_id, depth=0, max_depth=12):
    out = []
    for b in children(block_id):
        if b.get("has_children") and depth < max_depth and b["type"] not in ("child_page", "child_database"):
            b["children"] = walk_blocks(b["id"], depth + 1, max_depth)
        out.append(b)
    return out


def rt(richtext):
    return "".join(t.get("plain_text", "") for t in (richtext or []))


def title_of(page):
    for p in page.get("properties", {}).values():
        if p.get("type") == "title":
            return rt(p["title"])
    return ""


def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "portfolio-notion"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())
    return os.path.getsize(dest)


# ---- rich text / block builders -------------------------------------------------------------
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def rich(s):
    """Markdown-lite to Notion rich_text: **bold**, `code`, [label](url). Splits >1900-char runs."""
    out = []
    for part in INLINE.split(s or ""):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append({"type": "text", "text": {"content": part[2:-2]}, "annotations": {"bold": True}})
        elif part.startswith("`") and part.endswith("`"):
            out.append({"type": "text", "text": {"content": part[1:-1]}, "annotations": {"code": True}})
        elif part.startswith("[") and "](" in part and part.endswith(")"):
            label, url = part[1:-1].split("](", 1)
            out.append({"type": "text", "text": {"content": label, "link": {"url": url}}})
        else:
            out.append({"type": "text", "text": {"content": part}})
    fixed = []
    for t in out:
        c = t["text"]["content"]
        while len(c) > 1900:
            head, c = c[:1900], c[1900:]
            fixed.append({**t, "text": {**t["text"], "content": head}})
        fixed.append({**t, "text": {**t["text"], "content": c}})
    return fixed


def blk(kind, body):
    return {"object": "block", "type": kind, kind: body}


def text_prop(s):
    return {"rich_text": [{"type": "text", "text": {"content": (s or "")[:1900]}}]} if s else {"rich_text": []}


def master_ids(state=None):
    state = state or load_state()
    if "ds_id" not in state:
        raise SystemExit("state.json has no ds_id: run 01_create_master.py first")
    return state["db_id"], state["ds_id"]


def prop_ids(state=None):
    state = state or load_state()
    _, ds = master_ids(state)
    d = api_ok("GET", f"/data_sources/{ds}")
    ids = {name: p["id"] for name, p in d["properties"].items()}
    state["prop_ids"] = ids
    save_state(state)
    return ids, d
