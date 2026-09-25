"""Phase 7: per-cluster scenario evaluation + topology optimization.
S1   : like-for-like undergrounding of each reconstructed legacy tree
S1.5 : minimum-construction Steiner network (loss-blind)
S2   : life-cycle optimized = best-NPC candidate from multi-weight Steiner
       family (edge weight = length*(COST_M + w_loss*resistance-proxy)).
Loss : LinDistFlow approximation at peak demand (kW), voltage drop %.
Label: 'modeled'. S2 is best-found; optimality gap not certified."""
import os, math, glob
import numpy as np
import pandas as pd
import networkx as nx
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml"))
RHO = CFG["electrical"]["conductor_resistivity_ohm_m"]
A = CFG["electrical"]["lv_conductor_area_mm2"] * 1e-6
R_PER_M = RHO / A
V_LL = CFG["voltage"]["nominal_lv_v"]
PF = CFG["electrical"]["power_factor_default"]
H = CFG["project"]["primary_horizon_years"]
R = CFG["project"]["discount_rate"]
EKWH = CFG["cost_model"]["electricity_jpy_per_kwh"]
COST_M = (CFG["cost_model"]["excavation_jpy_per_m"] +
          CFG["cost_model"]["duct_bank_jpy_per_m"] +
          CFG["cost_model"]["cable_lv_jpy_per_m"])
OMF = CFG["cost_model"]["om_fraction_of_capex"]
LOAD_FACTOR = 0.35                      # assumed mean/peak for loss energy
ADF = sum(1.0/(1.0+R)**y for y in range(1, H+1))
EXC_DUCT = CFG["cost_model"]["excavation_jpy_per_m"] + CFG["cost_model"]["duct_bank_jpy_per_m"]
CAB_REF = CFG["cost_model"]["cable_lv_jpy_per_m"]   # jpy/m at 150 mm2, scaled by area
A_REF = CFG["electrical"]["lv_conductor_area_mm2"]  # 150
CONDUCTOR_SIZES = [150, 250, 400, 600]              # mm2 options (S2 can upsize)

def load_city(name):
    n = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv")
    e = pd.read_csv(f"{ROOT}/data/processed/{name}/edges.csv")
    G = nx.Graph()
    for _, r in e.iterrows():
        G.add_edge(str(r["u"]), str(r["v"]), length=float(r["length"]))
    pos = {str(r["node"]): (r["x_m"], r["y_m"]) for _, r in n.iterrows()}
    dem = {str(r["node"]): float(r["p_kw"]) for _, r in n.iterrows()}
    return G, pos, dem

def tree_flows(G, dem, src):
    order = list(nx.bfs_tree(G, src).edges())
    sub = {n: dem.get(n, 0.0) for n in G.nodes}
    for u, v in reversed(order):
        sub[u] = sub.get(u, 0) + sub.get(v, 0)
    return order, sub

def edge_metrics(G, dem, src, area_map=None):
    """Return per-edge flow and loss/drop; area_map edge(mm2)->optional."""
    order, sub = tree_flows(G, dem, src)
    out = []
    for u, v in order:
        Pw = sub[v]; L = G[u][v]["length"]
        I = Pw * 1000.0 / (math.sqrt(3) * V_LL * PF)
        a = (area_map or {}).get(tuple(sorted((u, v))), A_REF)
        Re = RHO * L / (a * 1e-6)
        out.append((u, v, Pw, I, Re, L))
    return order, out

def choose_conductor(order_flows):
    """Per-edge conductor size minimizing capex+discounted loss share."""
    amap = {}
    for u, v, Pw, I, Re150, L in order_flows:
        best_a, best_c = A_REF, math.inf
        for a in CONDUCTOR_SIZES:
            cab = CAB_REF * a / A_REF
            capex = L * (EXC_DUCT + cab)
            loss_kwh = 3.0 * I * I * (RHO * L / (a * 1e-6)) / 1000.0 * 8760 * LOAD_FACTOR
            tot = capex + (loss_kwh * EKWH + capex * OMF) * ADF
            if tot < best_c:
                best_c, best_a = tot, a
        amap[tuple(sorted((u, v)))] = best_a
    return amap

def npc(G, dem, src, optimize_conductor=False):
    order, flows = edge_metrics(G, dem, src)
    amap = choose_conductor(flows) if optimize_conductor else None
    pl = 0.0; drop = {src: 0.0}; md = 0.0; capex = 0.0; length_m = 0.0; up_m = 0.0
    for u, v, Pw, I, Re150, L in flows:
        a = (amap or {}).get(tuple(sorted((u, v))), A_REF)
        Re = RHO * L / (a * 1e-6)
        pl += 3.0 * I * I * Re / 1000.0
        drop[v] = drop.get(u, 0.0) + math.sqrt(3) * I * Re
        md = max(md, drop[v])
        capex += L * (EXC_DUCT + CAB_REF * a / A_REF)
        length_m += L
        if a > A_REF:
            up_m += L
    eloss = pl * 8760 * LOAD_FACTOR
    return dict(npc=capex + (eloss * EKWH + capex * OMF) * ADF,
                capex=capex, length_m=length_m, pl_kw=pl,
                eloss_kwh_y=eloss, vdrop_pct=md / V_LL * 100.0,
                upsize_m=up_m)

def weighted_steiner(G, terms, w_loss, src):
    """Edge weight = length*(COST_M + w_loss * W0/(50 + dist_to_source)).
    Loss priority loads the near-source trunk edges, pushing min-loss
    candidates toward source-hugging (hub) topologies."""
    d_src = nx.single_source_dijkstra_path_length(G, src, weight="length")
    Gw = nx.Graph()
    for u, v, d in G.edges(data=True):
        ds = min(d_src.get(u, 1e9), d_src.get(v, 1e9))
        Gw.add_edge(u, v, length=d["length"] * (COST_M + w_loss * 2e5 / (50.0 + ds)))
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
            out.add_edge(a, b, length=G[a][b]["length"])
    return out

def prune(G, keep):
    G = G.copy(); keep = set(keep)
    while True:
        leaves = [n for n in G.nodes if G.degree(n) <= 1 and n not in keep]
        if not leaves:
            return G
        G.remove_nodes_from(leaves)

rows = []
for name in ["sano", "kudamatsu", "yasu"]:
    G, pos, dem = load_city(name)
    cl = pd.read_csv(f"{ROOT}/data/processed/{name}/clusters.csv")
    cl["node"] = cl["node"].astype(str)
    recon_sum = pd.read_csv(f"{ROOT}/analysis/reconstruction_summary.csv")
    recon_sum["cluster"] = recon_sum["cluster"].astype(str)
    src_map = recon_sum[recon_sum["city"] == name].drop_duplicates("cluster").set_index("cluster")["src"].astype(str).to_dict()
    res_c = []
    outdir = f"{ROOT}/data/processed/{name}"
    for c, grp in cl.groupby("cluster"):
        terms_all = list(grp["node"])
        if len(terms_all) < 2:
            continue
        xs = [pos[t][0] for t in terms_all]; ys = [pos[t][1] for t in terms_all]
        w = np.array([dem[t] for t in terms_all])
        cx, cy = np.average(xs, weights=w), np.average(ys, weights=w)
        src = src_map.get(str(c))
        if src is None or src not in pos:
            xmin0, xmax0 = min(xs)-150, max(xs)+150; ymin0, ymax0 = min(ys)-150, max(ys)+150
            sub0 = [x for x in G.nodes if xmin0 <= pos[x][0] <= xmax0 and ymin0 <= pos[x][1] <= ymax0]
            src = min(sub0 or list(G.nodes), key=lambda x: (pos[x][0]-cx)**2 + (pos[x][1]-cy)**2)
        terms = [src] + [t for t in terms_all if t != src]
        # S1: recon trees for this cluster
        s1 = []
        for f in sorted(glob.glob(f"{outdir}/recon/c{c:03d}_r*_*csv")):
            ed = pd.read_csv(f)
            T = nx.Graph()
            for _, r in ed.iterrows():
                a, b = str(r["u"]), str(r["v"])
                T.add_edge(a, b, length=G[a][b]["length"])
            if src in T and nx.is_connected(T):
                s1.append((os.path.basename(f), npc(T, dem, src)))
        # candidates: multi-weight Steiner on cluster road subgraph
        xmin, xmax = min(xs)-200, max(xs)+200; ymin, ymax = min(ys)-200, max(ys)+200
        sub_nodes = [x for x in G.nodes if xmin <= pos[x][0] <= xmax and ymin <= pos[x][1] <= ymax]
        Hg = G.subgraph(sub_nodes)
        if not all(t in Hg for t in terms):
            continue
        cand = {}
        for wl in [0, 1, 3, 10, 30, 100]:
            t = weighted_steiner(Hg, terms, wl, src)
            if t is not None and nx.is_connected(t) and src in t:
                cand[wl] = prune(t, terms)
        if not cand or not s1:
            continue
        s15 = cand.get(0, list(cand.values())[0])
        cand_npc = {k: npc(v, dem, src, optimize_conductor=True) for k, v in cand.items()}
        best = min(cand_npc, key=lambda k: cand_npc[k]["npc"])
        ec = {tuple(sorted(e2)) for e2 in s15.edges()}
        el = {tuple(sorted(e2)) for e2 in cand[max(cand)] .edges()}
        tld = 1 - len(ec & el) / max(1, len(ec | el))
        s1B = [x[1] for x in s1 if "_B_" in x[0]] or [x[1] for x in s1]
        s1A = [x[1] for x in s1 if "_A_" in x[0]] or [x[1] for x in s1]
        res_c.append(dict(
            city=name, cluster=c, terminals=len(terms),
            s1_npc_mean=np.mean([x[1]["npc"] for x in s1]),
            s1_npc_std=np.std([x[1]["npc"] for x in s1]),
            s1B_npc_mean=np.mean([x["npc"] for x in s1B]),
            s1A_npc_mean=np.mean([x["npc"] for x in s1A]),
            s1B_length_mean=np.mean([x["length_m"] for x in s1B]),
            s1_capex_mean=np.mean([x[1]["capex"] for x in s1]),
            s1_length_mean=np.mean([x[1]["length_m"] for x in s1]),
            s1_plkw_mean=np.mean([x[1]["pl_kw"] for x in s1]),
            s1_vdrop_max=max(x[1]["vdrop_pct"] for x in s1),
            s2_npc=cand_npc[best]["npc"], s2_w=best,
            s2_capex=cand_npc[best]["capex"], s2_plkw=cand_npc[best]["pl_kw"],
            s2_length=cand_npc[best]["length_m"], s2_vdrop=cand_npc[best]["vdrop_pct"],
            s2_upsize_m=cand_npc[best]["upsize_m"],
            tld=tld))
        if c == 0:
            nx.write_edgelist(cand[best], f"{outdir}/s2_cluster0.edgelist", data=["length"])
    rc = pd.DataFrame(res_c)
    rc["delta_npc"] = rc["s1_npc_mean"] - rc["s2_npc"]
    rc["delta_npc_B"] = rc["s1B_npc_mean"] - rc["s2_npc"]
    rc["ltp_pct"] = 100 * rc["delta_npc"] / rc["s1_npc_mean"]
    rc["ltpB_pct"] = 100 * rc["delta_npc_B"] / rc["s1B_npc_mean"]
    rc.to_csv(f"{outdir}/cluster_results.csv", index=False)
    rows.append(dict(city=name, clusters=len(rc),
                     total_demand_kw=sum(dem.values()),
                     s1_npc=rc["s1_npc_mean"].sum(), s2_npc=rc["s2_npc"].sum(),
                     delta_npc=rc["delta_npc"].sum(),
                     delta_npc_B=rc["delta_npc_B"].sum(),
                     ltp_pct=100*rc["delta_npc"].sum()/rc["s1_npc_mean"].sum(),
                     ltpB_pct=100*rc["delta_npc_B"].sum()/rc["s1B_npc_mean"].sum(),
                     p_ltp_pos=float((rc["delta_npc"] > 0).mean()),
                     p_ltpB_pos=float((rc["delta_npc_B"] > 0).mean()),
                     mean_tld=float(rc["tld"].mean()),
                     upsize_km=float(rc["s2_upsize_m"].sum()/1000),
                     max_vdrop=float(rc[["s1_vdrop_max", "s2_vdrop"]].max().max()),
                     s1_plkw=rc["s1_plkw_mean"].sum(), s2_plkw=rc["s2_plkw"].sum()))
    print(rows[-1])
pd.DataFrame(rows).to_csv(f"{ROOT}/analysis/scenario_results.csv", index=False)
print("done")
