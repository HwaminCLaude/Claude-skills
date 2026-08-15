"""손계산 워크스루의 계산 노드 (템플릿).

    cp <skill>/assets/walkthrough_template/walkthrough_engine.py analysis/walkthrough.py

이 파일이 만드는 `walkthrough_facts.json`이 영상에 뜨는 **모든 숫자의 유일한 출처**다.
씬 코드는 여기서 읽기만 하고 숫자를 적지 않는다. 노트북 워크시트도 이 파일을
통째로 실어 정답표를 만든다.

세 가지를 지킨다.

1. **구조와 수식은 논문·상류 구현 그대로.** 줄이는 것은 크기뿐이다.
2. **가중치는 학습한 값이 아니라 우리가 정한 값이다.** 전부 0, ±0.5, ±1, ±2로 두어
   손으로 곱할 수 있게 한다. 영상과 노트북에서 그대로 밝힌다.
3. **각 단계 결과를 표시 자릿수로 반올림한 뒤 다음 단계에 넣는다.**
   화면 숫자만 보고 손계산해도 끝까지 같은 값이 나와야 하기 때문이다.
   반올림하지 않은 경로와의 차이는 마지막에 재서 함께 기록한다.

읽을 것: references/hand-calc-walkthrough.md

TODO 표시가 붙은 곳이 논문마다 달라지는 부분이다. 나머지는 그대로 쓴다.
완성된 예(Transformer 6~11편): assets/walkthrough_template/example_transformer.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DP = 2                      # 화면 표시 자릿수 = 계산 자릿수


# ─────────────────────────────────────────────────────── 반올림 규약

def q(x):
    """다음 단계로 넘기기 전에 표시 자릿수로 자른다. 이 시리즈의 핵심 장치."""
    return np.round(np.asarray(x, dtype=np.float64), DP)


def L(x):
    """JSON에 넣을 수 있는 중첩 리스트로."""
    return np.asarray(x, dtype=np.float64).round(6).tolist()


# ─────────────────────────────────────────────── TODO: 장난감 설정
# 크기 고르는 규칙은 references/hand-calc-walkthrough.md §1.
#   - 제곱근이 정수가 되는 차원 (d=4 → √4=2)
#   - 내적하는 축은 2개
#   - 층 1개, 어휘 5~7개, 계열 길이 3~4

D_MODEL, N_HEAD, D_K, D_FF, N_LAYERS = 4, 2, 2, 8, 1
EPS = 1e-6
SQRT_D_MODEL = math.sqrt(D_MODEL)
SQRT_D_K = math.sqrt(D_K)
NEG = -1e9                  # 상류 구현이 쓰는 마스킹 값 (논문은 −∞)

# TODO: 사전과 예시 입력. 축마다 뜻을 하나씩 맡긴다(0=주어, 1=장소, …).
#       낱말 값을 1이 아니라 2로 두는 이유는 §1 "값의 크기가 서로를 지운다" 참고.
VOCAB_IN: list[str] = []
VOCAB_OUT: list[str] = []
SENT_IN: list[str] = []
SENT_OUT: list[str] = []
E_IN = np.zeros((1, D_MODEL))
E_OUT = np.zeros((1, D_MODEL))

# TODO: 가중치. 손으로 곱할 수 있는 값만. 역할을 말로 설명할 수 있게 둔다.
#       끝까지 원하는 출력이 나오는 조합은 손으로 못 찾는다 — 격자 탐색으로
#       고르고, 결정 여유(1등−2등)의 최솟값이 가장 큰 것을 쓴다(§3).


def M(**cols):
    """열 이름으로 가중치를 적는다. cols['o0'] = 입력 차원별 계수."""
    return np.array([cols[f"o{j}"] for j in range(D_MODEL)], dtype=np.float64).T


# ─────────────────────────────────────────────────────── 기본 연산
# 여기부터는 대부분의 신경망에 그대로 쓴다.

def positional_encoding(n_pos: int) -> np.ndarray:
    """논문 §3.5. PE(pos,2i)=sin(pos/10000^(2i/d)), 홀수 자리는 cos."""
    pe = np.zeros((n_pos, D_MODEL))
    for pos in range(n_pos):
        for i in range(D_MODEL // 2):
            w = pos / (10000 ** (2 * i / D_MODEL))
            pe[pos, 2 * i] = math.sin(w)
            pe[pos, 2 * i + 1] = math.cos(w)
    return pe


def layer_norm(x):
    """LN(x) = (x−μ)/√(σ²+ε).  γ=1, β=0 (상류 구현 초기값)."""
    mu = x.mean(axis=-1, keepdims=True)
    var = ((x - mu) ** 2).mean(axis=-1, keepdims=True)
    return (x - mu) / np.sqrt(var + EPS), mu, var


def softmax_rows(x):
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def attention(Xq, Xk, Xv, Wq, Wk, Wv, Wo, mask=None, trace=None):
    """멀티헤드 어텐션 한 번. 중간값을 전부 trace에 적는다.

    화면에 올릴 것: Q·K·V → 헤드별 scores → scaled → (masked) → attn → out
    → concat → proj. 하나도 버리지 않는다.
    """
    Q, K, V = q(Xq @ Wq), q(Xk @ Wk), q(Xv @ Wv)
    heads, rec = [], []
    for h in range(N_HEAD):
        s = slice(h * D_K, (h + 1) * D_K)
        Qh, Kh, Vh = Q[:, s], K[:, s], V[:, s]
        raw = q(Qh @ Kh.T)
        scaled = q(raw / SQRT_D_K)
        masked = scaled if mask is None else np.where(mask, scaled, NEG)
        attn = q(softmax_rows(masked))
        out = q(attn @ Vh)
        heads.append(out)
        rec.append({"Q": L(Qh), "K": L(Kh), "V": L(Vh), "scores": L(raw),
                    "scaled": L(scaled),
                    "masked": L(np.where(masked < -1e8, NEG, masked)),
                    "attn": L(attn), "out": L(out)})
    concat = np.concatenate(heads, axis=1)
    proj = q(concat @ Wo)
    if trace is not None:
        trace.update({"Q": L(Q), "K": L(K), "V": L(V), "heads": rec,
                      "concat": L(concat), "proj": L(proj)})
    return proj


def add_norm(residual, sub, trace=None, name="ln"):
    """잔차 + LayerNorm. 평균·분산·표준편차를 남겨야 손계산을 따라올 수 있다."""
    added = q(residual + sub)
    normed, mu, var = layer_norm(added)
    normed = q(normed)
    if trace is not None:
        trace[name] = {"added": L(added), "mean": L(mu.ravel()),
                       "var": L(var.ravel()),
                       "std": L(np.sqrt(var + EPS).ravel()), "out": L(normed)}
    return normed


def ffn(x, W1, b1, W2, b2, trace=None, name="ffn"):
    """FFN(x) = max(0, xW1+b1)W2+b2.  hidden을 꼭 남긴다 — ReLU가 무엇을
    버렸는지가 화면의 핵심이다."""
    pre = q(x @ W1 + b1)
    hid = q(np.maximum(pre, 0.0))
    out = q(hid @ W2 + b2)
    if trace is not None:
        trace[name] = {"pre": L(pre), "hidden": L(hid), "out": L(out)}
    return out


# ─────────────────────────────────────────── TODO: 모델 통과 경로

def run_forward(tokens):
    """예시 입력 한 벌을 모델에 통과시키고 모든 중간값을 돌려준다.

    편성(walkthrough-6)의 2~5편이 여기서 나오는 값을 그대로 따라간다.
    단계마다 q()로 자른 뒤 다음 단계에 넣는 것을 잊지 않는다.
    """
    raise NotImplementedError("모델에 맞춰 채운다")


# ─────────────────────────────────────────────── 반올림 없는 대조

def float_reference(*args, **kwargs):
    """같은 코드를 자릿수만 늘려 한 번 더 돌린다. 차이를 재기 위한 것."""
    global DP
    keep, DP = DP, 12
    try:
        return run_forward(*args, **kwargs)
    finally:
        DP = keep


# ─────────────────────────────────────── 상류 구현과 대조 (검산 편)

def torch_crosscheck():
    """같은 가중치를 상류 저장소 모듈에 실어 돌린다. 드롭아웃은 eval()로 끈다.

    우리 쪽은 매 단계 반올림하므로 값이 완전히 같을 수는 없고,
    **그 차이가 얼마인지**를 재는 것이 목적이다.
    nn.Linear는 가중치를 뒤집어 저장하므로 `.T`를 넣는다.
    """
    try:
        import torch                                    # noqa: F401
        # TODO: from <repo>.SubLayers import MultiHeadAttention, ...
    except Exception as exc:
        return {"available": False, "reason": repr(exc)}
    return {"available": False, "reason": "TODO: 상류 모듈에 가중치를 실어 대조"}


# ─────────────────────────────────────────────────────────── 기록

def main() -> bool:
    trace = run_forward(SENT_IN)

    facts = {
        "source": ("예시 가중치는 이 스크립트가 정한 값이다(학습한 모델이 아니다). "
                   "구조·수식은 <논문>과 <상류 저장소 커밋>을 따른다."),
        "criteria": {
            "round_dp": DP,
            "note": ("각 단계 결과를 소수 둘째 자리로 반올림해 다음 단계에 넣는다. "
                     "화면 숫자로 손계산해도 같은 값이 나오게 하기 위한 우리 규약이며 "
                     "논문의 기준이 아니다."),
        },
        "config": {
            "d_model": D_MODEL, "n_head": N_HEAD, "d_k": D_K, "d_ff": D_FF,
            "n_layers": N_LAYERS, "eps": EPS, "mask_value": NEG,
            "sqrt_d_model": SQRT_D_MODEL, "sqrt_d_k": SQRT_D_K,
            # TODO: 논문 크기도 같이 적어 둔다 (검산 편에서 비교한다)
        },
        "vocab": {"in": VOCAB_IN, "out": VOCAB_OUT,
                  "sent_in": SENT_IN, "sent_out": SENT_OUT},
        "weights": {},          # TODO: 화면에 띄울 행렬을 전부 L()로
        "trace": trace,         # TODO: 편별로 읽기 쉬운 이름으로 나눈다
        "crosscheck": {"repo": torch_crosscheck()},
    }

    # 불변량 — 수학 검산 + **대본이 하는 주장**까지 (§5).
    # 하나라도 false면 실패시킨다. 대본을 고치다 숫자가 어긋나면 여기서 걸린다.
    facts["invariants"] = {
        "attention_rows_sum_to_one": True,        # TODO
        "layernorm_output_has_zero_mean": True,   # TODO
        "rounded_path_matches_float": True,       # TODO
        "example_produces_expected_output": True,  # TODO
        # 대본 주장 예: "간다가 학교에를 가장 크게 본다", "어순이 뒤집힌다"
    }

    (HERE / "walkthrough_facts.json").write_text(
        json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")

    print("=== 불변량 ===")
    for k, v in facts["invariants"].items():
        print(f"  {'OK ' if v else 'FAIL'} {k}")
    return all(facts["invariants"].values())


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
