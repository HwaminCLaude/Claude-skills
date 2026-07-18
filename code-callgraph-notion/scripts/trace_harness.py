#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trace_harness.py — NMFC src를 실제 실행해 '예시 데이터 숫자 트레이스' + 그림을 만든다 (torch CPU).

작은 예시(2D 4점·2클래스)를 실제 함수들에 통과시켜 중간 입력/출력/shape를 캡처(trace.json)하고,
시각화가 의미 있는 단계는 matplotlib 그림(figures/*.png)으로 저장한다. 값은 전부 '실제 실행 결과'(날조 0).
프로젝트별 예시라 NMFC 전용 — 다른 코드베이스는 이 파일을 참고해 새로 작성.

사용: python trace_harness.py <src_package_dir> <out_dir>
  <src_package_dir> = `src` 패키지를 담은 폴더(예: .../NMFC2/plan2_v3_모듈변형)
"""
import sys, os, json, argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def rnd(x, nd=2):
    if isinstance(x, list): return [rnd(v, nd) for v in x]
    if isinstance(x, float): return round(x, nd)
    return x

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src_dir"); ap.add_argument("out_dir")
    a = ap.parse_args()
    sys.path.insert(0, a.src_dir)
    figdir = os.path.join(a.out_dir, "figures"); os.makedirs(figdir, exist_ok=True)
    import torch
    torch.manual_seed(0)
    from src.nmfc.affinity import pairwise_sqdist, median_sigma2, soft_neighbor_weights
    from src.nmfc.energy import local_energies, mean_scale, geometric_logits
    from src.nmfc.losses import nmfc_loss, fisher_ratio, scatter_matrices, linear_mfa_loss
    from src.nmfc.softmin import hinge_temp_logits
    from src.nmfc.acs import fisher_j, neg_j_loss
    from src.models.encoders import EncoderMLP
    from src.models.banks import kcenter_greedy
    from src.models.baselines import LinearHead, ProtoHead
    from src.nmfc.apt import APTController

    def tl(t): return rnd(t.detach().tolist())

    funcs = {}; figures = {}; pipeline = []
    def cap(key, inputs, out, out_shape, fig=None, note=""):
        funcs[key] = {"inputs": inputs, "output": out, "output_shape": list(out_shape), "fig": fig, "note": note}
        pipeline.append(key)

    # ── 예시: 2D 4점, 2클래스(0=원점 부근, 1=(3,3) 부근). z=좌표를 임베딩으로 사용 ──
    X = torch.tensor([[0.0, 0.0], [0.6, 0.4], [3.0, 3.0], [3.4, 2.6]])
    y = torch.tensor([0, 0, 1, 1])
    classes = torch.tensor([0, 1])
    z = X.clone()  # 잘 나뉜 예시 임베딩(설명 투명성)
    cmap = ["#2563eb", "#e11d48"]; cols = [cmap[int(c)] for c in y]

    # fig: 임베딩 산점도
    plt.figure(figsize=(4, 4))
    for i in range(len(z)):
        plt.scatter(*z[i].tolist(), c=cols[i], s=140)
        plt.annotate(f"p{i}(c{int(y[i])})", z[i].tolist(), xytext=(5, 5), textcoords="offset points")
    plt.title("Example embeddings z (4 points, 2 classes)"); plt.xlabel("dim0"); plt.ylabel("dim1"); plt.grid(alpha=.3)
    p = os.path.join(figdir, "scatter.png"); plt.tight_layout(); plt.savefig(p, dpi=120); plt.close(); figures["scatter"] = p

    # 인코더(shape 역할 시연)
    enc = EncoderMLP(in_dim=2, hidden=(64, 64), embed_dim=2)
    z_enc = enc(X)
    cap("models/encoders.py::EncoderMLP.forward", {"x": tl(X)}, tl(z_enc), z_enc.shape,
        note="사진/좌표를 학습 가능한 임베딩으로. 여기선 학습 전이라 값은 무작위지만 shape (4,2)는 동일. 아래 트레이스는 잘 나뉜 z=X를 예시 임베딩으로 사용.")

    # pairwise_sqdist
    d2 = pairwise_sqdist(z, z)
    plt.figure(figsize=(4, 3.4)); im = plt.imshow(d2.tolist(), cmap="viridis"); plt.colorbar(im)
    plt.title("Pairwise squared distance d2 (4x4)"); plt.xlabel("neighbor j"); plt.ylabel("anchor i")
    for i in range(4):
        for j in range(4): plt.text(j, i, f"{d2[i,j]:.1f}", ha="center", va="center", color="w", fontsize=8)
    p = os.path.join(figdir, "dist.png"); plt.tight_layout(); plt.savefig(p, dpi=120); plt.close(); figures["dist"] = p
    cap("nmfc/affinity.py::pairwise_sqdist", {"a=z": tl(z)}, tl(d2), d2.shape, fig="dist",
        note="모든 점 쌍의 제곱거리. 같은 클래스끼리 작고 다른 클래스끼리 큼.")

    s2 = median_sigma2(d2)
    cap("nmfc/affinity.py::median_sigma2", {"d2": tl(d2)}, round(float(s2), 3), s2.shape,
        note="대각(자기쌍) 뺀 거리들의 중앙값 = 커널 폭 σ². '얼마나 멀면 안 친한가'의 기준.")

    pi_pos, pi_neg = soft_neighbor_weights(d2, y, classes, s2)
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.2))
    for k, (ax, pi, ttl) in enumerate([(axs[0], pi_pos, "pi_pos (class0)"), (axs[1], pi_pos, "pi_pos (class1)")]):
        m = pi[k].tolist(); im = ax.imshow(m, cmap="magma", vmin=0, vmax=1); ax.set_title(f"pi_pos class{k}")
        ax.set_xlabel("neighbor j"); ax.set_ylabel("anchor i")
        for i in range(4):
            for j in range(4): ax.text(j, i, f"{pi[k][i,j]:.2f}", ha="center", va="center", color="w", fontsize=7)
    p = os.path.join(figdir, "pi.png"); plt.tight_layout(); plt.savefig(p, dpi=120); plt.close(); figures["pi"] = p
    cap("nmfc/affinity.py::soft_neighbor_weights", {"d2": tl(d2), "sigma2": round(float(s2), 3)},
        {"pi_pos": tl(pi_pos), "pi_neg": tl(pi_neg)}, pi_pos.shape, fig="pi",
        note="가까운 같은-클래스 이웃일수록 큰 가중치(행 합=1, 마스크드 softmax).")

    e_pos, e_neg = local_energies(d2, pi_pos, pi_neg)
    xs = list(range(4)); w = 0.35
    plt.figure(figsize=(5, 3.2))
    plt.bar([x - w/2 for x in xs], e_pos[:, 0].tolist(), w, label="E+ vs class0", color="#2563eb")
    plt.bar([x + w/2 for x in xs], e_pos[:, 1].tolist(), w, label="E+ vs class1", color="#e11d48")
    plt.xticks(xs, [f"p{i}(c{int(y[i])})" for i in xs]); plt.ylabel("E+ (lower=fits better)")
    plt.title("Local positive energy E+ per point/class"); plt.legend()
    p = os.path.join(figdir, "energy.png"); plt.tight_layout(); plt.savefig(p, dpi=120); plt.close(); figures["energy"] = p
    cap("nmfc/energy.py::local_energies", {"d2": tl(d2), "pi_pos": "…", "pi_neg": "…"},
        {"e_pos": tl(e_pos), "e_neg": tl(e_neg)}, e_pos.shape, fig="energy",
        note="각 점의 클래스별 당김 에너지 E+ (낮을수록 그 클래스에 잘 맞음)·밀침 E-.")

    mu_pos, mu_neg = mean_scale(e_pos, e_neg, y)
    cap("nmfc/energy.py::mean_scale", {"e_pos": tl(e_pos), "e_neg": tl(e_neg), "y": y.tolist()},
        {"mu_pos": round(float(mu_pos), 3), "mu_neg": round(float(mu_neg), 3)}, mu_pos.shape,
        note="정답 클래스 에너지의 배치 평균 μ± (detach: 학습 되돌리기 금지 — 좌표 쪼그라뜨리는 편법 방지).")

    g = geometric_logits(e_pos, e_neg, mu_pos, mu_neg, lam=0.5)
    pred = g.argmax(1)
    plt.figure(figsize=(5, 3.2))
    plt.bar([x - w/2 for x in xs], g[:, 0].tolist(), w, label="logit class0", color="#2563eb")
    plt.bar([x + w/2 for x in xs], g[:, 1].tolist(), w, label="logit class1", color="#e11d48")
    plt.xticks(xs, [f"p{i}\n true c{int(y[i])}\n pred c{int(pred[i])}" for i in xs]); plt.ylabel("geometric logit g")
    plt.title("Geometric logits g -> prediction"); plt.legend()
    p = os.path.join(figdir, "logits.png"); plt.tight_layout(); plt.savefig(p, dpi=120); plt.close(); figures["logits"] = p
    cap("nmfc/energy.py::geometric_logits", {"e_pos": "…", "e_neg": "…", "mu_pos": round(float(mu_pos), 3), "mu_neg": round(float(mu_neg), 3), "lam": 0.5},
        tl(g), g.shape, fig="logits",
        note=f"g = -E+/μ+ + λ·E-/μ-. argmax → 예측 {pred.tolist()} (정답 {y.tolist()}).")

    loss = nmfc_loss(g, y)
    cap("nmfc/losses.py::nmfc_loss", {"g": tl(g), "y": y.tolist()}, round(float(loss), 4), loss.shape,
        note="정답 클래스에 높은 점수를 줬나 (cross-entropy). 낮을수록 잘 맞힘.")

    fr = fisher_ratio(z, y)
    Sw, Sb = scatter_matrices(z, y)
    cap("nmfc/losses.py::fisher_ratio", {"z": tl(z), "y": y.tolist()}, round(float(fr), 3), fr.shape,
        note="Tr(S_B)/Tr(S_W): 클래스 간 흩어짐 / 클래스 내 뭉침. 클수록 잘 나뉨.")
    cap("nmfc/losses.py::scatter_matrices", {"z": tl(z), "y": y.tolist()},
        {"S_W": tl(Sw), "S_B": tl(Sb)}, Sw.shape, note="클래스 내(S_W)·간(S_B) 산포 행렬 (m×m).")
    lmf = linear_mfa_loss(z, y, 0.1, 1e-6)
    cap("nmfc/losses.py::linear_mfa_loss", {"z": tl(z), "y": y.tolist(), "eta_rel": 0.1},
        round(float(lmf), 4), lmf.shape, note="Phase I 워밍업 손실 (-J 계열 판별 손실).")

    # 관통 밖 소형 예시
    g_v3 = hinge_temp_logits(e_pos, e_neg, lam=0.5, m=torch.tensor(2.0), tau=torch.tensor(1.0))
    cap("nmfc/softmin.py::hinge_temp_logits", {"e_pos": "…", "e_neg": "…", "lam": 0.5, "m": 2.0, "tau": 1.0},
        tl(g_v3), g_v3.shape, note="v3 로짓: 밀침을 m까지만 세고 온도 τ로 나눔(μ± 병목 해소).")
    J = fisher_j(z, y, 0.1, False)
    njl = neg_j_loss(z, y, 0.1, False, 0.0)
    cap("nmfc/acs.py::fisher_j", {"z": tl(z), "y": y.tolist(), "sphere": False}, round(float(J), 3), J.shape,
        note="J = Tr((S_W+ηI)⁻¹ S_B). 판별 기준.")
    cap("nmfc/acs.py::neg_j_loss", {"z": tl(z), "y": y.tolist()}, round(float(njl), 3), njl.shape,
        note="L = -J. 잘 나뉠수록 손실 하락(v1 역수형의 경사 소멸 제거).")

    idx = kcenter_greedy(z, 2, 0)
    plt.figure(figsize=(4, 4))
    for i in range(len(z)):
        sel = i in [int(x) for x in idx]
        plt.scatter(*z[i].tolist(), c=cols[i], s=(260 if sel else 90), edgecolors=("k" if sel else "none"), linewidths=2)
        plt.annotate(f"p{i}" + ("*" if sel else ""), z[i].tolist(), xytext=(5, 5), textcoords="offset points")
    plt.title("k-center greedy coreset (*=selected)"); plt.grid(alpha=.3)
    p = os.path.join(figdir, "kcenter.png"); plt.tight_layout(); plt.savefig(p, dpi=120); plt.close(); figures["kcenter"] = p
    cap("models/banks.py::kcenter_greedy", {"z": tl(z), "n_c": 2}, [int(x) for x in idx], (len(idx),),
        fig="kcenter", note="서로 최대한 먼 대표점 선택(적은 수로 전체 대변).")

    lh = LinearHead(2, 2); lo = lh(z)
    cap("models/baselines.py::LinearHead.forward", {"z": tl(z)}, tl(lo), lo.shape,
        note="비교군 softmax 헤드: z를 선형으로 클래스 점수로.")

    # APT 스케줄 시연
    apt = APTController(window=3, delta=1e-3, patience=2, min_warmup=2, max_warmup=20)
    ratios = [0.2, 0.6, 1.0, 1.4, 1.55, 1.56, 1.56, 1.56, 1.56, 1.56]
    phases = [str(apt.update(r)) for r in ratios]
    fire = apt.transition_epoch            # 1-indexed epoch, None이면 미전환
    fire_idx = (fire - 1) if fire else None
    plt.figure(figsize=(5, 3.2))
    plt.plot(range(len(ratios)), ratios, "-o", color="#0f766e", label="fisher ratio")
    if fire_idx is not None: plt.axvline(fire_idx, ls="--", color="#e11d48", label=f"Phase I->II @epoch {fire}")
    plt.xlabel("epoch"); plt.ylabel("fisher ratio"); plt.title("APT auto phase transition"); plt.legend(); plt.grid(alpha=.3)
    p = os.path.join(figdir, "apt.png"); plt.tight_layout(); plt.savefig(p, dpi=120); plt.close(); figures["apt"] = p
    cap("nmfc/apt.py::APTController.update", {"ratios": ratios}, {"phases": phases, "transition_epoch": fire, "reason": apt.transition_reason}, (len(ratios),),
        fig="apt", note="Fisher 비가 정체(plateau)되면 자동으로 Phase I→II 전환. 사람이 시점 안 정해도 됨.")

    trace = {"example_desc": "2차원 좌표 4점·2클래스(p0,p1=class0 원점 부근 / p2,p3=class1 (3,3) 부근). z=이 좌표를 예시 임베딩으로 사용.",
             "X": tl(X), "y": y.tolist(), "classes": classes.tolist(),
             "pred": pred.tolist(), "funcs": funcs, "pipeline": pipeline, "figures": {k: os.path.basename(v) for k, v in figures.items()}}
    json.dump(trace, open(os.path.join(a.out_dir, "trace.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"trace.json: {len(funcs)} 함수 캡처 · figures {len(figures)}개 -> {a.out_dir}")
    for k in figures: print("  fig", k)

if __name__ == "__main__":
    main()
