# -*- coding: utf-8 -*-
"""make_week_prompt.py — 주차별 Codex 저작 프롬프트를 생성한다.

curriculum.json 의 유닛 정의 + 실제 강의자료 파일 목록을 합쳐
`_prompts/W<NN>.md` 를 만든다. Codex 는 이 파일만 읽고 그 주차 유닛 전부를 작성한다.

    python make_week_prompt.py 4
    python make_week_prompt.py --all
"""
from __future__ import annotations

import os

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent

def _need(name: str, hint: str):
    """없으면 트레이스백 대신 무엇을 먼저 하라고 알려 준다."""
    import json as _j
    import sys as _s
    p = HERE / name
    if not p.exists():
        print(f"[!] {name} 가 없습니다. 먼저 {hint} 를 실행하세요.", file=_s.stderr)
        _s.exit(2)
    return _j.loads(p.read_text(encoding="utf-8"))

STAGE = Path(os.environ.get("CURRICULUM_MATERIALS", "materials"))
OUT = HERE / "_prompts"
CUR = _need("curriculum.json", "curriculum.py --dump")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def materials(folder: str) -> tuple[list[str], list[str], list[str]]:
    root = STAGE / folder
    if not root.is_dir():
        return [], [], []
    nbs, data, docs = [], [], []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        s = p.suffix.lower()
        if s == ".ipynb":
            nbs.append(rel)
        elif s in (".csv", ".pth", ".pkl", ".pickle", ".json", ".parquet"):
            data.append(rel)
        elif s in (".pdf", ".pptx", ".docx"):
            docs.append(rel)
    return nbs, data, docs


def build(week: int) -> Path:
    wk = next(w for w in CUR["weeks"] if w["week"] == week)
    units = [u for u in CUR["units"] if u["week"] == week]
    nbs, data, docs = materials(wk["folder"])

    L = [f"# {week}주차 유닛 저작 — {len(units)}개", "",
         "너는 '코딩북' 학습 커리큘럼의 유닛 저작자다.",
         "**기초지식이 전혀 없는 성인**이 코랩에서 따라하며 완전히 이해하도록 쓴다.", "",
         "## 먼저 읽을 것 (반드시)",
         "- `AUTHORING_CONTRACT.md` — 규약 전문. **모든 규칙을 지켜야 한다**",
         "- `units/W04U05.py` — **완성된 모범 예시**. 구조·어투·분량을 이것에 맞춰라",
         "- `scripts/blocks.py` — 블록 API",
         "",
         f"## 이번 주 주제", f"> {wk['intro']}", ""]

    done = [u for u in units if (HERE / "units" / f"{u['id']}.py").exists()]
    units = [u for u in units if u not in done]
    if done:
        L += ["## 이미 완성된 유닛 (수정 금지)", ""]
        L += [f"- `units/{u['id']}.py` — {u['title']}" for u in done]
        L += ["", "스타일 참고용으로 읽기만 하고 **고치지 마라**.", ""]

    L += ["## 만들 파일", ""]
    for u in units:
        L.append(f"### `units/{u['id']}.py`")
        L.append(f"- `UNIT = \"{u['id']}\"`")
        L.append(f"- `TITLE = \"{u['title']}\"`")
        L.append(f"- `GOAL = \"{u['goal']}\"`")
        L.append(f"- 유형 {u['type']} / 난이도 {u['level']} / 분량 약 {u['minutes']}분")
        if u["prereq"]:
            L.append(f"- `PREREQ` 는 바로 앞 유닛({u['prereq'][0]})의 내용을 한 줄로")
        L.append(f"- 이미지 key 접두사: `{u['id'].lower()}_`")
        L.append("")

    L += ["## '🧪 강의 자료에 적용' 섹션에 쓸 실제 경로", "",
          f"드라이브 루트: `메타코드 실습프로젝트/{wk['folder']}/`",
          "콜랩에서는 `/content/drive/MyDrive/메타코드 실습프로젝트/" + wk["folder"] + "/...`", ""]
    if nbs:
        L.append("**강사 노트북**")
        for x in nbs[:14]:
            L.append(f"- `{x}`")
        if len(nbs) > 14:
            L.append(f"- … 외 {len(nbs) - 14}개")
        L.append("")
    if data:
        L.append("**데이터 파일**")
        for x in data[:16]:
            L.append(f"- `{x}`")
        if len(data) > 16:
            L.append(f"- … 외 {len(data) - 16}개")
        L.append("")
    if docs:
        L.append("**강의자료(슬라이드)**")
        for x in docs[:10]:
            L.append(f"- `{x}`")
        L.append("")
    if not nbs:
        L += ["> ⚠️ 이 주차는 **강사 노트북이 없다**(슬라이드만). '적용' 섹션은 슬라이드 내용을",
              "> 근거로 **직접 만든 예제**로 구성하고, 어떤 슬라이드의 어느 주제인지 밝혀라.", ""]

    L += ["## 반드시 지킬 핵심 3가지", "",
          "1. **정답 누출 금지** — `setup`/`explore` 에 `todo` 의 정답을 넣지 마라.",
          "   이름만 바꾼 것(`_ref`, `_sol`)도 검사기가 잡는다. 관찰은 식을 그 자리에 직접 써라.",
          "2. **`SOLUTION` 필수** — `todo` 빈칸을 채운 정답 문자열. 이것만으로 `check` 가 통과해야 한다.",
          "3. **`check` 는 라이브러리와 대조** — `np.allclose`/`assert` 로 채점하고 통과 시 `print(\"✅ ...\")`.",
          "   라이브러리와 **관례가 다른 지점**(ddof, 내장 softmax, PCA 부호, cross-correlation,",
          "   sklearn 기본 규제 등)이 있으면 반드시 설명하고 코드에 반영해라.", "",
          "## 수식 섹션", "일반식만 쓰지 말고 **작은 예시 숫자를 직접 대입**해 한 줄씩 따라가게 하고,",
          "그 숫자가 코드 실행 결과와 **정확히 일치**해야 한다.", "",
          "## 검증 — 유닛마다 셋 다 통과시켜라", "```",
          "PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python preflight_unit.py units/<ID>.py",
          "PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python build_unit_notebook.py units/<ID>.py",
          "PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python verify_unit_nb.py units/<ID>.py",
          "```",
          "`verify_unit_nb.py` 는 **경고(FutureWarning/DeprecationWarning)도 에러로 잡는다**.",
          "전부 '통과' 가 뜰 때까지 고쳐라. 실패를 남겨두고 끝내지 마라.", "",
          "## 하지 말 것",
          "- 노션 API 호출 금지 (발행은 파이프라인이 한다). 모듈은 **블록 리스트만 반환**",
          f"- `units/W{week:02d}U*.py` 외 기존 파일 수정 금지",
          "- `B.code(src, \"text\")` 금지 → `\"plain text\"`",
          "- 무거운 학습(수십 분) 코드 금지. 검증이 돌아야 하니 **작은 데이터·적은 스텝**으로.",
          ]

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"W{week:02d}.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p


def main() -> int:
    weeks = ([w["week"] for w in CUR["weeks"]] if "--all" in sys.argv
             else [int(sys.argv[1])])
    for w in weeks:
        p = build(w)
        n = len([u for u in CUR["units"] if u["week"] == w])
        print(f"  W{w:02d}  유닛 {n}  →  {p.name}  ({p.stat().st_size:,}B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
