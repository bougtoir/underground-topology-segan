"""Phase 11: freeze all manuscript citable values into
analysis/manuscript_values.csv. Every number the manuscript reports must
come from this file (no hardcoding)."""
import pandas as pd
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scen = pd.read_csv(f"{ROOT}/analysis/scenario_results.csv")
mc = pd.read_csv(f"{ROOT}/analysis/sensitivity_mc.csv")
dg = pd.read_csv(f"{ROOT}/analysis/dg_results.csv")
rec = pd.read_csv(f"{ROOT}/analysis/reconstruction_summary.csv")
da = pd.read_csv(f"{ROOT}/analysis/data_audit.csv")
bench = pd.read_csv(f"{ROOT}/analysis/benchmark_validation.csv")

rows = []
def add(key, value, unit, source, label):
    rows.append(dict(key=key, value=value, unit=unit, source=source, label=label))

for _, r in scen.iterrows():
    c = r["city"]
    add(f"{c}_clusters", r["clusters"], "count", "scenario_results.csv", "modeled")
    add(f"{c}_demand_mw", r["total_demand_kw"]/1000, "MW", "scenario_results.csv", "modeled")
    add(f"{c}_s1_npc_bn", r["s1_npc"]/1e9, "bn JPY", "scenario_results.csv", "modeled")
    add(f"{c}_s2_npc_bn", r["s2_npc"]/1e9, "bn JPY", "scenario_results.csv", "modeled")
    add(f"{c}_delta_npc_bn", r["delta_npc"]/1e9, "bn JPY", "scenario_results.csv", "modeled")
    add(f"{c}_ltp_pct", r["ltp_pct"], "%", "scenario_results.csv", "modeled")
    add(f"{c}_ltpB_pct", r["ltpB_pct"], "%", "scenario_results.csv", "modeled")
    add(f"{c}_p_ltp_pos", r["p_ltp_pos"], "prob", "scenario_results.csv", "modeled")
    add(f"{c}_mean_tld", r["mean_tld"], "frac", "scenario_results.csv", "modeled")
    add(f"{c}_upsize_km", r["upsize_km"], "km", "scenario_results.csv", "modeled")
    add(f"{c}_max_vdrop", r["max_vdrop"], "%", "scenario_results.csv", "modeled")
    add(f"{c}_s1_plkw", r["s1_plkw"], "kW", "scenario_results.csv", "modeled")
    add(f"{c}_s2_plkw", r["s2_plkw"], "kW", "scenario_results.csv", "modeled")
    add(f"{c}_loss_red_pct", 100*(1-r["s2_plkw"]/r["s1_plkw"]), "%",
        "scenario_results.csv", "modeled")
for _, r in mc.iterrows():
    c = r["city"]
    add(f"{c}_mc_delta_mean_bn", r["delta_mean"]/1e9, "bn JPY", "sensitivity_mc.csv", "sensitivity")
    add(f"{c}_mc_delta_p5_bn", r["delta_p5"]/1e9, "bn JPY", "sensitivity_mc.csv", "sensitivity")
    add(f"{c}_mc_delta_p95_bn", r["delta_p95"]/1e9, "bn JPY", "sensitivity_mc.csv", "sensitivity")
    add(f"{c}_mc_ltp_pct", r["ltp_pct_mean"], "%", "sensitivity_mc.csv", "sensitivity")
    add(f"{c}_mc_p_ltp_pos", r["p_ltp_pos"], "prob", "sensitivity_mc.csv", "sensitivity")
for _, r in dg.iterrows():
    c = r["city"]
    add(f"{c}_pv_mwp", r["pv_kwp_total"]/1000, "MWp", "dg_results.csv", "modeled")
    add(f"{c}_gen_gwh_y", r["gen_gwh_y"], "GWh/yr", "dg_results.csv", "modeled")
    add(f"{c}_s3_npc_bn", r["npc_s3"]/1e9, "bn JPY", "dg_results.csv", "modeled")
    add(f"{c}_dg_delta_bn", r["dg_delta_npc"]/1e9, "bn JPY", "dg_results.csv", "modeled")
    add(f"{c}_p_s3_better", r["p_s3_better"], "prob", "dg_results.csv", "modeled")
for _, r in bench.iterrows():
    add(f"bench_{r['benchmark']}_converged", bool(r["converged"]), "", "benchmark_validation.csv", "benchmark")
for _, r in da.iterrows():
    add(f"audit_{str(r['municipality']).lower()}_rows", r["rows"], "rows", "data_audit.csv", "observed")
    add(f"audit_{str(r['municipality']).lower()}_tier", r["tier"], "", "data_audit.csv", "observed")
    add(f"audit_{str(r['municipality']).lower()}_pole_dupes", r["pole_dupes"], "count", "data_audit.csv", "observed")

pd.DataFrame(rows).to_csv(f"{ROOT}/analysis/manuscript_values.csv", index=False)
print(len(rows), "values frozen")
