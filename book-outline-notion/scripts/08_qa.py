"""
08_codex_qa.py — Stage C. 변환 결과를 원문과 대조 검수한다.

텍스트→블록 변환은 규칙 기반이라 빠르고 정확하지만, 규칙이 못 잡는 구석
(줄 이어붙이기 오류, 표·그림에 엉뚱한 출처가 붙음, 문단 경계 오인)이 있을 수 있다.
무작위 표본을 골라 **PDF 원문 줄 그대로** vs **변환 결과**를 Codex에 나란히 주고
누락·왜곡·오배치를 찾게 한다.

산출: _output/qa.json
사용: python scripts/08_codex_qa.py [--sample 30] [--seed 7]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).parent))
import llm_runner as R
import config as C

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["checks"],
    "properties": {
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "verdict", "issues"],
                "properties": {
                    "id": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["OK", "ISSUE"]},
                    "issues": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "발견한 문제. 없으면 빈 배열",
                    },
                },
            },
        }
    },
}

PROMPT_HEAD = """너는 PDF→노션 변환 결과를 검수한다. 아래 각 절마다
[원문] PDF에서 읽은 줄들(줄바꿈은 PDF의 물리적 줄바꿈이며 원래 한 문단이 여러 줄로 쪼개져 있다)
[변환] 노션에 넣을 블록으로 바꾼 결과
가 있다.

다음만 확인하고, 문제가 있으면 구체적으로 지적하라.
1. **누락**: 원문에 있는데 변환 결과에 없는 문장·표 셀·캡션·출처가 있는가?
2. **왜곡**: 글자가 바뀌거나, 줄을 이어붙이며 **띄어쓰기가 잘못**되었는가?
   (예: '문제 해결능력을' 처럼 붙으면 안 되는 곳이 붙음, 또는 '기술이 아 니라' 처럼 벌어짐)
3. **오배치**: `자료:` 출처가 엉뚱한 그림/표에 붙었는가? 표의 행·열이 뒤섞였는가?
   문단이 잘못 합쳐지거나 쪼개졌는가?

주의:
- 불릿 기호 `▣` 가 사라지고 블록 타입이 `bul` 로 바뀐 것은 **정상**이다.
- 그림은 이미지로 대체되어 `[figure]` 로만 표시된다. 이것도 **정상**이다.
- 표는 행 배열로 바뀐다. 셀 내용만 맞으면 **정상**이다.
- 문제가 없으면 verdict="OK", issues=[] 로 답하라. 억지로 흠을 찾지 마라.

출력은 JSON만. 인사말·코드펜스 금지.

{body}"""


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "ex", str(Path(__file__).parent / "02_extract_sections.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render_blocks(blocks: list[dict]) -> str:
    lines = []
    for b in blocks:
        t = b["type"]
        if t == "table":
            lines.append(f'[table] caption={b.get("caption","")!r} '
                         f'source={b.get("source","")!r}')
            for row in b.get("rows", []):
                lines.append("   " + " | ".join(row))
        elif t == "figure":
            lines.append(f'[figure] {b["label"]} {b.get("caption","")} '
                         f'source={b.get("source","")!r}')
        else:
            lines.append(f'[{t}] {b.get("text","")}')
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    sec = json.loads(C.SECTIONS_JSON.read_text(encoding="utf-8"))
    nodes = json.loads(C.TOC_JSON.read_text(encoding="utf-8"))

    print("원문 스트림 재구성 중…")
    ex = load_extractor()
    doc = fitz.open(C.PDF_PATH)
    stream = ex.build_stream(doc)
    pos, fails = ex.locate_headings(stream, nodes)
    if fails:
        # 02단계와 같은 게이트. 여기서 막지 않으면 아래 pos[...] 조회가 KeyError 난다.
        print(f"[ERROR] 헤딩 {len(fails)}개를 못 찾았습니다 "
              f"(예: {[f['display'][:30] for f in fails[:3]]}). "
              f"02단계를 다시 실행하세요.", file=sys.stderr)
        sys.exit(1)

    # 내용이 있는 절 위주로, 표·그림 포함 절을 우선 섞어 표본을 만든다
    cands = [n for n in nodes if len(sec[n["id"]]["blocks"]) >= 2]
    rich = [n for n in cands if sec[n["id"]]["n_table"] or sec[n["id"]]["n_figure"]]
    rng = random.Random(args.seed)
    pick = rng.sample(rich, min(len(rich), args.sample // 2)) + \
        rng.sample(cands, min(len(cands), args.sample - args.sample // 2))
    seen, sample = set(), []
    for n in pick:
        if n["id"] not in seen:
            seen.add(n["id"])
            sample.append(n)
    print(f"표본 {len(sample)}절 (표·그림 포함 우선)")

    idx = {n["id"]: i for i, n in enumerate(nodes)}
    docs = []
    for n in sample:
        i = idx[n["id"]]
        s = pos[n["id"]] + 1
        e = pos[nodes[i + 1]["id"]] if i + 1 < len(nodes) else len(stream)
        raw = []
        for it in stream[s:e]:
            if it["kind"] == "line":
                raw.append(it["text"])
            else:
                raw.append("[표] " + " || ".join(" | ".join(r) for r in it["rows"]))
        docs.append(f"### id={n['id']}  {sec[n['id']]['display']}\n"
                    f"[원문]\n" + "\n".join(raw) + "\n"
                    f"[변환]\n" + render_blocks(sec[n["id"]]["blocks"]))

    schema_path = R.write_schema("qa", SCHEMA)
    jobs = []
    for i in range(0, len(docs), args.batch):
        jobs.append({
            "key": f"qa_{i:03d}",
            "prompt": PROMPT_HEAD.format(body="\n\n".join(docs[i:i + args.batch])),
            "out_json": C.GEN_DIR / f"qa_{args.seed}_{i:03d}.json",
            "schema_path": schema_path,
            "timeout": 900,
        })
    todo = [j for j in jobs if not j["out_json"].exists()]
    print(f"배치 {len(jobs)}개 (남은 작업 {len(todo)}개)")
    if todo:
        R.run_parallel(todo, workers=args.workers, stage="qa")

    checks = []
    for j in jobs:
        if j["out_json"].exists():
            try:
                checks += json.loads(j["out_json"].read_text(encoding="utf-8")).get("checks", [])
            except json.JSONDecodeError:
                pass
    C.QA_JSON.write_text(json.dumps(checks, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    issues = [c for c in checks if c.get("verdict") == "ISSUE"]
    print(f"\n검수 {len(checks)}절 | 문제 있음 {len(issues)}절 → {C.QA_JSON}")
    for c in issues:
        print(f"\n  ✗ {c['id']} {sec.get(c['id'],{}).get('display','')[:44]}")
        for s in c.get("issues", []):
            print(f"      - {s}")
    if not issues:
        print("  ✅ 표본 전체 이상 없음")


if __name__ == "__main__":
    main()
