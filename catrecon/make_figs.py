import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
R = json.load(open("results/results.json")); X = json.load(open("results/extras.json"))
plt.rcParams.update({"font.family": "serif", "font.size": 9})

# Figure 1: sources and controls
fig, ax = plt.subplots(figsize=(6.6, 2.6)); ax.axis("off"); ax.set_xlim(0, 10.6); ax.set_ylim(0, 4)
def box(x, y, w, h, t, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec="black", lw=0.8))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8)
box(0.1, 2.6, 2.7, 1.0, "Firm order records\nand account master", "#e8eef7")
box(3.9, 2.6, 2.7, 1.0, "CAT file\n(MENO, MEOR, MEOC)", "#f7f1e0")
box(7.7, 2.6, 2.7, 1.0, "CAT feedback\n(specification checks)", "#e9f3e6")
box(3.9, 0.4, 2.7, 1.0, "Exchange order and\ncancel acknowledgements", "#e8eef7")
arr = dict(arrowstyle="->", lw=0.9)
ax.annotate("", xy=(3.85, 3.1), xytext=(2.85, 3.1), arrowprops=arr); ax.text(3.35, 3.28, "reporting", ha="center", fontsize=8)
ax.annotate("", xy=(7.65, 3.1), xytext=(6.65, 3.1), arrowprops=arr); ax.text(7.15, 3.28, "control 1", ha="center", fontsize=8)
ax.annotate("", xy=(2.85, 2.85), xytext=(3.85, 2.85), arrowprops=dict(arrowstyle="<->", lw=0.9, ls="--")); ax.text(3.35, 2.45, "control 2", ha="center", fontsize=8)
ax.annotate("", xy=(5.25, 1.45), xytext=(5.25, 2.55), arrowprops=dict(arrowstyle="<->", lw=0.9, ls="--")); ax.text(5.4, 2.0, "control 3", ha="left", fontsize=8)
ax.annotate("", xy=(8.2, 2.55), xytext=(6.65, 1.0), arrowprops=dict(arrowstyle="->", lw=0.7, color="gray")); ax.text(7.75, 1.5, "exchange's own\nCAT report", ha="left", fontsize=7.5, color="gray")
fig.savefig("fig_flow.pdf", bbox_inches="tight"); plt.close(fig)

# Figure 2: coverage
names = list(R["errors"]); ctrl = ("cat", "oms", "exch")
M = [[R["errors"][n][c] / R["errors"][n]["n"] for c in ctrl] for n in names]
fig, ax = plt.subplots(figsize=(4.6, 5.0))
ax.imshow(M, cmap="Greys", vmin=0, vmax=1.6, aspect="auto")
ax.set_xticks(range(3)); ax.set_xticklabels(["CAT\nfeedback", "Firm\nrecords", "Exchange\nacks"])
ax.set_yticks(range(len(names))); ax.set_yticklabels([R["errors"][n]["description"][:46] for n in names], fontsize=7.5)
for i, row in enumerate(M):
    for j, v in enumerate(row):
        ax.text(j, i, "all" if v == 1 else ("none" if v == 0 else f"{v:.0%}"), ha="center", va="center", fontsize=7.5, color="white" if v > 0.8 else "black")
ax.tick_params(length=0); fig.savefig("fig_coverage.pdf", bbox_inches="tight"); plt.close(fig)

# Figure 3: sampled review
fig, ax = plt.subplots(figsize=(4.6, 2.9))
for k, st in (("5", ":"), ("50", "--"), ("200", "-")):
    d = X["sampled_review"][k]; xs = [float(a[:-1]) for a in d]
    ax.plot(xs, list(d.values()), st, color="black", marker="o", ms=3, label=f"{k} instances per session")
ax.set_xscale("log"); ax.set_xlabel("Share of orders reviewed (%)"); ax.set_ylabel("Chance the error kind is seen"); ax.set_ylim(0, 1.05)
ax.legend(frameon=False, fontsize=8); fig.savefig("fig_sampling.pdf", bbox_inches="tight"); plt.close(fig)

# Figure 4: clock offsets under latency spikes
fig, ax = plt.subplots(figsize=(4.6, 2.9))
for (w, d), st in zip(X["clock_per_event"].items(), ("-", "--", ":")):
    xs = [float(k.split()[0]) for k in d if k.endswith("ms")]; ys = [d[k] for k in d if k.endswith("ms")]
    ax.plot(xs, ys, st, color="black", marker="o", ms=3, label=f"{w}; {d['false_flags_per_10000_orders']:g} false flags per 10,000")
ax.set_xscale("symlog", linthresh=2); ax.set_xticks([-50, -20, -5, -2, 2, 5, 20, 50]); ax.set_xticklabels(["-50", "-20", "-5", "-2", "+2", "+5", "+20", "+50"])
ax.set_xlabel("Clock offset (ms); positive = firm clock ahead"); ax.set_ylabel("Share of offsets found"); ax.set_ylim(-0.03, 1.05)
ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.28)); fig.savefig("fig_clock.pdf", bbox_inches="tight"); plt.close(fig)
print("figures written")
