#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_code_units.py — src + graph.json 에서 함수/메서드별 '코드 단위'를 뽑아 units.json 생성.

각 단위: 전체 소스 텍스트(데코레이터 포함, lineno..end_lineno) + 시그니처 + docstring +
호출(out)·피호출(in) 엣지(가이드북 '연결'용). 모듈별로 묶는다.

사용: python extract_code_units.py <src_root> <graph.json> <out_units.json> [--pkg-root src]
"""
import ast, os, sys, json, argparse, collections

def relmod(path, root): return os.path.relpath(path, root).replace("\\","/")

def unit_source(src_lines, node):
    start = min([node.lineno] + [d.lineno for d in getattr(node,"decorator_list",[])])
    end = getattr(node, "end_lineno", node.lineno)
    return "\n".join(src_lines[start-1:end]).rstrip("\n"), start, end

def signature_of(node):
    # def 헤더 한 줄로 재구성(인자명 위주; 어노테이션/기본값은 소스에서 별도 확인 가능)
    a = node.args
    parts=[]
    posonly=getattr(a,"posonlyargs",[])
    for arg in posonly+a.args: parts.append(arg.arg)
    if posonly: parts.insert(len(posonly), "/")
    if a.vararg: parts.append("*"+a.vararg.arg)
    elif a.kwonlyargs: parts.append("*")
    for arg in a.kwonlyargs: parts.append(arg.arg)
    if a.kwarg: parts.append("**"+a.kwarg.arg)
    kw = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{kw} {node.name}({', '.join(parts)})"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("src_root"); ap.add_argument("graph"); ap.add_argument("out")
    ap.add_argument("--pkg-root", default=None)
    a=ap.parse_args()
    g=json.load(open(a.graph,encoding="utf-8"))
    label=g.get("plan","code")
    nidx={ n["mod"]+"::"+n["sym"]: n for n in g["nodes"] }
    # 엣지 맵(연결용): out=이 심볼이 부르는 것, in=이 심볼을 부르는 것
    out_edges=collections.defaultdict(list); in_edges=collections.defaultdict(list)
    for e in g["edges"]:
        s=e["src_mod"]+"::"+e["src_sym"]; d=e["dst_mod"]+"::"+e["dst_sym"]
        if s==d: continue
        out_edges[s].append(d); in_edges[d].append(s)

    files=[]
    for r,_,fs in os.walk(a.src_root):
        for f in fs:
            if f.endswith(".py"): files.append(os.path.join(r,f))
    files.sort()
    modules=collections.OrderedDict()
    total_units=0
    for p in files:
        rm=relmod(p, a.src_root)
        try:
            src=open(p,encoding="utf-8").read(); tree=ast.parse(src)
        except Exception as ex:
            continue
        src_lines=src.split("\n")
        mod_doc=ast.get_docstring(tree) or ""
        units=[]
        def add_unit(node, cls=None):
            nonlocal total_units
            code, start, end = unit_source(src_lines, node)
            sym = (cls+"." if cls else "")+node.name
            key = rm+"::"+sym
            node_meta = nidx.get(key, {})
            units.append({
                "sym": sym, "kind": ("method" if cls else "func"), "class": cls,
                "line": start, "end_line": end,
                "signature": signature_of(node),
                "docstring": (ast.get_docstring(node) or ""),
                "code": code,
                "url": node_meta.get("url",""),
                "calls": sorted(set(out_edges.get(key, []))),
                "called_by": sorted(set(in_edges.get(key, []))),
            })
            total_units+=1
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef, ast.AsyncFunctionDef)):
                add_unit(node)
            elif isinstance(node, ast.ClassDef):
                for b in node.body:
                    if isinstance(b,(ast.FunctionDef, ast.AsyncFunctionDef)):
                        add_unit(b, cls=node.name)
        units.sort(key=lambda u:u["line"])
        # 모듈 URL(첫 심볼 url에서 #Lxx 제거)
        mod_url=""
        for u in units:
            if u["url"]: mod_url=u["url"].split("#")[0]; break
        classes=[n.name for n in tree.body if isinstance(n, ast.ClassDef)]
        modules[rm]={"url":mod_url, "module_docstring":mod_doc, "classes":classes, "units":units}

    out={"label":label, "counts":{"modules":len(modules),"units":total_units}, "modules":modules}
    json.dump(out, open(a.out,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[{label}] modules={len(modules)} units={total_units} -> {a.out}")

if __name__=="__main__":
    main()
