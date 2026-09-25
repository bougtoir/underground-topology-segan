"""Build corrected figures and machine-readable manuscript tables."""
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = f"{ROOT}/figures"
TAB = f"{ROOT}/tables"
os.makedirs(FIG, exist_ok=True)
os.makedirs(TAB, exist_ok=True)
plt.rcParams.update({
    "font.size": 9, "font.family": "DejaVu Sans", "figure.dpi": 300,
    "savefig.dpi": 300, "axes.spines.top": False,
    "axes.spines.right": False})
CITIES = ["sano", "kudamatsu", "yasu"]
NAMES = {"sano": "Sano", "kudamatsu": "Kudamatsu", "yasu": "Yasu"}
scen = pd.read_csv(f"{ROOT}/analysis/scenario_results.csv").set_index("city")
mc = pd.read_csv(f"{ROOT}/analysis/sensitivity_mc.csv").set_index("city")
dec = pd.read_csv(f"{ROOT}/analysis/ablation_decomposition.csv").set_index("city")


def save(fig, name):
    fig.savefig(f"{FIG}/{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"{FIG}/{name}.tiff", dpi=600, bbox_inches="tight",
                pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)


fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.5))
for ax, city in zip(axes, CITIES):
    edges = pd.read_csv(f"{ROOT}/data/processed/{city}/edges.csv")
    nodes = pd.read_csv(
        f"{ROOT}/data/processed/{city}/nodes.csv").set_index("node")
    for _, r in edges.iterrows():
        if r.u in nodes.index and r.v in nodes.index:
            u, v = nodes.loc[r.u], nodes.loc[r.v]
            ax.plot([u.lon, v.lon], [u.lat, v.lat], lw=0.25, c="0.75")
    demand = nodes[nodes.p_kw > 0]
    ax.scatter(
        demand.lon, demand.lat, s=2, c="#1864ab", zorder=3,
        label="Modeled demand node")
    ax.set_title(f"{NAMES[city]} ({len(demand)} demand nodes)", fontsize=8)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_aspect(1 / np.cos(np.deg2rad(36)))
    lon_per_km = 1.0 / (111.32 * np.cos(np.deg2rad(nodes.lat.mean())))
    x0 = nodes.lon.min() + 0.06 * (nodes.lon.max() - nodes.lon.min())
    y0 = nodes.lat.min() + 0.06 * (nodes.lat.max() - nodes.lat.min())
    ax.plot([x0, x0 + lon_per_km], [y0, y0], c="black", lw=1.2)
    ax.text(x0 + lon_per_km / 2, y0, "1 km", ha="center", va="bottom",
            fontsize=6)
    ax.annotate(
        "N", xy=(0.93, 0.92), xytext=(0.93, 0.75),
        xycoords="axes fraction", ha="center", fontsize=7,
        arrowprops=dict(arrowstyle="-|>", lw=0.8))
axes[0].plot([], [], lw=0.6, c="0.75", label="OSM road")
axes[0].legend(loc="lower right", fontsize=5, frameon=False)
fig.tight_layout()
save(fig, "fig1_study_zones")

city = "sano"
nodes = pd.read_csv(
    f"{ROOT}/data/processed/{city}/nodes.csv").set_index("node")
pos = {str(float(k)): (v.x_m, v.y_m) for k, v in nodes.iterrows()}
s1_file = sorted(glob.glob(
    f"{ROOT}/data/processed/{city}/recon/c000_r0*_A_steiner.csv"))[0]
fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0), sharex=True, sharey=True)
s1 = pd.read_csv(s1_file)
for _, r in s1.iterrows():
    u, v = str(float(r.u)), str(float(r.v))
    if u in pos and v in pos:
        axes[0].plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                     lw=0.8, c="#c92a2a")
metadata = json.load(open(
    f"{ROOT}/data/processed/{city}/s2_representative_metadata.json",
    encoding="utf-8"))
s2 = nx.read_edgelist(
    f"{ROOT}/data/processed/{city}/s2_representative.edgelist", data=False)
if s2.number_of_edges() == 0:
    raise RuntimeError("representative S2 topology is empty")
for u, v in s2.edges:
    u, v = str(float(u)), str(float(v))
    if u in pos and v in pos:
        axes[1].plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                     lw=0.8, c="#2b8a3e")
axes[0].set_title("S1 reconstruction replicate", fontsize=8)
axes[1].set_title(
    f"S2 best-found candidate (weight {metadata['selected_weight']:g})",
    fontsize=8)
for ax in axes:
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_aspect("equal")
fig.tight_layout()
save(fig, "fig2_topology_example")

fig, ax = plt.subplots(figsize=(4.6, 3.0))
x = np.arange(3)
base = scen.loc[CITIES, "combined_screening_savings_pct"].to_numpy()
mean = mc.loc[
    CITIES, "combined_screening_savings_pct_mean"].to_numpy()
low = mc.loc[
    CITIES, "combined_screening_savings_pct_p2_5"].to_numpy()
high = mc.loc[
    CITIES, "combined_screening_savings_pct_p97_5"].to_numpy()
ax.bar(x - 0.16, base, 0.32, label="Base case", color="#1971c2")
ax.errorbar(x + 0.16, mean, yerr=[mean - low, high - mean], fmt="o",
            color="#c92a2a", capsize=3, label="Uncertainty mean and 95% interval")
ax.axhline(0, color="0.3", lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([NAMES[c] for c in CITIES])
ax.set_ylabel("Combined screening savings (% of S1 NPC)")
ax.legend(fontsize=7)
fig.tight_layout()
save(fig, "fig3_savings_uncertainty")

fig, ax = plt.subplots(figsize=(4.8, 3.0))
top = dec.loc[
    CITIES, "routing_policy_shapley_savings_jpy"].to_numpy() / 1e9
cond = dec.loc[CITIES, "conductor_shapley_savings_jpy"].to_numpy() / 1e9
ax.bar(x, top, label="Routing/topology", color="#74c0fc")
ax.bar(x, cond, bottom=top, label="Conductor sizing", color="#1864ab")
ax.set_xticks(x); ax.set_xticklabels([NAMES[c] for c in CITIES])
ax.set_ylabel("Paired-policy attribution (billion JPY)")
ax.legend(fontsize=7)
fig.tight_layout()
save(fig, "fig4_ablation_decomposition")

table2 = scen.reset_index()[[
    "city", "clusters", "total_demand_kw", "s1_npc", "s15_npc", "s2_npc",
    "routing_policy_savings_pct", "combined_screening_savings_pct",
    "s1_plkw", "s2_plkw", "max_mv_vdrop_pct",
    "min_customer_voltage_pu", "mean_edge_set_divergence"]].copy()
table2["total_demand_kw"] /= 1000
for field in ["s1_npc", "s15_npc", "s2_npc"]:
    table2[field] /= 1e9
table2.columns = [
    "municipality", "clusters", "modeled_demand_MW", "S1_NPC_billion_JPY",
    "S1_5_NPC_billion_JPY", "S2_NPC_billion_JPY",
    "routing_policy_savings_pct", "combined_screening_savings_pct",
    "S1_peak_loss_kW", "S2_peak_loss_kW", "max_MV_drop_pct",
    "min_customer_voltage_pu", "edge_set_divergence"]
table2.to_csv(f"{TAB}/table2_corrected_results.csv", index=False)
mc.to_csv(f"{TAB}/table3_uncertainty.csv")
dec.reset_index().to_csv(f"{TAB}/table4_ablation.csv", index=False)
print("corrected figures and tables written")
