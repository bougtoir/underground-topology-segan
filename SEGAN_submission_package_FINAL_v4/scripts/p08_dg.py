"""Phase 8: S3 = S2 topology + rooftop-PV distributed generation.
PV potential per demand node: snapped building footprint x usable-roof
fraction x 0.15 kWp/m2 (assumptions, labelled). PV value = generation value +
avoided losses (bounded approximation on S2 topology); curtailment handled by
capping the loss-reduction fraction. NPC_S3 = NPC_S2 + DG CAPEX(+O&M)
- (generation value + avoided loss value)."""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import yaml
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml"))
H = CFG["project"]["primary_horizon_years"]
R = CFG["project"]["discount_rate"]
EKWH = CFG["cost_model"]["electricity_jpy_per_kwh"]
OMF = CFG["cost_model"]["om_fraction_of_capex"]
DG_CAPEX = CFG["cost_model"]["dg_pv_jpy_per_kwp"]
PV_CF = CFG["dg"]["pv_capacity_factor"]
ROOF = CFG["dg"]["rooftop_fraction_usable"]
PV_KW_M2 = 0.15
LOAD_FACTOR = 0.35
ADF = sum(1.0/(1.0+R)**y for y in range(1, H+1))

rows = []
for name in ["sano", "kudamatsu", "yasu"]:
    nodes_df = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv")
    dem = {str(r["node"]): float(r["p_kw"]) for _, r in nodes_df.iterrows()}
    b = gpd.read_file(f"{ROOT}/data/raw/osm_{name}_buildings.geojson")
    b = b[b.geometry.notna()]
    zone = gpd.read_file(f"{ROOT}/data/processed/{name}/zone.geojson")
    b = gpd.clip(b, zone.union_all())
    b["footprint_m2"] = b.to_crs(b.estimate_utm_crs()).geometry.area
    b["geometry"] = b.geometry.centroid
    tree = cKDTree(nodes_df[["lat", "lon"]].values)
    d, i = tree.query(np.array([[g.y, g.x] for g in b.geometry]))
    pv_node = (pd.Series(b["footprint_m2"].values * ROOF * PV_KW_M2,
                         index=nodes_df["node"].astype(float).astype(str).values[i])
               .groupby(level=0).sum())
    grp = pd.read_csv(f"{ROOT}/data/processed/{name}/clusters.csv")
    grp["node"] = grp["node"].astype(str)
    rc = pd.read_csv(f"{ROOT}/data/processed/{name}/cluster_results.csv")
    s3_rows = []
    for c in rc["cluster"].unique():
        terms = list(grp[grp["cluster"] == c]["node"])
        pv_c = pv_node.reindex(terms).fillna(0.0)
        row = rc[rc["cluster"] == c].iloc[0]
        eloss2 = row["s2_plkw"] * 8760 * LOAD_FACTOR
        pen = pv_c.sum() / max(sum(dem.get(t, 0) for t in terms), 1e-9)
        loss_red_frac = min(0.5, PV_CF * pen)          # bounded approx
        eloss3 = eloss2 * (1 - loss_red_frac)
        gen_kwh = pv_c.sum() * 8760 * PV_CF
        dem_kwh = sum(dem.get(t, 0) for t in terms) * 8760 * LOAD_FACTOR
        gen_kwh = min(gen_kwh, dem_kwh)   # self-consumption bound
        capex_dg = pv_c.sum() * DG_CAPEX
        npc_s2 = row["s2_npc"]
        npc_s3 = (npc_s2 + capex_dg * (1 + OMF * ADF)
                  - (gen_kwh * EKWH + (eloss2 - eloss3) * EKWH) * ADF)
        s3_rows.append(dict(city=name, cluster=c, pv_kwp=pv_c.sum(), pen=pen,
                            gen_kwh_y=gen_kwh, eloss_delta_kwh=eloss2 - eloss3,
                            capex_dg=capex_dg, npc_s2=npc_s2, npc_s3=npc_s3,
                            delta_npc_s3=row["s1_npc_mean"] - npc_s3))
    s3 = pd.DataFrame(s3_rows)
    s3.to_csv(f"{ROOT}/data/processed/{name}/s3_results.csv", index=False)
    rows.append(dict(city=name, pv_kwp_total=float(s3["pv_kwp"].sum()),
                     gen_gwh_y=float(s3["gen_kwh_y"].sum()/1e6),
                     npc_s3=float(s3["npc_s3"].sum()), npc_s2=float(s3["npc_s2"].sum()),
                     dg_delta_npc=float(s3["npc_s3"].sum() - s3["npc_s2"].sum()),
                     p_s3_better=float((s3["npc_s3"] < s3["npc_s2"]).mean())))
    print(rows[-1])
pd.DataFrame(rows).to_csv(f"{ROOT}/analysis/dg_results.csv", index=False)
print("done")
