"""Freeze every quantitative manuscript value from final machine outputs."""
import os

import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scen = pd.read_csv(f"{ROOT}/analysis/scenario_results.csv")
mc = pd.read_csv(f"{ROOT}/analysis/sensitivity_mc.csv")
audit = pd.read_csv(f"{ROOT}/MUNICIPAL_DATA_PROVENANCE_AUDIT.csv")
bench = pd.read_csv(f"{ROOT}/analysis/benchmark_radial_comparison.csv")
prefix = pd.read_csv(
    f"{ROOT}/analysis/reconstruction_prefix_stability_summary.csv")
decomp = pd.read_csv(f"{ROOT}/analysis/ablation_decomposition.csv")
components = pd.read_csv(f"{ROOT}/analysis/component_decomposition.csv")
candidates = pd.read_csv(f"{ROOT}/analysis/candidate_search_summary.csv")
original = pd.read_csv(f"{ROOT}/audit/original_results/scenario_results.csv")
spec = yaml.safe_load(open(
    f"{ROOT}/ENGINEERING_FEASIBILITY_SPEC.yaml", encoding="utf-8"))
cfg = yaml.safe_load(open(f"{ROOT}/config/study.yaml", encoding="utf-8"))

rows = []


def add(key, value, unit, source, label):
    rows.append(dict(
        key=key, value=value, unit=unit, source=source,
        epistemic_label=label))


scenario_fields = {
    "clusters": ("count", "modeled"),
    "total_demand_kw": ("kW", "modeled"),
    "transformer_sites": ("count", "modeled"),
    "transformer_units": ("count", "modeled"),
    "s1_npc": ("JPY", "modeled"),
    "s15_npc": ("JPY", "modeled"),
    "s2_npc": ("JPY", "modeled"),
    "delta_npc": ("JPY", "modeled"),
    "routing_policy_delta_npc": ("JPY", "modeled"),
    "routing_policy_savings_pct": ("%", "modeled"),
    "combined_screening_savings_pct": ("%", "modeled"),
    "s1_plkw": ("kW", "modeled"),
    "s2_plkw": ("kW", "modeled"),
    "max_mv_vdrop_pct": ("%", "modeled"),
    "min_customer_voltage_pu": ("pu", "modeled"),
    "mean_edge_set_divergence": ("fraction", "modeled"),
    "cluster_positive_fraction": ("fraction", "conditional diagnostic"),
}
for _, r in scen.iterrows():
    city = r.city
    for field, (unit, label) in scenario_fields.items():
        add(f"{city}_{field}", r[field], unit,
            "analysis/scenario_results.csv", label)
    add(
        f"{city}_peak_loss_change_pct",
        100.0 * (r.s2_plkw / r.s1_plkw - 1.0), "%",
        "analysis/scenario_results.csv", "modeled")
    add(
        f"{city}_frequency_hz",
        spec["system"]["municipality_frequency_hz"][city], "Hz",
        "ENGINEERING_FEASIBILITY_SPEC.yaml",
        "assumed engineering parameter")

mc_fields = [
    ("npc_savings_mean", "delta_mean", "JPY"),
    ("npc_savings_median", "delta_median", "JPY"),
    ("npc_savings_p2_5", "delta_p2_5", "JPY"),
    ("npc_savings_p97_5", "delta_p97_5", "JPY"),
    ("combined_savings_pct_mean",
     "combined_screening_savings_pct_mean", "%"),
    ("combined_savings_pct_p2_5",
     "combined_screening_savings_pct_p2_5", "%"),
    ("combined_savings_pct_p97_5",
     "combined_screening_savings_pct_p97_5", "%"),
    ("positive_draw_frequency", "scenario_positive_fraction",
     "conditional frequency"),
    ("n_draws", "n_draws", "draws"),
]
for _, r in mc.iterrows():
    for key_suffix, field, unit in mc_fields:
        add(
            f"{r.city}_sampling_{key_suffix}", r[field], unit,
            "analysis/sensitivity_mc.csv",
            "conditional scenario sampling; frozen designs")

for _, r in decomp.iterrows():
    for field in [
            "routing_policy_shapley_savings_jpy",
            "conductor_shapley_savings_jpy",
            "routing_conductor_interaction_jpy",
            "transformer_variation_savings_jpy"]:
        add(
            f"{r.city}_{field}", r[field], "JPY",
            "analysis/ablation_decomposition.csv",
            "paired policy-screening attribution")
for _, r in components.iterrows():
    key = r.component.lower().replace("/", "_").replace(" ", "_")
    add(
        f"{r.city}_component_{key}_jpy", r.npc_savings_jpy, "JPY",
        "analysis/component_decomposition.csv",
        "accounting decomposition; non-causal")

for _, r in audit.iterrows():
    city = r.municipality.lower()
    for field, unit in [
            ("rows", "records"),
            ("duplicate_extra_records", "records"),
            ("multi_record_identifier_groups", "groups"),
            ("maximum_records_per_identifier", "records")]:
        if pd.notna(r[field]):
            add(
                f"{city}_{field}", r[field], unit,
                "MUNICIPAL_DATA_PROVENANCE_AUDIT.csv", "observed")
    add(
        f"{city}_evidence_tier", r.evidence_tier, "",
        "MUNICIPAL_DATA_PROVENANCE_AUDIT.csv", "observed")

add("benchmark_max_voltage_error_pu", bench.voltage_abs_error_pu.max(), "pu",
    "analysis/benchmark_radial_comparison.csv", "benchmark")
add("benchmark_max_loss_relative_error", bench.loss_relative_error.max(),
    "fraction", "analysis/benchmark_radial_comparison.csv", "benchmark")
add("benchmark_feeders_validated", int(bench.validated.sum()), "count",
    "analysis/benchmark_radial_comparison.csv", "benchmark")
add("benchmark_voltage_tolerance_pu", bench.voltage_tolerance_pu.iloc[0], "pu",
    "analysis/benchmark_radial_comparison.csv", "predeclared benchmark gate")
add("benchmark_loss_relative_tolerance",
    bench.loss_relative_tolerance.iloc[0], "fraction",
    "analysis/benchmark_radial_comparison.csv", "predeclared benchmark gate")
add("candidate_clusters_total", len(candidates), "clusters",
    "analysis/candidate_search_summary.csv", "modeled search diagnostic")
add("candidate_clusters_one_unique_route",
    int((candidates.unique_route_count == 1).sum()), "clusters",
    "analysis/candidate_search_summary.csv", "modeled search diagnostic")
add("candidate_clusters_selected_weight_zero",
    int((candidates.selected_weight == 0).sum()), "clusters",
    "analysis/candidate_search_summary.csv", "modeled search diagnostic")
add("quarantined_original_min_voltage_drop_pct", original.max_vdrop.min(), "%",
    "audit/original_results/scenario_results.csv", "quarantined original")
add("quarantined_original_max_voltage_drop_pct", original.max_vdrop.max(), "%",
    "audit/original_results/scenario_results.csv", "quarantined original")

for _, r in prefix.iterrows():
    add(
        f"{r.city}_reconstruction_last_change_pp",
        r.last_increment_change_percentage_points, "percentage points",
        "analysis/reconstruction_prefix_stability_summary.csv",
        "within-ensemble diagnostic")
    add(
        f"{r.city}_reconstruction_prefix_stability_pass",
        r.within_ensemble_prefix_stability_pass, "boolean",
        "analysis/reconstruction_prefix_stability_summary.csv",
        "within-ensemble diagnostic")

assumptions = {
    "mv_nominal_kv": (spec["system"]["mv_nominal_kv"], "kV"),
    "lv_nominal_v": (spec["system"]["lv_nominal_v"], "V"),
    "service_nominal_v": (spec["system"]["lv_service_nominal_v"], "V"),
    "power_factor": (spec["system"]["power_factor"], "fraction"),
    "source_voltage_pu": (spec["system"]["source_voltage_pu"], "pu"),
    "mv_drop_max_pct": (spec["voltage_gates"]["mv_drop_max_pct"], "%"),
    "transformer_drop_max_pct": (
        spec["voltage_gates"]["transformer_drop_max_pct"], "%"),
    "lv_drop_max_pct": (spec["voltage_gates"]["lv_drop_max_pct"], "%"),
    "customer_min_pu": (
        spec["voltage_gates"]["customer_min_pu_on_105v"], "pu"),
    "customer_max_pu": (
        spec["voltage_gates"]["customer_max_pu_on_105v"], "pu"),
    "buried_ampacity_derating": (
        spec["thermal_gates"]["ampacity_derating_duct"], "fraction"),
    "design_loading_pct": (
        spec["thermal_gates"]["design_cable_loading_pct"], "%"),
    "maximum_loading_pct": (
        spec["thermal_gates"]["max_cable_loading_pct"], "%"),
    "lv_stub_length_m": (
        spec["topology_gates"]["modeled_lv_stub_length_m"], "m"),
    "max_lv_unit_kw": (
        spec["topology_gates"]["max_lv_unit_kw"], "kW"),
    "horizon_years": (cfg["project"]["primary_horizon_years"], "years"),
    "discount_rate": (cfg["project"]["discount_rate"], "fraction"),
    "load_factor": (cfg["project"]["load_factor"], "fraction"),
    "conductor_area_cost_exponent": (
        cfg["cost_model"]["cable_area_cost_exponent"], "exponent"),
    "scenario_sampling_draws": (cfg["sensitivity"]["n_mc"], "draws"),
    "reconstruction_replicates_per_family": (
        cfg["reconstruction"]["n_replicates"] // 2, "replicates"),
}
for key, (value, unit) in assumptions.items():
    add(
        key, value, unit,
        "ENGINEERING_FEASIBILITY_SPEC.yaml"
        if key in {
            "mv_nominal_kv", "lv_nominal_v", "service_nominal_v",
            "power_factor", "source_voltage_pu", "mv_drop_max_pct",
            "transformer_drop_max_pct", "lv_drop_max_pct",
            "customer_min_pu", "customer_max_pu",
            "buried_ampacity_derating", "design_loading_pct",
            "maximum_loading_pct",
            "lv_stub_length_m", "max_lv_unit_kw"}
        else "config/study.yaml",
        "assumed parameter")

for key, value in cfg["sensitivity"]["ranges"].items():
    if isinstance(value, list):
        add(
            f"sensitivity_{key}_min", min(value), "", "config/study.yaml",
            "declared sensitivity range")
        add(
            f"sensitivity_{key}_max", max(value), "", "config/study.yaml",
            "declared sensitivity range")

out = pd.DataFrame(rows)
if out.key.duplicated().any():
    raise RuntimeError(
        f"duplicate frozen keys: {out.loc[out.key.duplicated(), 'key'].tolist()}")
out.to_csv(f"{ROOT}/FINAL_MANUSCRIPT_VALUES.csv", index=False)
out.to_csv(f"{ROOT}/analysis/manuscript_values.csv", index=False)
print(len(out), "values frozen")
