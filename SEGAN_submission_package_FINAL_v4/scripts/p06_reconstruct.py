"""Phase 6: per-LV-feeder-cluster reconstruction, 2 families x M replicates.
Each cluster (~350 kW target, k-means on demand nodes) is an LV service area
behind a MODELLED distribution transformer at the demand-weighted centroid.
Family A: anchor-constrained Steiner/radial reconstruction (jittered costs).
Family B: incremental historical-growth/path-dependence reconstruction.
A reconstructed network is NEVER labelled observed utility topology."""
import glob
import os, json, math
import numpy as np
import pandas as pd
import networkx as nx
from scipy.spatial import cKDTree
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml"))
M = CFG["reconstruction"]["n_replicates"] // 2      # per family
SEED = CFG["project"]["seed"]
CLUSTER_KW = 350.0                                  # ~500kVA class LV feeder
BUFFER_M = 150.0

def nid(value):
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.12g}"


def node_key(value):
    return (float(value), str(value))


def ordered_edges(graph, data=False):
    edges = []
    for edge in graph.edges(data=data):
        u, v = edge[:2]
        if node_key(v) < node_key(u):
            edge = (v, u, *edge[2:])
        edges.append(edge)
    return sorted(edges, key=lambda edge: (node_key(edge[0]), node_key(edge[1])))


def load_city(name):
    n = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv")
    e = pd.read_csv(f"{ROOT}/data/processed/{name}/edges.csv")
    G = nx.Graph()
    for _, r in e.iterrows():
        G.add_edge(nid(r["u"]), nid(r["v"]), length=float(r["length"]))
    pos = {nid(r["node"]): (r["x_m"], r["y_m"]) for _, r in n.iterrows()}
    dem = {nid(r["node"]): float(r["p_kw"]) for _, r in n.iterrows()}
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
    for u, v, d in ordered_edges(G, data=True):
        w = d["length"] * (1.0 + jitter * rng.random())
        if anchor_bias is not None:
            w *= anchor_bias.get((u, v), 1.0)
        Gw.add_edge(u, v, length=w)
    T = nx.Graph()
    tl = sorted(dict.fromkeys(terms), key=node_key)
    for i, s in enumerate(tl):
        sp, spp = nx.single_source_dijkstra(Gw, s, weight="length")
        for t in tl[i+1:]:
            if t in sp:
                T.add_edge(s, t, weight=sp[t], path=spp[t])
    if not T.edges:
        return None
    mst = nx.minimum_spanning_tree(T, weight="weight")
    out = nx.Graph()
    for s, t in ordered_edges(mst):
        path = T[s][t]["path"]
        for a, b in zip(path[:-1], path[1:]):
            out.add_edge(a, b)
    return out

def incremental(G, source, terminals, rng):
    order = sorted(dict.fromkeys(terminals), key=node_key)
    rng.shuffle(order)
    net = {source}
    out = nx.Graph()
    for t in order:
        dist, paths = nx.single_source_dijkstra(G, t, weight="length")
        best, bp = (math.inf, (math.inf, "")), None
        for nn in sorted(net, key=node_key):
            candidate = (dist[nn], node_key(nn)) if nn in dist else best
            if candidate < best:
                best, bp = candidate, paths[nn]
        if bp:
            for a, b in zip(bp[:-1], bp[1:]):
                out.add_edge(a, b)
                net.update([a, b])
    return out

def anchor_bias_map(name, nlatlon):
    p = f"{ROOT}/data/processed/{name}_anchors.csv"
    if not os.path.exists(p):
        return None
    a = pd.read_csv(p)[["緯度", "経度"]].values
    tree = cKDTree(nlatlon.values)
    d, i = tree.query(a)
    near = set(nlatlon.index[i[d < 0.001]].astype(str))   # ~<100m snap
    return near

summary = []
for name in ["sano", "kudamatsu", "yasu"]:
    n, G, pos, dem = load_city(name)
    dnodes = [x for x in G.nodes if dem.get(x, 0) > 0]
    # Cluster within connected road-graph components.
    cluster_of = {}
    cluster_component = {}
    next_cluster = 0
    components = sorted(
        (sorted(component, key=node_key)
         for component in nx.connected_components(G)),
        key=lambda component: node_key(component[0]))
    for component_index, component in enumerate(components):
        component = set(component)
        local_nodes = [x for x in dnodes if x in component]
        if not local_nodes:
            continue
        target = max(1, int(round(sum(dem[x] for x in local_nodes) / CLUSTER_KW)))
        local_k = min(len(local_nodes), target)
        if local_k == 1:
            labels = np.zeros(len(local_nodes), dtype=int)
        else:
            X = np.array([pos[x] for x in local_nodes])
            labels, _ = kmeans(
                X, local_k,
                np.random.default_rng(SEED + 1009 * component_index))
        for local_cluster in range(local_k):
            cluster = next_cluster + local_cluster
            cluster_component[cluster] = component
            for node, label in zip(local_nodes, labels):
                if label == local_cluster:
                    cluster_of[node] = cluster
        next_cluster += local_k
    k = next_cluster
    nlatlon = n.set_index("node")[["lat", "lon"]]
    nlatlon.index = nlatlon.index.map(nid)
    near_anchor_nodes = anchor_bias_map(name, nlatlon)
    outdir = f"{ROOT}/data/processed/{name}/recon"
    os.makedirs(outdir, exist_ok=True)
    for stale in glob.glob(f"{outdir}/c*_r*_*.csv"):
        os.remove(stale)
    edge_freq = {}
    for c in range(k):
        terms = [x for x in dnodes if cluster_of[x] == c]
        if not terms:
            continue
        if len(terms) == 1:
            src = terms[0]
            for r in range(2 * M):
                fam = "A_steiner" if r < M else "B_incremental"
                pd.DataFrame(columns=["u", "v"]).to_csv(
                    f"{outdir}/c{c:03d}_r{r:02d}_{fam}.csv", index=False)
                summary.append(dict(
                    city=name, cluster=c, rep=r, family=fam, src=src,
                    edges=0, length_m=0.0, terminals=1))
            continue
        xs = [pos[t][0] for t in terms]; ys = [pos[t][1] for t in terms]
        xmin, xmax = min(xs) - BUFFER_M, max(xs) + BUFFER_M
        ymin, ymax = min(ys) - BUFFER_M, max(ys) + BUFFER_M
        sub_nodes = sorted([
            x for x in cluster_component[c]
            if xmin <= pos[x][0] <= xmax and ymin <= pos[x][1] <= ymax],
            key=node_key)
        H = G.subgraph(sub_nodes).copy()
        if (not set(terms).issubset(H)
                or not set(terms).issubset(nx.node_connected_component(H, terms[0]))):
            H = G.subgraph(cluster_component[c]).copy()
        xs = [pos[t][0] for t in terms]; ys = [pos[t][1] for t in terms]
        w = np.array([dem[t] for t in terms])
        cx, cy = np.average(xs, weights=w), np.average(ys, weights=w)
        src = min(
            H.nodes,
            key=lambda x: (
                (pos[x][0]-cx)**2 + (pos[x][1]-cy)**2,
                node_key(x)))
        terms = [src] + [t for t in terms if t != src]
        bias = None
        if near_anchor_nodes:
            bias = {(u, v): 0.9 if (u in near_anchor_nodes or v in near_anchor_nodes) else 1.0
                    for u, v in ordered_edges(H)}
        for r in range(2 * M):
            rng = np.random.default_rng(SEED + 977 * c + r)
            if r < M:
                net = steiner_approx(H, terms, rng, anchor_bias=bias)
                fam = "A_steiner"
            else:
                net = incremental(H, src, terms, rng)
                fam = "B_incremental"
            if net is None or not nx.is_connected(net):
                continue
            for a, b in ordered_edges(net):
                key = (name, c, *sorted((a, b)))
                edge_freq[key] = edge_freq.get(key, 0) + 1
            ed = pd.DataFrame(ordered_edges(net), columns=["u", "v"])
            ed.to_csv(f"{outdir}/c{c:03d}_r{r:02d}_{fam}.csv", index=False)
            summary.append(dict(city=name, cluster=c, rep=r, family=fam, src=src,
                                edges=len(net.edges),
                                length_m=sum(
                                    H[a][b]["length"]
                                    for a, b in ordered_edges(net)),
                                terminals=len(terms)))
    pd.DataFrame([{"city": kk[0], "cluster": kk[1], "u": kk[2], "v": kk[3], "freq": vv/(2*M)}
                  for kk, vv in sorted(edge_freq.items())]
                 ).to_csv(f"{outdir}/edge_presence_freq.csv", index=False)
    n_out = n.copy()
    n_out["cluster"] = n_out["node"].map(
        lambda value: cluster_of.get(nid(value), np.nan))
    n_out.to_csv(f"{ROOT}/data/processed/{name}/nodes_with_cluster.csv", index=False)
    ordered_cluster_nodes = sorted(cluster_of, key=node_key)
    pd.DataFrame({"node": ordered_cluster_nodes,
                  "cluster": [cluster_of[node] for node in ordered_cluster_nodes]}
                 ).to_csv(f"{ROOT}/data/processed/{name}/clusters.csv", index=False)
    print(name, "clusters", k, "replicates written",
          len([s for s in summary if s["city"] == name]))
pd.DataFrame(summary).to_csv(f"{ROOT}/analysis/reconstruction_summary.csv", index=False)
print("done")
