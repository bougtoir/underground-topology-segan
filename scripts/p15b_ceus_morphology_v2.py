"""CEUS Gate-3 morphology v2 — repairs degenerate-hull density from v1.

Changes vs p15 (v1), per CEUS_ADDITIONAL_ANALYSIS_PROTOCOL / phase-1 audit:
- hull-area density kept ONLY for non-degenerate hulls (terminals>=3 and
  hull area >= 1e-4 km2). Degenerate hulls get demand_density=NaN and a
  quality flag; they are excluded from the density correlation, never
  silently clipped.
- New stable-support density: union of R=100 m buffers around the
  cluster's demand terminals (shapely unary_union) -> demand density and
  road length per buffered area. This is a fixed-radius GIS support
  independent of hull degeneracy.
- Quality flags per cluster: degenerate_hull, few_terminals(<3),
  no_road_edges, zero_vof. Rows are never dropped silently.
- Two-part framing preserved: (A) any positive VoF vs (B) magnitude —
  reported descriptively; no hurdle regression with ~30 positive cases.
- Same inputs/outputs layout as v1 plus quality-flag columns;
  correlations restricted to non-degenerate rows for density.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
from scipy.stats import spearmanr
from shapely.geometry import Point
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CITIES = ["sano", "kudamatsu", "yasu"]
BUFFER_R_M = 100.0
MIN_HULL_AREA_KM2 = 1e-4  # ~100 m^2; below this the hull is degenerate for density

def hull_area(pts):
    if len(pts) < 3:
        return 0.0
    try:
        return float(ConvexHull(pts).volume)
    except Exception:
        return 0.0

def buffer_union_area_km2(pts, r_m):
    if len(pts) == 0:
        return 0.0
    union = unary_union([Point(x, y).buffer(r_m) for x, y in pts])
    return float(union.area) / 1e6

rows = []
for c in CITIES:
    d = f"{ROOT}/data/processed/{c}"
    nodes = pd.read_csv(f"{d}/nodes.csv")
    edges = pd.read_csv(f"{d}/edges.csv")
    dem = pd.read_csv(f"{d}/demand_nodes.csv")
    cl = pd.read_csv(f"{d}/clusters_v2.csv")
    res = pd.read_csv(f"{d}/cluster_results_v2.csv")
    res = res[res["city"] == c]
    nmap = nodes.set_index("node")
    clmap = dict(zip(cl["node"], cl["cluster"]))
    edges["cl_u"] = edges["u"].map(clmap)
    edges["cl_v"] = edges["v"].map(clmap)
    edges_in = edges[edges["cl_u"] == edges["cl_v"]]
    deg = {}
    for _, r in edges_in.iterrows():
        deg[r["u"]] = deg.get(r["u"], 0) + 1
        deg[r["v"]] = deg.get(r["v"], 0) + 1
    demc = dem.copy()
    demc["cluster"] = demc["node"].map(clmap)
    for _, r in res.iterrows():
        k = int(r["cluster"])
        dn = demc[demc["cluster"] == k]["node"].tolist()
        pts = nmap.loc[nmap.index.intersection(dn), ["x_m", "y_m"]].dropna().values
        sub_e = edges_in[edges_in["cl_u"] == k]
        mean_elen = float(sub_e["length"].mean()) if len(sub_e) else np.nan
        road_km_in = float(sub_e["length"].sum()) / 1000.0 if len(sub_e) else 0.0
        member = set(sub_e["u"]).union(sub_e["v"]) if len(sub_e) else set()
        mdeg = float(np.mean([deg.get(n, 0) for n in member])) if member else np.nan
        n_term = int(r["terminals"])
        area = hull_area(pts) / 1e6
        degenerate = (n_term < 3) or (area < MIN_HULL_AREA_KM2)
        buf_area = buffer_union_area_km2(pts, BUFFER_R_M)
        centroid = pts.mean(axis=0) if len(pts) else np.array([np.nan, np.nan])
        span = float(np.mean(np.hypot(*(pts - centroid).T))) if len(pts) else np.nan
        s1npc = r.get("s1_npc_mean", np.nan)
        vof = r.get("vof_mean", np.nan)
        vof_pct = vof / s1npc * 100 if s1npc and not np.isnan(s1npc) and s1npc != 0 else np.nan
        rows.append({
            "city": c, "cluster": k, "terminals": n_term,
            "coinc_kw": r["coinc_kw"], "hull_area_km2": area,
            "degenerate_hull": bool(degenerate),
            "few_terminals": n_term < 3,
            "no_road_edges": len(sub_e) == 0,
            "demand_density_hull_kw_km2": (r["coinc_kw"] / area if area >= MIN_HULL_AREA_KM2 else np.nan),
            "buffer_area_km2": buf_area,
            "demand_density_buffer_kw_km2": (r["coinc_kw"] / buf_area if buf_area else np.nan),
            "road_density_km_per_km2": (road_km_in / buf_area if buf_area else np.nan),
            "mean_edge_len_m": mean_elen, "mean_degree": mdeg,
            "s1_length_m": r["s1_length_mean"],
            "route_len_per_terminal_m": (r["s1_length_mean"] / n_term if n_term else np.nan),
            "span_m": span,
            "s1_npc": s1npc, "vof": vof, "vof_pct": vof_pct,
            "zero_vof": bool(vof_pct is not None and not np.isnan(vof_pct) and vof_pct <= 0),
            "tld": r.get("tld", np.nan),
            "s2_feasible": r.get("s2_feasible", ""),
        })
m = pd.DataFrame(rows)
m.to_csv(f"{ROOT}/analysis/CEUS_MORPHOLOGY_CLUSTER.csv", index=False)

mf = m.dropna(subset=["vof_pct"])
preds = ["terminals", "coinc_kw", "hull_area_km2", "demand_density_hull_kw_km2",
         "demand_density_buffer_kw_km2", "road_density_km_per_km2",
         "mean_edge_len_m", "mean_degree", "route_len_per_terminal_m",
         "span_m", "tld"]
cors = []
for p in preds:
    sub = mf if p not in ("demand_density_hull_kw_km2", "hull_area_km2") else mf[~mf.degenerate_hull]
    sub = sub.dropna(subset=[p, "vof_pct"])
    rho = np.nan; pv = np.nan
    if len(sub) > 4:
        rho, pv = spearmanr(sub[p], sub["vof_pct"])
    signs = {}
    for c in CITIES:
        subz = mf[mf.city == c]
        if p in ("demand_density_hull_kw_km2", "hull_area_km2"):
            subz = subz[~subz.degenerate_hull]
        subz = subz.dropna(subset=[p, "vof_pct"])
        if len(subz) > 4:
            signs[c] = np.sign(spearmanr(subz[p], subz["vof_pct"])[0])
    cors.append({"predictor": p, "spearman_rho_pooled": rho,
                 "spearman_p_pooled": pv, "n_used": len(sub),
                 "sign_by_zone": ";".join(f"{k}:{int(v)}" for k, v in signs.items())})
cor = pd.DataFrame(cors)
cor.to_csv(f"{ROOT}/analysis/CEUS_MORPHOLOGY_CORRELATIONS.csv", index=False)
print(cor.to_string(index=False))
print("degenerate hulls:", int(mf["degenerate_hull"].sum()), "of", len(mf))
