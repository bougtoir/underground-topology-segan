"""Conditional global scenario sampling for the corrected screening model.

Each draw uses one coherent reconstruction family/replicate across a city and
one coherent S2 heuristic weight across non-singleton clusters. Accounting
parameters and the assumed conductor area-price exponent vary jointly.
Topology and equipment are not redesigned within a draw, so frequencies and
intervals are scenario-sampling summaries, not calibrated probabilities.
"""
import json
import os
from collections import Counter

import numpy as np
import pandas as pd
import yaml

from electrical_model import loss_factor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml", encoding="utf-8"))
SEED = CFG["project"]["seed"]
N = CFG["sensitivity"]["n_mc"]
RANGES = CFG["sensitivity"]["ranges"]
BASE_LF = CFG["project"]["load_factor"]
BASE_EXPONENT = CFG["cost_model"]["cable_area_cost_exponent"]
BASE = dict(
    discount_rate=CFG["project"]["discount_rate"],
    horizon=CFG["project"]["primary_horizon_years"],
    electricity_jpy_kwh=CFG["cost_model"]["electricity_jpy_per_kwh"],
    om_fraction=CFG["cost_model"]["om_fraction_of_capex"],
    construction_multiplier=1.0, conductor_multiplier=1.0,
    transformer_multiplier=1.0, load_factor=BASE_LF,
    demand_multiplier=1.0, conductor_area_cost_exponent=BASE_EXPONENT)


def annuity_factor(rate, horizon):
    return sum(1.0 / (1.0 + rate) ** year
               for year in range(1, int(horizon) + 1))


def conductor_terms(inventory_text):
    terms = []
    for key, length_m in json.loads(inventory_text).items():
        tier, area = key.split(":")
        base = CFG["cost_model"][
            "cable_mv_jpy_per_m" if tier == "MV"
            else "cable_lv_jpy_per_m"]
        terms.append((float(length_m) * base, float(area) / 150.0))
    return terms


def components(row):
    return dict(
        trench=float(row.capex_trench_jpy),
        conductor_terms=conductor_terms(row.conductor_inventory_json),
        transformer=float(row.capex_transformer_jpy),
        variable_loss=float(row.variable_loss_kwh_y),
        no_load_loss=float(row.no_load_loss_kwh_y))


def npc(parts, params):
    conductor = sum(
        cost * ratio ** params["conductor_area_cost_exponent"]
        for cost, ratio in parts["conductor_terms"])
    capex = (
        parts["trench"] * params["construction_multiplier"]
        + conductor * params["conductor_multiplier"]
        + parts["transformer"] * params["transformer_multiplier"])
    variable_loss = (
        parts["variable_loss"]
        * params["demand_multiplier"] ** 2
        * loss_factor(params["load_factor"]) / loss_factor(BASE_LF))
    annual_loss = variable_loss + parts["no_load_loss"]
    return capex + (
        annual_loss * params["electricity_jpy_kwh"]
        + capex * params["om_fraction"]) * annuity_factor(
            params["discount_rate"], params["horizon"])


rng = np.random.default_rng(SEED)
draws = pd.DataFrame(dict(
    discount_rate=rng.uniform(*RANGES["discount_rate"], N),
    horizon=rng.choice(RANGES["horizon_years"], N),
    electricity_jpy_kwh=rng.uniform(
        *RANGES["electricity_jpy_per_kwh"], N),
    om_fraction=rng.uniform(*RANGES["om_fraction"], N),
    construction_multiplier=rng.uniform(
        *RANGES["construction_multiplier"], N),
    conductor_multiplier=rng.uniform(
        *RANGES["conductor_multiplier"], N),
    conductor_area_cost_exponent=rng.uniform(
        *RANGES["conductor_area_cost_exponent"], N),
    transformer_multiplier=rng.uniform(
        *RANGES["transformer_multiplier"], N),
    load_factor=rng.uniform(*RANGES["load_factor"], N),
    demand_multiplier=rng.uniform(*RANGES["demand_multiplier"], N),
    reconstruction_family=rng.choice(["A_steiner", "B_incremental"], N),
    reconstruction_replicate_within_family=rng.integers(
        0, CFG["reconstruction"]["n_replicates"] // 2, N),
    s2_candidate_weight=rng.choice(
        CFG["optimization"]["candidate_weight_grid"], N)))
draws["reconstruction_replicate"] = (
    draws.reconstruction_replicate_within_family
    + np.where(draws.reconstruction_family == "B_incremental",
               CFG["reconstruction"]["n_replicates"] // 2, 0))
draws.insert(0, "draw", range(N))
draws.to_csv(f"{ROOT}/analysis/sensitivity_draws.csv", index=False)

diagnostics = pd.read_csv(f"{ROOT}/analysis/feasibility_diagnostics.csv")
diagnostics = diagnostics[diagnostics.feasible].copy()

mc_rows = []
tornado_rows = []
sampled_counts = Counter()
for city in ["sano", "kudamatsu", "yasu"]:
    legacy = diagnostics[
        (diagnostics.city == city) & (diagnostics.scenario == "S1")]
    s2_candidates = diagnostics[
        (diagnostics.city == city)
        & (diagnostics.scenario == "S2_candidate")]
    clusters = sorted(int(value) for value in legacy.cluster.unique())
    legacy_lookup = {}
    singleton_lookup = {}
    for _, row in legacy.iterrows():
        if row.family == "singleton":
            singleton_lookup[int(row.cluster)] = (
                components(row), row.candidate)
        else:
            legacy_lookup[
                (int(row.cluster), row.family, int(row.replicate))
            ] = (components(row), row.candidate)
    s2_lookup = {
        (int(row.cluster), round(float(row.candidate_weight), 12)):
        (components(row), row.candidate)
        for _, row in s2_candidates.iterrows()
    }
    s2_cluster_keys = {
        cluster: [key for key in s2_lookup if key[0] == cluster]
        for cluster in clusters
    }
    delta = np.empty(N)
    s1_values = np.empty(N)
    s2_values = np.empty(N)
    for draw_id, draw in draws.iterrows():
        params = draw.drop(labels=[
            "draw", "reconstruction_family", "reconstruction_replicate",
            "reconstruction_replicate_within_family",
            "s2_candidate_weight"]).to_dict()
        s1_total = 0.0
        s2_total = 0.0
        for cluster in clusters:
            if cluster in singleton_lookup:
                selected_s1, s1_candidate = singleton_lookup[cluster]
            else:
                key = (
                    cluster, draw.reconstruction_family,
                    int(draw.reconstruction_replicate))
                if key not in legacy_lookup:
                    raise RuntimeError(
                        f"{city} cluster {cluster}: missing coherent "
                        "reconstruction candidate")
                selected_s1, s1_candidate = legacy_lookup[key]
            weight_key = (
                cluster, round(float(draw.s2_candidate_weight), 12))
            if weight_key not in s2_lookup:
                weight_key = None
            if weight_key is None:
                cluster_keys = s2_cluster_keys[cluster]
                if len(cluster_keys) == 1:
                    weight_key = cluster_keys[0]
            if weight_key is None:
                raise RuntimeError(
                    f"{city} cluster {cluster}: missing coherent S2 weight "
                    f"{draw.s2_candidate_weight}")
            selected_s2, _ = s2_lookup[weight_key]
            s1_total += npc(selected_s1, params)
            s2_total += npc(selected_s2, params)
            sampled_counts[(
                city, cluster, draw.reconstruction_family,
                int(draw.reconstruction_replicate),
                int(draw.reconstruction_replicate_within_family),
                s1_candidate, float(draw.s2_candidate_weight))] += 1
        s1_values[draw_id] = s1_total
        s2_values[draw_id] = s2_total
        delta[draw_id] = s1_total - s2_total
    ratio = delta / s1_values
    mc_rows.append(dict(
        city=city, n_draws=N, delta_mean=float(delta.mean()),
        delta_median=float(np.median(delta)),
        delta_p2_5=float(np.percentile(delta, 2.5)),
        delta_p97_5=float(np.percentile(delta, 97.5)),
        combined_screening_savings_pct_mean=float(100.0 * np.mean(ratio)),
        combined_screening_savings_pct_p2_5=float(
            100.0 * np.percentile(ratio, 2.5)),
        combined_screening_savings_pct_p97_5=float(
            100.0 * np.percentile(ratio, 97.5)),
        scenario_positive_fraction=float(np.mean(delta > 0)),
        coherent_city_reconstruction_draw=True,
        coherent_city_s2_policy_draw=True,
        conductor_area_price_curve_varied=True,
        topology_reoptimized_each_draw=False,
        equipment_resized_each_draw=False,
        interpretation="conditional scenario-sampling frequency"))

    city_s1 = legacy.groupby("cluster").first()
    base_s1 = [components(row) for _, row in city_s1.iterrows()]
    city_s2 = s2_candidates.loc[
        s2_candidates.groupby("cluster").npc_jpy.idxmin()]
    base_s2 = [components(row) for _, row in city_s2.iterrows()]
    for parameter, limits in RANGES.items():
        normalized = "horizon" if parameter == "horizon_years" else parameter
        for level, value in zip(["low", "high"], [limits[0], limits[-1]]):
            params = dict(BASE)
            params[normalized] = value
            s1_value = sum(npc(part, params) for part in base_s1)
            s2_value = sum(npc(part, params) for part in base_s2)
            tornado_rows.append(dict(
                city=city, parameter=normalized, level=level, value=value,
                delta_npc=s1_value - s2_value,
                combined_screening_savings_pct=(
                    100.0 * (s1_value - s2_value) / s1_value)))

pd.DataFrame(mc_rows).to_csv(
    f"{ROOT}/analysis/sensitivity_mc.csv", index=False)
pd.DataFrame(tornado_rows).to_csv(
    f"{ROOT}/analysis/sensitivity_tornado.csv", index=False)
sample_counts = pd.DataFrame([
    dict(
        city=key[0], cluster=key[1], reconstruction_family=key[2],
        reconstruction_replicate=key[3],
        reconstruction_replicate_within_family=key[4],
        s1_candidate=key[5], s2_candidate_weight=key[6],
        selection_count=count)
    for key, count in sampled_counts.items()
])
sample_counts.to_csv(
    f"{ROOT}/analysis/sensitivity_scenario_sampling.csv", index=False)
print(pd.DataFrame(mc_rows).to_string(index=False))
