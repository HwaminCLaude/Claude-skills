#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ast_graph.py — Python 패키지의 원자단위(함수/클래스/메서드) 호출그래프 추출기 (stdlib ast만).

무엇을 하나:
- 절대 import(예: `from <pkg>.x.y import z`)와 `__init__.py` 재수출을 **import 스코프**로 해석해
  함수/클래스 호출 엣지를 높은 정밀도로 뽑는다.
- `__init__`/`forward`/`update` 같은 흔한 이름의 전역 오결선을 피하려고, 엣지는
  (a) import된 심볼 호출, (b) 코드베이스 전체에서 '고유한' 메서드명 호출만 인정한다.
- 각 심볼의 소스 lineno를 담아 GitHub `blob/<ref>/<prefix>/<mod>#Lxx` 딥링크 URL을 만든다.

산출: <out_dir>/graph.json  { plan, github_base, counts, nodes[], edges[] }
  node = {mod, sym, kind(class|func|method), line, subsys, url}
  edge = {src_mod, src_sym, dst_mod, dst_sym, kind(import-call|method-call|local-call), count}

사용:
  python ast_graph.py <src_root> <out_dir> \
      [--pkg-root src] [--github-base https://github.com/OWNER/REPO] \
      [--ref main] [--url-prefix src] [--label myproj]

주의:
- <src_root>는 패키지 루트 디렉터리(그 안에 __init__.py 및 하위 모듈). --pkg-root 는 import에서 쓰는
  최상위 패키지명(코드가 `from src.x import y`면 src). 보통 <src_root>의 폴더명과 같다.
- --url-prefix 는 repo 루트에서 <src_root>까지의 경로(예: 코드가 repo의 src/ 아래면 "src").
"""
import ast, os, sys, json, argparse, collections

DUNDER = {"__init__","__len__","__getitem__","__iter__","__call__","__repr__","__enter__","__exit__"}
COMMON_AMBIG = {"forward","update","predict","reset","step","state_dict","load_state_dict","fit"}

def relmod(path, root): return os.path.relpath(path, root).replace("\\","/")

def dotted_to_rel(mod, pkg_root, modset=None):
    parts = mod.split(".")
    if parts and parts[0] == pkg_root: parts = parts[1:]
    if not parts: return "__init__.py"
    base = "/".join(parts)
    as_module, as_package = base+".py", base+"/__init__.py"
    if modset is not None:
        if as_module in modset: return as_module
        if as_package in modset: return as_package
    return as_module

def collect(root):
    files=[]
    for r,_,fs in os.walk(root):
        for f in fs:
            if f.endswith(".py"): files.append(os.path.join(r,f))
    files.sort()
    mods=collections.OrderedDict(); trees={}
    for p in files:
        rm=relmod(p,root)
        try: tree=ast.parse(open(p,encoding="utf-8").read())
        except Exception as e:
            mods[rm]={"error":str(e)}; continue
        trees[rm]=tree
        info={"classes":{}, "functions":{}, "methods":collections.OrderedDict()}
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                info["classes"][node.name]=node.lineno
                mm=collections.OrderedDict()
                for b in node.body:
                    if isinstance(b,(ast.FunctionDef, ast.AsyncFunctionDef)): mm[b.name]=b.lineno
                info["methods"][node.name]=mm
            elif isinstance(node,(ast.FunctionDef, ast.AsyncFunctionDef)):
                info["functions"][node.name]=node.lineno
        mods[rm]=info
    return mods, trees

def build_reexports(trees):
    reexport={}
    for rm,tree in trees.items():
        if not rm.endswith("__init__.py"): continue
        pkg_dir=rm[:-len("__init__.py")].rstrip("/")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level>=1 and node.module:
                target_rel=(pkg_dir+"/" if pkg_dir else "")+node.module.replace(".","/")+".py"
                for a in node.names:
                    reexport[(pkg_dir, a.asname or a.name)]=target_rel
    return reexport

def symbol_owner(mods, name):
    hits=[]
    for rm,info in mods.items():
        if "error" in info: continue
        if name in info.get("classes",{}): hits.append((rm,"class"))
        if name in info.get("functions",{}): hits.append((rm,"func"))
    return hits

def build_import_table(tree, mods, reexports, pkg_root):
    modset=set(mods.keys()); tbl={}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level==0:
            if not (node.module==pkg_root or node.module.startswith(pkg_root+".")): continue
            target_rel=dotted_to_rel(node.module, pkg_root, modset)
            is_pkg=target_rel.endswith("__init__.py")
            pkg_dir=target_rel[:-len("__init__.py")].rstrip("/") if is_pkg else None
            for a in node.names:
                local=a.asname or a.name; orig=a.name
                if is_pkg:
                    rx=reexports.get((pkg_dir, orig))
                    if rx: tbl[local]=(rx, orig)
                    else:
                        owners=symbol_owner(mods, orig)
                        tbl[local]=(owners[0][0], orig) if len(owners)==1 else (target_rel, orig)
                else:
                    tbl[local]=(target_rel, orig)
    return tbl

def unique_method_index(mods):
    idx=collections.defaultdict(list)
    for rm,info in mods.items():
        if "error" in info: continue
        for cls,mm in info.get("methods",{}).items():
            for mname in mm: idx[mname].append((rm,cls))
    return idx

def iter_defs(tree):
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node
        elif isinstance(node, ast.ClassDef):
            for b in node.body:
                if isinstance(b,(ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield node.name+"."+b.name, b

def extract_edges(mods, trees, reexports, pkg_root):
    umeth=unique_method_index(mods); edges=collections.Counter()
    for rm,tree in trees.items():
        if "error" in mods.get(rm,{}): continue
        tbl=build_import_table(tree, mods, reexports, pkg_root)
        local_funcs=set(mods[rm].get("functions",{})) | set(mods[rm].get("classes",{}))
        for qual, defnode in iter_defs(tree):
            for n in ast.walk(defnode):
                if not isinstance(n, ast.Call): continue
                f=n.func
                if isinstance(f, ast.Name):
                    nm=f.id
                    if nm in tbl:
                        dst_mod,orig=tbl[nm]; edges[(rm,qual,dst_mod,orig,"import-call")]+=1
                    elif nm in local_funcs:
                        edges[(rm,qual,rm,nm,"local-call")]+=1
                elif isinstance(f, ast.Attribute):
                    attr=f.attr
                    if attr in DUNDER or attr in COMMON_AMBIG: continue
                    hits=umeth.get(attr,[])
                    if len(hits)==1:
                        dm,cls=hits[0]; edges[(rm,qual,dm,cls+"."+attr,"method-call")]+=1
    return edges

def subsys_of(m):
    top=m.split("/")[0]
    return top if top!=m else "root"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("src_root"); ap.add_argument("out_dir")
    ap.add_argument("--pkg-root", default=None, help="import 최상위 패키지명(기본: src_root 폴더명)")
    ap.add_argument("--github-base", default="", help="https://github.com/OWNER/REPO")
    ap.add_argument("--ref", default="main")
    ap.add_argument("--url-prefix", default=None, help="repo 루트→src_root 경로(기본: pkg-root)")
    ap.add_argument("--label", default="graph")
    a=ap.parse_args()
    pkg_root=a.pkg_root or os.path.basename(os.path.normpath(a.src_root))
    url_prefix=a.url_prefix if a.url_prefix is not None else pkg_root

    mods, trees = collect(a.src_root)
    reexports = build_reexports(trees)
    edges = extract_edges(mods, trees, reexports, pkg_root)

    def url(rm, ln):
        if not a.github_base: return ""
        pre=(url_prefix+"/") if url_prefix else ""
        return f"{a.github_base}/blob/{a.ref}/{pre}{rm}#L{ln}"
    nodes=[]
    for rm,info in mods.items():
        if "error" in info: continue
        ss=subsys_of(rm)
        for c,ln in info.get("classes",{}).items():
            nodes.append({"mod":rm,"sym":c,"kind":"class","line":ln,"subsys":ss,"url":url(rm,ln)})
        for fn,ln in info.get("functions",{}).items():
            nodes.append({"mod":rm,"sym":fn,"kind":"func","line":ln,"subsys":ss,"url":url(rm,ln)})
        for cls,mm in info.get("methods",{}).items():
            for mn,ln in mm.items():
                nodes.append({"mod":rm,"sym":cls+"."+mn,"kind":"method","line":ln,"subsys":ss,"url":url(rm,ln)})
    edge_list=[{"src_mod":s,"src_sym":b,"dst_mod":c,"dst_sym":d,"kind":k,"count":n}
               for (s,b,c,d,k),n in edges.items()]
    nclass=sum(len(i.get("classes",{})) for i in mods.values() if "error" not in i)
    counts={"files":sum(1 for m in mods if "error" not in mods[m]), "classes":nclass,
            "funcs_methods":len(nodes)-nclass, "nodes":len(nodes), "edges":len(edge_list)}
    os.makedirs(a.out_dir, exist_ok=True)
    json.dump({"plan":a.label,"github_base":a.github_base,"counts":counts,"nodes":nodes,"edges":edge_list},
              open(os.path.join(a.out_dir,"graph.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[{a.label}] files={counts['files']} classes={counts['classes']} "
          f"funcs/methods={counts['funcs_methods']} nodes={counts['nodes']} edges={counts['edges']} "
          f"-> {os.path.join(a.out_dir,'graph.json')}")

if __name__=="__main__":
    main()
