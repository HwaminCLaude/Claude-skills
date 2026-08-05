"""
06_codex_summaries.py — Stage B. 725개 절의 한 줄 요약을 Codex로 만든다.

입력은 절 원문 + 그 절 그림의 판독 결과(04단계)다. 그림 내용을 알고 요약하게 하려는
것이다. 자체 본문이 없는 부모 절(142개 중 115개)은 하위 목차 제목으로 요약한다.

산출: _output/summaries.json {node_id: "한 줄 요약"}
사용: python scripts/06_codex_summaries.py [--limit N] [--workers 5]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llm_runner as R
import config as C

MAX_TEXT = 1400          # 절 원문 최대 길이(최대가 1069자라 실제로 잘릴 일은 거의 없음)
MAX_OCR = 400            # 그림 판독은 요약 위주로만

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summaries"],
    "properties": {
        "summaries": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "summary"],
                "properties": {
                    "id": {"type": "string"},
                    "summary": {"type": "string",
                                "description": "그 절의 핵심을 담은 한 문장(한국어, 100자 이내)"},
                },
            },
        }
    },
}

PROMPT_HEAD = """너는 「생성형 AI 및 AI 에이전트 기반 산업 자동화 시장 기술동향과 디지털 전환전략」
보고서를 노션으로 옮기는 편집자다. 아래 각 절에 대해 **한 줄 요약**을 쓴다.

요약 규칙:
- 한국어 한 문장, **100자 이내**. 문장은 '~한다/~이다' 체로 끝낸다.
- 그 절을 안 읽은 사람이 무슨 내용인지 바로 알 수 있게, **구체적인 내용**을 담는다.
  ("이 절은 ~를 설명한다" 같은 빈 껍데기 금지. 실제 결론·수치·구성요소를 넣어라.)
- 자료에 없는 내용을 지어내지 마라. 본문이 비어 있는 절은 하위 목차 구성을 요약한다.
- 전문용어는 그대로 쓰되 필요하면 괄호로 풀어 준다.
- 출력은 JSON만. 인사말·설명·코드펜스 금지. id 는 준 값을 그대로 쓴다.

--- 절 목록 ---
{body}"""


def section_input(node_id: str, sec: dict, ocr: dict, all_sec: dict) -> str:
    s = sec[node_id]
    lines = [f"### id={node_id}",
             f"제목: {s['display']}",
             f"위치: {s['path']}  (본문 {s['page_start']}~{s['page_end']}쪽)"]
    body = (s.get("text") or "").strip()
    if body:
        lines.append("본문:\n" + body[:MAX_TEXT])
    kids = s.get("children") or []
    if kids:
        titles = [all_sec[k]["display"] for k in kids if k in all_sec]
        lines.append("하위 목차: " + " / ".join(titles))
    figs = [b for b in s["blocks"] if b["type"] == "figure"]
    for f in figs:
        o = ocr.get(f["fig_id"])
        if o:
            lines.append(f"{f['label']} 도식 판독: {o.get('summary') or ''} "
                         f"{o.get('text','')[:MAX_OCR]}")
    tabs = [b for b in s["blocks"] if b["type"] == "table"]
    for t in tabs[:3]:
        rows = t.get("rows") or []
        head = " | ".join(rows[0]) if rows else ""
        lines.append(f"{t.get('caption','[표]')} (열: {head})")
    return "\n".join(lines)


def build_jobs(order: list[str], sec: dict, ocr: dict, batch: int) -> list[dict]:
    schema_path = R.write_schema("summary", SCHEMA)
    jobs = []
    for i in range(0, len(order), batch):
        chunk = order[i:i + batch]
        body = "\n\n".join(section_input(nid, sec, ocr, sec) for nid in chunk)
        jobs.append({
            "key": f"sum_{i:04d}",
            "ids": chunk,                       # 이 배치가 책임지는 절 id
            "prompt": PROMPT_HEAD.format(body=body),
            "out_json": C.GEN_DIR / f"sum_{i:04d}.json",
            "schema_path": schema_path,
            "timeout": 900,
        })
    return jobs


def drop_incomplete(jobs: list[dict]) -> int:
    """자기 담당 id를 다 채우지 못한 배치 산출물을 지운다 → 재실행 시 그 배치만 재시도."""
    dropped = 0
    for j in jobs:
        p = j["out_json"]
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            p.unlink(missing_ok=True)
            dropped += 1
            continue
        got = {x.get("id") for x in data.get("summaries", []) if (x.get("summary") or "").strip()}
        if not set(j["ids"]).issubset(got):
            p.unlink(missing_ok=True)
            dropped += 1
    return dropped


def merge(jobs: list[dict], known: set[str]) -> dict:
    out: dict[str, str] = {}
    for j in jobs:
        p = j["out_json"]
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for item in data.get("summaries", []):
            nid, s = item.get("id"), (item.get("summary") or "").strip()
            if nid in known and s:
                out[nid] = s
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--batch", type=int, default=C.SUM_BATCH)
    args = ap.parse_args()

    sec = json.loads(C.SECTIONS_JSON.read_text(encoding="utf-8"))
    ocr = json.loads(C.FIGOCR_JSON.read_text(encoding="utf-8")) \
        if C.FIGOCR_JSON.exists() else {}
    if not ocr:
        print("[WARN] figocr.json 이 비어 있습니다 — 그림 내용 없이 요약합니다.",
              file=sys.stderr)

    order = [n["id"] for n in sorted(sec.values(), key=lambda s: s["seq"])]
    if args.limit:
        order = order[:args.limit]

    jobs = build_jobs(order, sec, ocr, args.batch)
    todo = [j for j in jobs if not j["out_json"].exists()]
    print(f"절 {len(order)}개 → 배치 {len(jobs)}개 (남은 작업 {len(todo)}개, "
          f"동시 {args.workers})")
    if todo:
        R.run_parallel(todo, workers=args.workers, stage="summary")

    got = merge(jobs, set(order))
    C.SUMMARIES_JSON.write_text(json.dumps(got, ensure_ascii=False, indent=1),
                                encoding="utf-8")
    miss = [n for n in order if n not in got]
    print(f"\n요약 완료 {len(got)}/{len(order)} → {C.SUMMARIES_JSON}")
    if miss:
        n_dropped = drop_incomplete(jobs)
        print(f"[WARN] 누락 {len(miss)}개: {miss[:10]}\n"
              f"       불완전 배치 {n_dropped}개를 비웠습니다. "
              f"같은 명령을 다시 실행하면 그 배치만 재시도합니다.", file=sys.stderr)
        sys.exit(1)
    over = [n for n, s in got.items() if len(s) > 130]
    avg = sum(len(s) for s in got.values()) // max(len(got), 1)
    print(f"평균 {avg}자 | 130자 초과 {len(over)}개")
    print("\n샘플:")
    for nid in order[:5]:
        print(f"  {sec[nid]['display'][:36]:38s} → {got[nid]}")


if __name__ == "__main__":
    main()
