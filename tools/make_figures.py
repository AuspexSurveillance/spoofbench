"""Figure for the fixed-multiple sweep (paper Section 6.3), drawn from the results files.

    python tools/make_figures.py            # writes docs/fig_sweep.pdf and docs/fig_sweep.png
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BOOKS = [("Simulated", "results/results.json", "o", "-"), ("ZN recorded", "results_real/results_real_ZN.json", "s", "--"),
         ("ES recorded", "results_real/results_real_ES.json", "^", ":")]


def sweep(path):
    R = json.load(open(os.path.join(HERE, path)))
    ks = [float(r["name"].split("=")[1]) for r in R["fixed_k"]]
    rec = [100 * r["recall_faithful"] for r in R["fixed_k"]]
    fc = [r["false_cases_per_100_legit_account_sessions"] for r in R["fixed_k"]]
    return ks, rec, fc


def draw(out_base, title=True):
    plt.rcParams.update({"font.family": "serif", "font.size": 9})
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.7))
    for name, path, mk, ls in BOOKS:
        ks, rec, fc = sweep(path)
        ax[0].plot(ks, rec, marker=mk, linestyle=ls, color="black", markersize=4, linewidth=1, label=name, markerfacecolor="white")
        ax[1].plot(ks, fc, marker=mk, linestyle=ls, color="black", markersize=4, linewidth=1, label=name, markerfacecolor="white")
    for a, yl in zip(ax, ("Recall on completed episodes (%)", "False cases per 100 legitimate\naccount-sessions")):
        a.set_xscale("log"); a.set_xlabel("Imbalance multiple k"); a.set_ylabel(yl)
        a.grid(True, which="major", linewidth=0.3, color="0.8"); a.spines["top"].set_visible(False); a.spines["right"].set_visible(False)
    ax[0].set_ylim(0, 100); ax[1].set_ylim(bottom=-0.5)
    ax[0].legend(frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(out_base + ".pdf"); fig.savefig(out_base + ".png", dpi=200); plt.close(fig)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
    draw(os.path.join(HERE, "docs", "fig_sweep"))
    print("wrote docs/fig_sweep.pdf, docs/fig_sweep.png")
