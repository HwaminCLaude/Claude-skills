"""Extract a notebook or source tree into codebase.json (Stage 1, code input).

The code branch of this skill is organised around **data flow** — what a piece
of data looks like at each step and how its shape changes. So this parser does
not just list functions; it hunts for the shape evidence a video needs:

- `torch.Size([...])` in cell outputs — actual measured shapes
- `# (B, T, D)` style shape comments the author left in the code
- reshape/view/permute/stack/cat/pad calls — the places shape changes
- markdown headings — the author's own chapter boundaries

    python parse_code.py --input notebook.ipynb --out C:\\manimwork\\my-code
    python parse_code.py --input src/ --out <root>          # .py tree

Run with the PROJECT VENV python if the notebook is large; stdlib only otherwise.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


# Windows consoles default to cp949 here, and every one of these scripts prints
# Korean. Without this, a run dies with UnicodeEncodeError *after* it has already
# written its output files — the confusing failure mode of looking broken while
# actually having succeeded.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# torch.Size([64, 1]) / (64, 512) style shapes printed by a cell
SIZE_OUT = re.compile(r"torch\.Size\(\[([^\]]*)\]\)|Size\(\[([^\]]*)\]\)")
# author's own annotations: # (B, T, D)  |  #(B,T,D)  |  # (B, 2*D)
# Dims only — an ordinary prose comment that happens to start with a capital and
# contain a comma must not be mistaken for a shape.
SHAPE_COMMENT = re.compile(
    r"#\s*\(\s*([BTDLNCHWS0-9][BTDLNCHWS0-9\s,\*\+\-]*)\)\s*$")
# operations where a tensor's shape actually changes
RESHAPE_OP = re.compile(
    r"\.(?:reshape|view|permute|transpose|squeeze|unsqueeze|flatten|expand|repeat)\(|"
    r"torch\.(?:stack|cat|zeros|ones|full|roll)\(|F\.pad\(|pack_padded_sequence\(|"
    r"pad_packed_sequence\("
)
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)


def load_cells(path: Path) -> list[dict]:
    """Notebook cells, or one pseudo-cell per .py file."""
    if path.suffix == ".ipynb":
        nb = json.loads(path.read_text(encoding="utf-8"))
        cells = []
        for i, c in enumerate(nb.get("cells", [])):
            source = "".join(c.get("source", []))
            outputs = []
            for o in c.get("outputs", []):
                text = o.get("text") or (o.get("data") or {}).get("text/plain")
                if text:
                    outputs.append("".join(text) if isinstance(text, list) else text)
                elif "image/png" in (o.get("data") or {}):
                    outputs.append("<image output>")
            cells.append({"index": i, "type": c.get("cell_type"),
                          "source": source, "outputs": outputs})
        return cells

    if path.is_dir():
        cells = []
        for i, f in enumerate(sorted(path.rglob("*.py"))):
            if "__pycache__" in f.parts:
                continue
            cells.append({"index": i, "type": "code", "file": str(f),
                          "source": f.read_text(encoding="utf-8", errors="replace"),
                          "outputs": []})
        return cells

    return [{"index": 0, "type": "code", "file": str(path),
             "source": path.read_text(encoding="utf-8", errors="replace"), "outputs": []}]


def defs_in(source: str) -> list[dict]:
    """Top-level and nested classes / functions, without executing anything."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []  # notebook magics (!pip, nn.RNN?) are not valid Python
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            bases = [ast.unparse(b) for b in node.bases]
            found.append({"kind": "class", "name": node.name,
                          "bases": bases, "methods": methods, "lineno": node.lineno})
        elif isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            found.append({"kind": "function", "name": node.name,
                          "args": args, "lineno": node.lineno})
    return found


def imports_in(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names += [f"{node.module}.{a.name}" for a in node.names]
    return names


def shapes_from_outputs(outputs: list[str]) -> list[str]:
    found = []
    for out in outputs:
        for m in SIZE_OUT.finditer(out):
            dims = (m.group(1) or m.group(2) or "").strip()
            if dims:
                found.append(f"({dims})")
    return found


def shape_comments(source: str) -> list[str]:
    found = []
    for line in source.splitlines():
        m = SHAPE_COMMENT.search(line.rstrip())
        if m:
            tag = m.group(1).strip()
            # The regex already demands literal parens and a dims-only charset, so
            # prose cannot reach here. Keep the shape-ish guard anyway: a real
            # annotation is either multi-dim ("B, T, D") or a single short dim.
            if 1 <= len(tag) <= 40 and ("," in tag or len(tag) <= 4):
                found.append(f"({tag})")
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description="노트북·코드 → codebase.json (Stage 1)")
    ap.add_argument("--input", required=True, help=".ipynb 파일 / .py 파일 / 소스 디렉터리")
    ap.add_argument("--out", required=True, help="프로젝트 루트")
    ap.add_argument("--dump-text", action="store_true", help="code.txt도 저장")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise SystemExit(f"입력을 찾을 수 없습니다: {src}")
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cells = load_cells(src)

    sections: list[dict] = []
    all_defs: list[dict] = []
    all_imports: set[str] = set()
    flow: list[dict] = []

    current = "(intro)"
    for c in cells:
        source, outs = c["source"], c["outputs"]
        if c["type"] == "markdown":
            m = HEADING.search(source)
            if m:
                current = m.group(1).strip()
                sections.append({"title": current, "cell": c["index"]})
            continue

        for d in defs_in(source):
            d["cell"] = c["index"]
            d["section"] = current
            all_defs.append(d)
        all_imports.update(imports_in(source))

        measured = shapes_from_outputs(outs)
        annotated = shape_comments(source)
        ops = sorted({m.group(0).strip("(") for m in RESHAPE_OP.finditer(source)})
        if measured or annotated or ops:
            flow.append({
                "cell": c["index"], "section": current,
                "measured_shapes": measured,      # 실행 결과에서 읽은 실제 shape
                "annotated_shapes": annotated,    # 저자가 주석으로 남긴 shape
                "reshape_ops": ops,               # shape가 바뀌는 지점
                "snippet": "\n".join(source.strip().splitlines()[:6]),
            })

    payload = {
        "source": str(src),
        "kind": "notebook" if src.suffix == ".ipynb" else "source",
        "cell_count": len(cells),
        "sections": sections,
        "imports": sorted(all_imports),
        "definitions": all_defs,
        "data_flow": flow,
    }
    dest = out_dir / "codebase.json"
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dump_text:
        txt = out_dir / "code.txt"
        with txt.open("w", encoding="utf-8") as fh:
            for c in cells:
                if not c["source"].strip():
                    continue
                tag = "MD " if c["type"] == "markdown" else "CODE"
                fh.write(f"\n--- [{c['index']:02d}] {tag} ---\n{c['source'].rstrip()}\n")
                for o in c["outputs"][:2]:
                    for line in [l for l in o.strip().splitlines() if l.strip()][:5]:
                        fh.write(f"   OUT> {line[:180]}\n")
        print(f"[parse_code] {txt}")

    print(f"[parse_code] {dest}")
    print(f"[parse_code] 셀 {len(cells)}개 · 섹션 {len(sections)}개 · "
          f"정의 {len(all_defs)}개 · shape 흐름 지점 {len(flow)}개")
    for s in sections:
        print(f"    cell {s['cell']:>3}  {s['title']}")
    print("  --- shape 증거가 있는 지점 ---")
    for f in flow[:20]:
        bits = (f["measured_shapes"] or []) + (f["annotated_shapes"] or [])
        print(f"    cell {f['cell']:>3}  {', '.join(bits) or '·'}"
              f"   [{', '.join(f['reshape_ops'][:3])}]")
    if len(flow) > 20:
        print(f"    ... (+{len(flow) - 20})")

    if args.json:
        print(json.dumps({"codebase_json": str(dest), "cells": len(cells),
                          "sections": len(sections), "flow_points": len(flow)},
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
