"""Phase 6-8 (corrected): feasibility-gated per-cluster scenarios + ablations.

Corrections vs v1 (see audit_v2/VOLTAGE_ROOT_CAUSE_AUDIT.md):
- coincident demand = coincidence_factor x raw building peak (flows/voltage)
- ampacity constraint in conductor sizing; S1 fixed at 150 mm2 and may be infeasible
- gates: vdrop<=6%, ampacity, transformer coincident kVA<=rated, radiality
- transformer capex (150 kVA unit) added to every scenario NPC (cancels in delta)
- ablation arms per cluster: T_fixed+C_fixed (S1), T_fixed+C_opt (S1*),
  T_opt+C_fixed (S2f), T_opt+C_opt (S2) -> benefit decomposition
Outputs: data/processed/<city>/cluster_results_"+TAG+".csv,
         analysis/scenario_results_"+TAG+".csv, analysis/ablation_results.csv
Label: modeled; S2 is best-found, optimality gap not certified."""
import os, math, glob
import numpy as np
import pandas as pd
import networkx as nx
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml"))
SPEC = yaml.safe_load(open(f"{ROOT}/config/ENGINEERING_FEASIBILITY_SPEC.yaml"))
RHO = SPEC["power_flow"]["rho_ohm_m"]
V_LL = SPEC["power_flow"]["v_ll_v"]
PF = SPEC["power_flow"]["power_factor"]
TAG = os.environ.get("TAG", "v2")
INTAG = os.environ.get("INTAG", TAG)
COINC = float(os.environ.get("COINC", SPEC["demand_model"]["coincidence_factor"]))
AMP = {int(k): v for k, v in SPEC["feasibility"]["ampacity_a"].items()}
VDROP_MAX = SPEC["feasibility"]["voltage_drop_max_pct"]
XFORM_KVA = SPEC["feasibility"]["transformer"]["rated_kva"]
XFORM_COST = SPEC["feasibility"]["transformer"]["unit_cost_jpy"]
H = CFG["project"]["primary_horizon_years"]
R = CFG["project"]["discount_rate"]
EKWH = CFG["cost_model"]["electricity_jpy_per_kwh"]
COST_M = (CFG["cost_model"]["excavation_jpy_per_m"] +
          CFG["cost_model"]["duct_bank_jpy_per_m"] +
          CFG["cost_model"]["cable_lv_jpy_per_m"])
OMF = CFG["cost_model"]["om_fraction_of_capex"]
LOAD_FACTOR = 0.35
ADF = sum(1.0/(1.0+R)**y for y in range(1, H+1))
EXC_DUCT = (CFG["cost_model"]["excavation_jpy_per_m"] +
            CFG["cost_model"]["duct_bank_jpy_per_m"])
CAB_REF = CFG["cost_model"]["cable_lv_jpy_per_m"]
A_REF = 150
SIZES = SPEC["feasibility"]["conductor_sizes_mm2"]
TRM_NPC = XFORM_COST * (1 + OMF * ADF)   # per cluster, all scenarios

def load_city(name):
    n = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv")
    e = pd.read_csv(f"{ROOT}/data/processed/{name}/edges.csv")
    G = nx.Graph()
    for _, r in e.iterrows():
        G.add_edge(str(r["u"]), str(r["v"]), length=float(r["length"]))
    pos = {str(r["node"]): (r["x_m"], r["y_m"]) for _, r in n.iterrows()}
    dem = {str(r["node"]): float(r["p_kw"]) for _, r in n.iterrows()}
    return G, pos, dem

def tree_flows(G, dem_c, src):
    order = list(nx.bfs_tree(G, src).edges())
    sub = {n: dem_c.get(n, 0.0) for n in G.nodes}
    for u, v in reversed(order):
        sub[u] = sub.get(u, 0) + sub.get(v, 0)
    return order, sub

def edge_metrics(G, dem_c, src, area_map=None):
    order, sub = tree_flows(G, dem_c, src)
    out = []
    for u, v in order:
        Pw = sub[v]; L = G[u][v]["length"]
        I = Pw * 1000.0 / (math.sqrt(3) * V_LL * PF)
        a = (area_map or {}).get(tuple(sorted((u, v))), A_REF)
        Re = RHO * L / (a * 1e-6)
        out.append((u, v, Pw, I, Re, L))
    return order, out

def feasible_sizes(I):
    return [a for a in SIZES if I <= AMP[a]]

def choose_conductor(flows):
    """Per-edge conductor minimizing capex+discounted loss share,
    restricted to sizes satisfying ampacity."""
    amap = {}
    for u, v, Pw, I, Re150, L in flows:
        cand = feasible_sizes(I)
        if not cand:
            return None
        best_a, best_c = cand[0], math.inf
        for a in cand:
            cab = CAB_REF * a / A_REF
            capex = L * (EXC_DUCT + cab)
            loss_kwh = 3.0 * I * I * (RHO * L / (a * 1e-6)) / 1000.0 * 8760 * LOAD_FACTOR
            tot = capex + (loss_kwh * EKWH + capex * OMF) * ADF
            if tot < best_c:
                best_c, best_a = tot, a
        amap[tuple(sorted((u, v)))] = best_a
    return amap

def evaluate(G, dem_c, src, optimize_conductor):
    """Returns metrics dict or None if ampacity-infeasible."""
    order, flows = edge_metrics(G, dem_c, src)
    if optimize_conductor:
        amap = choose_conductor(flows)
        if amap is None:
            return None
    else:
        # fixed 150 mm2: infeasible if any edge exceeds ampacity
        if any(I > AMP[A_REF] for _, _, _, I, _, _ in flows):
            return None
        amap = None
    pl = 0.0; drop = {src: 0.0}; md = 0.0; capex = 0.0; length_m = 0.0; up_m = 0.0
    maxI = 0.0
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
        maxI = max(maxI, I)
    eloss = pl * 8760 * LOAD_FACTOR
    coinc_kva = sum(dem_c.values()) / PF if dem_c else 0.0
    vd = md / V_LL * 100.0
    feasible = vd <= VDROP_MAX and coinc_kva <= XFORM_KVA
    return dict(capex=capex, length_m=length_m, pl_kw=pl,
                eloss_kwh_y=eloss, vdrop_pct=vd, upsize_m=up_m,
                max_I=maxI, coinc_kva=coinc_kva, feasible=feasible)

def npc_value(G, dem_c, src, optimize_conductor):
    m = evaluate(G, dem_c, src, optimize_conductor)
    if m is None:
        return None
    capex_total = m["capex"] + XFORM_COST
    m["npc"] = capex_total + (m["eloss_kwh_y"]*EKWH + capex_total*OMF) * ADF
    return m

def weighted_steiner(G, terms, w_loss, src):
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
    G, pos, dem_raw = load_city(name)
    dem_c = {k: v * COINC for k, v in dem_raw.items()}
    cl = pd.read_csv(f"{ROOT}/data/processed/{name}/clusters_"+INTAG+".csv")
    cl["node"] = cl["node"].astype(str)
    recon_sum = pd.read_csv(f"{ROOT}/analysis/reconstruction_summary_"+INTAG+".csv")
    recon_sum["cluster"] = recon_sum["cluster"].astype(str)
    src_map = (recon_sum[recon_sum["city"] == name].drop_duplicates("cluster")
               .set_index("cluster")["src"].astype(str).to_dict())
    outdir = f"{ROOT}/data/processed/{name}"
    res_c = []
    for c, grp in cl.groupby("cluster"):
        terms_all = list(grp["node"])
        if len(terms_all) < 2:
            # degenerate single-customer zone: drop-only feeder, no
            # topology choice -> S1=S2=transformer cost, delta=0
            if len(terms_all) == 1:
                res_c.append(dict(city=name, cluster=c, terminals=1,
                    raw_kw=dem_raw[terms_all[0]], coinc_kw=dem_c[terms_all[0]],
                    n_s1=1, n_s1_feas=1,
                    s1_npc_mean=TRM_NPC, s1_npc_feas_mean=TRM_NPC,
                    s1_capex_mean=0.0, s1_length_mean=0.0, s1_plkw_mean=0.0,
                    s1_vdrop_max=0.0, s1cond_npc_mean=TRM_NPC,
                    s1cond_vdrop_max=0.0, n_s1cond_feas=1, s1cond_plkw_mean=0.0,
                    s2f_npc=TRM_NPC, s2f_plkw=0.0, s2_npc=TRM_NPC, s2_w=0,
                    s2_capex=0.0, s2_plkw=0.0, s2_length=0.0, s2_vdrop=0.0,
                    s2_upsize_m=0.0, s2_feasible=True, vof_mean=0.0, tld=0.0))
            continue
        xs = [pos[t][0] for t in terms_all]; ys = [pos[t][1] for t in terms_all]
        w = np.array([dem_raw[t] for t in terms_all])
        cx, cy = np.average(xs, weights=w), np.average(ys, weights=w)
        src = src_map.get(str(c))
        if src is None or src not in pos:
            xmin0, xmax0 = min(xs)-150, max(xs)+150; ymin0, ymax0 = min(ys)-150, max(ys)+150
            sub0 = [x for x in G.nodes if xmin0 <= pos[x][0] <= xmax0 and ymin0 <= pos[x][1] <= ymax0]
            src = min(sub0 or list(G.nodes), key=lambda x: (pos[x][0]-cx)**2 + (pos[x][1]-cy)**2)
        terms = [src] + [t for t in terms_all if t != src]
        # cluster coincident load for transformer gate
        dem_c_cluster = {t: dem_c.get(t, 0.0) for t in terms}
        # S1 replicates (T_fixed+C_fixed) plus ablations on each tree
        s1, s1cond, s1_tree = [], [], []
        s1_fam = {}
        for f in sorted(glob.glob(f"{outdir}/recon_"+INTAG+f"/c{int(c):03d}_r*_*csv")):
            fam = f.rsplit("_",2)[-2] if "_r" in f else "?"
            ed = pd.read_csv(f)
            T = nx.Graph()
            ok = True
            for _, r in ed.iterrows():
                a, b = str(r["u"]), str(r["v"])
                if a not in G or b not in G or not G.has_edge(a, b):
                    ok = False; break
                T.add_edge(a, b, length=G[a][b]["length"])
            if not (ok and src in T and nx.is_connected(T)):
                continue
            m0 = npc_value(T, dem_c_cluster, src, False)
            m1 = npc_value(T, dem_c_cluster, src, True)
            s1.append(m0); s1cond.append(m1); s1_tree.append(T)
            if m0 is not None: s1_fam.setdefault(fam, []).append(m0["npc"])
        # S2 candidates: multi-weight Steiner (T_opt) with C_fixed and C_opt
        xmin, xmax = min(xs)-200, max(xs)+200; ymin, ymax = min(ys)-200, max(ys)+200
        sub_nodes = [x for x in G.nodes if xmin <= pos[x][0] <= xmax and ymin <= pos[y_ := x][1] <= ymax]
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
        # topology-optimized + conductor-fixed: best NPC among candidates w/ 150mm2
        tfc = {k: npc_value(v, dem_c_cluster, src, False) for k, v in cand.items()}
        tfc_ok = {k: m for k, m in tfc.items() if m is not None}
        toc = {k: npc_value(v, dem_c_cluster, src, True) for k, v in cand.items()}
        toc_ok = {k: m for k, m in toc.items() if m is not None}
        s15 = cand.get(0, list(cand.values())[0])
        s1_ok = [m for m in s1 if m is not None]
        s1c_ok = [m for m in s1cond if m is not None]
        best_toc = min(toc_ok, key=lambda k: toc_ok[k]["npc"]) if toc_ok else None
        best_tfc = min(tfc_ok, key=lambda k: tfc_ok[k]["npc"]) if tfc_ok else None
        # R6 value-of-flexibility: retain-S1 is admissible ->
        # per-rep max(0, npc_rep - npc_bestS2), >=0 by construction
        s2n = toc_ok[best_toc]["npc"] if best_toc is not None else np.nan
        vof_vals = ([max(0.0, m["npc"] - s2n) for m in s1_ok]
                    if (s1_ok and best_toc is not None) else [])
        # TLD vs best candidate
        ec = {tuple(sorted(e2)) for e2 in s15.edges()}
        el = {tuple(sorted(e2)) for e2 in cand[max(cand)].edges()}
        tld = 1 - len(ec & el) / max(1, len(ec | el))
        res_c.append(dict(
            city=name, cluster=c, terminals=len(terms),
            raw_kw=sum(dem_raw[t] for t in terms_all),
            coinc_kw=sum(dem_c_cluster.values()),
            n_s1=len(s1), n_s1_feas=len(s1_ok),
            s1_npc_mean=np.mean([m["npc"] for m in s1 if m is not None]) if s1 else np.nan,
            s1_npc_feas_mean=np.mean([m["npc"] for m in s1_ok]) if s1_ok else np.nan,
            s1_capex_mean=np.mean([m["capex"] for m in s1 if m is not None]) if s1 else np.nan,
            s1_length_mean=np.mean([m["length_m"] for m in s1 if m is not None]) if s1 else np.nan,
            s1_plkw_mean=np.mean([m["pl_kw"] for m in s1 if m is not None]) if s1 else np.nan,
            s1_vdrop_max=max((m["vdrop_pct"] for m in s1 if m is not None), default=np.nan) if s1 else np.nan,
            s1cond_npc_mean=np.mean([m["npc"] for m in s1c_ok]) if s1c_ok else np.nan,
            s1cond_vdrop_max=max((m["vdrop_pct"] for m in s1c_ok), default=np.nan),
            n_s1cond_feas=len(s1c_ok),
            s1cond_plkw_mean=np.mean([m["pl_kw"] for m in s1c_ok]) if s1c_ok else np.nan,
            s2f_npc=tfc_ok[best_tfc]["npc"] if best_tfc is not None else np.nan,
            s2f_plkw=tfc_ok[best_tfc]["pl_kw"] if best_tfc is not None else np.nan,
            s2_npc=toc_ok[best_toc]["npc"] if best_toc is not None else np.nan,
            s2_w=best_toc,
            s2_capex=toc_ok[best_toc]["capex"] if best_toc is not None else np.nan,
            s2_plkw=toc_ok[best_toc]["pl_kw"] if best_toc is not None else np.nan,
            s2_length=toc_ok[best_toc]["length_m"] if best_toc is not None else np.nan,
            s2_vdrop=toc_ok[best_toc]["vdrop_pct"] if best_toc is not None else np.nan,
            s2_upsize_m=toc_ok[best_toc]["upsize_m"] if best_toc is not None else np.nan,
            s2_feasible=toc_ok[best_toc]["feasible"] if best_toc is not None else False,
            vof_mean=np.mean(vof_vals) if vof_vals else np.nan,
            s1_famA_npc=np.mean(s1_fam.get("A",[])) if s1_fam.get("A") else np.nan,
            s1_famB_npc=np.mean(s1_fam.get("B",[])) if s1_fam.get("B") else np.nan,
            tld=tld))
        if not os.path.exists(f"{outdir}/s2_cluster0_"+TAG+".edgelist") and best_toc is not None:
            nx.write_edgelist(cand[best_toc],
                              f"{outdir}/s2_cluster0_"+TAG+".edgelist", data=["length"])
    rc = pd.DataFrame(res_c)
    rc.to_csv(f"{outdir}/cluster_results_"+TAG+".csv", index=False)
    feas = rc[rc["s2_feasible"] & (rc["n_s1_feas"] > 0)]
    rows.append(dict(city=name,
        clusters=len(rc),
        clusters_feasible=len(feas),
        lv_demand_kw=float(rc["raw_kw"].sum()),
        s1_npc=feas["s1_npc_feas_mean"].sum(),
        s2_npc=feas["s2_npc"].sum(),
        delta_npc=float((feas["s1_npc_feas_mean"] - feas["s2_npc"]).sum()),
        ltp_pct=float(100*(feas["s1_npc_feas_mean"]-feas["s2_npc"]).sum()/feas["s1_npc_feas_mean"].sum()),
        p_ltp_pos=float(((feas["s1_npc_feas_mean"]-feas["s2_npc"])>0).mean()),
        mean_tld=float(rc["tld"].mean()),
        upsize_km=float(feas["s2_upsize_m"].sum()/1000),
        max_vdrop=float(feas[["s1_vdrop_max","s2_vdrop"]].max().max()),
        s1_plkw=float(feas["s1_plkw_mean"].sum()), s2_plkw=float(feas["s2_plkw"].sum()),
        vof=float(feas["vof_mean"].sum()),
        vof_pct=float(100*feas["vof_mean"].sum()/feas["s1_npc_feas_mean"].sum()),
        p_vof_pos=float((feas["vof_mean"]>0).mean())))
    print(rows[-1])
pd.DataFrame(rows).to_csv(f"{ROOT}/analysis/scenario_results_"+TAG+".csv", index=False)
print("done")
