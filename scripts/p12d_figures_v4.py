"""Phase F10 (v4): manuscript figures (PNG, 300 dpi, separate files per journal
rules) + table CSVs. All numbers from analysis/*.csv only.
Fig4 distinguishes primary VoF from secondary naive Delta-NPC sensitivity.
S3/rooftop-PV figure moved to Supplement as Figure S1."""
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
fig.savefig(f"{FIG}/v4_fig1_study_zones.png", bbox_inches="tight"); plt.close(fig)

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
fig.suptitle("Example feeder cluster (Sano c002): S1 vs S2 layout", fontsize=9)
fig.tight_layout()
fig.savefig(f"{FIG}/v4_fig2_topology_example.png", bbox_inches="tight"); plt.close(fig)

# Fig 3: primary VoF bars + MC mean of the secondary naive Delta-NPC -------
fig, ax = plt.subplots(figsize=(4.2, 2.8))
x = np.arange(3)
ax.bar(x - 0.15, scen.loc[CITIES, "vof_pct"], 0.3, label="VoF% (primary estimand)")
ax.bar(x + 0.15, mc.loc[CITIES, "mc_ltp_pct" if "mc_ltp_pct" in mc.columns else "ltp_pct_mean"],
       0.3, label="MC mean ΔNPC%")
for i, c in enumerate(CITIES):
    ax.text(i - 0.15, scen.loc[c, "vof_pct"] + 0.02, f'{scen.loc[c,"vof_pct"]:.2f}',
            ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels([CNAMES[c] for c in CITIES])
ax.set_ylabel("% of S1 NPC"); ax.set_ylim(bottom=0)
ax.legend(fontsize=7)
fig.tight_layout()
fig.savefig(f"{FIG}/v4_fig3_delta.png", bbox_inches="tight"); plt.close(fig)

# Fig 4: engineering-assumption sensitivity — secondary Delta-NPC range
# (bars) vs primary VoF values (dots), per city. Pre-registered 1%
# economic-equivalence margin shaded.
ea = pd.read_csv(f"{ROOT}/analysis/ENGINEERING_ASSUMPTION_SENSITIVITY.csv")
ea = ea[ea.scenario != "v2"]
fig, axes = plt.subplots(1, 3, figsize=(9.5, 3.0), sharey=True)
GRPS = {"MV threshold": "MV-served threshold (120/200 kW)",
        "cluster target": "cluster target 80 kW",
        "coincidence": "coincidence factor 0.5-0.8",
        "replicates": "24 replicates"}
for k, (ax, name) in enumerate(zip(axes, CITIES)):
    sub = ea[ea.city == name]
    base = scen.loc[name, "ltp_pct"]
    labels = list(GRPS.values()); ys = np.arange(len(GRPS))
    for i, g in enumerate(GRPS):
        vals = sub[sub.group == g]["delta_npc_pct"]
        ax.barh(i, vals.max() - vals.min(), left=vals.min(),
                color="tab:blue", alpha=0.6,
                label="secondary ΔNPC% range" if k == 0 and i == 0 else None)
        vofv = sub[sub.group == g]["vof_pct"]
        ax.scatter(vofv, [i] * len(vofv), c="tab:red", s=18, zorder=5,
                   label="primary VoF%" if k == 0 and i == 0 else None)
    ax.axvspan(-1, 1, color="0.85", alpha=0.4, zorder=0)
    ax.axvline(base, c="k", lw=1)
    ax.axvline(0, c="0.3", lw=0.6, ls="--")
    ax.set_title(f"{CNAMES[name]} (secondary base {base:+.2f}%)", fontsize=8)
    ax.set_yticks(ys); ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("% of S1 NPC", fontsize=7)
axes[0].legend(fontsize=7, loc="lower right")
fig.suptitle("Sensitivity to engineering assumptions: secondary naive ΔNPC (bars) "
             "vs primary VoF (red dots); grey band = 1% equivalence margin", fontsize=8)
fig.tight_layout()
fig.savefig(f"{FIG}/v4_fig4_tornado.png", bbox_inches="tight"); plt.close(fig)

# Supplementary Figure S1: DG — NPC S2 vs S3 (secondary, scenario-based)
fig, ax = plt.subplots(figsize=(4.2, 2.8))
x = np.arange(3)
ax.bar(x - 0.15, scen.loc[CITIES, "s2_npc"]/1e9, 0.3, label="S2")
ax.bar(x + 0.15, dg.loc[CITIES, "npc_s3"]/1e9, 0.3, label="S3 (+rooftop PV)")
ax.set_xticks(x); ax.set_xticklabels([CNAMES[c] for c in CITIES])
ax.set_ylabel("NPC (bn JPY, 40 y, 3%)"); ax.legend(fontsize=7)
ax.set_title("Secondary scenario overlay (upper bound)", fontsize=8)
fig.tight_layout()
fig.savefig(f"{FIG}/v4_supp_figS1_dg.png", bbox_inches="tight"); plt.close(fig)

# Tables as CSVs ----------------------------------------------------------
tab = scen[["clusters", "clusters_feasible", "lv_demand_kw", "s1_npc", "s2_npc",
            "vof", "vof_pct", "p_vof_pos", "delta_npc", "ltp_pct", "mean_tld"]].copy()
tab["lv_demand_kw"] /= 1000
for c in ["s1_npc", "s2_npc", "delta_npc", "vof"]:
    tab[c] /= 1e9
tab.columns = ["clusters", "clusters_feasible", "demand_MW", "S1_NPC_bn", "S2_NPC_bn",
               "VoF_bn", "VoF_pct_primary", "P_VoF_pos",
               "Delta_NPC_bn_secondary", "Delta_NPC_pct_secondary", "mean_TDD"]
tab.to_csv(f"{ROOT}/tables/table2_results_v4.csv", index_label="city")
print("figs+tables done")
