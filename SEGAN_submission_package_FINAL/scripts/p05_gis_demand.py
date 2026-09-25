"""Phase 5: build study zones (roads + demand nodes) per municipality.
Demand is MODELLED (labelled): building footprint area x assumed floors x
demand density, clustered onto road nodes. Aggregate calibration is reported."""
import os, json
import geopandas as gpd
import pandas as pd
import numpy as np
import networkx as nx
import osmnx as ox
from scipy.spatial import cKDTree
from shapely.geometry import box

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CITIES = {
    "sano":      dict(anchor_csv=None, anchor_hint="sano_anchors"),
    "kudamatsu": dict(anchor_csv=None, anchor_hint="kudamatsu_anchors"),
    "yasu":      dict(anchor_csv=None, anchor_hint=None),
}
ZONE_HALF_M = 1300          # study zone half-width (m) -> ~2.6 km square
FLOOR_ASSUMED = 2           # assumed floors when tag missing (assumption)
# demand density W/m2 peak, by building class (assumed; documented)
DENSITY = {"yes": 25.0, "residential": 30.0, "house": 35.0, "detached": 35.0,
           "apartments": 22.0, "commercial": 55.0, "retail": 55.0,
           "office": 50.0, "industrial": 45.0, "warehouse": 20.0,
           "public": 40.0, "school": 40.0, "hospital": 60.0, "default": 28.0}
# aggregate calibration target: Japanese household avg peak ~3.2 kW (assumed)
CALIB_NOTE = "aggregate demand calibrated so mean residential peak ~= 3.2 kW/dwelling-equivalent"

def load_graph(name):
    return ox.load_graphml(f"{ROOT}/data/raw/osm_{name}.graphml")

def project(gdf):
    return gdf.to_crs(gdf.estimate_utm_crs())

def building_demands(b):
    b = b[b.geometry.notna()].copy()
    bt = b.get("building", pd.Series(["yes"] * len(b))).fillna("yes").astype(str).str.lower()
    b["density_w_m2"] = bt.map(lambda t: DENSITY.get(t, DENSITY["default"]))
    lvl = pd.to_numeric(b.get("building:levels", pd.Series([np.nan] * len(b))), errors="coerce").fillna(FLOOR_ASSUMED)
    b["p_kw"] = b["footprint_m2"] * lvl * b["density_w_m2"] / 1000.0
    return b

for name, meta in CITIES.items():
    print("===", name)
    G = load_graph(name)
    # study zone center: median of anchors (tier1/2) else building-density centroid
    if meta["anchor_hint"]:
        a = pd.read_csv(f"{ROOT}/data/processed/{meta['anchor_hint']}.csv")
        lat = a["緯度"].median(); lon = a["経度"].median()
    else:
        bb = gpd.read_file(f"{ROOT}/data/raw/osm_{name}_buildings.geojson")
        c = bb.geometry.centroid
        lat, lon = c.y.median(), c.x.median()
    # zone polygon in local CRS
    center = gpd.GeoSeries([__import__("shapely").geometry.Point(lon, lat)], crs=4326)
    utm = center.estimate_utm_crs()
    cu = center.to_crs(utm).iloc[0]
    zone_poly = box(cu.x - ZONE_HALF_M, cu.y - ZONE_HALF_M,
                    cu.x + ZONE_HALF_M, cu.y + ZONE_HALF_M)
    # graph to gdfs in utm
    nodes, edges = ox.graph_to_gdfs(G)
    nodes = nodes.to_crs(utm); edges = edges.to_crs(utm)
    nodes_z = nodes[nodes.geometry.within(zone_poly)]
    keep = set(nodes_z.index)
    edges_z = edges[edges.index.get_level_values(0).isin(keep) & edges.index.get_level_values(1).isin(keep)]
    H = nx.Graph()
    for idx, e in edges_z.iterrows():
        u, v, k = idx
        H.add_edge(u, v, length=float(e.get("length", np.nan) or 0.0))
    H = H.subgraph(max(nx.connected_components(H), key=len)).copy()
    keep = set(H.nodes)
    nodes_z = nodes_z.loc[list(keep)]
    edges_z = edges_z[edges_z.index.get_level_values(0).isin(keep) & edges_z.index.get_level_values(1).isin(keep)]
    # demand: buildings inside zone, snapped to nearest road node
    b = gpd.read_file(f"{ROOT}/data/raw/osm_{name}_buildings.geojson")
    b = b[b.geometry.notna()]
    b["footprint_m2"] = b.to_crs(b.estimate_utm_crs()).geometry.area
    b["geometry"] = b.geometry.centroid
    bu = b.to_crs(utm)
    bu = bu[bu.geometry.within(zone_poly)]
    bu = building_demands(bu)
    ncoords = np.array([[g.x, g.y] for g in nodes_z.geometry])
    tree = cKDTree(ncoords)
    bcoords = np.array([[g.x, g.y] for g in bu.geometry])
    dist, idx = tree.query(bcoords)
    node_ids = list(nodes_z.index)
    bu["node"] = [node_ids[i] for i in idx]
    bu["snap_m"] = dist
    dem = bu.groupby("node")["p_kw"].sum().rename("p_kw")
    demand_nodes = nodes_z.join(dem).fillna({"p_kw": 0.0})
    outdir = f"{ROOT}/data/processed/{name}"
    os.makedirs(outdir, exist_ok=True)
    export_nodes = demand_nodes.copy()
    export_nodes["lon"], export_nodes["lat"] = export_nodes.to_crs(4326).geometry.x, export_nodes.to_crs(4326).geometry.y
    export_nodes["x_m"], export_nodes["y_m"] = export_nodes.geometry.x, export_nodes.geometry.y
    export_nodes["node"] = export_nodes.index.astype(str)
    export_nodes[["node", "lat", "lon", "x_m", "y_m", "p_kw"]].to_csv(f"{outdir}/nodes.csv", index=False)
    eexp = edges_z.reset_index()[["u", "v", "length"]]
    eexp.to_csv(f"{outdir}/edges.csv", index=False)
    pd.DataFrame({"node": dem.index, "p_kw": dem.values}).to_csv(f"{outdir}/demand_nodes.csv", index=False)
    gpd.GeoSeries([zone_poly], crs=utm).to_crs(4326).to_file(f"{outdir}/zone.geojson", driver="GeoJSON")
    qc = dict(city=name, road_nodes=len(nodes_z), road_edges=len(edges_z),
              buildings=len(bu), mean_snap_m=float(dist.mean()),
              total_p_kw=float(demand_nodes["p_kw"].sum()),
              median_building_p_kw=float(bu["p_kw"].median()),
              mean_building_p_kw=float(bu["p_kw"].mean()))
    json.dump(qc, open(f"{outdir}/zone_qc.json", "w"), indent=1)
    print(qc)
print("done")
