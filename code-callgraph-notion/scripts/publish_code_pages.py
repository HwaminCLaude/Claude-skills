#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_code_pages.py — units.json + glossary.json + specs.json 으로 plan 페이지 아래에
📖 개념·용어 개요 페이지 + 모듈당 1 코드 가이드북 페이지를 발행하고, 함수 블록 앵커를 수집.

LLM은 설명(개념/용어/입력/로직/출력)만 쓰고, 코드·연결(호출)·GitHub 링크는 여기서 units.json으로 삽입.
멱등: 같은 title의 child 페이지가 있으면 재사용(자식 블록 비우고 재발행).

사용:
  python publish_code_pages.py --plan-page <PAGE_ID> --github-base https://github.com/OWNER/REPO \
     --units units.json --glossary glossary.json --specs specs.json \
     --out-anchors anchors.json [--label plan1] [--token ntn_xxx]
"""
import os, sys, json, time, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from notion_blocks import block_from_spec, flatten_specs
from notion_client import Client

def get_token(explicit=None):
    if explicit: return explicit
    if os.environ.get("NOTION_TOKEN"): return os.environ["NOTION_TOKEN"]
    d=json.load(open(os.path.expanduser("~/.claude.json"),encoding="utf-8"))
    h=json.loads(d["mcpServers"]["notion"]["env"]["OPENAPI_MCP_HEADERS"])
    return (h.get("Authorization") or h.get("authorization")).split()[-1].strip()

def list_children(client, pid):
    kids=[]; cur=None
    while True:
        r=client.blocks.children.list(pid, start_cursor=cur) if cur else client.blocks.children.list(pid)
        kids+=r["results"]
        if not r.get("has_more"): break
        cur=r["next_cursor"]
    return kids

def child_page_map(client, parent_pid):
    m={}
    for b in list_children(client, parent_pid):
        if b.get("type")=="child_page":
            m[b["child_page"]["title"]]=b["id"]
    return m

def clear_children(client, pid):
    for b in list_children(client, pid):
        try: client.blocks.delete(b["id"]); time.sleep(0.05)
        except Exception as e: print("  del err", e)

def anchor_url(page_url, block_id):
    return f"{page_url}#{block_id.replace('-','')}"

def append_collect(client, pid, blocks, chunk=30):
    """청크 append + 반환된 top-level heading_2 블록 ID를 순서대로 수집."""
    heading_ids=[]
    for i in range(0, len(blocks), chunk):
        resp=client.blocks.children.append(pid, children=blocks[i:i+chunk])
        for b in resp["results"]:
            if b["type"]=="heading_2": heading_ids.append(b["id"])
        time.sleep(0.34)
    return heading_ids

# ---------- 블록 빌더 ----------
def build_overview_blocks(gloss):
    specs=[
        {"type":"callout","emoji":"🎯","color":"orange_background",
         "text":f"**이 프로젝트가 뭘 하려는 건가** — {gloss.get('problem','')}"},
        {"type":"p","text":f"**핵심 아이디어** — {gloss.get('idea','')}"},
        {"type":"p","text":f"**전체 흐름** — {gloss.get('flow','')}"},
        {"type":"divider"},
        {"type":"h2","text":"📖 용어집 — 모르는 말이 나오면 여기서 찾기"},
        {"type":"bul","items":[f"**{g['term']}** — {g['def']}" for g in gloss.get("glossary",[])]},
    ]
    return flatten_specs(specs)

def build_module_blocks(mod, spec, umod, mod_url, glossary_url, github_base, trace=None, drive_urls=None):
    trace=trace or {}; drive_urls=drive_urls or {}
    by_sym={u["sym"]:u for u in umod["units"]}
    blocks=[]; func_order=[]
    blocks.append(block_from_spec({"type":"h1","text":f"{mod} — {spec.get('title','')}"}))
    goal=spec.get("module_concept","")
    if spec.get("prerequisites"): goal+=f"\n**미리 알면 좋은 것**: {spec['prerequisites']}"
    blocks.append(block_from_spec({"type":"callout","emoji":"🎯","color":"blue_background","text":goal}))
    stages=[]
    for i,f in enumerate(spec.get("functions",[]),1):
        short=(f.get("concept","").replace("\n"," ").split(". ")[0])[:44]
        stages.append({"n":i,"name":f["sym"],"role":short})
    if stages:
        blocks+=flatten_specs([{"type":"flowmap","goal":spec.get("flowmap_goal",""),"stages":stages}])
    blocks.append(block_from_spec({"type":"divider"}))
    for f in spec.get("functions",[]):
        u=by_sym.get(f["sym"])
        if not u: continue
        func_order.append(f["sym"])
        blocks.append(block_from_spec({"type":"h2","text":u["signature"]}))
        blocks.append(block_from_spec({"type":"p","text":f"💡 **개념** — {f.get('concept','')}"}))
        terms=f.get("terms") or []
        if terms:
            blocks+=flatten_specs([{"type":"bul","items":[
                f"📖 **{t['term']}** — {t['def']} ([용어집]({glossary_url}))" for t in terms]}])
        if f.get("formula_latex"):
            blocks.append(block_from_spec({"type":"p","text":"📐 **수식** (이 함수가 계산하는 식)"}))
            blocks.append(block_from_spec({"type":"eq","expression":f["formula_latex"]}))
        # 입력 + 주요 인자/하이퍼파라미터 표(bul)
        blocks.append(block_from_spec({"type":"p","text":f"📥 **입력(Input)** — {f.get('input','')}"}))
        args=f.get("args") or []
        if args:
            items=[]
            for a in args:
                s=f"`{a.get('name','')}` — {a.get('meaning','')}"
                if a.get('note'): s+=f" · 권장/주의: {a['note']}"
                items.append(s)
            blocks+=flatten_specs([{"type":"bul","items":items}])
        # 로직(큰 흐름)
        logic=f.get("logic") or []
        if logic:
            blocks.append(block_from_spec({"type":"p","text":"⚙️ **로직(Logic) — 큰 흐름**"}))
            blocks+=flatten_specs([{"type":"num","items":logic}])
        # 예시로 따라가기 (실제 실행값 + 그림)
        tf=trace.get("funcs",{}).get(mod+"::"+f["sym"])
        if f.get("example_note") or tf:
            blocks.append(block_from_spec({"type":"p","text":"🔢 **예시로 따라가기** (아래 값은 실제 코드 실행 결과)"}))
            if f.get("example_note"): blocks.append(block_from_spec({"type":"p","text":f["example_note"]}))
            if tf:
                lines=[]
                for k,v in (tf.get("inputs") or {}).items(): lines.append(f"입력 {k} = {v}")
                lines.append(f"출력 (shape {tf.get('output_shape')}) = {tf.get('output')}")
                if tf.get("note"): lines.append(f"→ {tf['note']}")
                blocks.append(block_from_spec({"type":"code","language":"text","code":"\n".join(str(x) for x in lines)}))
                fk=tf.get("fig")
                if fk and drive_urls.get(fk):
                    blocks.append(block_from_spec({"type":"image","url":drive_urls[fk]}))
        # 코드 전체(toggle) + 한 줄씩 풀이
        blocks.append(block_from_spec({"type":"toggle","text":"▶ 코드 전체 보기",
            "children":[{"type":"code","language":"python","code":u["code"]}]}))
        lbl=f.get("line_by_line") or []
        if lbl:
            blocks.append(block_from_spec({"type":"p","text":"🔬 **코드 한 줄씩 풀이**"}))
            blocks+=flatten_specs([{"type":"bul","items":[
                f"`{it.get('code','')}` → {it.get('explain','')}" for it in lbl]}])
        # 출력
        blocks.append(block_from_spec({"type":"p","text":f"📤 **출력(Output)** — {f.get('output','')}"}))
        # 연결
        conn=[]
        for d in u.get("calls",[]):
            tmod,tsym=d.split("::"); url=mod_url.get(tmod)
            if url: conn.append(f"→ 이 함수가 부름: [{tsym} ({tmod})]({url})")
        for s in u.get("called_by",[]):
            smod,ssym=s.split("::"); url=mod_url.get(smod)
            if url: conn.append(f"← 이 함수를 부르는 곳: [{ssym} ({smod})]({url})")
        if conn:
            blocks.append(block_from_spec({"type":"p","text":"🔗 **연결(어디로 이어지나)**"}))
            blocks+=flatten_specs([{"type":"bul","items":conn}])
        # 실무 팁
        if f.get("tip_engineering"):
            blocks.append(block_from_spec({"type":"callout","emoji":"⚙️","color":"blue_background",
                "text":f"**실무 팁** — {f['tip_engineering']}"}))
        if f.get("tip_practice"):
            blocks.append(block_from_spec({"type":"callout","emoji":"💼","color":"gray_background",
                "text":f"**실무에서는** — {f['tip_practice']}"}))
        # 원본
        gh=f"{github_base}/blob/main/src/{mod}#L{u['line']}"
        blocks.append(block_from_spec({"type":"callout","emoji":"🔗","color":"default_background",
            "text":f"[GitHub 원본 소스 (L{u['line']})]({gh})"}))
        blocks.append(block_from_spec({"type":"divider"}))
    # ✅ 핵심 체크리스트 (h3 → 함수 앵커로 수집 안 됨)
    checklist=spec.get("checklist") or []
    if checklist:
        blocks.append(block_from_spec({"type":"h3","text":"✅ 이 파일에서 꼭 기억할 것"}))
        blocks+=flatten_specs([{"type":"num","items":checklist}])
    return blocks, func_order

def page_url_of(client, pid):
    return client.pages.retrieve(pid)["url"]

def ensure_page(client, parent_pid, title, existing):
    # 멱등: 같은 title 페이지가 있으면 통째로 아카이브(1콜) 후 새로 생성.
    if title in existing:
        try: client.blocks.delete(existing[title]); time.sleep(0.1)
        except Exception as e: print("  archive err", e)
    p=client.pages.create(parent={"type":"page_id","page_id":parent_pid},
                          properties={"title":{"title":[{"text":{"content":title}}]}})
    return p["id"], p["url"]

def create_child_page(client, parent_pid, title):
    p=client.pages.create(parent={"type":"page_id","page_id":parent_pid},
                          properties={"title":{"title":[{"text":{"content":title}}]}})
    return p["id"], p["url"]

def _data_source_id(client, db_id):
    ds=(client.databases.retrieve(db_id).get("data_sources") or [])
    return ds[0]["id"] if ds else None

def db_title_prop(client, db_id):
    # 새 API: 속성은 data_source에 있음. 없으면 흔한 기본값 fallback.
    try:
        dsid=_data_source_id(client, db_id)
        if dsid:
            dsr=client.request(path=f"data_sources/{dsid}", method="GET")
            for name,pr in (dsr.get("properties") or {}).items():
                if pr.get("type")=="title": return name
    except Exception as e:
        print("  title prop 감지 실패(기본 '이름'):", str(e)[:100])
    return "이름"

def db_rows(client, db_id):
    # 새 API: data_sources/{id}/query 로 행 조회(구 databases.query 제거됨). 실패 시 빈 dict(멱등 생략).
    rows={}
    try:
        dsid=_data_source_id(client, db_id)
        if not dsid: return rows
        cur=None
        while True:
            body={"start_cursor":cur} if cur else {}
            r=client.request(path=f"data_sources/{dsid}/query", method="POST", body=body)
            for pg in r.get("results",[]):
                t=""
                for pr in (pg.get("properties") or {}).values():
                    if pr.get("type")=="title": t="".join(x["plain_text"] for x in pr["title"]); break
                rows[t]=pg["id"]
            if not r.get("has_more"): break
            cur=r["next_cursor"]
    except Exception as e:
        print("  db_rows 조회 실패(멱등 생략):", str(e)[:120])
    return rows

def ensure_db_row(client, db_id, title, existing, tprop):
    if title in existing:
        try: client.blocks.delete(existing[title]); time.sleep(0.1)
        except Exception as e: print("  archive err", e)
    p=client.pages.create(parent={"type":"database_id","database_id":db_id},
                          properties={tprop:{"title":[{"text":{"content":title}}]}})
    return p["id"], p["url"]

# ── 파이프라인 관통 페이지(예시 데이터 전체 흐름) ──
_PIPE_SEQ=["models/encoders.py::EncoderMLP.forward",
 "nmfc/affinity.py::pairwise_sqdist","nmfc/affinity.py::median_sigma2","nmfc/affinity.py::soft_neighbor_weights",
 "nmfc/energy.py::local_energies","nmfc/energy.py::mean_scale","nmfc/energy.py::geometric_logits",
 "nmfc/losses.py::nmfc_loss"]

def build_pipeline_page(trace, drive_urls):
    b=[block_from_spec({"type":"h1","text":"🔢 예시 데이터로 보는 전체 흐름 (실제 숫자 트레이스)"})]
    b.append(block_from_spec({"type":"callout","emoji":"🧭","color":"orange_background",
        "text":f"{trace.get('example_desc','')}  ·  최종 예측 {trace.get('pred')} (정답 {trace.get('y')}). 아래 값·그림은 전부 실제 코드 실행 결과예요."}))
    if drive_urls.get("scatter"): b.append(block_from_spec({"type":"image","url":drive_urls["scatter"]}))
    b.append(block_from_spec({"type":"divider"}))
    funcs=trace.get("funcs",{}); i=0
    for key in _PIPE_SEQ:
        tf=funcs.get(key)
        if not tf: continue
        i+=1; mod,sym=key.split("::")
        b.append(block_from_spec({"type":"h3","text":f"{i}. {sym}  ({mod})"}))
        if tf.get("note"): b.append(block_from_spec({"type":"p","text":tf["note"]}))
        lines=[f"입력 {k} = {v}" for k,v in (tf.get('inputs') or {}).items()]
        lines.append(f"출력 (shape {tf.get('output_shape')}) = {tf.get('output')}")
        b.append(block_from_spec({"type":"code","language":"text","code":"\n".join(str(x) for x in lines)}))
        fk=tf.get("fig")
        if fk and drive_urls.get(fk): b.append(block_from_spec({"type":"image","url":drive_urls[fk]}))
    return b

# ── DB 폴더구조 발행(통합 1벌) ──
def publish_db_folder(client, db_id, units, gloss, specs, trace, drive_urls, github_base, out_anchors, label):
    tprop=db_title_prop(client, db_id)
    existing=db_rows(client, db_id)
    mods=[m for m in units if m in specs]
    ov_pid, ov_url = ensure_db_row(client, db_id, gloss.get("title","📖 개념·용어 개요"), existing, tprop)
    append_collect(client, ov_pid, build_overview_blocks(gloss))
    src_pid, src_url = ensure_db_row(client, db_id, "📁 src (코드 폴더)", existing, tprop)
    dirs={}; root=[]
    for m in mods:
        (dirs.setdefault(m.split("/")[0],[]).append(m) if "/" in m else root.append(m))
    folder_pid={}
    for d in dirs:
        pid,_=create_child_page(client, src_pid, f"📁 {d}"); folder_pid[d]=pid; time.sleep(0.15)
    mod_pid={}; mod_url={}
    for m in mods:
        parent = folder_pid[m.split("/")[0]] if "/" in m else src_pid
        pid,url = create_child_page(client, parent, m); mod_pid[m]=pid; mod_url[m]=url; time.sleep(0.15)
    print(f"[{label}] 폴더 {len(dirs)}개 · 모듈 {len(mods)}개 생성")
    anchors={}
    for m in mods:
        blocks, order = build_module_blocks(m, specs[m], units[m], mod_url, ov_url, github_base, trace, drive_urls)
        hids=append_collect(client, mod_pid[m], blocks)
        for sym,bid in zip(order,hids): anchors[m+"::"+sym]=anchor_url(mod_url[m], bid)
        print(f"  {m}: 블록 {len(blocks)} · 앵커 {len(order)}")
    pp_pid, pp_url = ensure_db_row(client, db_id, "🔢 예시 데이터로 보는 전체 흐름", existing, tprop)
    append_collect(client, pp_pid, build_pipeline_page(trace, drive_urls))
    json.dump({"label":label,"overview_url":ov_url,"pipeline_url":pp_url,"src_page":src_pid,"module_urls":mod_url,"anchors":anchors},
              open(out_anchors,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[{label}] 앵커 {len(anchors)}개 · 개요 {ov_url} · 관통 {pp_url}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--plan-page", default=None); ap.add_argument("--parent-db", default=None)
    ap.add_argument("--github-base", required=True)
    ap.add_argument("--units", required=True); ap.add_argument("--glossary", required=True)
    ap.add_argument("--specs", required=True); ap.add_argument("--out-anchors", required=True)
    ap.add_argument("--trace", default=None); ap.add_argument("--drive-urls", default=None)
    ap.add_argument("--label", default=""); ap.add_argument("--token", default=None)
    a=ap.parse_args()
    client=Client(auth=get_token(a.token))
    units=json.load(open(a.units,encoding="utf-8"))["modules"]
    gloss=json.load(open(a.glossary,encoding="utf-8"))
    specs=json.load(open(a.specs,encoding="utf-8"))
    trace=json.load(open(a.trace,encoding="utf-8")) if a.trace else {}
    drive_urls=json.load(open(a.drive_urls,encoding="utf-8")) if a.drive_urls else {}

    if a.parent_db:
        publish_db_folder(client, a.parent_db, units, gloss, specs, trace, drive_urls, a.github_base, a.out_anchors, a.label)
        return

    existing=child_page_map(client, a.plan_page)
    ov_pid, ov_url = ensure_page(client, a.plan_page, gloss.get("title","📖 개념·용어 개요"), existing)
    append_collect(client, ov_pid, build_overview_blocks(gloss))
    mods=[m for m in units.keys() if m in specs]
    mod_pid={}; mod_url={}
    for mod in mods:
        pid, url = ensure_page(client, a.plan_page, mod, existing); mod_pid[mod]=pid; mod_url[mod]=url
    anchors={}
    for mod in mods:
        blocks, func_order = build_module_blocks(mod, specs[mod], units[mod], mod_url, ov_url, a.github_base, trace, drive_urls)
        hids=append_collect(client, mod_pid[mod], blocks)
        for sym,bid in zip(func_order, hids): anchors[mod+"::"+sym]=anchor_url(mod_url[mod], bid)
        print(f"  {mod}: 블록 {len(blocks)} · 함수앵커 {len(func_order)}")
    json.dump({"label":a.label,"overview_url":ov_url,"module_urls":mod_url,"anchors":anchors},
              open(a.out_anchors,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[{a.label}] 앵커 {len(anchors)}개 -> {a.out_anchors}")

if __name__=="__main__":
    main()
