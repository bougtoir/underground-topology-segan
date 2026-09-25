"""Phase 14 (v2): Monte-Carlo driver sensitivity on stored S1/S2 components.
NPC decomposition per cluster is exact: NPC = capex*m + (eloss*ekwh +
capex*m*omf)*ADF(R,H). Topology is held fixed at the base-case optimum
(labelled approximation; topology re-optimisation under each draw is out
of scope). Outputs analysis/sensitivity_mc_v2.csv + analysis/sensitivity_tornado_v2.csv."""
import numpy as np
import pandas as pd
import yaml, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml"))
SEED = CFG["project"]["seed"]
BASE = dict(r=CFG["project"]["discount_rate"],
            h=CFG["project"]["primary_horizon_years"],
            ekwh=CFG["cost_model"]["electricity_jpy_per_kwh"],
            omf=CFG["cost_model"]["om_fraction_of_capex"],
            cm=1.0, lf=0.35)

def adf(r, h):
    return sum(1.0/(1.0+r)**y for y in range(1, int(h)+1))

def npc(capex, plkw, r, h, ekwh, omf, cm, lf):
    capex = capex * cm
    eloss = plkw * 8760 * lf
    return capex + (eloss*ekwh + capex*omf)*adf(r, h)

rng = np.random.default_rng(SEED)
N = 500
draws = pd.DataFrame(dict(
    R=rng.uniform(0.02, 0.045, N),
    H=rng.choice([30, 40, 50], N),
    EKWH=rng.uniform(15, 35, N),
    OMF=rng.uniform(0.005, 0.02, N),
    CM=rng.uniform(0.7, 1.3, N),
    LF=rng.uniform(0.25, 0.45, N)))

mc_rows, tor_rows = [], []
for name in ["sano", "kudamatsu", "yasu"]:
    rc = pd.read_csv(f"{ROOT}/data/processed/{name}/cluster_results_v2.csv")
    rc = rc[rc["s2_feasible"] & (rc["n_s1_feas"] > 0)]
    XFORM = 3.5e6
    c1, p1 = rc["s1_capex_mean"].values + XFORM, rc["s1_plkw_mean"].values
    c2, p2 = rc["s2_capex"].values + XFORM, rc["s2_plkw"].values
    dmat = np.empty((N, len(rc)))
    for k, r in draws.iterrows():
        kw = {kk.lower(): vv for kk, vv in r.to_dict().items()}
        dmat[k] = (npc(c1, p1, **kw) - npc(c2, p2, **kw))

    delta = dmat.sum(axis=1)
    s1b = np.array([npc(c1.sum(), p1.sum(), **BASE) for _ in [0]])[0]
    base_delta = npc(c1.sum(), p1.sum(), **BASE) - npc(c2.sum(), p2.sum(), **BASE)
    mc_rows.append(dict(
        city=name, n_draws=N, delta_mean=float(delta.mean()),
        delta_p5=float(np.percentile(delta, 5)),
        delta_p95=float(np.percentile(delta, 95)),
        ltp_pct_mean=float(100*delta.mean()/s1b),
        p_ltp_pos=float((delta > 0).mean()),
        base_delta=float(base_delta)))
    # one-at-a-time tornado (10th/90th percentile swings)
    ranges = dict(r=(0.02, 0.045), ekwh=(15, 35), cm=(0.7, 1.3),
                  omf=(0.005, 0.02), lf=(0.25, 0.45), h=(30, 50))
    for par, (lo, hi) in ranges.items():
        for tag, v in [("lo", lo), ("hi", hi)]:
            kw = dict(BASE); kw[par] = v
            d = npc(c1.sum(), p1.sum(), **kw) - npc(c2.sum(), p2.sum(), **kw)
            tor_rows.append(dict(city=name, param=par, level=tag, value=v,
                                 delta_npc=float(d),
                                 ltp_pct=float(100*d/npc(c1.sum(), p1.sum(), **kw))))

pd.DataFrame(mc_rows).to_csv(f"{ROOT}/analysis/sensitivity_mc_v2.csv", index=False)
pd.DataFrame(tor_rows).to_csv(f"{ROOT}/analysis/sensitivity_tornado_v2.csv", index=False)
for r in mc_rows:
    print(r)
print("done")
