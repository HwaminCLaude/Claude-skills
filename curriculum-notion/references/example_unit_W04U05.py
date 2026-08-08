# -*- coding: utf-8 -*-
from textwrap import dedent


UNIT = "W04U05"
TITLE = "05 · 로지스틱 회귀 — 시그모이드와 로그손실"
GOAL = "시그모이드·로그손실을 직접 구현하고 왜 MSE를 안 쓰는지 설명한다."
PREREQ = "4주차 02 경사하강법 — 기울기로 파라미터를 조금씩 고치는 과정"


SOLUTION = """
def sigmoid(z):
    return 1 / (1 + np.exp(-z))

def log_loss(y, p):
    p = np.clip(p, 1e-15, 1 - 1e-15)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()

def gradient(X, y, w, b):
    p = sigmoid(X @ w + b)
    err = p - y
    return X.T @ err / len(y), err.mean()
"""


def figs(plt):
    import numpy as np
    from unitkit import save

    x = np.array([-4, -3, -2, -1, 1, 2, 3, 4], dtype=float)
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    xx = np.linspace(-7, 7, 300)
    yy = slope * xx + intercept

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.axhspan(0, 1, color="#e8f3ff", alpha=0.7, label="확률로 해석 가능한 구간")
    ax.scatter(x[y == 0], y[y == 0], s=70, color="#3b82f6", label="정답 0")
    ax.scatter(x[y == 1], y[y == 1], s=70, color="#ef4444", label="정답 1")
    ax.plot(xx, yy, color="#111827", linewidth=2.2, label="이진 라벨에 맞춘 직선")
    ax.axhline(0, color="#6b7280", linewidth=1)
    ax.axhline(1, color="#6b7280", linewidth=1)
    ax.fill_between(xx, yy, 1, where=yy > 1, color="#fee2e2", alpha=0.8)
    ax.fill_between(xx, yy, 0, where=yy < 0, color="#fee2e2", alpha=0.8)
    ax.annotate("1보다 큰 예측", xy=(5.5, slope * 5.5 + intercept), xytext=(3.5, 1.35),
                arrowprops={"arrowstyle": "->", "color": "#b91c1c"}, color="#b91c1c")
    ax.annotate("0보다 작은 예측", xy=(-5.5, slope * -5.5 + intercept), xytext=(-6.8, -0.35),
                arrowprops={"arrowstyle": "->", "color": "#b91c1c"}, color="#b91c1c")
    ax.set_title("선형회귀를 분류에 그대로 쓰면 확률 범위를 벗어나요")
    ax.set_xlabel("특징 x")
    ax.set_ylabel("예측값")
    ax.set_ylim(-0.55, 1.55)
    ax.legend(loc="upper left", frameon=False)
    ax.grid(alpha=0.25)
    save(fig, "w04u05_why_not_linear")
    plt.close(fig)

    z = np.linspace(-8, 8, 400)
    p = 1 / (1 + np.exp(-z))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(z, p, color="#0f766e", linewidth=3)
    ax.axvline(0, color="#6b7280", linestyle="--")
    ax.axhline(0.5, color="#6b7280", linestyle="--")
    ax.scatter([0], [0.5], s=90, color="#ef4444", zorder=3)
    ax.annotate("z=0이면 0.5", xy=(0, 0.5), xytext=(1.0, 0.28),
                arrowprops={"arrowstyle": "->", "color": "#ef4444"}, color="#991b1b")
    ax.set_title("시그모이드는 어떤 실수도 0과 1 사이로 눌러요")
    ax.set_xlabel("z = wx + b")
    ax.set_ylabel("σ(z)")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(alpha=0.25)
    save(fig, "w04u05_sigmoid")
    plt.close(fig)

    xs = np.array([-3, -2, -1, 0, 1, 2, 3], dtype=float)
    ys = np.array([0, 1, 0, 1, 0, 1, 0], dtype=float)
    w_grid = np.linspace(-5, 5, 180)
    b_grid = np.linspace(-8, 8, 180)
    W, B0 = np.meshgrid(w_grid, b_grid)
    Z = W[..., None] * xs + B0[..., None]
    P = 1 / (1 + np.exp(-Z))
    P = np.clip(P, 1e-9, 1 - 1e-9)
    bce = -(ys * np.log(P) + (1 - ys) * np.log(1 - P)).mean(axis=-1)
    mse = 0.5 * ((P - ys) ** 2).mean(axis=-1)

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.3), sharex=True, sharey=True)
    for ax, loss, title, note in [
        (axes[0], bce, "로그손실: 한 방향으로 내려가는 볼록한 그릇", "전역 최저점"),
        (axes[1], mse, "시그모이드+MSE: 포화 때문에 굴곡이 생겨요", "갇히기 쉬운 낮은 경사"),
    ]:
        clipped = np.minimum(loss, np.quantile(loss, 0.94))
        cs = ax.contourf(W, B0, clipped, levels=28, cmap="viridis")
        ax.contour(W, B0, clipped, levels=10, colors="white", linewidths=0.45, alpha=0.65)
        ax.set_title(title, fontsize=10.5)
        ax.set_xlabel("w")
        ax.grid(alpha=0.18)
        fig.colorbar(cs, ax=ax, fraction=0.046, pad=0.04)
        if ax is axes[0]:
            ax.annotate(note, xy=(0, -0.3), xytext=(-4.6, -6.2),
                        arrowprops={"arrowstyle": "->", "color": "white"},
                        color="white", fontsize=9)
        else:
            ax.annotate(note, xy=(3.0, 7.0), xytext=(-3.8, 5.0),
                        arrowprops={"arrowstyle": "->", "color": "white"},
                        color="white", fontsize=9)
    axes[0].set_ylabel("b")
    fig.suptitle("같은 시그모이드 모델이라도 손실을 바꾸면 지형이 달라져요", y=1.02)
    save(fig, "w04u05_loss_compare")
    plt.close(fig)


def build(B, IM):
    impl_code = dedent("""
    import numpy as np

    def sigmoid(z):
        return 1 / (1 + np.exp(-z))

    def log_loss(y, p):
        p = np.clip(p, 1e-15, 1 - 1e-15)
        return -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()

    def gradient(X, y, w, b):
        p = sigmoid(X @ w + b)
        err = p - y
        return X.T @ err / len(y), err.mean()

    X = np.array([[2.0]])
    y = np.array([1.0])
    w = np.array([0.5])
    b = -1.0

    p = sigmoid(X @ w + b)
    print("z =", X @ w + b)
    print("p =", p)
    print("loss =", log_loss(y, p))
    print("gradient =", gradient(X, y, w, b))
    """).strip()

    check_code = dedent("""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import log_loss as sk_log_loss

    X = np.array([[-2.0], [-1.0], [0.0], [1.0], [2.0], [3.0]])
    y = np.array([0, 0, 1, 0, 1, 1])

    w = np.zeros(X.shape[1])
    b = 0.0
    for _ in range(60000):
        gw, gb = gradient(X, y, w, b)
        w -= 0.1 * gw
        b -= 0.1 * gb

    clf = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=10000, tol=1e-12)
    clf.fit(X, y)

    my_p = sigmoid(X @ w + b)
    sk_p = clf.predict_proba(X)[:, 1]

    print("직접 구현 계수:", w, b)
    print("sklearn 계수:", clf.coef_.ravel(), clf.intercept_[0])
    print("직접 구현 손실:", log_loss(y, my_p))
    print("sklearn 손실:", sk_log_loss(y, sk_p))
    """).strip()

    return [
        B.callout("이 유닛의 목표는 **로지스틱 회귀(logistic regression)**의 `sigmoid`, `log_loss`, `gradient`를 직접 만들고, 왜 MSE 대신 로그손실을 쓰는지 그림과 숫자로 설명할 수 있게 되는 거예요.", "🎯", B.ORANGE),
        B.h2("🧭 먼저 알고 오세요"),
        B.p("4주차 02에서 배운 **경사하강법(gradient descent)**만 기억하면 충분해요. 손실이 작아지는 방향으로 `w`, `b`를 조금씩 움직였죠."),
        B.bullet("**선형회귀(linear regression)**의 예측은 `y_hat = wx + b`처럼 아무 실수나 나올 수 있어요."),
        B.bullet("**분류(classification)**에서는 답을 0 또는 1로 두고, 모델 출력은 보통 **확률(probability)**처럼 읽고 싶어요."),
        B.bullet("이번 유닛에서는 실수를 확률로 바꾸는 시그모이드와, 확률 예측을 벌주는 로그손실을 이어 붙여요."),
        B.h2("📖 개념"),
        B.h3("선형회귀로 분류하면 생기는 문제"),
        B.p("이진 라벨 0과 1에 직선을 맞출 수는 있어요. 하지만 직선은 끝없이 내려가고 올라가서, 새 데이터에서는 0보다 작거나 1보다 큰 값을 쉽게 만들어요. 확률로 읽기 어려운 값이에요."),
        IM("w04u05_why_not_linear", "이진 라벨에 직선을 맞추면 관측 범위 밖에서 0~1을 벗어나요."),
        B.h3("시그모이드: 실수를 확률처럼 바꾸기"),
        B.p("**시그모이드(sigmoid)**는 아무 실수 `z`도 0과 1 사이 값으로 눌러 담는 함수예요. `z`가 커질수록 1에 가까워지고, 작아질수록 0에 가까워져요."),
        IM("w04u05_sigmoid", "`z=0`에서는 정확히 `0.5`라서 양쪽 클래스의 경계처럼 읽을 수 있어요."),
        B.h3("로그손실: 확신하고 틀리면 크게 벌주기"),
        B.p("**로그손실(log loss)** 또는 **이진 교차엔트로피(binary cross entropy)**는 정답 확률을 높이면 0에 가까워지고, 정답인데 0에 가까운 확률을 내면 아주 커져요."),
        B.table(
            ["상황", "예측 확률", "손실 느낌"],
            [
                ["정답 `y=1`, `p=0.99`", "`-log(0.99) ≈ 0.010`", "거의 안 벌줘요"],
                ["정답 `y=1`, `p=0.50`", "`-log(0.50) ≈ 0.693`", "반반이라 꽤 벌줘요"],
                ["정답 `y=1`, `p=0.01`", "`-log(0.01) ≈ 4.605`", "확신하고 틀려서 크게 벌줘요"],
            ],
        ),
        B.h3("왜 평균제곱오차(MSE)를 안 쓰나요?"),
        B.p("시그모이드 뒤에 MSE를 붙이면 손실 지형이 매끈한 그릇 하나가 아니라 굴곡과 포화 구간을 만들 수 있어요. 경사하강법은 기울기를 따라 움직이기 때문에, 이런 낮은 경사 구간에서 오래 머물 수 있어요."),
        IM("w04u05_loss_compare", "같은 `w`, `b` 좌표에서 로그손실은 볼록한 지형이고, sigmoid+MSE는 포화 때문에 비볼록 지형을 만들 수 있어요."),
        B.callout("로지스틱 회귀가 특별히 편한 이유는 로그손실을 쓰면 경사가 `X.T @ (y_hat - y) / n`처럼 선형회귀 때와 거의 같은 모양으로 정리된다는 점이에요.", "💡", B.BLUE),
        B.h2("🧮 수식"),
        B.p("한 샘플에서 먼저 `z = wx + b`를 만들고, 그 값을 시그모이드에 넣어 확률 `p`를 얻어요."),
        B.equation(r"\sigma(z)=\frac{1}{1+e^{-z}}"),
        B.equation(r"L(y,p)=-\{y\log(p)+(1-y)\log(1-p)\}"),
        B.equation(r"\frac{\partial L}{\partial w}=\frac{X^T(\hat{y}-y)}{n},\quad \frac{\partial L}{\partial b}=\frac{1}{n}\sum_i(\hat{y}_i-y_i)"),
        B.p("숫자를 직접 넣어 볼게요. `x=[2.0]`, `w=0.5`, `b=-1.0`, 정답 `y=1`이에요."),
        B.numbered("`z = 2.0 × 0.5 + (-1.0) = 0.0`"),
        B.numbered("`sigma(0.0) = 1 / (1 + exp(0)) = 0.5`"),
        B.numbered("`L = -log(0.5) = 0.693`"),
        B.numbered("`dL/dw = 2.0 × (0.5 - 1.0) = -1.0`, `dL/db = -0.5`"),
        B.p("아래 코드도 같은 숫자를 출력해요. 수식과 코드가 같은 계산을 하는지 맞춰 보는 게 핵심이에요."),
        B.h2("💻 직접 만들기"),
        B.p("라이브러리 모델 없이 `numpy`만으로 세 함수를 만들면 로지스틱 회귀의 핵심이 끝나요."),
        B.code(impl_code, "python"),
        B.h2("🔬 맞는지 확인"),
        B.callout("L2 규제가 기본으로 켜져 있어서 `C=np.inf` 로 꺼야 계수가 맞아요.", "⚠️", B.RED),
        B.p("아래 검산은 직접 만든 경사하강 결과를 sklearn의 규제 없는 로지스틱 회귀와 나란히 비교해요."),
        B.code(check_code, "python"),
        B.h2("🧪 강의 자료에 적용"),
        B.p("코랩에서는 드라이브를 마운트한 뒤 아래 경로를 그대로 확인하면 돼요. 두 덱에서 파일명이 `diabete_`와 `diabetes_`로 다르니 철자를 바꾸면 안 돼요."),
        B.bullet("회귀 덱 노트북: `/content/drive/MyDrive/메타코드 실습프로젝트/4주차_회귀·분류를 이용한 지도학습/4주차 실습/(회귀)김동환_강사님_강의자료_메타코드M/2. code/lesson3_5_regression_logistic.ipynb`"),
        B.bullet("회귀 덱 데이터: `1. data/diabete_lgr_tr.csv`, `1. data/diabete_lgr_te.csv`"),
        B.bullet("분류 덱 노트북: `/content/drive/MyDrive/메타코드 실습프로젝트/4주차_회귀·분류를 이용한 지도학습/4주차 실습/(분류)김동환_강사님/2. code/lesson4_2_maching_learning1_classifier.ipynb`"),
        B.bullet("분류 덱 데이터: `1. data/diabetes_lgr_tr.csv`, `1. data/diabetes_lgr_te.csv`"),
        B.callout("강의 자료에서는 먼저 sklearn 결과를 확인하고, 이 유닛의 `sigmoid`, `log_loss`, `gradient`를 같은 데이터에 적용해 손실이 내려가는지 보면 돼요.", "✅", B.GREEN),
        B.h2("✅ 스스로 확인"),
        B.bullet("선형회귀 예측값이 왜 확률로 부족한지 0~1 범위로 설명할 수 있어요."),
        B.bullet("`sigma(0)=0.5`와 `sigma(z)`의 출력 범위를 말할 수 있어요."),
        B.bullet("로그손실이 맞히면 0에 가까워지고, 확신하고 틀리면 커지는 이유를 그래프로 설명할 수 있어요."),
        B.bullet("`X.T @ (y_hat - y) / n`이 로지스틱 회귀의 `w` 경사라는 것을 코드로 계산할 수 있어요."),
        B.toggle("망가뜨리기 실험", [
            B.bullet("학습률을 100배로 키우면 손실이 출렁이거나 커지는지 확인해요."),
            B.bullet("라벨을 무작위로 섞으면 손실이 잘 줄지 않는지 확인해요."),
        ]),
        B.h2("🔗 더 보기"),
        B.bullet("다음 유닛에서는 확률을 0/1 예측으로 바꾼 뒤, 혼동행렬·정밀도·재현율·ROC·AUC로 분류 성능을 재요."),
        B.bullet("규제까지 다시 켜면 `penalty`, `C`가 계수를 얼마나 누르는지도 비교할 수 있어요."),
    ]


NB = {
    "setup": [
        ("md", "이번 노트북에서는 `numpy`로 로지스틱 회귀의 핵심 계산을 직접 만들어요."),
        ("code", dedent("""
        import numpy as np

        np.random.seed(0)
        """).strip()),
    ],
    "explore": [
        ("md", "`x=[2.0]`, `w=0.5`, `b=-1.0`, `y=1`인 한 샘플을 지금은 식 그대로 눈으로 따라가고, 3장에서 함수로 만들 거예요."),
        ("code", dedent("""
        x = np.array([[2.0]])
        y = np.array([1.0])
        w = np.array([0.5])
        b = -1.0

        z = x @ w + b
        p = 1 / (1 + np.exp(-z))
        loss = -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()
        grad_w = x.T @ (p - y) / len(y)
        grad_b = (p - y).mean()

        print("z =", z)
        print("sigmoid(z) =", p)
        print("loss =", round(float(loss), 3))
        print("grad_w =", grad_w)
        print("grad_b =", grad_b)
        """).strip()),
    ],
    "todo": [
        ("md", "`sigmoid`, `log_loss`, `gradient` 세 함수를 직접 채워 보세요. `gradient`는 `(grad_w, grad_b)`를 반환해야 해요."),
        ("code", dedent("""
        def sigmoid(z):
            # TODO: z를 0과 1 사이 확률로 바꿔 보세요.
            raise NotImplementedError("TODO: sigmoid를 구현하세요")

        def log_loss(y, p):
            # TODO: np.log(0)을 피하려고 p를 clip한 뒤 평균 로그손실을 계산하세요.
            raise NotImplementedError("TODO: log_loss를 구현하세요")

        def gradient(X, y, w, b):
            # TODO: p = sigmoid(X @ w + b)에서 시작해 grad_w, grad_b를 계산하세요.
            raise NotImplementedError("TODO: gradient를 구현하세요")
        """).strip()),
    ],
    "check": [
        ("md", "직접 구현을 sklearn과 대조해요. L2 규제가 기본으로 켜져 있어서 `C=np.inf` 로 꺼야 계수가 맞아요."),
        ("code", dedent("""
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import log_loss as sk_log_loss

        X = np.array([[-2.0], [-1.0], [0.0], [1.0], [2.0], [3.0]])
        y = np.array([0, 0, 1, 0, 1, 1])

        w = np.zeros(X.shape[1])
        b = 0.0
        for _ in range(60000):
            grad_w, grad_b = gradient(X, y, w, b)
            w -= 0.1 * grad_w
            b -= 0.1 * grad_b

        clf = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=10000, tol=1e-12)
        clf.fit(X, y)

        my_p = sigmoid(X @ w + b)
        sk_p = clf.predict_proba(X)[:, 1]

        assert np.allclose(w, clf.coef_.ravel(), atol=2e-2)
        assert np.allclose(b, clf.intercept_[0], atol=2e-2)
        assert np.allclose(log_loss(y, my_p), sk_log_loss(y, sk_p), atol=1e-4)

        print("✅ 직접 구현한 계수와 손실이 sklearn 결과와 맞아요.")
        print("직접 구현:", w, b, log_loss(y, my_p))
        print("sklearn:", clf.coef_.ravel(), clf.intercept_[0], sk_log_loss(y, sk_p))
        """).strip()),
    ],
    "apply": [
        ("md", "실제 강의 자료 경로를 그대로 써서 CSV를 불러오는 자리예요. 두 데이터 파일 이름의 철자가 다르니 주의하세요."),
        ("code", dedent("""
        from google.colab import drive
        import pandas as pd

        drive.mount("/content/drive")

        base = "/content/drive/MyDrive/메타코드 실습프로젝트/4주차_회귀·분류를 이용한 지도학습/4주차 실습"

        reg_nb = base + "/(회귀)김동환_강사님_강의자료_메타코드M/2. code/lesson3_5_regression_logistic.ipynb"
        reg_train = base + "/(회귀)김동환_강사님_강의자료_메타코드M/1. data/diabete_lgr_tr.csv"
        reg_test = base + "/(회귀)김동환_강사님_강의자료_메타코드M/1. data/diabete_lgr_te.csv"

        clf_nb = base + "/(분류)김동환_강사님/2. code/lesson4_2_maching_learning1_classifier.ipynb"
        clf_train = base + "/(분류)김동환_강사님/1. data/diabetes_lgr_tr.csv"
        clf_test = base + "/(분류)김동환_강사님/1. data/diabetes_lgr_te.csv"

        print(reg_nb)
        print(clf_nb)

        train_df = pd.read_csv(clf_train)
        test_df = pd.read_csv(clf_test)
        display(train_df.head())
        display(test_df.head())
        """).strip()),
    ],
    "wreck": [
        ("md", "일부러 조건을 망가뜨려요. 학습률을 100배로 키우면 손실이 튀고, 라벨을 섞으면 데이터의 규칙이 사라져 손실이 잘 줄지 않아요."),
        ("code", dedent("""
        def fit_history(X, y, lr, steps=60):
            w = np.zeros(X.shape[1])
            b = 0.0
            history = []
            for step in range(steps):
                p = sigmoid(X @ w + b)
                history.append(log_loss(y, p))
                grad_w, grad_b = gradient(X, y, w, b)
                w -= lr * grad_w
                b -= lr * grad_b
            return np.array(history)

        X_small = np.array([[-20.0], [-10.0], [0.0], [10.0], [20.0], [30.0]])
        y_small = np.array([0, 0, 1, 0, 1, 1])

        normal = fit_history(X_small, y_small, lr=0.01)
        too_big = fit_history(X_small, y_small, lr=1.0)  # 100배

        rng = np.random.default_rng(0)
        shuffled = fit_history(X_small, rng.permutation(y_small), lr=0.01)

        print("정상 학습률 처음/끝:", normal[0], normal[-1])
        print("100배 학습률 처음/끝:", too_big[0], too_big[-1])
        print("섞은 라벨 처음/끝:", shuffled[0], shuffled[-1])
        print("100배 학습률 앞 10개:", np.round(too_big[:10], 3))
        """).strip()),
    ],
}
