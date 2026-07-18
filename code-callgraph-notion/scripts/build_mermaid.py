#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_mermaid.py — graph.json(+layout+delta)에서 계층형 Mermaid 문서(_diagrams.md)를 결정론적으로 생성.

- 노드 라벨/URL/라인번호는 graph.json에서 verbatim -> 전사 오류 0.
- L1: layout.groups(모듈 집합)별 함수 호출 그래프(그룹 내부 엣지만 그려 cross-call 포착).
- L2: layout.chains(순서 있는 [src,dst,label] 엣지 리스트)로 실행 호출체인.
- delta.owned_modules/owned_symbols 노드는 toneDelta(굵은 주황)로 강조. intro_md/inactive_note 삽입.

사용:
  python build_mermaid.py <graph.json> <out_md> [--layout layout.json] [--delta delta.json]

layout.json (없으면 최상위 디렉터리별 자동 그룹 + 체인 없음):
{
  "title": "원자단위 아키텍처",
  "groups": [{"id":"g1","title":"...","modules":["a/b.py","c.py"]}, ...],
  "chains": [{"title":"...","edges":[["mod::sym","mod::sym","label"], ...]}, ...],
  "tones":  {"nmfc/":"toneIndigo", "models/":"toneAmber", "train.py":"toneMint"}   // 선택(접두사 매칭)
}
delta.json:
  {"owned_modules":[...], "owned_symbols":["mod::sym",...], "intro_md":"...", "inactive_note":"..."}
"""
import json, sys, re, argparse, collections

CLASSDEFS = """classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
classDef toneDelta fill:#fff7ed,stroke:#ea580c,stroke-width:3px,color:#7c2d12"""
PALETTE = ["toneBlue","toneAmber","toneMint","toneRose","toneIndigo","toneTeal","toneNeutral"]

def nid(key): return "n_"+re.sub(r'[^0-9A-Za-z]+','_', key)
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"'")

def tone_for(mod, tones):
    # 접두사/정확 매칭 우선
    best=None
    for pat,t in tones.items():
        if mod==pat or mod.startswith(pat):
            if best is None or len(pat)>len(best[0]): best=(pat,t)
    return best[1] if best else None

def auto_groups(nodes):
    tops=collections.OrderedDict()
    for n in nodes: tops.setdefault(n["subsys"], True)
    return [{"id":t,"title":t,"modules":sorted({n["mod"] for n in nodes if n["subsys"]==t})} for t in tops]

def render_nodes(node_keys, index, delta_set, tones, tone_fallback):
    by_mod=collections.OrderedDict()
    for k in node_keys: by_mod.setdefault(index[k]["mod"], []).append(k)
    lines=[]; classes=collections.defaultdict(list)
    for mod, keys in by_mod.items():
        lines.append(f'subgraph sg_{re.sub(r"[^0-9A-Za-z]+","_",mod)}["{esc(mod)}"]')
        for k in keys:
            lines.append(f'  {nid(k)}["{esc(index[k]["sym"])}"]')
            if index[k]["mod"] in delta_set or k in delta_set: cls="toneDelta"
            else: cls=tone_for(mod, tones) or tone_fallback(mod)
            classes[cls].append(nid(k))
        lines.append("end")
    return lines, classes

def flowchart(body, node_keys, index, classes):
    out=["```mermaid","flowchart TD",""]+body+[""]
    out+=[f'click {nid(k)} "{index[k]["url"]}"' for k in sorted(set(node_keys)) if index[k]["url"]]
    out+=["", CLASSDEFS]+[f'class {",".join(ids)} {cls}' for cls,ids in classes.items() if ids]
    out.append("```")
    return "\n".join(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("graph"); ap.add_argument("out_md")
    ap.add_argument("--layout", default=None); ap.add_argument("--delta", default=None)
    a=ap.parse_args()
    g=json.load(open(a.graph,encoding="utf-8"))
    index={ n["mod"]+"::"+n["sym"]: n for n in g["nodes"] }
    edges=g["edges"]
    layout=json.load(open(a.layout,encoding="utf-8")) if a.layout else {}
    title=layout.get("title","원자단위 아키텍처")
    groups=layout.get("groups") or auto_groups(g["nodes"])
    chains=layout.get("chains", [])
    tones=layout.get("tones", {})
    # 자동 톤 폴백(모듈 top-level별 순환 팔레트)
    tops=list(collections.OrderedDict((n["subsys"],1) for n in g["nodes"]))
    fallback_map={t:PALETTE[i%len(PALETTE)] for i,t in enumerate(tops)}
    tone_fallback=lambda mod: fallback_map.get(mod.split("/")[0], "toneNeutral")

    delta_set=set(); intro_md=""; inactive_note=""
    if a.delta:
        try:
            dc=json.load(open(a.delta,encoding="utf-8"))
            delta_set|=set(dc.get("owned_modules",[])); delta_set|=set(dc.get("owned_symbols",[]))
            intro_md=dc.get("intro_md","") or ""; inactive_note=dc.get("inactive_note","") or ""
        except FileNotFoundError: pass
    clean=lambda s:(s.replace("**","").replace("&lt;","<").replace("&gt;",">").replace("&amp;","&")).strip()
    intro_md, inactive_note = clean(intro_md), clean(inactive_note)

    doc=[f"# {title} — {g['plan']}  ·  코드 링크 = GitHub #Lxx\n"]
    doc.append(f"> 노드 = 함수/메서드(원자단위), 화살표 = 실제 호출/의존(정적 AST 추출). 각 노드를 누르면 GitHub 소스 라인으로 이동. "
               f"규모: 파일 {g['counts']['files']} · 클래스 {g['counts']['classes']} · 함수/메서드 {g['counts']['funcs_methods']} · 호출엣지 {g['counts']['edges']}.\n")
    if intro_md: doc+=["## 이 대상의 델타 (공유 코어 대비)\n", intro_md+"\n"]
    if inactive_note: doc.append(f"*비활성/미사용: {inactive_note}*\n")
    if delta_set: doc.append("*아래 다이어그램에서 굵은 주황 테두리 노드 = 신규 작성·처음 활성화·핵심 사용 원자단위.*\n")

    doc.append("## L1 — 서브시스템별 함수 호출 그래프\n")
    for grp in groups:
        modset=set(grp["modules"])
        nks=[k for k,n in index.items() if n["mod"] in modset]
        if not nks: continue
        body, classes = render_nodes(nks, index, delta_set, tones, tone_fallback); body.append("")
        seen=set()
        for e in edges:
            if e["src_mod"] in modset and e["dst_mod"] in modset:
                s=e["src_mod"]+"::"+e["src_sym"]; d=e["dst_mod"]+"::"+e["dst_sym"]
                if s in index and d in index and (s,d) not in seen:
                    seen.add((s,d)); body.append(f'{nid(s)} --> {nid(d)}')
        doc.append(f"### {grp['title']}")
        doc.append(f"*모듈: {', '.join(grp['modules'])} · 노드 {len(nks)} · 내부 엣지 {len(seen)}*\n")
        doc.append(flowchart(body, nks, index, classes)); doc.append("")

    if chains:
        doc.append("## L2 — 핵심 실행 호출체인\n")
        for ch in chains:
            cedges=ch["edges"]; nks=[]
            for s,d,_ in cedges:
                for x in (s,d):
                    if x in index and x not in nks: nks.append(x)
            missing=sorted({x for s,d,_ in cedges for x in (s,d) if x not in index})
            body, classes = render_nodes(nks, index, delta_set, tones, tone_fallback); body.append("")
            for s,d,lab in cedges:
                if s in index and d in index: body.append(f'{nid(s)} -->|"{esc(lab)}"| {nid(d)}')
            doc.append(f"### {ch['title']}")
            if missing: doc.append(f"*(그래프에 없는 심볼 생략: {missing})*")
            doc.append("")
            doc.append(flowchart(body, nks, index, classes)); doc.append("")

    open(a.out_md,"w",encoding="utf-8").write("\n".join(doc))
    print(f"[{g['plan']}] _diagrams.md: L1 {len(groups)} + L2 {len(chains)} 블록 -> {a.out_md}")

if __name__=="__main__":
    main()
