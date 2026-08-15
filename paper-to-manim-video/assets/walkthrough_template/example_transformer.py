"""완성 예 — Transformer 손계산 워크스루(영상 6~11편)의 계산 노드.

이 파일은 **그대로 돌아간다.** 참고용으로 읽고, 새 논문에 옮길 때는
walkthrough_engine.py(뼈대)에 여기서 필요한 부분만 옮겨 쓴다.

    python example_transformer.py       # 불변량 14개 전부 통과하면 0으로 끝난다

무엇을 보면 되나:
  - q()로 매 단계 반올림해 다음 단계에 넣는 방식
  - 축마다 뜻을 맡긴 임베딩과, 역할을 말로 읽을 수 있는 가중치
  - 잔차+가중치공유 때문에 직전 토큰이 반복되던 것을 W_O의 −2로 막은 자리
  - 원문 끝에 <eos>를 붙여 "끝내는 신호"를 만든 자리
  - 불변량 14개 (수학 검산 + 대본이 하는 주장)
  - 상류 저장소 모듈에 같은 가중치를 실어 대조하는 torch_crosscheck()

원본 논문: arXiv:1706.03762 §3
상류 구현: jadore801120/attention-is-all-you-need-pytorch (MIT, 132907d)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DP = 2  # 화면 표시 자릿수 = 계산 자릿수


# ─────────────────────────────────────────────────────────── 반올림 규약

def q(x):
    """다음 단계로 넘기기 전에 표시 자릿수로 자른다."""
    return np.round(np.asarray(x, dtype=np.float64), DP)


def L(x):
    """JSON에 넣을 수 있는 중첩 리스트로."""
    return np.asarray(x, dtype=np.float64).round(6).tolist()


# ─────────────────────────────────────────────────────────── 장난감 설정

D_MODEL, N_HEAD, D_K, D_FF, N_LAYERS = 4, 2, 2, 8, 1
EPS = 1e-6
SQRT_D_MODEL = math.sqrt(D_MODEL)          # 2.0
SQRT_D_K = math.sqrt(D_K)                  # 1.4142...
NEG = -1e9                                 # 저장소가 쓰는 마스킹 값

SRC_VOCAB = ["<pad>", "나는", "학교에", "간다", "집에", "<eos>"]
TGT_VOCAB = ["<pad>", "<sos>", "<eos>", "I", "go", "to school", "home"]

# 실제 번역 모델처럼 원문 끝에도 <eos>를 붙인다. 디코더는 이 자리를 보고
# "원문이 여기서 끝났다"를 알게 된다.
SRC_SENT = ["나는", "학교에", "간다", "<eos>"]
TGT_SENT = ["I", "go", "to school"]

# 차원마다 뜻을 하나씩 맡긴다. 0=나/I, 1=학교/장소, 2=가다/이동, 3=문장 제어
#
# 값을 1이 아니라 2로 둔 이유가 있다. 위치 인코딩은 −1~+1 사이를 오간다.
# 낱말 값이 1이면 √d_model=2를 곱해도 2라, 세 번째 자리의 cos(3)=−0.99가
# 낱말 뜻을 거의 지워버린다. 논문의 실제 크기(√512≈22.6)에서는 이런 일이
# 없다. 작게 줄인 예시라서 생기는 문제이므로, 낱말 값을 2로 올려
# (곱하면 4) 위치 인코딩과의 비를 4:1로 맞춰 두었다.
E_SRC = np.array([
    [0.0, 0.0, 0.0, 0.0],   # <pad>
    [2.0, 0.0, 0.0, 0.0],   # 나는
    [0.0, 2.0, 0.0, 0.0],   # 학교에
    [0.0, 0.0, 2.0, 0.0],   # 간다
    [0.0, -2.0, 0.0, 0.0],  # 집에  (쓰지 않는 낱말. 사전이 하나가 아님을 보이려고 둔다)
    [0.0, 0.0, 0.0, -2.0],  # <eos> 원문의 끝. 3번 축이 음수면 "여기서 끝"
])

E_TGT = np.array([
    [0.0, 0.0, 0.0, 0.0],   # <pad>
    [0.0, 0.0, 0.0, 2.0],   # <sos>   3번 축이 양수면 "아직 시작"
    [0.0, 0.0, 0.0, -2.0],  # <eos>   3번 축이 음수면 "이제 끝"
    [2.0, 0.0, 0.0, 0.0],   # I
    [0.0, 0.0, 2.0, 0.0],   # go
    [0.0, 2.0, 0.0, 0.0],   # to school
    [1.0, 1.0, 0.0, 0.0],   # home  (오답 후보. 장소이면서 주어 쪽으로 반쯤 걸친다)
])


def M(**cols):
    """열 이름으로 4×4 가중치를 적는다. cols['o0'] = 입력 4차원의 계수."""
    return np.array([cols[f"o{j}"] for j in range(D_MODEL)], dtype=np.float64).T


# 인코더 자기어텐션 -----------------------------------------------------
# 헤드1: 질의 (x2, x0) · 키 (x1, x0)  → "이동 동사인 내가 장소인 너를 본다"
# 헤드2: 질의 (x0, x1) · 키 (x0, x1)  → "나와 닮은 자리를 본다"(내용 유사도)
# 계수를 0.5로 둔 이유: 낱말 값이 ±4까지 가므로 계수가 1이면 점수가 16까지
# 올라 softmax가 1.00 / 0.00 으로 포화된다. 그러면 "얼마나 더 보는가"가
# 화면에서 안 보인다. 어텐션의 날카로움은 가중치 크기가 정한다.
WQ_E = 0.5 * M(o0=[0, 0, 1, 0], o1=[1, 0, 0, 0], o2=[1, 0, 0, 0], o3=[0, 1, 0, 0])
WK_E = 0.5 * M(o0=[0, 1, 0, 0], o1=[1, 0, 0, 0], o2=[1, 0, 0, 0], o3=[0, 1, 0, 0])
WV_E = np.eye(D_MODEL)                       # 값은 손대지 않고 그대로 나른다
WO_E = np.eye(D_MODEL)

# 인코더 FFN: 여덟 개의 ReLU 뉴런. 양수 쪽과 음수 쪽을 다르게 다룬다.
#   0~3 : ReLU(x_i)  → +0.5·x_i    (양수는 절반을 더 얹는다)
#   4~7 : ReLU(−x_i) → −0.25·|x_i| (음수는 그 절반만)
# 그래서 FFN(x) = 0.5·x⁺ + 0.25·x⁻. 같은 크기라도 부호에 따라 다르게 움직인다
# — 이 비대칭이 곧 비선형이다. ReLU 하나로는 음수를 나르지 못해 뉴런이 두 벌
# 필요하다는 것도 여기서 보인다.
W1_E = np.zeros((D_MODEL, D_FF))
B1_E = np.zeros(D_FF)
W2_E = np.zeros((D_FF, D_MODEL))
B2_E = np.zeros(D_MODEL)
for i in range(4):
    W1_E[i, i] = 1.0
    W2_E[i, i] = 0.5
    W1_E[i, 4 + i] = -1.0
    W2_E[4 + i, i] = -0.25

# 디코더 마스크드 자기어텐션 -------------------------------------------
# 두 헤드 모두 내용 유사도. 헤드1은 (x0,x1), 헤드2는 (x2,x3)을 본다.
WQ_DS = 0.5 * M(o0=[1, 0, 0, 0], o1=[0, 1, 0, 0], o2=[0, 0, 1, 0], o3=[0, 0, 0, 1])
WK_DS = WQ_DS.copy()
WV_DS = np.eye(D_MODEL)
WO_DS = np.eye(D_MODEL)

# 디코더 크로스어텐션 ---------------------------------------------------
# 번역이 일어나는 자리다. "직전에 무엇을 말했는가"가 "이번에 원문의 무엇을
# 볼 것인가"를 정한다. 질의는 디코더에서, 키·값은 인코더 출력에서 온다.
#   헤드1 "무엇을 옮길까" — 질의 (s3−s0, s2) · 키 (e0, e1) · 값 (e0, e1)
#          s3는 "아직 <sos>뿐이다"라는 뜻이라 주어 축이 큰 '나는'을 부른다.
#          −s0 덕분에 I를 말하고 나면 '나는'에서 눈을 뗀다.
#          s2는 "방금 go를 말했다"이고, 그때 장소 축이 큰 '학교에'를 본다.
#   헤드2 "무엇이 남았나" — 질의 (s0, 3·s1) · 키 (e2, −e3) · 값 (e2, e3)
#          I를 말한 뒤(s0↑)면 이동 축이 큰 '간다'를 가져오고,
#          장소까지 말한 뒤(s1↑)면 제어 축이 −로 큰 원문 끝 <eos>를 본다.
#          계수 3은 이 두 번째 일을 또렷하게 만들기 위한 값이다. 1이나 2로
#          두면 <eos>가 '학교에'에 밀린다.
WQ_DC = M(o0=[-2, 0, 0, 1], o1=[0, 0, 1, 0], o2=[1, 0, 0, 0], o3=[0, 2, 0, 0])
WK_DC = M(o0=[1, 0, 0, 0], o1=[0, 1, 0, 0], o2=[0, 0, 1, 0], o3=[0, 0, 0, -1])
WV_DC = np.eye(D_MODEL)
# W_O는 "가져온 것을 어디에 더하고 무엇을 뺄지"를 정한다.
# 행은 concat한 네 자리(헤드1의 e0·e1, 헤드2의 e2·e3), 열은 출력 축이다.
#   out0 = 1·e0 − 2·e2   ← 이동 축을 가져왔으면 주어 축을 눌러라
#                          (I를 말한 뒤 또 I가 나오지 않게 하는 장치)
#   out1 = 4·e1          ← 장소를 가져왔으면 장소 축으로
#   out2 = 5·e2          ← 이동을 가져왔으면 이동 축으로
#   out3 = 1·e3          ← 원문 끝의 제어 축을 그대로 옮긴다
WO_DC = np.array([
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 4.0, 0.0, 0.0],
    [-2.0, 0.0, 5.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
])

# 디코더 FFN: 뉴런 여덟 개.
#   0~2 : ReLU(x_i)  → +0.5·x_i   (뜻을 담은 세 축은 양수면 그대로 통과)
#   3~5 : ReLU(−x_i) → −0.5·|x_i| (음수를 나르려면 뉴런이 하나 더 든다)
#   6   : ReLU(x3)   → −1.5       (제어 축이 양수면 눌러라 = <sos>를 되풀이하지 않는다)
#   7   : ReLU(−x3)  → −0.5       (제어 축이 음수면 더 내려라 = 끝내겠다는 신호를 굳힌다)
W1_DC = np.zeros((D_MODEL, D_FF))
B1_DC = np.zeros(D_FF)
W2_DC = np.zeros((D_FF, D_MODEL))
B2_DC = np.zeros(D_MODEL)
for i in range(3):
    W1_DC[i, i] = 1.0
    W2_DC[i, i] = 0.5
    W1_DC[i, 3 + i] = -1.0
    W2_DC[3 + i, i] = -0.5
W1_DC[3, 6] = 1.0
W2_DC[6, 3] = -1.5
W1_DC[3, 7] = -1.0
W2_DC[7, 3] = -0.5


# ─────────────────────────────────────────────────────────── 기본 연산

def positional_encoding(n_pos: int) -> np.ndarray:
    """논문 §3.5. PE(pos,2i)=sin(pos/10000^(2i/d)), PE(pos,2i+1)=cos(...)"""
    pe = np.zeros((n_pos, D_MODEL))
    for pos in range(n_pos):
        for i in range(D_MODEL // 2):
            w = pos / (10000 ** (2 * i / D_MODEL))
            pe[pos, 2 * i] = math.sin(w)
            pe[pos, 2 * i + 1] = math.cos(w)
    return pe


def layer_norm(x):
    """LayerNorm(x) = (x-μ)/√(σ²+ε).  γ=1, β=0 (저장소 초기값)."""
    mu = x.mean(axis=-1, keepdims=True)
    var = ((x - mu) ** 2).mean(axis=-1, keepdims=True)
    return (x - mu) / np.sqrt(var + EPS), mu, var


def softmax_rows(x):
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def attention(Xq, Xk, Xv, Wq, Wk, Wv, Wo, mask=None, trace=None):
    """멀티헤드 어텐션 한 번. 중간값을 전부 trace에 적는다."""
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
    added = q(residual + sub)
    normed, mu, var = layer_norm(added)
    normed = q(normed)
    if trace is not None:
        trace[name] = {"added": L(added), "mean": L(mu.ravel()),
                       "var": L(var.ravel()),
                       "std": L(np.sqrt(var + EPS).ravel()), "out": L(normed)}
    return normed


def ffn(x, W1, b1, W2, b2, trace=None, name="ffn"):
    pre = q(x @ W1 + b1)
    hid = q(np.maximum(pre, 0.0))
    out = q(hid @ W2 + b2)
    if trace is not None:
        trace[name] = {"pre": L(pre), "hidden": L(hid), "out": L(out)}
    return out


# ─────────────────────────────────────────────────────────── 인코더

def run_encoder(tokens):
    tr = {"tokens": tokens}
    ids = [SRC_VOCAB.index(t) for t in tokens]
    emb = E_SRC[ids]
    scaled = q(emb * SQRT_D_MODEL)
    pe = q(positional_encoding(len(tokens)))
    x = q(scaled + pe)
    tr.update({"ids": ids, "emb": L(emb), "emb_scaled": L(scaled),
               "pe": L(pe), "x": L(x)})

    attn_tr = {}
    proj = attention(x, x, x, WQ_E, WK_E, WV_E, WO_E, trace=attn_tr)
    tr["selfattn"] = attn_tr
    s1 = add_norm(x, proj, tr, "addnorm1")

    f_tr = {}
    f = ffn(s1, W1_E, B1_E, W2_E, B2_E, f_tr, "ffn")
    tr["ffn"] = f_tr["ffn"]
    out = add_norm(s1, f, tr, "addnorm2")
    tr["out"] = L(out)
    return out, tr


# ─────────────────────────────────────────────────────────── 디코더

def decoder_step(enc_out, prev_tokens):
    """지금까지 나온 토큰들을 넣고 다음 토큰 분포를 만든다."""
    tr = {"input_tokens": list(prev_tokens)}
    ids = [TGT_VOCAB.index(t) for t in prev_tokens]
    emb = E_TGT[ids]
    scaled = q(emb * SQRT_D_MODEL)
    pe = q(positional_encoding(len(prev_tokens)))
    x = q(scaled + pe)
    tr.update({"ids": ids, "emb": L(emb), "emb_scaled": L(scaled),
               "pe": L(pe), "x": L(x)})

    n = len(prev_tokens)
    mask = np.tril(np.ones((n, n), dtype=bool))
    tr["mask"] = mask.astype(int).tolist()

    self_tr = {}
    proj = attention(x, x, x, WQ_DS, WK_DS, WV_DS, WO_DS,
                     mask=mask, trace=self_tr)
    tr["selfattn"] = self_tr
    s = add_norm(x, proj, tr, "addnorm1")

    cross_tr = {}
    projc = attention(s, enc_out, enc_out, WQ_DC, WK_DC, WV_DC, WO_DC,
                      trace=cross_tr)
    tr["crossattn"] = cross_tr
    c = add_norm(s, projc, tr, "addnorm2")

    f_tr = {}
    f = ffn(c, W1_DC, B1_DC, W2_DC, B2_DC, f_tr, "ffn")
    tr["ffn"] = f_tr["ffn"]
    d = add_norm(c, f, tr, "addnorm3")
    tr["dec_out"] = L(d)

    logits = q(d @ E_TGT.T)          # §3.4 가중치 공유
    probs = q(softmax_rows(logits))
    last = int(np.argmax(logits[-1]))
    tr.update({"logits": L(logits), "probs": L(probs),
               "logits_last": L(logits[-1]), "probs_last": L(probs[-1]),
               "argmax": last, "next_token": TGT_VOCAB[last]})
    return tr


def run_decoder(enc_out, max_steps=5):
    seq, steps = ["<sos>"], []
    for _ in range(max_steps):
        tr = decoder_step(enc_out, seq)
        steps.append(tr)
        seq = seq + [tr["next_token"]]
        if tr["next_token"] == "<eos>":
            break
    return seq, steps


# ─────────────────────────────────────────────────────── float32 대조

def float_reference(tokens):
    """반올림 없이 float64로 같은 계산을 한 번 더. 차이를 재기 위한 것."""
    global DP
    keep, DP = DP, 12
    try:
        enc_out, _ = run_encoder(tokens)
        seq, steps = run_decoder(enc_out)
    finally:
        DP = keep
    return enc_out, seq, steps


def torch_crosscheck():
    """우리 손계산 경로를 저장소(jadore801120)의 모듈에 그대로 넣어 대조한다.

    같은 가중치를 `MultiHeadAttention`·`PositionwiseFeedForward`에 실어
    (드롭아웃은 eval로 꺼서) 인코더 한 층을 돌린다. 우리 쪽은 매 단계
    소수 둘째 자리로 반올림하므로 값이 완전히 같을 수는 없고, 그 차이가
    얼마인지를 재는 것이 목적이다.
    """
    try:
        import torch
        import torch.nn as nn
        sys_path = str(HERE)
        if sys_path not in __import__("sys").path:
            __import__("sys").path.insert(0, sys_path)
        from transformer.SubLayers import MultiHeadAttention, PositionwiseFeedForward
    except Exception as exc:                       # torch가 없으면 건너뛴다
        return {"available": False, "reason": repr(exc)}

    torch.set_grad_enabled(False)
    mha = MultiHeadAttention(N_HEAD, D_MODEL, D_K, D_K, dropout=0.0).eval()
    ff = PositionwiseFeedForward(D_MODEL, D_FF, dropout=0.0).eval()
    mha.layer_norm.eps = EPS
    ff.layer_norm.eps = EPS

    def T(a):
        return torch.tensor(np.asarray(a, dtype=np.float64), dtype=torch.float64)

    for m in (mha, ff):
        m.double()
    mha.w_qs.weight.copy_(T(WQ_E).T)
    mha.w_ks.weight.copy_(T(WK_E).T)
    mha.w_vs.weight.copy_(T(WV_E).T)
    mha.fc.weight.copy_(T(WO_E).T)
    ff.w_1.weight.copy_(T(W1_E).T)
    ff.w_1.bias.copy_(T(B1_E))
    ff.w_2.weight.copy_(T(W2_E).T)
    ff.w_2.bias.copy_(T(B2_E))

    ids = [SRC_VOCAB.index(t) for t in SRC_SENT]
    x = T(E_SRC[ids] * SQRT_D_MODEL + positional_encoding(len(SRC_SENT)))
    x = x.unsqueeze(0)
    out, attn = mha(x, x, x)
    out = ff(out)

    _, tr = run_encoder(SRC_SENT)
    ours = np.asarray(tr["out"])
    theirs = out.squeeze(0).numpy()
    attn_ours = np.asarray([h["attn"] for h in tr["selfattn"]["heads"]])
    attn_theirs = attn.squeeze(0).numpy()
    return {
        "available": True,
        "repo_commit": "jadore801120/attention-is-all-you-need-pytorch 132907d",
        "encoder_out_max_abs_diff": float(np.abs(ours - theirs).max()),
        "attention_max_abs_diff": float(np.abs(attn_ours - attn_theirs).max()),
        "repo_encoder_out": L(theirs),
    }


def main():
    enc_out, enc_tr = run_encoder(SRC_SENT)
    seq, steps = run_decoder(enc_out)

    ref_enc, ref_seq, ref_steps = float_reference(SRC_SENT)
    enc_diff = float(np.abs(np.asarray(enc_out) - np.asarray(ref_enc)).max())
    logit_diff = float(np.abs(
        np.asarray(steps[0]["logits_last"]) -
        np.asarray(ref_steps[0]["logits_last"])).max())

    produced = [t for t in seq[1:] if t != "<eos>"]

    facts = {
        "source": ("예시 가중치는 이 스크립트가 정한 값이다(학습한 모델이 아니다). "
                   "구조·수식은 arXiv:1706.03762v7 §3과 "
                   "jadore801120/attention-is-all-you-need-pytorch 커밋 132907d를 따른다."),
        "criteria": {
            "round_dp": DP,
            "note": ("각 단계 결과를 소수 둘째 자리로 반올림해 다음 단계에 넣는다. "
                     "화면 숫자로 손계산해도 같은 값이 나오게 하기 위한 우리 규약이며 "
                     "논문의 기준이 아니다."),
        },
        "config": {
            "d_model": D_MODEL, "n_head": N_HEAD, "d_k": D_K, "d_v": D_K,
            "d_ff": D_FF, "n_layers": N_LAYERS, "eps": EPS,
            "sqrt_d_model": SQRT_D_MODEL, "sqrt_d_k": SQRT_D_K,
            "mask_value": NEG,
            "paper_d_model": 512, "paper_n_head": 8, "paper_d_k": 64,
            "paper_d_ff": 2048, "paper_n_layers": 6,
        },
        "vocab": {"src": SRC_VOCAB, "tgt": TGT_VOCAB,
                  "src_sent": SRC_SENT, "tgt_sent": TGT_SENT},
        "weights": {
            "E_src": L(E_SRC), "E_tgt": L(E_TGT),
            "enc": {"Wq": L(WQ_E), "Wk": L(WK_E), "Wv": L(WV_E), "Wo": L(WO_E),
                    "W1": L(W1_E), "b1": L(B1_E), "W2": L(W2_E), "b2": L(B2_E)},
            "dec_self": {"Wq": L(WQ_DS), "Wk": L(WK_DS), "Wv": L(WV_DS),
                         "Wo": L(WO_DS)},
            "dec_cross": {"Wq": L(WQ_DC), "Wk": L(WK_DC), "Wv": L(WV_DC),
                          "Wo": L(WO_DC)},
            "dec_ffn": {"W1": L(W1_DC), "b1": L(B1_DC), "W2": L(W2_DC),
                        "b2": L(B2_DC)},
        },
        "encoder": enc_tr,
        "decoder": {"steps": steps, "sequence": seq, "produced": produced},
        "crosscheck": {
            "encoder_out_max_abs_diff_vs_float": enc_diff,
            "first_logit_max_abs_diff_vs_float": logit_diff,
            "float_sequence": ref_seq,
            "repo": torch_crosscheck(),
        },
    }

    # 우리 장난감 모델의 파라미터 수. 논문 base 모델과 견주기 위한 값이다.
    toy_params = (
        E_SRC.size + E_TGT.size                      # 두 사전
        + 4 * D_MODEL * D_MODEL                      # 인코더 W_Q·W_K·W_V·W_O
        + W1_E.size + B1_E.size + W2_E.size + B2_E.size
        + 4 * D_MODEL * D_MODEL                      # 디코더 자기어텐션
        + 4 * D_MODEL * D_MODEL                      # 디코더 크로스어텐션
        + W1_DC.size + B1_DC.size + W2_DC.size + B2_DC.size
    )
    facts["params"] = {
        "toy_total": int(toy_params),
        "toy_note": "가중치 공유 때문에 출력 사영은 따로 세지 않는다",
        "paper_base_millions": 65,
        "ratio": round(65e6 / toy_params, 1),
    }

    facts["invariants"] = {
        "attention_rows_sum_to_one": bool(all(
            abs(sum(r) - 1.0) < 0.02
            for h in enc_tr["selfattn"]["heads"] for r in h["attn"])),
        "causal_mask_blocks_the_future": bool(all(
            steps[-1]["selfattn"]["heads"][0]["attn"][i][j] == 0.0
            for i in range(len(steps[-1]["input_tokens"]))
            for j in range(i + 1, len(steps[-1]["input_tokens"])))),
        "layernorm_output_has_zero_mean": bool(
            abs(float(np.mean(np.asarray(enc_tr["addnorm2"]["out"])
                              .mean(axis=1)))) < 0.02),
        "decoder_produces_target_sentence": produced == TGT_SENT,
        "decoder_stops_with_eos": seq[-1] == "<eos>",
        "rounded_path_matches_float_sequence": seq == ref_seq,
        "sqrt_d_model_is_exactly_two": SQRT_D_MODEL == 2.0,
        "heads_split_d_model_exactly": N_HEAD * D_K == D_MODEL,
        "post_layernorm_like_repo": True,
        # 대본이 하는 주장들을 숫자로 못박아 둔다. 하나라도 깨지면 대본을 고쳐야 한다.
        "verb_attends_place_most": bool(
            np.argmax(enc_tr["selfattn"]["heads"][0]["attn"][2]) == 1),
        "first_step_looks_at_subject": bool(
            np.argmax(steps[0]["crossattn"]["heads"][0]["attn"][-1]) == 0),
        "last_step_looks_at_source_eos": bool(
            np.argmax(steps[-1]["crossattn"]["heads"][1]["attn"][-1])
            == len(SRC_SENT) - 1),
        "word_order_is_reordered": bool(
            np.argmax(steps[1]["crossattn"]["heads"][0]["attn"][-1]) == 2
            and np.argmax(steps[2]["crossattn"]["heads"][0]["attn"][-1]) == 1),
        "repo_matches_within_rounding": bool(
            (not facts["crosscheck"]["repo"]["available"])
            or facts["crosscheck"]["repo"]["encoder_out_max_abs_diff"] < 0.05),
    }

    out = HERE / "walkthrough_facts.json"
    out.write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    print("=== 인코더 입력 X ===")
    print(np.asarray(enc_tr["x"]))
    print("=== 헤드별 어텐션 ===")
    for i, h in enumerate(enc_tr["selfattn"]["heads"]):
        print(f"head{i+1} scaled\n{np.asarray(h['scaled'])}")
        print(f"head{i+1} attn\n{np.asarray(h['attn'])}")
    print("=== 인코더 출력 ===")
    print(np.asarray(enc_tr["out"]))
    print("=== 디코더 ===")
    for s in steps:
        print(s["input_tokens"], "→", s["next_token"],
              "logits", s["logits_last"])
        for i, h in enumerate(s["crossattn"]["heads"]):
            print(f"   cross head{i+1} attn", h["attn"][-1])
    print("=== 불변량 ===")
    for k, v in facts["invariants"].items():
        print(f"  {'OK ' if v else 'FAIL'} {k}")
    print("차이(반올림 경로 vs float):", enc_diff, logit_diff)
    return all(facts["invariants"].values())


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
