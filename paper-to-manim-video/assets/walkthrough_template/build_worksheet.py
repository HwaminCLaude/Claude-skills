"""손계산 워크시트 노트북을 만든다 (템플릿).

    cp <skill>/assets/walkthrough_template/build_worksheet.py notebooks/
    python notebooks/build_worksheet.py --check    # 코드 셀만 이어붙여 실행 검증
    python notebooks/build_worksheet.py            # .ipynb 쓰기

영상 6~11편과 짝을 이루는 노트북이다. 시청자가 종이에 적은 값을 넣으면
정답과의 차이를 알려 준다.

**핵심 규칙 하나: 정답을 손으로 옮겨 적지 않는다.**
`analysis/walkthrough.py`를 통째로 읽어 첫 셀에 넣고, 노트북이 그 코드를
그대로 돌려 정답을 만든다. 분석을 고치면 노트북의 정답도 같이 바뀐다.

읽을 것: references/hand-calc-walkthrough.md §7
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ────────────────────────────────────────────────── .ipynb 직렬화
# .ipynb를 손으로 쓰면 JSON 이스케이프에서 사고가 난다. 셀을 파이썬
# 리터럴로 정의하고 여기서 직렬화한다.

def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {},
            "source": text.rstrip("\n").split("\n")}


def code(text: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": text.rstrip("\n").split("\n")}


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": [
            {**c, "source": [ln + "\n" for ln in c["source"][:-1]]
             + [c["source"][-1]]}
            for c in cells
        ],
        "metadata": {
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }


# ─────────────────────────────────────────── 계산 엔진을 그대로 싣기

def engine_source() -> str:
    """analysis/walkthrough.py에서 계산부만 떼어 온다.

    torch 대조 함수와 main()은 노트북에 필요 없다(저장소 clone이 필요하다).
    파일 경로를 쓰는 줄도 걷어낸다 — 노트북에는 파일이 없다.
    """
    src = (ROOT / "analysis" / "walkthrough.py").read_text(encoding="utf-8")
    cut = src.index("def torch_crosscheck(")      # 이 앞까지만 쓴다
    body = src[:cut]
    body = body.replace("HERE = Path(__file__).resolve().parent\n", "")
    body = re.sub(r"^from pathlib import Path\n", "", body, flags=re.M)
    return body.strip()


ENGINE = engine_source()


# ─────────────────────────────────────────────────── 정답표와 check()

# TODO: 영상에서 시청자가 계산할 단계들. 키 이름은 영상의 순서대로.
CHECKER = '''\
# 정답표를 만든다. 위 코드를 그대로 돌린 결과다.
TRACE = run_forward(SENT_IN)

ANSWER = {
    "X":       TRACE["x"],
    # TODO: 단계마다 한 줄씩. 영상에서 "직접 계산해 보세요"라고 말한 것 전부.
}

TOL = 0.005          # 표시 자릿수가 0.01이므로 그 절반까지 봐준다


def check(key, mine):
    """내가 계산한 값을 정답과 맞춰 본다."""
    import numpy as _np
    want = _np.asarray(ANSWER[key], dtype=float)
    got = _np.asarray(mine, dtype=float)
    if got.shape != want.shape:
        print(f"[{key}] 모양이 다릅니다. 정답 {want.shape}, 내 값 {got.shape}")
        print("정답:"); print(want)
        return False
    diff = _np.abs(got - want)
    if diff.max() <= TOL:
        print(f"[{key}] 맞았습니다.  최대 차이 {diff.max():.4f}")
        return True
    print(f"[{key}] 다릅니다.  최대 차이 {diff.max():.4f}")
    print("정답:"); print(want)
    print("내 값:"); print(got)
    print("차이:"); print(_np.round(got - want, 4))
    return False


def answer(key):
    """막혔을 때 정답만 본다."""
    import numpy as _np
    print(_np.asarray(ANSWER[key], dtype=float))


print("준비 끝. 정답표에 든 항목:")
print(", ".join(ANSWER))
'''


# ──────────────────────────────────────────────────────── 셀 구성
# 영상과 **같은 순서**로 간다. 한 단계 = 마크다운(수식 정의) + 코드(빈칸).

CELLS = [
    md("""\
# 손계산 워크시트 — 숫자 하나가 모델을 통과한다

영상 **N~M편**과 짝을 이루는 노트북입니다.
영상에서 손으로 계산한 값을 여기에 넣으면, 맞았는지 알려 줍니다.

**두 가지를 분명히 하고 시작합니다.**

1. 이 모델의 가중치는 **학습한 값이 아니라 손으로 곱할 수 있게 정한 값**입니다.
2. 구조와 수식은 <논문>과 <상류 구현>을 따릅니다. 줄인 것은 크기뿐입니다.

**계산 규약**: 각 단계의 결과를 **소수 둘째 자리로 반올림한 뒤** 다음 단계에 넣습니다.
그래야 화면의 숫자만으로 손계산을 이어가도 끝까지 같은 값이 나옵니다.

> 계산기가 필요한 곳: `sin`, `cos`, `exp`, `√`. 나머지는 종이로 됩니다."""),

    md("""\
## 0. 계산기 싣기

아래 셀은 **영상에 나온 숫자를 만든 바로 그 코드**입니다.
읽지 않고 실행만 해도 됩니다."""),
    code(ENGINE),
    code(CHECKER),

    md("""\
## 1. 예시 가중치 — 그대로 옮겨 적으세요

손으로 계산하려면 이 표들이 필요합니다. 출력해서 옆에 두고 쓰세요."""),
    code('''\
import numpy as np
np.set_printoptions(precision=2, suppress=True, linewidth=120)

# TODO: 화면에 띄운 행렬을 전부 출력한다
print("상수:  √d_model =", SQRT_D_MODEL, " √d_k =", round(SQRT_D_K, 4),
      " eps =", EPS, " 마스크 값 =", NEG)
'''),

    md("""\
## 2. 첫 단계  (영상 N편)

**수식**

$$ TODO $$

**해 보세요** — 아래 빈칸을 채우고 실행하세요."""),
    code('''\
my_X = [
    [0.00, 0.00, 0.00, 0.00],
]
check("X", my_X)
# 막히면: answer("X")
'''),

    # TODO: 단계마다 md + code 한 쌍을 이어 붙인다

    md("""\
## 마지막. 전체를 한 번에 — 영상과 같은 답이 나오는가

여기서는 계산하지 말고 그냥 실행하세요."""),
    code('''\
# TODO: 전체 forward를 돌려 최종 출력과 중간 요약을 찍는다
'''),

    md("""\
## 검산 — 이 노트북이 스스로 확인하는 것들

영상 마지막 편에서 다룬 불변량입니다. 하나라도 깨지면 여기서 걸립니다."""),
    code('''\
inv = {
    # TODO: analysis/walkthrough.py의 invariants와 같은 것들
}
for k, v in inv.items():
    print(("OK   " if v else "FAIL ") + k)
assert all(inv.values()), "불변량이 깨졌습니다"
print("\\n전부 통과했습니다.")
'''),

    md("""\
## 반올림하지 않으면 얼마나 달라지는가

우리는 매 단계 소수 둘째 자리로 잘랐습니다. 그러지 않은 경로와 비교하면
차이가 얼마인지, 그리고 **그래도 결론은 같은지**를 봅니다."""),
    code('''\
_keep = DP
try:
    globals()["DP"] = 12                    # 반올림하지 않는 경로
    ref = run_forward(SENT_IN)
finally:
    globals()["DP"] = _keep

# TODO: 두 경로의 차이를 재고, 결론(뽑힌 답)이 같은지 출력한다
'''),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="쓰지 않고 코드 셀 실행만 검증")
    ap.add_argument("--out", default="04_손계산_워크시트.ipynb")
    args = ap.parse_args()

    if args.check:
        src = "\n\n".join("\n".join(c["source"]) for c in CELLS
                          if c["cell_type"] == "code")
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "run.py"
            f.write_text(src, encoding="utf-8")
            r = subprocess.run([sys.executable, str(f)], cwd=tmp,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
        print((r.stdout or "").strip()[-3000:])
        if r.returncode:
            print("FAIL\n" + (r.stderr or "")[-3000:])
        return r.returncode

    path = HERE / args.out
    path.write_text(json.dumps(notebook(CELLS), ensure_ascii=False, indent=1),
                    encoding="utf-8")
    n_code = sum(1 for c in CELLS if c["cell_type"] == "code")
    print(f"[build] {path.name} — 셀 {len(CELLS)}개 (코드 {n_code})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
