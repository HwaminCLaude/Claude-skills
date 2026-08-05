"""
04_codex_ocr.py — Stage A. 그림 222장을 Codex 비전으로 판독한다.

본문의 그림은 전부 이미지라 텍스트 레이어가 비어 있다(실측 222/222에서 0자).
도식 안의 글자·수치·구조를 읽어 두면
  (1) 노션에서 그림 내용까지 검색되고
  (2) 06단계 요약이 그림 내용을 알고 쓸 수 있다.

산출: _output/figocr.json  {fig_id: {"text": 판독, "summary": 한 줄}}
사용: python scripts/04_codex_ocr.py [--limit N] [--workers 4]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llm_runner as R
import config as C

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["figures"],
    "properties": {
        "figures": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["fig_id", "text", "summary"],
                "properties": {
                    "fig_id": {"type": "string"},
                    "text": {"type": "string",
                             "description": "도식 안 모든 글자·수치를 구조가 드러나게 옮긴 것"},
                    "summary": {"type": "string",
                                "description": "이 도식이 말하는 바 한 문장"},
                },
            },
        }
    },
}

PROMPT_HEAD = """너는 한국어 산업분석 보고서의 도식을 판독하는 전문가다.

첨부된 이미지 {n}장은 「생성형 AI 및 AI 에이전트 기반 산업 자동화 시장 기술동향과
디지털 전환전략」 보고서의 그림이다. 이미지 순서와 아래 목록의 순서가 정확히 일치한다.

{listing}

각 그림에 대해 다음을 작성하라.
- `text`: 도식 안에 **실제로 적힌 모든 글자와 숫자**를 빠짐없이 옮긴다. 단순 나열이 아니라
  구조가 드러나게 쓴다. 예: 단계 흐름은 `A → B → C`, 박스 안 항목은 `제목: 항목1, 항목2`,
  표 형태는 `행이름 | 값1 | 값2`, 축이 있는 그래프는 축 이름과 눈금·계열명과 값.
  원문이 영어면 영어 그대로 쓰고 필요하면 괄호로 한국어를 덧붙인다.
- `summary`: 이 도식이 전달하는 핵심을 한 문장(80자 이내)으로.

규칙:
- 이미지에 없는 내용을 지어내지 마라. 안 보이는 글자는 생략한다.
- 출력은 JSON만. 설명·인사말·코드펜스 금지.
- fig_id 는 목록에 준 값을 그대로 쓴다."""


def build_jobs(figs: list[dict], batch: int) -> list[dict]:
    """배치 키를 **첫 fig_id** 로 잡는다.

    인덱스로 키를 잡으면 figures.json 에 항목이 추가돼 순서가 밀렸을 때
    기존 산출물이 엉뚱한 배치로 재사용돼 새 그림이 영원히 판독되지 않는다.
    """
    schema_path = R.write_schema("ocr", SCHEMA)
    jobs = []
    for i in range(0, len(figs), batch):
        chunk = figs[i:i + batch]
        listing = "\n".join(
            f"{k + 1}. fig_id={f['fig_id']} | {f['label']} {f['caption']} (본문 {f['page']}쪽)"
            for k, f in enumerate(chunk))
        jobs.append({
            "key": f"ocr_{chunk[0]['fig_id']}",
            "ids": [f["fig_id"] for f in chunk],
            "prompt": PROMPT_HEAD.format(n=len(chunk), listing=listing),
            "out_json": C.GEN_DIR / f"ocr_{chunk[0]['fig_id']}.json",
            "schema_path": schema_path,
            "images": [C.FIG_DIR / f"{f['fig_id']}.png" for f in chunk],
            "timeout": 1200,
        })
    return jobs


def collect(known: set[str]) -> dict:
    """gen/ 의 모든 ocr_*.json 을 훑어 판독 결과를 모은다(과거 산출물 포함)."""
    out: dict[str, dict] = {}
    for p in sorted(C.GEN_DIR.glob("ocr_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for item in data.get("figures", []):
            fid = item.get("fig_id")
            if fid in known and (item.get("text") or "").strip():
                out[fid] = {"text": item["text"].strip(),
                            "summary": (item.get("summary") or "").strip()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="앞 N장만 (시험용)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--batch", type=int, default=C.OCR_BATCH)
    args = ap.parse_args()

    figs = json.loads(C.FIGURES_JSON.read_text(encoding="utf-8"))
    if args.limit:
        figs = figs[:args.limit]
    missing = [f["fig_id"] for f in figs if not (C.FIG_DIR / f"{f['fig_id']}.png").exists()]
    if missing:
        print(f"[ERROR] PNG 없음 {len(missing)}장: {missing[:5]} — 03단계 먼저 실행",
              file=sys.stderr)
        sys.exit(1)

    known = {f["fig_id"] for f in figs}
    done = collect(known)                       # 이미 판독된 것
    pending = [f for f in figs if f["fig_id"] not in done]
    jobs = build_jobs(pending, args.batch)      # 미판독분만 배치
    print(f"그림 {len(figs)}장 | 판독됨 {len(done)}장 | 남은 {len(pending)}장 "
          f"→ 배치 {len(jobs)}개 (동시 {args.workers})")
    if jobs:
        R.run_parallel(jobs, workers=args.workers, stage="ocr")

    ocr = collect(known)
    C.FIGOCR_JSON.write_text(json.dumps(ocr, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    miss = [f["fig_id"] for f in figs if f["fig_id"] not in ocr]
    print(f"\n판독 완료 {len(ocr)}/{len(figs)}장 → {C.FIGOCR_JSON}")
    if miss:
        print(f"[WARN] 누락 {len(miss)}장: {miss[:10]}\n"
              f"       같은 명령을 다시 실행하면 누락분만 재시도합니다.", file=sys.stderr)
        sys.exit(1)
    avg = sum(len(v["text"]) for v in ocr.values()) // max(len(ocr), 1)
    print(f"평균 판독 길이 {avg}자")


if __name__ == "__main__":
    main()
