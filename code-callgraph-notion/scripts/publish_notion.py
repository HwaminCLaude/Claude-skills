#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_notion.py — _diagrams.md(계층형 Mermaid 문서)를 Notion 페이지에 멱등 발행.

- 토큰: --token / env NOTION_TOKEN / ~/.claude.json > mcpServers.notion.env.OPENAPI_MCP_HEADERS 의 Bearer 순으로 탐색.
- 페이지의 기존 내용은 보존하고, 센티넬 heading(기본 텍스트 "원자단위 아키텍처")이 이미 있으면
  그 블록 + 이후 전부 삭제 후 재발행 -> 재실행 안전(멱등).
- Notion 코드블록 2000자 제한 -> mermaid 내용을 rich_text 다중 조각으로 분할. language "mermaid".

사용:
  python publish_notion.py <page_id> <diagrams_md> [--label plan2] [--sentinel "원자단위 아키텍처"] [--token ntn_xxx]

필수: pip install notion-client. 페이지가 통합(integration)과 공유돼 있어야 함.
"""
import json, os, re, sys, time, argparse
from notion_client import Client

def get_token(explicit=None):
    if explicit: return explicit
    if os.environ.get("NOTION_TOKEN"): return os.environ["NOTION_TOKEN"]
    p=os.path.expanduser("~/.claude.json")
    d=json.load(open(p,encoding="utf-8"))
    hdr=d["mcpServers"]["notion"]["env"]["OPENAPI_MCP_HEADERS"]
    h=json.loads(hdr)
    auth=h.get("Authorization") or h.get("authorization")
    return auth.split()[-1].strip()

def chunks(s, n=1900): return [s[i:i+n] for i in range(0, len(s), n)] or [""]
def rt(text): return [{"type":"text","text":{"content":c}} for c in chunks(text)]
def h(level,text): t=f"heading_{level}"; return {"object":"block","type":t,t:{"rich_text":rt(text)}}
def para(text): return {"object":"block","type":"paragraph","paragraph":{"rich_text":rt(text)}}
def quote(text): return {"object":"block","type":"quote","quote":{"rich_text":rt(text)}}
def code(m): return {"object":"block","type":"code","code":{"language":"mermaid","rich_text":rt(m)}}

def parse_md(md):
    lines=md.split("\n"); blocks=[]; i=0
    while i < len(lines):
        ln=lines[i]
        if ln.startswith("```mermaid"):
            i+=1; buf=[]
            while i < len(lines) and not lines[i].startswith("```"): buf.append(lines[i]); i+=1
            blocks.append(code("\n".join(buf))); i+=1; continue
        s=ln.strip()
        if not s: i+=1; continue
        if   s.startswith("### "): blocks.append(h(3,s[4:]))
        elif s.startswith("## "):  blocks.append(h(2,s[3:]))
        elif s.startswith("# "):   blocks.append(h(1,s[2:]))
        elif s.startswith("> "):   blocks.append(quote(s[2:]))
        else:                      blocks.append(para(s.strip("*")))
        i+=1
    return blocks

def list_children(client, page_id):
    kids=[]; cur=None
    while True:
        r=client.blocks.children.list(page_id, start_cursor=cur) if cur else client.blocks.children.list(page_id)
        kids+=r["results"]
        if not r.get("has_more"): break
        cur=r["next_cursor"]
    return kids

def clear_section(client, page_id, sentinel):
    kids=list_children(client, page_id); start=None
    for idx,b in enumerate(kids):
        if b["type"].startswith("heading"):
            txt="".join(t["plain_text"] for t in b[b["type"]]["rich_text"])
            if sentinel in txt: start=idx; break
    if start is None: return 0, len(kids)
    deleted=0
    for b in kids[start:]:
        if b.get("type")=="child_page": continue   # 하위 코드 가이드북 페이지는 보존
        try: client.blocks.delete(b["id"]); deleted+=1; time.sleep(0.05)
        except Exception as e: print("  del err", e)
    return deleted, len(kids)

def append_batched(client, page_id, blocks, size=90):
    for i in range(0, len(blocks), size):
        client.blocks.children.append(page_id, children=blocks[i:i+size]); time.sleep(0.2)
    return len(blocks)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("page_id"); ap.add_argument("diagrams_md")
    ap.add_argument("--label", default=""); ap.add_argument("--sentinel", default="원자단위 아키텍처")
    ap.add_argument("--token", default=None)
    a=ap.parse_args()
    client=Client(auth=get_token(a.token))
    blocks=parse_md(open(a.diagrams_md,encoding="utf-8").read())
    deleted, before = clear_section(client, a.page_id, a.sentinel)
    added=append_batched(client, a.page_id, blocks)
    print(f"[{a.label or a.page_id[:8]}] 기존자식={before} 삭제={deleted} 추가블록={added}")

if __name__=="__main__":
    main()
