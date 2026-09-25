"""Phases 7-8: original-vs-corrected comparison, ablation decomposition,
inclusion/exclusion sensitivity. Reads v1 + v2 cluster/scenario results."""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- 1) original vs corrected (Phase 7) ------------------------------------
v1 = pd.read_csv(f"{ROOT}/analysis/scenario_results.csv")
v2 = pd.read_csv(f"{ROOT}/analysis/scenario_results_v2.csv")
rows = []
for _, r1 in v1.iterrows():
    r2 = v2[v2.city == r1.city].iloc[0]
    rows.append(dict(
        city=r1.city,
        ltp_pct_v1=r1["ltp_pct"], ltp_pct_v2=r2["ltp_pct"],
        delta_npc_bn_v1=r1["delta_npc"]/1e9, delta_npc_bn_v2=r2["delta_npc"]/1e9,
        max_vdrop_v1=r1["max_vdrop"], max_vdrop_v2=r2["max_vdrop"],
        loss_red_pct_v1=100*(1-r1["s2_plkw"]/r1["s1_plkw"]),
        loss_red_pct_v2=100*(1-r2["s2_plkw"]/r2["s1_plkw"]),
        clusters_v1=r1["clusters"], clusters_v2=r2["clusters"],
        clusters_feasible_v2=r2["clusters_feasible"],
        mean_tld_v1=r1["mean_tld"], mean_tld_v2=r2["mean_tld"]))
pd.DataFrame(rows).to_csv(f"{ROOT}/analysis/original_vs_corrected.csv", index=False)
print(pd.DataFrame(rows).to_string(index=False))

# --- 2) ablation decomposition (Phase 8) -----------------------------------
# arms per cluster: A=S1 mean (T0C0), B=s1cond (T0Copt), C=s2f (ToptC0), D=S2
ab_rows = []
for name in ["sano", "kudamatsu", "yasu"]:
    rc = pd.read_csv(f"{ROOT}/data/processed/{name}/cluster_results_v2.csv")
    feas = rc[rc["s2_feasible"] & (rc["n_s1_feas"] > 0)].copy()
    A = feas["s1_npc_feas_mean"]
    B = feas["s1cond_npc_mean"].fillna(feas["s1_npc_feas_mean"])
    C = feas["s2f_npc"].fillna(feas["s2_npc"])
    D = feas["s2_npc"]
    topo_eff = (A - C).sum()            # topology only (conductor fixed)
    cond_eff = (A - B).sum()            # conductor only (topology fixed)
    total = (A - D).sum()
    inter = total - topo_eff - cond_eff
    ab_rows.append(dict(city=name, total_delta=total, topology_only=topo_eff,
                        conductor_only=cond_eff, interaction=inter,
                        topo_share=np.where(total != 0, topo_eff/total, np.nan)))
pd.DataFrame(ab_rows).to_csv(f"{ROOT}/analysis/ablation_results.csv", index=False)
print(pd.DataFrame(ab_rows).to_string(index=False))

# --- 3) inclusion/exclusion sensitivity ------------------------------------
se_rows = []
for name in ["sano", "kudamatsu", "yasu"]:
    rc = pd.read_csv(f"{ROOT}/data/processed/{name}/cluster_results_v2.csv")
    excl = rc[rc["s2_feasible"] & (rc["n_s1_feas"] > 0)]
    incl = rc.dropna(subset=["s2_npc", "s1_npc_mean"])   # include all, infeasible too
    for tag, d in [("feasible_only", excl), ("all_included", incl)]:
        s1col = "s1_npc_feas_mean" if tag == "feasible_only" else "s1_npc_mean"
        d1 = d.dropna(subset=[s1col])
        se_rows.append(dict(city=name, mode=tag, n=len(d1),
            delta_npc=float((d1[s1col]-d1["s2_npc"]).sum()),
            ltp_pct=float(100*(d1[s1col]-d1["s2_npc"]).sum()/d1[s1col].sum())))
pd.DataFrame(se_rows).to_csv(f"{ROOT}/analysis/feasibility_sensitivity.csv", index=False)
print(pd.DataFrame(se_rows).to_string(index=False))
print("done")
