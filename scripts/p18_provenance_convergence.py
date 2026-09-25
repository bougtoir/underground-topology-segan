"""Create cost provenance and within-ensemble prefix-stability audits."""
import os

import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml", encoding="utf-8"))
RANGES = CFG["sensitivity"]["ranges"]


def span(key, suffix=""):
    low, high = RANGES[key]
    return f"{low:g}-{high:g}{suffix}"

cost_rows = [
    ("excavation", CFG["cost_model"]["excavation_jpy_per_m"], "JPY/m",
     "unpublished scenario assumption inherited from canonical package", "",
     "2026-09-24", "open-cut urban trench",
     span("construction_multiplier", "x"), "low",
     "dominant routing-cost uncertainty; not an observed municipal tariff"),
    ("duct bank", CFG["cost_model"]["duct_bank_jpy_per_m"], "JPY/m",
     "unpublished scenario assumption inherited from canonical package", "",
     "2026-09-24", "conduit and installation above excavation",
     span("construction_multiplier", "x"), "low",
     "varied jointly with excavation"),
    ("MV cable at 150 mm2", CFG["cost_model"]["cable_mv_jpy_per_m"], "JPY/m",
     "unpublished scenario assumption; size scaling is modeled", "",
     "2026-09-24", "materials and jointing",
     span("conductor_multiplier", "x"), "low",
     "catalogue supports electrical properties, not installed price"),
    ("LV cable at 150 mm2", CFG["cost_model"]["cable_lv_jpy_per_m"], "JPY/m",
     "unpublished scenario assumption; size scaling is modeled", "",
     "2026-09-24", "materials and jointing",
     span("conductor_multiplier", "x"), "low",
     "catalogue supports electrical properties, not installed price"),
    ("cable area-price exponent",
     CFG["cost_model"]["cable_area_cost_exponent"], "dimensionless",
     "unpublished relative-price scenario assumption", "", "2026-09-24",
     "price(area)=price(150)*(area/150)^exponent",
     span("conductor_area_cost_exponent"), "low",
     "varied directly because catalogues contain no installed prices"),
    ("100 kVA transformer reference", CFG["cost_model"]["pad_transformer_jpy"],
     "JPY/unit", "unpublished scenario assumption; rating scaling is modeled",
     "", "2026-09-24", "installed replacement unit",
     span("transformer_multiplier", "x"), "low",
     "Toshiba catalogue supports losses/loading, not installed price"),
    ("electricity/loss value", CFG["cost_model"]["electricity_jpy_per_kwh"],
     "JPY/kWh", "unpublished scenario assumption inherited from canonical package",
     "", "2026-09-24", "value of technical losses",
     span("electricity_jpy_per_kwh", " JPY/kWh"), "low",
     "not asserted as a utility procurement tariff"),
    ("annual O&M", CFG["cost_model"]["om_fraction_of_capex"], "fraction/year",
     "unpublished scenario assumption inherited from canonical package", "",
     "2026-09-24", "fraction of installed CAPEX",
     span("om_fraction"), "low",
     "applied consistently to alternatives"),
    ("discount rate", CFG["project"]["discount_rate"], "fraction/year",
     "study scenario assumption", "", "2026-09-24", "real social discount rate",
     span("discount_rate"), "medium",
     f"{'/'.join(map(str, RANGES['horizon_years']))}-year horizons are also evaluated"),
]
pd.DataFrame(cost_rows, columns=[
    "parameter", "base_value", "unit", "source_or_status", "source_url",
    "retrieval_date_utc", "basis", "uncertainty_range", "confidence",
    "interpretation"]).to_csv(
        f"{ROOT}/COST_PARAMETER_PROVENANCE.csv", index=False)

diagnostics = pd.read_csv(f"{ROOT}/analysis/feasibility_diagnostics.csv")
diagnostics = diagnostics[
    (diagnostics.scenario == "S1") & diagnostics.feasible].copy()
scenario = pd.read_csv(f"{ROOT}/analysis/scenario_results.csv").set_index("city")
rows = []
for city in ["sano", "kudamatsu", "yasu"]:
    subset = diagnostics[diagnostics.city == city]
    cluster_values = {}
    for cluster, frame in subset.groupby("cluster"):
        a = frame[frame.family == "A_steiner"].reset_index(drop=True)
        b = frame[frame.family == "B_incremental"].reset_index(drop=True)
        singleton = frame[frame.family == "singleton"]
        cluster_values[int(cluster)] = (a, b, singleton)
    previous_ltp = None
    for per_family in [2, 4, 6, 8, 10, 12]:
        s1_total = 0.0
        used = 0
        for a, b, singleton in cluster_values.values():
            if not singleton.empty:
                s1_total += float(singleton.npc_jpy.iloc[0])
                continue
            selected = pd.concat([
                a.iloc[:min(per_family, len(a))],
                b.iloc[:min(per_family, len(b))]], ignore_index=True)
            s1_total += float(selected.npc_jpy.mean())
            used += len(selected)
        s2 = float(scenario.loc[city, "s2_npc"])
        savings = 100.0 * (s1_total - s2) / s1_total
        rows.append(dict(
            city=city, replicates_per_family=per_family,
            requested_total_replicates=2 * per_family,
            aggregate_s1_npc_jpy=s1_total,
            combined_screening_savings_pct=savings,
            change_from_previous_percentage_points=(
                "" if previous_ltp is None else savings - previous_ltp),
            mean_non_singleton_records_used_per_cluster=(
                used / max(1, sum(1 for a, b, s in cluster_values.values()
                                  if s.empty)))))
        previous_ltp = savings
pd.DataFrame(rows).to_csv(
    f"{ROOT}/analysis/reconstruction_prefix_stability.csv", index=False)

final = pd.DataFrame(rows)
summary = []
for city, frame in final.groupby("city"):
    frame = frame.sort_values("replicates_per_family")
    last_change = abs(float(
        frame.iloc[-1].change_from_previous_percentage_points))
    summary.append(dict(
        city=city, final_replicates_per_family=12,
        final_total_replicates=24,
        final_combined_screening_savings_pct=float(
            frame.iloc[-1].combined_screening_savings_pct),
        last_increment_change_percentage_points=last_change,
        prefix_stability_threshold_percentage_points=0.10,
        within_ensemble_prefix_stability_pass=last_change <= 0.10,
        interpretation=(
            "within-ensemble prefix stability; not independent-seed "
            "algorithmic convergence")))
pd.DataFrame(summary).to_csv(
    f"{ROOT}/analysis/reconstruction_prefix_stability_summary.csv",
    index=False)
print(pd.DataFrame(summary).to_string(index=False))
