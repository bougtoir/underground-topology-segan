"""Phase 20 (v2): manuscript figures (PNG, 300 dpi, separate files per journal
rules) + LaTeX-style table CSVs. All numbers from analysis/*.csv only."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import geopandas as gpd
import networkx as nx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = f"{ROOT}/figures"
os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans",
                     "figure.dpi": 300, "savefig.dpi": 300,
                     "axes.spines.top": False, "axes.spines.right": False})
CITIES = ["sano", "kudamatsu", "yasu"]
CNAMES = {"sano": "Sano", "kudamatsu": "Kudamatsu", "yasu": "Yasu"}
scen = pd.read_csv(f"{ROOT}/analysis/scenario_results_v2.csv").set_index("city")
mc = pd.read_csv(f"{ROOT}/analysis/sensitivity_mc_v2.csv").set_index("city")
dg = pd.read_csv(f"{ROOT}/analysis/dg_results_v2.csv").set_index("city")
tor = pd.read_csv(f"{ROOT}/analysis/sensitivity_tornado_v2.csv")

# Fig 1: study zones — roads, demand nodes, anchors -----------------------
fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.4))
for ax, name in zip(axes, CITIES):
    e = pd.read_csv(f"{ROOT}/data/processed/{name}/edges.csv")
    n = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv").set_index("node")
    for _, r in e.iterrows():
        try:
            u, v = n.loc[r["u"]], n.loc[r["v"]]
            ax.plot([u.lon, v.lon], [u.lat, v.lat], lw=0.3, c="0.7")
        except KeyError:
            continue
    dn = n[n["p_kw"] > 0]
    ax.scatter(dn.lon, dn.lat, s=2, c="tab:blue", zorder=3)
    ax.set_title(f"{CNAMES[name]} ({len(dn)} demand nodes)", fontsize=8)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_aspect(1/np.cos(np.deg2rad(36)))
fig.suptitle("Study zones: OSM road graph (grey) and snapped building demand nodes (blue)",
             fontsize=9, y=1.02)
fig.tight_layout()
fig.savefig(f"{FIG}/v2_fig1_study_zones.png", bbox_inches="tight"); plt.close(fig)

# Fig 2: one cluster — S1 vs S2 topology ---------------------------------
name = "sano"
n = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv").set_index("node")
pos = {f"{float(k)}": (v.x_m, v.y_m) for k, v in n.iterrows()}
import glob
f1 = sorted(glob.glob(f"{ROOT}/data/processed/{name}/recon_v2/c002_r0*_A_steiner.csv"))[0]
fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.0), sharex=True, sharey=True)
for ax, (f, ttl) in zip(axes, [(f1, "S1 like-for-like (reconstruction replicate)"),
                             (None, "S2 life-cycle optimized")]):
    if f:
        ed = pd.read_csv(f)
        for _, r in ed.iterrows():
            u, v = str(r["u"]), str(r["v"])
            ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                    lw=0.8, c="tab:red")
    ax.set_title(ttl, fontsize=8)
    ax.set_xticks([]); ax.set_yticks([])
# right panel: optimized S2 tree (dumped by p07 for cluster 0)
s2 = nx.read_edgelist(f"{ROOT}/data/processed/{name}/s2_cluster0_v2.edgelist",
                      data=False)
for u, v in s2.edges():
    ax = axes[1]
    ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
            lw=0.8, c="tab:green")
axes[1].set_title("S2 life-cycle optimized", fontsize=8)
fig.suptitle("Example feeder cluster (Sano c002 (v2)): S1 vs S2 layout", fontsize=9)
fig.tight_layout()
fig.savefig(f"{FIG}/v2_fig2_topology_example.png", bbox_inches="tight"); plt.close(fig)

# Fig 3: LTP bars + MC P(LTP>0) ------------------------------------------
fig, ax = plt.subplots(figsize=(4.2, 2.8))
x = np.arange(3)
ax.bar(x - 0.15, scen.loc[CITIES, "ltp_pct"], 0.3, label="LTP% (family mean)")
ax.bar(x + 0.15, mc.loc[CITIES, "mc_ltp_pct" if "mc_ltp_pct" in mc.columns else "ltp_pct_mean"],
       0.3, label="MC mean")
for i, c in enumerate(CITIES):
    ax.text(i - 0.15, scen.loc[c, "ltp_pct"] + 0.3, f'{scen.loc[c,"ltp_pct"]:.1f}',
            ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels([CNAMES[c] for c in CITIES])
ax.set_ylabel("Renewal benefit ΔNPC (% of S1 NPC)")
ax.legend(fontsize=7)
fig.tight_layout()
fig.savefig(f"{FIG}/v2_fig3_delta.png", bbox_inches="tight"); plt.close(fig)

# Fig 4: tornado (Sano) ---------------------------------------------------
fig, ax = plt.subplots(figsize=(4.5, 2.8))
t = tor[tor.city == "sano"]
base = t["ltp_pct"].abs().mean()  # placeholder for ordering
order = (t.pivot_table(index="param", values="ltp_pct")
          .assign(sp=lambda d: d["ltp_pct"].max()-d["ltp_pct"].min())
          .sort_values("sp").index)
base_ltp = scen.loc["sano", "ltp_pct"]
for i, p in enumerate(order):
    lo = t[(t.param == p) & (t.level == "lo")]["ltp_pct"].iloc[0]
    hi = t[(t.param == p) & (t.level == "hi")]["ltp_pct"].iloc[0]
    ax.barh(i, hi - lo, left=lo, color="tab:blue", alpha=0.6)
ax.axvline(base_ltp, c="k", lw=1)
ax.set_yticks(range(len(order)))
ax.set_yticklabels({"r": "discount rate", "ekwh": "electricity price",
                    "cm": "construction cost", "omf": "O&M fraction",
                    "lf": "load factor", "h": "horizon"}[p] for p in order)
ax.set_xlabel("ΔNPC (%) under one-at-a-time parameter swing (Sano)")
fig.tight_layout()
fig.savefig(f"{FIG}/v2_fig4_tornado.png", bbox_inches="tight"); plt.close(fig)

# Fig 5: DG — NPC S2 vs S3 ------------------------------------------------
fig, ax = plt.subplots(figsize=(4.2, 2.8))
x = np.arange(3)
ax.bar(x - 0.15, scen.loc[CITIES, "s2_npc"]/1e9, 0.3, label="S2")
ax.bar(x + 0.15, dg.loc[CITIES, "npc_s3"]/1e9, 0.3, label="S3 (+rooftop PV)")
ax.set_xticks(x); ax.set_xticklabels([CNAMES[c] for c in CITIES])
ax.set_ylabel("NPC (bn JPY, 40 y, 3%)"); ax.legend(fontsize=7)
fig.tight_layout()
fig.savefig(f"{FIG}/v2_fig5_dg.png", bbox_inches="tight"); plt.close(fig)

# Tables as CSVs ----------------------------------------------------------
tab = scen[["clusters", "clusters_feasible", "lv_demand_kw", "s1_npc", "s2_npc", "delta_npc",
            "ltp_pct", "p_ltp_pos", "mean_tld"]].copy()
tab["lv_demand_kw"] /= 1000
for c in ["s1_npc", "s2_npc", "delta_npc"]:
    tab[c] /= 1e9
tab.columns = ["clusters", "clusters_feasible", "demand_MW", "S1_NPC_bn", "S2_NPC_bn",
               "Delta_NPC_bn", "LTP_pct", "P_LTP_pos", "mean_TLD"]
tab.to_csv(f"{ROOT}/tables/table2_results_v2.csv")
print("figs+tables done")
