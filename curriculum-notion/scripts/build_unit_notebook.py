# -*- coding: utf-8 -*-
"""build_unit_notebook.py — 유닛 spec → 6장 고정 구조 콜랩 노트북.

메타코드 `_scripts/build_lab_notebook.py` 의 nbformat 빌드 방식을 그대로 쓰되,
장 구성만 **코딩북 유닛용**으로 바꿨다.

  1장 준비물        환경 셋업 · import
  2장 눈으로 보기    개념을 작은 예로 먼저 관찰
  3장 직접 만들기    TODO 빈칸 — 여기서 학습자가 직접 짠다
  4장 맞는지 확인    라이브러리 정답과 대조 (자동 채점)
  5장 강의 자료 적용  실제 메타코드 데이터로
  6장 망가뜨리기      일부러 틀리게 해서 이론이 맞는지 확인

4장이 **자동 채점기**라 스스로 맞았는지 판정할 수 있다 — 이 노트북의 핵심.

    python build_unit_notebook.py units/W04U05.py [out.ipynb]
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent
OUT = HERE / "notebooks"

CHAPTERS = [
    ("setup", "1장 · 준비물", "필요한 라이브러리를 불러오고 재현 가능하게 시드를 고정해요."),
    ("explore", "2장 · 눈으로 보기", "개념을 아주 작은 예제로 먼저 관찰해요. 숫자가 몇 개 안 되니 손으로도 따라갈 수 있어요."),
    ("todo", "3장 · 직접 만들기", "여기가 핵심이에요. **빈칸(TODO)을 직접 채워** 보세요. 막히면 2장으로 돌아가요."),
    ("check", "4장 · 맞는지 확인", "내가 짠 게 맞는지 **라이브러리 정답과 대조**해요. 전부 ✅ 가 나오면 성공이에요."),
    ("apply", "5장 · 강의 자료에 적용", "실제 메타코드 강의 데이터로 같은 걸 해봐요."),
    ("wreck", "6장 · 망가뜨리기", "일부러 조건을 어겨서 **이론이 예측한 대로 망가지는지** 확인해요."),
]


def md(t: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(t.rstrip())


def code(t: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(t.rstrip())


def _header(mod) -> str:
    lines = [f"# {mod.TITLE}", "",
             f"> 🎯 **목표** — {mod.GOAL}", ""]
    if getattr(mod, "PREREQ", None):
        lines += [f"> 🧭 **먼저 알고 오세요** — {mod.PREREQ}", ""]
    lines += ["| 장 | 하는 일 |", "|---|---|"]
    for _, name, why in CHAPTERS:
        lines.append(f"| {name} | {why} |")
    lines += ["", "---",
              "**쓰는 법**: 위에서부터 셀을 차례로 실행하세요. "
              "3장의 `TODO` 를 직접 채운 뒤 4장을 돌리면 맞았는지 바로 채점돼요."]
    return "\n".join(lines)


def build(mod) -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    cells = [md(_header(mod))]
    for key, name, why in CHAPTERS:
        items = getattr(mod, "NB", {}).get(key)
        if not items:
            continue
        cells.append(md(f"## {name}\n\n{why}"))
        for kind, body in items:
            cells.append(md(body) if kind == "md" else code(body))

    # 정답은 **맨 끝에만** 둔다. 앞쪽(특히 1장)에 정답이 있으면 3장 TODO 가 무의미해진다.
    if getattr(mod, "SOLUTION", None):
        cells.append(md(
            "## 7장 · 정답 보기\n\n"
            "⚠️ **3장을 직접 해본 뒤에 여세요.** 먼저 보면 실력이 안 늘어요.\n\n"
            "막혔다면 답을 베끼지 말고, 어디서 갈렸는지만 확인하고 3장으로 돌아가 다시 써보세요."))
        cells.append(md("<details>\n<summary>정답 펼치기</summary>\n\n"
                        "```python\n" + mod.SOLUTION.strip() + "\n```\n\n</details>"))
    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    }
    return nb


def check(nb: nbf.NotebookNode, mod) -> list[str]:
    """생성된 노트북이 규약을 지켰는지."""
    errs = []
    src = "\n".join("".join(c["source"]) if isinstance(c["source"], list) else c["source"]
                    for c in nb["cells"])
    have = {k for k, _, _ in CHAPTERS if getattr(mod, "NB", {}).get(k)}
    for must in ("setup", "explore", "todo", "check"):
        if must not in have:
            errs.append(f"필수 장 누락: {must}")
    if "TODO" not in src:
        errs.append("3장에 TODO 빈칸이 없음")
    chk = "\n".join(b for k, b in getattr(mod, "NB", {}).get("check", []) if k == "code")
    if not any(t in chk for t in ("allclose", "assert", "np.testing")):
        errs.append("4장에 자동 채점(allclose/assert)이 없음")
    if not any(c["cell_type"] == "code" for c in nb["cells"]):
        errs.append("코드 셀이 없음")
    return errs


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = m
    spec.loader.exec_module(m)
    return m


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    p = Path(sys.argv[1])
    mod = load(p)
    nb = build(mod)
    errs = check(nb, mod)
    OUT.mkdir(parents=True, exist_ok=True)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT / f"{p.stem}.ipynb"
    out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    n_code = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
    print(f"{out.name}  셀 {len(nb['cells'])} (코드 {n_code})")
    if errs:
        print("[규약 위반]")
        for e in errs:
            print("  -", e)
        return 1
    print("규약 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
