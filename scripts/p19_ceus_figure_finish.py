"""Final figure finishing: Fig1 orthogonal routing, Fig6 independent-scale tags."""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = f"{ROOT}/figures"

def save(fig, name):
    for e in ["png", "tiff"]:
        fig.savefig(f"{FIG}/{name}.{e}", dpi=300, bbox_inches="tight")
    plt.close(fig)

# ---- Fig 1: two rows, all connectors routed through empty space ----
fig, ax = plt.subplots(figsize=(7.4, 4.6)); ax.axis("off")
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
stages = [("Open urban data", "roads, buildings (OSM)\nsecurity-light anchors\nengineering datasheets"),
          ("Demand model", "building archetypes\npeak kW, coincidence\nload zones"),
          ("Reconstruction", "legacy LV ensemble\nobservability tiers 1-3\nroad-graph conduit"),
          ("Feasibility gates", "radial 415 V feeders\nampacity, transformer\n6% voltage-drop limit"),
          ("Decision model", "S1 incumbent admissible\nS2 screened candidates\nlife-cycle NPC"),
          ("Outcome", "VoF per cluster\nfeasible cohort n=554\nexploratory morphology")]
xs = [0.03, 0.365, 0.70]; ys = [0.62, 0.14]; W, H = 0.27, 0.28
for i, (t, s) in enumerate(stages):
    x, y = xs[i % 3], ys[i // 3]
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.008",
                 fc="#eef3fb" if i % 2 == 0 else "#f4f0e8", ec="#335", lw=1.2))
    ax.text(x + W/2, y + H - 0.04, t, ha="center", fontsize=11,
            fontweight="bold", color="#223")
    ax.text(x + W/2, y + H/2 - 0.035, s, ha="center", va="center",
            fontsize=8.6, color="#334")
# horizontal arrows within each row
for i in [0, 1, 3, 4]:
    x, y = xs[i % 3] + W + 0.008, ys[i // 3] + H/2
    ax.add_patch(FancyArrowPatch((x, y), (x + 0.05, y), arrowstyle="-|>",
                 mutation_scale=16, lw=1.5, color="#335"))
# row 1 -> row 2 elbow: straight down through the inter-row gap on the left
x_drop = xs[2] + W/2        # bottom-centre of "Reconstruction"
x_in   = xs[0] + W/2        # top-centre of "Feasibility gates"
y_mid  = (0.62 + 0.14 + 0.28) / 2   # mid-gap line
ax.plot([x_drop, x_drop], [0.62 - 0.005, y_mid], lw=1.5, color="#335")
ax.plot([x_drop, x_in], [y_mid, y_mid], lw=1.5, color="#335")
ax.add_patch(FancyArrowPatch((x_in, y_mid), (x_in, 0.14 + 0.28 + 0.008),
             arrowstyle="-|>", mutation_scale=16, lw=1.5, color="#335"))
ax.text(0.5, 0.955, "Modelled / reconstructed network - not observed utility topology",
        ha="center", fontsize=9, style="italic", color="#553")
ax.text(0.5, 0.015, "screening decision support at undergrounding renewal; not engineering design",
        ha="center", fontsize=8.5, style="italic", color="#445")
save(fig, "ceus_fig_pipeline")

# ---- Fig 6: municipal facets + explicit independent-scale tagging ----
H_ = 40; ann = (1 - 1.03 ** -H_) / 0.03; EKWH = 25; LF = 0.35
rows = []
for c in ["sano", "kudamatsu", "yasu"]:
    r = pd.read_csv(f"{ROOT}/data/processed/{c}/cluster_results_v2.csv")
    f = r[(r.s2_feasible == True) & (r.n_s1_feas > 0)]
    dc = (f.s1_capex_mean - f.s2_capex).sum()
    dl = ((f.s1_plkw_mean - f.s2_plkw).sum()) * 8760 * LF * EKWH * ann
    dt = (f.s1_npc_feas_mean - f.s2_npc).sum()
    vof = f.vof_mean.sum()
    rows.append(dict(city=c, capex=dc/1e9, loss=dl/1e9,
                     resid=(dt-dc-dl)/1e9, vof=vof/1e9, delta=dt/1e9))
d = pd.DataFrame(rows)
fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.9))
names = {"sano": "Sano", "kudamatsu": "Kudamatsu", "yasu": "Yasu"}
for ax, (_, r) in zip(axes, d.iterrows()):
    v = [r.capex, r.loss, r.resid]
    ax.bar(range(3), v, color=["#4878a8", "#72a06b", "#999999"], width=0.6)
    ax.bar(3.4, r.vof, color="#ffffff", ec="#222", width=0.75, lw=1.4)
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_xticks([0, 1, 2, 3.4])
    ax.set_xticklabels(["capex", "loss", "other", "VoF"], fontsize=8.5)
    ax.set_title(f"{names[r.city]} - d {r.delta:.3f} bn JPY", fontsize=9)
    ax.text(0.02, 0.94, "independent y-scale", transform=ax.transAxes,
            fontsize=7.5, style="italic", color="#666", va="top")
    ax.tick_params(labelsize=8)
    mx = max(max(abs(np.array(v))) * 1.3, abs(r.vof) * 1.3, 0.005)
    ax.set_ylim(-mx, mx)
axes[0].set_ylabel("40-yr discounted diff. S1-S2 (bn JPY)", fontsize=9)
fig.text(0.5, -0.03, "Panels use independent y-scales. 'other' covers O&M and transformer terms. "
         "VoF = sum of max(0, S1-S2) per cluster (non-negative); negative d bars indicate "
         "forced re-layout costlier than incumbent renewal.",
         ha="center", fontsize=7.8, style="italic")
fig.tight_layout()
save(fig, "ceus_fig_decomposition")
print(d.to_string(index=False))
print("done")
