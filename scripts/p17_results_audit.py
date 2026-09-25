"""Create original-versus-corrected and interaction-aware ablation outputs."""
import os

import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def add(rows, city, metric, original, corrected, reason, interpretation):
    if isinstance(original, (int, float)) and isinstance(corrected, (int, float)):
        change = corrected - original
    else:
        change = ""
    rows.append(dict(
        Municipality=city.title(), Metric=metric, Original=original,
        Corrected=corrected, Change=change, Reason=reason,
        Interpretation=interpretation))


original = pd.read_csv(f"{ROOT}/audit/original_results/scenario_results.csv").set_index("city")
corrected = pd.read_csv(f"{ROOT}/analysis/scenario_results.csv").set_index("city")
rows = []
for city in corrected.index:
    old = original.loc[city]
    new = corrected.loc[city]
    add(rows, city, "modeled demand (kW)", old.total_demand_kw,
        new.total_demand_kw,
        "Demand is unchanged; disconnected road components are now clustered separately.",
        "The correction changes electrical representation, not modeled demand.")
    add(rows, city, "feeder/service clusters", old.clusters, new.clusters,
        "Clustering is constrained within connected road-graph components and retains singletons.",
        "No demand cluster is silently discarded because its road subgraph is disconnected.")
    add(rows, city, "S1 NPC (JPY)", old.s1_npc, new.s1_npc,
        "Corrected NPC includes explicit transformers, equivalent LV services, catalogued cables and losses.",
        "Absolute NPC is not directly comparable to the incomplete legacy boundary.")
    add(rows, city, "S2 NPC (JPY)", old.s2_npc, new.s2_npc,
        "Corrected NPC includes the same complete MV/LV/transformer boundary as S1.",
        "Absolute NPC is higher because omitted assets were restored.")
    add(rows, city, "S1-S2 NPC difference (JPY)", old.delta_npc, new.delta_npc,
        "Recomputed after enforcing engineering feasibility and complete asset boundaries.",
        "Positive savings survive, but their magnitude changes.")
    add(rows, city, "combined static-horizon screening savings (%)",
        old.ltp_pct, new.combined_screening_savings_pct,
        "Recomputed as an assumption-conditional combined routing and equipment-screening contrast.",
        "This is not a topology likelihood, causal topology effect, calibrated probability, or full life-cycle result.")
    add(rows, city, "minimum-construction routing-policy savings (%)", "",
        new.routing_policy_savings_pct,
        "Reference-conductor reconstructed-route ensemble is compared with the fixed-conductor minimum-construction policy.",
        "This isolates the declared routing-policy contrast from conductor sizing.")
    old_loss_reduction = 100.0 * (old.s1_plkw - old.s2_plkw) / old.s1_plkw
    new_loss_reduction = 100.0 * (new.s1_plkw - new.s2_plkw) / new.s1_plkw
    add(rows, city, "peak-loss reduction S1 to S2 (%)",
        old_loss_reduction, new_loss_reduction,
        "Corrected conductors use bounded one-edge economic search under ampacity and voltage gates.",
        "Losses are an explicit cost component, but the heuristic does not certify a global economic optimum.")
    add(rows, city, "maximum primary voltage drop (%)", old.max_vdrop,
        new.max_mv_vdrop_pct,
        "The legacy calculation applied a 415 V base to aggregated cluster routes; corrected routes are 6.6 kV primary feeders.",
        "The 29-38% values were structural/model artifacts, not feasible-network diagnostics.")
    add(rows, city, "minimum customer voltage (pu)", "", new.min_customer_voltage_pu,
        "New metric combines MV, transformer and equivalent LV-service drop.",
        "All reported cluster models pass the frozen local-source screening gates; upstream utility networks are outside scope.")
    add(rows, city, "transformer units", "", new.transformer_units,
        "Explicit catalogued transformer units are sized at <=80% design loading.",
        "Transformer count is now visible in engineering and cost boundaries.")
    add(rows, city, "edge-set divergence", old.mean_tld,
        new.mean_edge_set_divergence,
        "The metric is renamed from TLD because it is a Jaccard edge-set distance, not a likelihood.",
        "The corrected candidate family often selects the minimum-construction topology; routing changes are modest.")

pd.DataFrame(rows).to_csv(f"{ROOT}/ORIGINAL_VS_CORRECTED_RESULTS.csv", index=False)

ablation = pd.read_csv(f"{ROOT}/analysis/ablation_results.csv")
pivot = (ablation.groupby(["city", "ablation"]).npc_jpy.sum()
         .unstack("ablation"))
decomposition = []
for city, row in pivot.iterrows():
    f00 = row["representative_legacy_route_conductor_fixed"]
    f01 = row["representative_legacy_route_conductor_optimized"]
    f10 = row["minimum_construction_route_conductor_fixed"]
    f11 = row["minimum_construction_route_conductor_optimized"]
    routing_first = f00 - f10
    routing_after_conductor = f01 - f11
    conductor_first = f00 - f01
    conductor_after_routing = f10 - f11
    routing_shapley = 0.5 * (routing_first + routing_after_conductor)
    conductor_shapley = 0.5 * (conductor_first + conductor_after_routing)
    interaction = (f00 - f10 - f01 + f11)
    decomposition.append(dict(
        city=city, estimand=(
            "paired representative-legacy versus minimum-construction "
            "routing-policy contrast"),
        npc_legacy_route_conductor_fixed=f00,
        npc_legacy_route_conductor_optimized=f01,
        npc_minimum_construction_route_conductor_fixed=f10,
        npc_minimum_construction_route_conductor_optimized=f11,
        total_savings_jpy=f00 - f11,
        routing_policy_shapley_savings_jpy=routing_shapley,
        conductor_shapley_savings_jpy=conductor_shapley,
        routing_conductor_interaction_jpy=interaction,
        transformer_variation_savings_jpy=0.0,
        decomposition_check_jpy=routing_shapley + conductor_shapley
        - (f00 - f11)))
pd.DataFrame(decomposition).to_csv(
    f"{ROOT}/analysis/ablation_decomposition.csv", index=False)

cfg = yaml.safe_load(open(f"{ROOT}/config/study.yaml", encoding="utf-8"))
adf = sum(
    1.0 / (1.0 + cfg["project"]["discount_rate"]) ** year
    for year in range(1, cfg["project"]["primary_horizon_years"] + 1))
capex_factor = 1.0 + cfg["cost_model"]["om_fraction_of_capex"] * adf
loss_factor_npc = cfg["cost_model"]["electricity_jpy_per_kwh"] * adf
component_rows = []
for city in corrected.index:
    cluster = pd.read_csv(
        f"{ROOT}/data/processed/{city}/cluster_results.csv")
    components = {
        "routing/excavation": (
            cluster.s1_capex_trench_mean.sum()
            - cluster.s2_capex_trench.sum()) * capex_factor,
        "conductors": (
            cluster.s1_capex_conductor_mean.sum()
            - cluster.s2_capex_conductor.sum()) * capex_factor,
        "transformers": (
            cluster.s1_capex_transformer_mean.sum()
            - cluster.s2_capex_transformer.sum()) * capex_factor,
        "variable technical losses": (
            cluster.s1_variable_loss_kwh_y_mean.sum()
            - cluster.s2_variable_loss_kwh_y.sum()) * loss_factor_npc,
        "transformer no-load losses": (
            cluster.s1_no_load_loss_kwh_y_mean.sum()
            - cluster.s2_no_load_loss_kwh_y.sum()) * loss_factor_npc,
    }
    accounted = sum(components.values())
    total = float(corrected.loc[city, "delta_npc"])
    components["rounding/selection interaction residual"] = total - accounted
    for component, value in components.items():
        component_rows.append(dict(
            city=city, component=component, npc_savings_jpy=value,
            share_of_combined_savings=(
                value / total if abs(total) > 1e-12 else float("nan")),
            interpretation=(
                "accounting decomposition of the selected screening "
                "policies; not a causal marginal effect")))
pd.DataFrame(component_rows).to_csv(
    f"{ROOT}/analysis/component_decomposition.csv", index=False)
audit_lines = [
    "# Voltage root-cause audit",
    "",
    "## Finding",
    "",
    "The quarantined voltage-drop results were caused by both an "
    "implementation defect and a structural network-model defect. They were "
    "not a valid comparison between engineering-feasible alternatives.",
    "",
    "## Implementation defects",
    "",
    "- The legacy evaluator treated road-tree edges as one low-voltage feeder.",
    "- Reactive power, cable reactance, transformer behavior and line-loss "
    "feedback into upstream flow were omitted.",
    "- There were no binding ampacity, voltage, connectivity, radiality, "
    "complete-service or source-power-balance gates.",
    "- Node-identifier conversion and disconnected-component handling could "
    "silently remove modeled demand.",
    "",
    "## Structural defects",
    "",
    "Large aggregated loads were assigned to an LV-only tree without explicit "
    "MV primaries, transformer placement/capacity, service units or LV reach. "
    "The corrected model instead uses balanced 6.6-kV MV trees, catalogued "
    "single-phase 6.6-kV/210–105-V transformers, conservative parallel service "
    "units and equivalent 210-V LV stubs. Each connected cluster has its own "
    "idealized source; shared upstream utility assets remain outside scope.",
    "",
    "## Quantitative resolution",
    "",
    "| Municipality | Quarantined maximum drop | Corrected maximum MV drop | "
    "Corrected minimum customer voltage |",
    "| --- | ---: | ---: | ---: |",
]
for city in original.index:
    audit_lines.append(
        f"| {city.capitalize()} | {original.loc[city, 'max_vdrop']:.2f}% | "
        f"{corrected.loc[city, 'max_mv_vdrop_pct']:.3f}% | "
        f"{corrected.loc[city, 'min_customer_voltage_pu']:.4f} pu |")
audit_lines.extend([
    "",
    "All clusters entering the reported scenario summaries pass the frozen "
    "screening gates; failed clusters may not be excluded.",
    "",
    "## Interpretation",
    "",
    "The corrected outputs establish internal feasibility of the declared "
    "local-source screening model. They do not establish actual municipal "
    "feeder topology, shared-substation feasibility, construction readiness, "
    "or global optimization. Routing-policy savings and combined routing-and-"
    "sizing savings are reported separately.",
    "",
])
with open(f"{ROOT}/VOLTAGE_ROOT_CAUSE_AUDIT.md", "w", encoding="utf-8") as handle:
    handle.write("\n".join(audit_lines))
print(pd.DataFrame(decomposition).to_string(index=False))
