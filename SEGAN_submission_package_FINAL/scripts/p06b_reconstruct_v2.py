"""Phase 6 (corrected): LV-cluster reconstruction under
config/ENGINEERING_FEASIBILITY_SPEC.yaml.
Corrections vs v1: MV-served nodes (>lv_max_node_kw raw peak) excluded and
recorded; cluster target ~100 kW raw (150 kVA transformer zones).
Outputs go to recon_v2/ and clusters_v2.csv; v1 outputs untouched."""
import os, math
import numpy as np
import pandas as pd
import networkx as nx
from scipy.spatial import cKDTree
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml"))
SPEC = yaml.safe_load(open(f"{ROOT}/config/ENGINEERING_FEASIBILITY_SPEC.yaml"))
M = CFG["reconstruction"]["n_replicates"] // 2
SEED = CFG["project"]["seed"]
CLUSTER_KW = SPEC["demand_model"]["cluster_target_kw"]     # 100 kW
LV_MAX = SPEC["demand_model"]["lv_max_node_kw"]            # 150 kW
BUFFER_M = 150.0

def load_city(name):
    n = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv")
    e = pd.read_csv(f"{ROOT}/data/processed/{name}/edges.csv")
    G = nx.Graph()
    for _, r in e.iterrows():
        G.add_edge(str(r["u"]), str(r["v"]), length=float(r["length"]))
    pos = {str(r["node"]): (r["x_m"], r["y_m"]) for _, r in n.iterrows()}
    dem = {str(r["node"]): float(r["p_kw"]) for _, r in n.iterrows()}
    return n, G, pos, dem

def kmeans(X, k, rng, iters=60):
    idx = rng.choice(len(X), k, replace=False)
    C = X[idx].copy()
    for _ in range(iters):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            if (lab == j).any():
                C[j] = X[lab == j].mean(0)
    return lab, C

def steiner_approx(G, terms, rng, jitter=0.15, anchor_bias=None):
    Gw = nx.Graph()
    for u, v, d in G.edges(data=True):
        w = d["length"] * (1.0 + jitter * rng.random())
        if anchor_bias is not None:
            w *= anchor_bias.get((u, v), 1.0)
        Gw.add_edge(u, v, length=w)
    sp = dict(nx.all_pairs_dijkstra_path_length(Gw, weight="length"))
    spp = dict(nx.all_pairs_dijkstra_path(Gw, weight="length"))
    T = nx.Graph(); tl = list(terms)
    for i, s in enumerate(tl):
        for t in tl[i+1:]:
            if s in sp and t in sp[s]:
                T.add_edge(s, t, weight=sp[s][t])
    if not T.edges:
        return None
    mst = nx.minimum_spanning_tree(T, weight="weight")
    out = nx.Graph()
    for s, t in mst.edges():
        for a, b in zip(spp[s][t][:-1], spp[s][t][1:]):
            out.add_edge(a, b)
    return out

def incremental(G, source, terminals, rng):
    order = list(terminals); rng.shuffle(order)
    net = {source}; out = nx.Graph()
    for t in order:
        dist, paths = nx.single_source_dijkstra(G, t, weight="length")
        best, bp = math.inf, None
        for nn in net:
            if nn in dist and dist[nn] < best:
                best, bp = dist[nn], paths[nn]
        if bp:
            for a, b in zip(bp[:-1], bp[1:]):
                out.add_edge(a, b); net.update([a, b])
    return out

def anchor_bias_map(name, nlatlon):
    p = f"{ROOT}/data/processed/{name}_anchors.csv"
    if not os.path.exists(p):
        return None
    a = pd.read_csv(p)[["緯度", "経度"]].values
    tree = cKDTree(nlatlon.values)
    d, i = tree.query(a)
    return set(nlatlon.index[i[d < 0.001]].astype(str))

summary, mv_rows = [], []
for name in ["sano", "kudamatsu", "yasu"]:
    n, G, pos, dem = load_city(name)
    dnodes_all = [x for x in G.nodes if dem.get(x, 0) > 0]
    mv_nodes = [x for x in dnodes_all if dem[x] > LV_MAX]
    dnodes = [x for x in dnodes_all if dem[x] <= LV_MAX]
    mv_rows.append(dict(city=name, n_mv=len(mv_nodes),
                        mv_demand_kw=sum(dem[x] for x in mv_nodes),
                        lv_nodes=len(dnodes),
                        lv_demand_kw=sum(dem[x] for x in dnodes)))
    X = np.array([pos[x] for x in dnodes])
    k = max(2, int(round(sum(dem[x] for x in dnodes) / CLUSTER_KW)))
    lab, C = kmeans(X, k, np.random.default_rng(SEED))
    cluster_of = dict(zip(dnodes, lab))
    nlatlon = n.set_index("node")[["lat", "lon"]]
    nlatlon.index = nlatlon.index.astype(str)
    near_anchor_nodes = anchor_bias_map(name, nlatlon)
    outdir = f"{ROOT}/data/processed/{name}/recon_v2"
    os.makedirs(outdir, exist_ok=True)
    edge_freq = {}
    for c in range(k):
        terms = [x for x in dnodes if cluster_of[x] == c]
        if len(terms) < 2:
            continue
        xs = [pos[t][0] for t in terms]; ys = [pos[t][1] for t in terms]
        xmin, xmax = min(xs)-BUFFER_M, max(xs)+BUFFER_M
        ymin, ymax = min(ys)-BUFFER_M, max(ys)+BUFFER_M
        sub_nodes = [x for x in G.nodes
                     if xmin <= pos[x][0] <= xmax and ymin <= pos[x][1] <= ymax]
        H = G.subgraph(sub_nodes)
        if not all(t in H for t in terms):
            H = nx.compose(H, G.subgraph([t for t in terms if t not in H]))
        comps = list(nx.connected_components(H))
        if len(comps) > 1:
            H = H.subgraph(max(comps, key=len)).copy()
        terms = [t for t in terms if t in H]
        if len(terms) < 2:
            continue
        xs = [pos[t][0] for t in terms]; ys = [pos[t][1] for t in terms]
        w = np.array([dem[t] for t in terms])
        cx, cy = np.average(xs, weights=w), np.average(ys, weights=w)
        src = min(H.nodes, key=lambda x: (pos[x][0]-cx)**2 + (pos[x][1]-cy)**2)
        terms = [src] + [t for t in terms if t != src]
        bias = None
        if near_anchor_nodes:
            bias = {(u, v): 0.9 if (u in near_anchor_nodes or v in near_anchor_nodes) else 1.0
                    for u, v in H.edges()}
        for r in range(2 * M):
            rng = np.random.default_rng(SEED + 977 * c + r)
            if r < M:
                net = steiner_approx(H, terms, rng, anchor_bias=bias); fam = "A_steiner"
            else:
                net = incremental(H, src, terms, rng); fam = "B_incremental"
            if net is None or not nx.is_connected(net):
                continue
            for a, b in net.edges():
                key = (name, c, *sorted((a, b)))
                edge_freq[key] = edge_freq.get(key, 0) + 1
            pd.DataFrame(list(net.edges), columns=["u", "v"]).to_csv(
                f"{outdir}/c{c:03d}_r{r:02d}_{fam}.csv", index=False)
            summary.append(dict(city=name, cluster=c, rep=r, family=fam, src=src,
                                edges=len(net.edges),
                                length_m=sum(H[a][b]["length"] for a, b in net.edges()),
                                terminals=len(terms),
                                raw_kw=sum(dem[t] for t in terms)))
    pd.DataFrame([{"city": kk[0], "cluster": kk[1], "u": kk[2], "v": kk[3],
                   "freq": vv/(2*M)} for kk, vv in edge_freq.items()]
                 ).to_csv(f"{outdir}/edge_presence_freq.csv", index=False)
    pd.DataFrame({"node": list(cluster_of.keys()), "cluster": list(cluster_of.values())}
                 ).to_csv(f"{ROOT}/data/processed/{name}/clusters_v2.csv", index=False)
    print(name, "clusters done; LV nodes", len(dnodes), "MV excluded", len(mv_nodes))
pd.DataFrame(summary).to_csv(f"{ROOT}/analysis/reconstruction_summary_v2.csv", index=False)
pd.DataFrame(mv_rows).to_csv(f"{ROOT}/analysis/mv_served_nodes.csv", index=False)
print("done")
