# -*- coding: utf-8 -*-
"""notion_direct_upload.py — 청크 JSON들을 Notion REST API로 직접 순차 append + 검증.

에이전트에 블록을 넘겨 재출력시키면 (1) 서브에이전트 32k output-token 한도에 걸려
대용량(수십 블록/청크) 업로드가 실패하고 (2) MCP 지연/5xx 재시도로 청크당 10~30분씩
걸린다. 이 스크립트는 통합 토큰으로 REST API에 직접 PATCH 해서 수백 블록을 수초 만에,
순서·원형 그대로(코드/이미지/수식/콜아웃 보존) 올린다.

토큰 출처(순서대로 시도, 스크립트는 토큰을 저장/출력하지 않음):
  1) 환경변수 OPENAPI_MCP_HEADERS (JSON 문자열; Authorization 헤더 포함)
  2) 환경변수 NOTION_TOKEN (secret_... / ntn_...)
  3) --config 파일(기본 ~/.claude.json)의 mcpServers.notion.env.OPENAPI_MCP_HEADERS

사용법:
  PYTHONUTF8=1 python notion_direct_upload.py <page_id> <chunk_dir> \
      [--glob "*.json"] [--config ~/.claude.json] [--expect N] [--verify]

  - <chunk_dir> 안에서 --glob 에 맞는 파일을 **이름순**으로 순차 업로드.
    각 파일 = 노션 블록 객체 배열(한 파일 ≤100블록 권장). build_guidebook.py 산출물
    (<prefix>_c01.json …) 을 그대로 넣으면 된다.
  - --verify: 업로드 후 페이지 자식 블록을 페이지네이션해 총 개수·타입 분포를 출력.
  - --expect N: --verify와 함께 쓰면 총 블록 수를 N과 대조.
"""
from __future__ import annotations
import argparse, glob as globmod, json, os, sys, time, urllib.request, urllib.error
from collections import Counter

API = "https://api.notion.com/v1"


def load_headers(config_path: str) -> dict:
    # 1) OPENAPI_MCP_HEADERS
    raw = os.environ.get("OPENAPI_MCP_HEADERS")
    headers = None
    if raw:
        try:
            headers = json.loads(raw)
        except Exception:
            headers = None
    # 2) NOTION_TOKEN
    if headers is None:
        tok = os.environ.get("NOTION_TOKEN")
        if tok:
            headers = {"Authorization": f"Bearer {tok}"}
    # 3) config 파일
    if headers is None:
        p = os.path.expanduser(config_path)
        if os.path.exists(p):
            cfg = json.load(open(p, encoding="utf-8"))
            env = (cfg.get("mcpServers", {}).get("notion", {}) or {}).get("env", {})
            if "OPENAPI_MCP_HEADERS" in env:
                headers = json.loads(env["OPENAPI_MCP_HEADERS"])
    if not headers or "Authorization" not in headers:
        sys.exit("[ERROR] Notion 토큰을 찾지 못했어. OPENAPI_MCP_HEADERS/NOTION_TOKEN 환경변수나 "
                 "--config(~/.claude.json)를 확인해.")
    headers.setdefault("Notion-Version", "2022-06-28")
    headers["Content-Type"] = "application/json"
    return headers


def request(method: str, url: str, headers: dict, body: bytes | None = None) -> dict:
    last = None
    for attempt in range(6):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8")[:300]
            last = f"HTTP {e.code} {msg}"
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(2 * (attempt + 1)); continue
            raise RuntimeError(last)
        except Exception as e:  # 소켓/타임아웃
            last = str(e)
            if attempt < 5:
                time.sleep(2 * (attempt + 1)); continue
            raise RuntimeError(last)
    raise RuntimeError(last or "unknown")


def upload(page_id: str, files: list[str], headers: dict) -> tuple[int, list[str]]:
    total, failed = 0, []
    for f in files:
        children = json.load(open(f, encoding="utf-8"))
        if not isinstance(children, list):
            print(f"  {os.path.basename(f)}: ❌ 최상위가 리스트 아님 — 건너뜀"); failed.append(f); continue
        body = json.dumps({"children": children}).encode("utf-8")
        try:
            data = request("PATCH", f"{API}/blocks/{page_id}/children", headers, body)
            n = len(data.get("results", []))
            total += n
            print(f"  {os.path.basename(f)}: OK (+{n}, expected {len(children)})")
        except Exception as e:
            print(f"  {os.path.basename(f)}: ❌ {e}"); failed.append(f)
        time.sleep(0.4)  # rate limit (~3 req/s)
    return total, failed


def verify(page_id: str, headers: dict, expect: int | None) -> None:
    types, total, cursor = Counter(), 0, None
    while True:
        url = f"{API}/blocks/{page_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        d = request("GET", url, headers)
        for b in d.get("results", []):
            types[b["type"]] += 1; total += 1
        if d.get("has_more"):
            cursor = d["next_cursor"]; time.sleep(0.34)
        else:
            break
    print(f"\n[검증] 페이지 총 블록: {total}" + (f" (기대 {expect})" if expect is not None else ""))
    print(f"[검증] 타입 분포: {dict(types)}")
    if expect is not None:
        print("[검증] 판정:", "OK ✅" if total == expect else "불일치 ⚠️ (누락/초과 점검)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page_id")
    ap.add_argument("chunk_dir")
    ap.add_argument("--glob", default="*.json")
    ap.add_argument("--config", default="~/.claude.json")
    ap.add_argument("--expect", type=int, default=None)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()

    headers = load_headers(a.config)
    files = sorted(globmod.glob(os.path.join(a.chunk_dir, a.glob)))
    if not files:
        sys.exit(f"[ERROR] 청크 없음: {a.chunk_dir}/{a.glob}")
    print(f"업로드 대상: {len(files)}개 청크 → page {a.page_id}")
    total, failed = upload(a.page_id, files, headers)
    print(f"\n총 추가 블록: {total} | 실패: {[os.path.basename(f) for f in failed] if failed else '없음'}")
    if a.verify or a.expect is not None:
        verify(a.page_id, headers, a.expect)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
