"""
extract_notebook.py — .ipynb 한 개를 해설 작성용 JSON으로 추출한다.

왜 필요한가:
  실측 코퍼스에서 노트북의 대부분이 base64 이미지다.
  예) Step0_EDA.ipynb = 3766KB 중 3649KB(97%)가 image/png.
  원본을 그대로 읽으면 컨텍스트가 즉시 고갈된다.
  이 스크립트는 소스를 무손실로 보존하면서 출력만 요약해 60배 축소한다.

사용법:
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python extract_notebook.py <노트북.ipynb>
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python extract_notebook.py <노트북.ipynb> --stats

출력:
  stdout에 JSON.
  {
    "path": "...", "name": "...",
    "cells": [{"index":0,"type":"code","source":"...","outputs":"...","images":[...]}],
    "shape_hints": [{"cell":4,"tuples":["(60000, 784)"],"summary_table":"...","params":["269,322"]}],
    "stats": {"n_code":19,"n_md":0,"source_bytes":6386,"gate_exceeded":false,...}
  }

설계 규칙:
  - source 는 절대 요약하지 않는다. 해설의 대상 그 자체다.
  - outputs 는 삭제가 아니라 요약한다. 각 셀이 무엇을 만드는지가 해설의 재료다.
  - error/traceback 은 전문 보존한다. 교육 가치가 가장 높은 출력이다.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys

# 출력 텍스트 보존 한도 (줄)
MAX_OUTPUT_LINES = 40

# 대용량 게이트 — SKILL.md 의 판단 기준과 동일하게 유지할 것.
# 세 조건 중 하나라도 넘으면 통째로 만들지 않고 범위를 되묻는다.
GATE_MAX_CODE_CELLS = 20
GATE_MAX_SECTIONS = 30          # 코드+마크다운. 섹션 수가 곧 페이지 길이다.
GATE_MAX_SOURCE_BYTES = 60 * 1024

# model.summary() 출력은 ANSI 색상 코드로 뒤덮여 있다.
# 벗겨내지 않으면 shape 표가 읽을 수 없게 되고, 관측 shape 근거가 통째로 사라진다.
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# (60000, 784) / (None, 26, 26, 32) 같은 shape 튜플
SHAPE_TUPLE_RE = re.compile(r"\((?:\s*(?:None|-?\d+)\s*,){1,5}\s*(?:None|-?\d+)\s*\)")

# "Total params: 269,322" / "Trainable params: 21,706"
PARAM_RE = re.compile(r"(?:Total|Trainable|Non-trainable)\s+params:\s*([\d,]+)")

# 마크다운 안에 박힌 base64 이미지
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(data:image/[^)]+\)")
MD_B64_RE = re.compile(r"data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=\s]+")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def as_text(value) -> str:
    """nbformat 은 문자열 또는 문자열 리스트를 준다."""
    if isinstance(value, list):
        return "".join(value)
    return value or ""


def truncate_lines(text: str, limit: int = MAX_OUTPUT_LINES) -> str:
    lines = text.split("\n")
    if len(lines) <= limit:
        return text
    kept = "\n".join(lines[:limit])
    return f"{kept}\n…({len(lines) - limit}줄 생략)"


def extract_outputs(outputs: list) -> tuple[str, list]:
    """코드 셀 출력에서 (텍스트, 이미지설명목록) 을 뽑는다.

    이미지는 디스크에 저장하지 않는다. 해설에 필요한 건 '그림이 나온다'는 사실과
    대략의 크기뿐이고, 바이트를 들고 있으면 컨텍스트만 먹는다.
    """
    parts: list[str] = []
    images: list[str] = []

    for out in outputs or []:
        kind = out.get("output_type")

        if kind == "stream":
            parts.append(as_text(out.get("text")))

        elif kind in ("execute_result", "display_data"):
            data = out.get("data", {})
            # text/html 과 text/plain 이 함께 오는 경우가 많다.
            # HTML 쪽은 태그 범벅이므로 항상 text/plain 을 쓴다.
            if "text/plain" in data:
                parts.append(as_text(data["text/plain"]))
            for fmt, label in (("image/png", "PNG"), ("image/jpeg", "JPEG"),
                               ("image/svg+xml", "SVG")):
                if fmt not in data:
                    continue
                payload = as_text(data[fmt])
                try:
                    nbytes = len(base64.b64decode(payload))
                except Exception:
                    nbytes = len(payload)
                desc = f"[이미지 출력: {label}, {nbytes // 1024}KB]"
                images.append(desc)
                parts.append(desc)

        elif kind == "error":
            # 에러는 자르지 않는다. 왜 실패했는지가 해설에서 가장 값진 재료다.
            tb = strip_ansi("\n".join(out.get("traceback", [])))
            ename = out.get("ename", "")
            evalue = out.get("evalue", "")
            parts.append(f"[에러] {ename}: {evalue}\n{tb}")

    text = strip_ansi("\n".join(p for p in parts if p).strip())
    return truncate_lines(text), images


def collect_shape_hints(cell_index: int, output_text: str) -> dict | None:
    """관측된 shape 근거를 모은다. 해설에서 '지어낸 숫자'를 막는 장치다."""
    if not output_text:
        return None

    tuples = SHAPE_TUPLE_RE.findall(output_text)
    params = PARAM_RE.findall(output_text)
    # Keras model.summary() 표 감지
    summary = output_text if "Layer (type)" in output_text else ""

    if not (tuples or params or summary):
        return None

    hint = {"cell": cell_index}
    if tuples:
        # 순서 유지하며 중복 제거
        hint["tuples"] = list(dict.fromkeys(tuples))
    if params:
        hint["params"] = params
    if summary:
        hint["summary_table"] = summary
    return hint


def extract(nb_path: str) -> dict:
    with open(nb_path, encoding="utf-8") as fh:
        nb = json.load(fh)

    cells = []
    shape_hints = []
    n_code = n_md = 0
    code_bytes = md_bytes = 0

    for idx, cell in enumerate(nb.get("cells", [])):
        ctype = cell.get("cell_type")
        source = as_text(cell.get("source")).rstrip()

        if ctype == "markdown":
            if not source.strip():
                continue
            n_md += 1
            source = MD_IMG_RE.sub("[그림]", source)
            source = MD_B64_RE.sub("[그림]", source)
            md_bytes += len(source.encode("utf-8"))
            cells.append({"index": idx, "type": "markdown", "source": source})

        elif ctype == "code":
            n_code += 1
            code_bytes += len(source.encode("utf-8"))
            out_text, images = extract_outputs(cell.get("outputs", []))
            entry = {"index": idx, "type": "code", "source": source,
                     "outputs": out_text}
            if images:
                entry["images"] = images
            cells.append(entry)

            hint = collect_shape_hints(idx, out_text)
            if hint:
                shape_hints.append(hint)

    # 게이트는 '페이지가 얼마나 길어지는가'를 재야 한다.
    # 코드 셀만 세면 마크다운 40개짜리 노트북을 놓친다 — 마크다운도 섹션 산문이 되어
    # 그대로 출력 분량이 된다. 그래서 섹션 수(코드+마크다운)와 총 소스를 함께 본다.
    total_bytes = code_bytes + md_bytes
    n_sections = n_code + n_md
    gate_reasons = []
    if n_code > GATE_MAX_CODE_CELLS:
        gate_reasons.append(f"코드셀 {n_code}개 > {GATE_MAX_CODE_CELLS}")
    if n_sections > GATE_MAX_SECTIONS:
        gate_reasons.append(f"총 셀 {n_sections}개 > {GATE_MAX_SECTIONS}")
    if total_bytes > GATE_MAX_SOURCE_BYTES:
        gate_reasons.append(f"총 소스 {total_bytes}B > {GATE_MAX_SOURCE_BYTES}B")

    return {
        "path": os.path.abspath(nb_path),
        "name": os.path.splitext(os.path.basename(nb_path))[0],
        "cells": cells,
        "shape_hints": shape_hints,
        "stats": {
            "n_code": n_code,
            "n_md": n_md,
            "n_sections": n_sections,
            "code_bytes": code_bytes,
            "md_bytes": md_bytes,
            "total_source_bytes": total_bytes,
            "file_bytes": os.path.getsize(nb_path),
            "gate_exceeded": bool(gate_reasons),
            "gate_reasons": gate_reasons,
            "gate_rule": (f"코드셀>{GATE_MAX_CODE_CELLS} 또는 "
                          f"총셀>{GATE_MAX_SECTIONS} 또는 "
                          f"총소스>{GATE_MAX_SOURCE_BYTES}B"),
        },
    }


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    stats_only = "--stats" in sys.argv

    if not args:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    nb_path = args[0]
    if not os.path.isfile(nb_path):
        print(f"[오류] 파일이 없습니다: {nb_path}", file=sys.stderr)
        return 1
    if not nb_path.lower().endswith(".ipynb"):
        print(f"[오류] .ipynb 가 아닙니다: {nb_path}\n"
              f"       .py/.js 등 일반 스크립트는 이 스크립트를 거치지 말고 "
              f"Read 도구로 직접 읽으세요.", file=sys.stderr)
        return 1

    result = extract(nb_path)
    payload = result["stats"] if stats_only else result
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
