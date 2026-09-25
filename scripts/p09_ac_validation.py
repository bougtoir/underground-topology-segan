"""Phase R1: LinDistFlow vs full AC power flow (pandapower) per feeder.
For each feasible cluster: take the first S1 replicate tree and the best
S2 candidate; build pandapower net (slack at source, coincident loads,
per-edge R/X), runpp, compare min vm_pu, losses, feasibility agreement.
Outputs AC_VS_LINEAR_VALIDATION.csv + AC_VALIDATION_REPORT.md."""
import os, math, glob
import numpy as np
import pandas as pd
import networkx as nx
import pandapower as pp
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml"))
SPEC = yaml.safe_load(open(f"{ROOT}/config/ENGINEERING_FEASIBILITY_SPEC.yaml"))
AC = yaml.safe_load(open(f"{ROOT}/config/AC_VALIDATION_SPEC.yaml"))
TOL = AC["ac_validation"]["tolerances"]
RHO = SPEC["power_flow"]["rho_ohm_m"]
V_LL = SPEC["power_flow"]["v_ll_v"]
PF = SPEC["power_flow"]["power_factor"]
COINC = SPEC["demand_model"]["coincidence_factor"]
X_KM = 0.08
R_KM_150 = RHO * 1000.0 / (150e-6)

def load_city(name):
    n = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv")
    e = pd.read_csv(f"{ROOT}/data/processed/{name}/edges.csv")
    G = nx.Graph()
    for _, r in e.iterrows():
        G.add_edge(str(r["u"]), str(r["v"]), length=float(r["length"]))
    dem = {str(r["node"]): float(r["p_kw"]) for _, r in n.iterrows()}
    return G, dem

def ac_feeder(T, dem_c, src):
    """pandapower net; returns (min_vm_pu, pl_kw_ac, converged)."""
    net = pp.create_empty_network(sn_mva=1.0)
    bus = {nd: pp.create_bus(net, vn_kv=V_LL/1000.0, name=str(nd)) for nd in T.nodes}
    pp.create_ext_grid(net, bus=bus[src], vm_pu=1.0)
    for nd in T.nodes:
        p = dem_c.get(nd, 0.0)
        if p > 0:
            pp.create_load(net, bus=bus[nd], p_mw=p/1000.0,
                           q_mvar=p/1000.0*math.tan(math.acos(PF)))
    for a, b in T.edges():
        Lkm = T[a][b]["length"]/1000.0
        pp.create_line_from_parameters(net, bus[a], bus[b], length_km=Lkm,
                       r_ohm_per_km=R_KM_150, x_ohm_per_km=X_KM,
                       c_nf_per_km=0.0, max_i_ka=0.35)
    try:
        pp.runpp(net, verbose=False, numba=False)
    except Exception:
        return None, None, False
    if not net.converged:
        return None, None, False
    return float(net.res_bus.vm_pu.min()), float(net.res_line.pl_mw.sum()*1000.0), True

def lin_vdrop_pct(T, dem_c, src):
    order = list(nx.bfs_tree(T, src).edges())
    sub = {n: dem_c.get(n, 0.0) for n in T.nodes}
    for u, v in reversed(order):
        sub[u] = sub.get(u, 0) + sub.get(v, 0)
    md = 0.0; pl = 0.0
    for u, v in order:
        Pw = sub[v]; L = T[u][v]["length"]
        I = Pw*1000.0/(math.sqrt(3)*V_LL*PF)
        Re = RHO*L/(150e-6)
        pl += 3.0*I*I*Re/1000.0
        md = max(md, 0)   # cumulative below
    drop = {src: 0.0}; md = 0.0
    for u, v in order:
        Pw = sub[v]; L = T[u][v]["length"]
        I = Pw*1000.0/(math.sqrt(3)*V_LL*PF)
        Re = RHO*L/(150e-6)
        drop[v] = drop[u] + math.sqrt(3)*I*Re
        md = max(md, drop[v])
    return md/V_LL*100.0, pl

rows = []
for name in ["sano", "kudamatsu", "yasu"]:
    G, dem = load_city(name)
    dem_c = {k: v*COINC for k, v in dem.items()}
    rc = pd.read_csv(f"{ROOT}/data/processed/{name}/cluster_results_v2.csv")
    cl = pd.read_csv(f"{ROOT}/data/processed/{name}/clusters_v2.csv"); cl["node"]=cl["node"].astype(str)
    rs = pd.read_csv(f"{ROOT}/analysis/reconstruction_summary_v2.csv")
    rs["cluster"] = rs["cluster"].astype(str)
    src_map = (rs[rs.city==name].drop_duplicates("cluster")
               .set_index("cluster")["src"].astype(str).to_dict())
    feas = rc[rc["s2_feasible"] & (rc["n_s1_feas"] > 0)]
    for _, rr in feas.iterrows():
        c = int(rr["cluster"])
        f = sorted(glob.glob(f"{ROOT}/data/processed/{name}/recon_v2/c{c:03d}_r00_*.csv"))
        if not f:
            continue
        ed = pd.read_csv(f[0])
        T = nx.Graph()
        for _, r in ed.iterrows():
            T.add_edge(str(r["u"]), str(r["v"]), length=G[str(r["u"])][str(r["v"])]["length"])
        src = src_map.get(str(c))
        if src is None or src not in T:
            continue
        dem_cc = {t: dem_c.get(t, 0.0) for t in T.nodes}
        lin_v, lin_pl = lin_vdrop_pct(T, dem_cc, src)
        vmin, pl_ac, conv = ac_feeder(T, dem_cc, src)
        if not conv:
            rows.append(dict(city=name, cluster=c, scenario="S1", converged=False))
            continue
        vm_lin_pu = 1.0 - lin_v/100.0
        rows.append(dict(city=name, cluster=c, scenario="S1", converged=True,
                         min_vm_ac=vmin, min_vm_lin=vm_lin_pu,
                         vm_abs_err=abs(vmin-vm_lin_pu),
                         pl_kw_ac=pl_ac, pl_kw_lin=lin_pl,
                         loss_rel_err=abs(pl_ac-lin_pl)/max(lin_pl,1e-9),
                         lin_vdrop_pct=lin_v,
                         ac_vdrop_pct=(1.0-vmin)*100.0,
                         feas_lin=lin_v<=6.0, feas_ac=(1.0-vmin)*100.0<=6.0))
        # S2 best candidate: rebuild via weighted steiner w=0 (min-length)
        # (same construction as p07b; w_loss chosen = s2_w stored)
        terms_all = list(cl[cl.cluster==c]["node"])
        terms = [src]+[t for t in terms_all if t!=src]
        n2 = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv")
        pos = {str(r["node"]): (r["x_m"], r["y_m"]) for _, r in n2.iterrows()}
        xs=[pos[t][0] for t in terms_all]; ys=[pos[t][1] for t in terms_all]
        xmin,xmax=min(xs)-200,max(xs)+200; ymin,ymax=min(ys)-200,max(ys)+200
        sub=[x for x in G.nodes if xmin<=pos[x][0]<=xmax and ymin<=pos[x][1]<=ymax]
        Hg=G.subgraph(sub)
        if not all(t in Hg for t in terms):
            continue
        d_src = nx.single_source_dijkstra_path_length(Hg, src, weight="length")
        wl = rr["s2_w"]
        Gw = nx.Graph()
        for u, v, d in Hg.edges(data=True):
            ds = min(d_src.get(u,1e9), d_src.get(v,1e9))
            Gw.add_edge(u, v, length=d["length"]*(150000+wl*2e5/(50.0+ds)))
        sp = dict(nx.all_pairs_dijkstra_path_length(Gw, weight="length"))
        spp = dict(nx.all_pairs_dijkstra_path(Gw, weight="length"))
        Tg = nx.Graph(); tl=list(terms)
        for i,s in enumerate(tl):
            for t in tl[i+1:]:
                if s in sp and t in sp[s]:
                    Tg.add_edge(s,t,weight=sp[s][t])
        if not Tg.edges:
            continue
        mst=nx.minimum_spanning_tree(Tg, weight="weight")
        T2=nx.Graph()
        for s,t in mst.edges():
            for a,b in zip(spp[s][t][:-1], spp[s][t][1:]):
                T2.add_edge(a,b,length=Hg[a][b]["length"])
        # prune
        keep=set(terms)
        while True:
            lv=[nn for nn in T2.nodes if T2.degree(nn)<=1 and nn not in keep]
            if not lv: break
            T2.remove_nodes_from(lv)
        dem_cc2={t:dem_c.get(t,0.0) for t in terms}
        lin_v2, lin_pl2 = lin_vdrop_pct(T2, dem_cc2, src)
        vmin2, pl_ac2, conv2 = ac_feeder(T2, dem_cc2, src)
        if not conv2:
            rows.append(dict(city=name, cluster=c, scenario="S2", converged=False))
            continue
        vm_lin2 = 1.0 - lin_v2/100.0
        rows.append(dict(city=name, cluster=c, scenario="S2", converged=True,
                         min_vm_ac=vmin2, min_vm_lin=vm_lin2,
                         vm_abs_err=abs(vmin2-vm_lin2),
                         pl_kw_ac=pl_ac2, pl_kw_lin=lin_pl2,
                         loss_rel_err=abs(pl_ac2-lin_pl2)/max(lin_pl2,1e-9),
                         lin_vdrop_pct=lin_v2, ac_vdrop_pct=(1.0-vmin2)*100.0,
                         feas_lin=lin_v2<=6.0, feas_ac=(1.0-vmin2)*100.0<=6.0))
    print(name, "done")

df = pd.DataFrame(rows)
df.to_csv(f"{ROOT}/analysis/AC_VS_LINEAR_VALIDATION.csv", index=False)
ok = df[df.converged==True]
rep = []
rep.append("# AC validation report (Phase R1)\n")
rep.append(f"Feeders evaluated: {len(ok)} ({(df.converged==False).sum()} non-converged)\n")
rep.append(f"|vm_ac - vm_lin| median {ok.vm_abs_err.median():.4f} pu, "
           f"max {ok.vm_abs_err.max():.4f} pu (tolerance {TOL['min_vm_pu_abs_err']})\n")
rep.append(f"loss rel err median {ok.loss_rel_err.median():.3f}, "
           f"max {ok.loss_rel_err.max():.3f} (tolerance {TOL['loss_rel_err']})\n")
agree = (ok.feas_lin==ok.feas_ac).mean()
rep.append(f"feasibility agreement {agree:.3f} (tolerance {TOL['feasibility_agreement']})\n")
rep.append(f"AC vdrop max {ok.ac_vdrop_pct.max():.2f}% vs linear {ok.lin_vdrop_pct.max():.2f}%\n")
open(f"{ROOT}/analysis/AC_VALIDATION_REPORT.md","w").write("\n".join(rep))
print("\n".join(rep))
