"""Figures (greyscale, 180 mm print width, 600 dpi TIFF; TRSTMH charges for colour).

Figure 1  National snakebite deaths 2014-2024: reconciled estimate (primary S0, 95% CrI band) and the two recent-anchor
          scenarios, against the counts recorded by NCRB, MCCD, NHP and IHIP (log scale).
Figure 2  States: (A) estimated deaths in 2024 (S0, 95% CrI); (B) completeness of police (NCRB) recording, 2014 vs 2024.
Figure 3  NAPSE monitoring: observed 2024-2030 change each system would report if the halving target were met vs under
          business as usual (median, 95% interval), with completeness drift continuing at the 2014-24 pace.
"""
import pathlib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from PIL import Image

P = pathlib.Path(__file__).resolve().parents[1]; O = P / "outputs"
units = pd.read_csv(P / "data/model/units.csv").set_index("unit"); U = list(units.index)
pop = units[[f"pop_{y}" for y in range(2014, 2025)]].to_numpy(float); YR = np.arange(2014, 2025)
K, DG, MG, LG = "#000000", "#4d4d4d", "#8c8c8c", "#d0d0d0"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6})
SHORT = {"Andhra Pradesh + Telangana (undivided AP)": "Andhra Pradesh + Telangana", "Jammu & Kashmir + Ladakh (former J&K state)": "Jammu & Kashmir + Ladakh",
         "NE-7 (Arunachal, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, Tripura)": "North-east (7 states)", "MDS residual group: all other states": "All other states/UTs"}
thou = FuncFormatter(lambda v, _: f"{v:,.0f}")


def save(fig, name):
    for s in ("top", "right"):
        for ax in fig.axes: ax.spines[s].set_visible(False)
    fig.savefig(O / f"{name}.png", dpi=600)
    Image.open(O / f"{name}.png").convert("L").save(O / f"{name}.tif", dpi=(600, 600), compression="tiff_lzw")
    plt.close(fig)


# ---- Figure 1 ----
nat = {S: (np.load(O / f"draws_{S}.npz")["lam_2014_2024"] * pop[None] / 1e5).sum(1) for S in ("S0", "S3", "S4")}
gov = pd.read_csv(O / "completeness_national_S0.csv")
fig, ax = plt.subplots(figsize=(7.09, 3.4))
lo, md, hi = np.percentile(nat["S0"], [2.5, 50, 97.5], axis=0)
ax.fill_between(YR, lo, hi, color=LG, lw=0); ax.plot(YR, md, color=K, lw=1.6)
ax.text(2024.15, md[-1], "Reconciled, primary\n(MDS-anchored)", va="center", fontsize=6.8)
for S, ls, lab, nud in (("S3", (0, (4, 2)), "Recent anchors, task-force\ncompleteness unknown", 1.12), ("S4", (0, (1, 1.5)), "Recent anchors, task-force\nassumed ~90% complete", 0.86)):
    m = np.median(nat[S], 0); ax.plot(YR, m, color=DG, lw=1.1, ls=ls); ax.text(2024.15, m[-1] * nud, lab, va="center", fontsize=6.8)
for src, mk, mfc, lab in (("NCRB", "o", K, "Police (NCRB)"), ("MCCD", "s", "white", "Medical certification (MCCD)*"), ("NHP", "^", MG, "Public health facilities (NHP)")):
    d = gov[gov.source == src]
    ax.plot(d.year, d.recorded, color=DG, lw=0.6, marker=mk, ms=4, mfc=mfc, mec=K, mew=0.7)
    ax.text(d.year.iloc[-1] + 0.15, d.recorded.iloc[-1], lab, va="center", fontsize=6.8)
ax.plot([2024], [370], marker="D", ms=4.5, mfc="white", mec=K, mew=0.8, ls="none"); ax.text(2024.15, 370, "Disease surveillance (IHIP)", va="center", fontsize=6.8)
ax.set_yscale("log"); ax.set_ylim(250, 100000); ax.yaxis.set_major_formatter(thou)
ax.set_xlim(2013.6, 2029.2); ax.set_xticks(range(2014, 2025, 2))
ax.set_ylabel("Snakebite deaths per year (log scale)"); ax.set_xlabel("Year")
fig.tight_layout(); save(fig, "Figure_1")

# ---- Figure 2 ----
E = np.load(O / "draws_S0.npz")["lam_2014_2024"] * pop[None] / 1e5
c = pd.read_csv(O / "completeness_unit_year_S0.csv")
order = np.argsort(np.median(E[:, :, -1], 0))
fig, (a, b) = plt.subplots(1, 2, figsize=(7.09, 4.3), sharey=True, gridspec_kw={"width_ratios": [1, 1.15]})
y = np.arange(len(U))
for yi, ui in zip(y, order):
    m, l, h = np.percentile(E[:, ui, -1], [50, 2.5, 97.5])
    a.plot([l, h], [yi, yi], color=DG, lw=1.0); a.plot(m, yi, "o", ms=3.8, color=K)
    cu = c[(c.source == "NCRB") & (c.unit == U[ui])].set_index("year").c_pct
    if 2014 in cu and 2024 in cu:
        x0, x1 = max(cu[2014], 0.08), max(cu[2024], 0.08)
        b.annotate("", xy=(x1, yi), xytext=(x0, yi), arrowprops=dict(arrowstyle="-|>", color=DG, lw=0.8, mutation_scale=7, shrinkA=2.5, shrinkB=2.5))
        b.plot(x0, yi, "o", ms=3.8, mfc="white", mec=K, mew=0.7); b.plot(x1, yi, "o", ms=3.8, color=K)
a.set_yticks(y); a.set_yticklabels([SHORT.get(U[i], U[i]) for i in order], fontsize=6.8)
a.set_xlabel("Estimated snakebite deaths, 2024 (95% CrI)"); a.xaxis.set_major_formatter(thou); a.set_xlim(0, 16000)
b.set_xscale("log"); b.set_xlim(0.08, 150); b.axvline(100, color=MG, lw=0.6, ls=(0, (2, 2)))
b.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
b.set_xlabel("Police (NCRB) recording completeness, % (log scale)")
b.plot([], [], "o", ms=3.8, mfc="white", mec=K, mew=0.7, label="2014"); b.plot([], [], "o", ms=3.8, color=K, label="2024")
b.legend(frameon=False, loc="upper right", fontsize=6.8)
for ax, lab in ((a, "A"), (b, "B")): ax.text(-0.02 if ax is b else -0.55, 1.02, lab, transform=ax.transAxes, fontsize=9, fontweight="bold")
fig.tight_layout(w_pad=1.0); save(fig, "Figure_2")

# ---- Figure 3 ----
mon = pd.read_csv(O / "napse_monitoring.csv")
rows = [("Police (NCRB)", mon[(mon.system == "NCRB") & (mon.drift == "drift continues")]),
        ("Medical certification (MCCD)", mon[(mon.system == "MCCD") & (mon.drift == "drift continues")]),
        ("Public health facilities (NHP)", mon[(mon.system == "NHP") & (mon.drift == "drift continues")]),
        ("Disease surveillance (IHIP)", mon[mon.system.str.startswith("IHIP") & (mon.drift == "drift continues")]),
        ("SRS verbal autopsy (proposed)", mon[mon.system.str.contains(r"SRS.*S0")])]
fig, ax = plt.subplots(figsize=(7.09, 3.0))
tr = lambda v: np.sign(v / 100 + 1) * np.log(v / 100 + 1)                          # plot on log(ratio)
for i, (lab, r) in enumerate(rows):
    r = r.iloc[0]
    for k, (key, mk, mfc, off, ls) in enumerate((("target", "o", K, -0.13, "-"), ("bau", "s", "white", 0.13, (0, (3, 1.5))))):
        m, l, h = r[f"obs_change_if_{'target_met' if key == 'target' else 'bau'}"], r[f"{key}_lo"], r[f"{key}_hi"]
        ax.plot([np.log1p(l / 100), np.log1p(h / 100)], [i + off] * 2, color=K if key == "target" else DG, lw=1.1, ls=ls)
        ax.plot(np.log1p(m / 100), i + off, mk, ms=4.5, mfc=mfc, mec=K, mew=0.8)
ax.axvline(np.log(0.5), color=K, lw=0.6); ax.axvline(0, color=MG, lw=0.6, ls=(0, (2, 2)))
ticks = [-75, -50, 0, 100, 1000]
ax.set_xticks([np.log1p(t / 100) for t in ticks]); ax.set_xticklabels([f"{t:+d}%" if t else "0" for t in ticks])
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows]); ax.invert_yaxis()
ax.set_xlabel("Change in recorded snakebite deaths, 2024 to 2030 (log scale)")
ax.plot([], [], "o", ms=4.5, color=K, label="True deaths halved (target met)")
ax.plot([], [], "s", ms=4.5, mfc="white", mec=K, label="Business as usual (MDS trend)")
ax.legend(frameon=False, loc="lower right", fontsize=6.8)
fig.tight_layout(); save(fig, "Figure_3")
for f in ("Figure_1", "Figure_2", "Figure_3"): print(f, Image.open(O / f"{f}.tif").size)
