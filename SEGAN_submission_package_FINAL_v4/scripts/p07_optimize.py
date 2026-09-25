"""Phase 7 (forensic revision): engineering-feasible MV/LV scenario analysis.

Correction relative to the quarantined legacy implementation:
* road-network edges are explicit 6.6 kV primary feeders, not one implicit
  415 V feeder carrying an entire ~350 kW cluster;
* every demand node is an explicit transformer site;
* aggregated nodes are split across as many catalogued transformer units as
  needed, with a conservative 60 kW/unit design cap and a 25 m equivalent LV
  service stub per unit;
* three-phase MV and single-phase 210-105 V LV P/Q voltage drop, catalogue
  R/X, derated ampacity, transformer
  loading/loss/drop, source voltage, connectivity, radiality, power balance and
  statutory customer voltage are enforced;
* infeasible candidates are rejected, never clipped or hidden.

S1   reconstructed legacy route undergrounded with reference conductors.
S1.5 minimum-construction feasible Steiner primary route, fixed conductors.
S2   best-screening-NPC feasible candidate in a declared heuristic candidate
     family, with bounded one-edge-at-a-time economic conductor search. It
     remains "best-found", not globally optimal.
"""
import glob
import json
import math
import os
import re

import networkx as nx
import numpy as np
import pandas as pd
import yaml

from electrical_model import (
    choose_transformer,
    load_catalogs,
    load_spec,
    loss_factor,
    size_tree_conductors,
    transformer_drop_pct,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml", encoding="utf-8"))
SPEC = load_spec(f"{ROOT}/ENGINEERING_FEASIBILITY_SPEC.yaml")
BASE_CABLES, TRANSFORMERS = load_catalogs(ROOT, SPEC)
CABLES = BASE_CABLES
CITY_FREQUENCY_HZ = SPEC["system"]["municipality_frequency_hz"]

PF = float(SPEC["system"]["power_factor"])
MV_V = float(SPEC["system"]["mv_nominal_kv"]) * 1000.0
LV_V = float(SPEC["system"]["lv_nominal_v"])
LV_STUB_M = float(SPEC["topology_gates"]["modeled_lv_stub_length_m"])
LV_UNIT_KW = float(SPEC["topology_gates"]["max_lv_unit_kw"])
H = CFG["project"]["primary_horizon_years"]
DISCOUNT = CFG["project"]["discount_rate"]
ENERGY_JPY_KWH = CFG["cost_model"]["electricity_jpy_per_kwh"]
OM_FRAC = CFG["cost_model"]["om_fraction_of_capex"]
EXCAVATION = CFG["cost_model"]["excavation_jpy_per_m"]
DUCT = CFG["cost_model"]["duct_bank_jpy_per_m"]
MV_CABLE_150 = CFG["cost_model"]["cable_mv_jpy_per_m"]
LV_CABLE_150 = CFG["cost_model"]["cable_lv_jpy_per_m"]
TRANSFORMER_100 = CFG["cost_model"]["pad_transformer_jpy"]
CABLE_COST_EXPONENT = CFG["cost_model"]["cable_area_cost_exponent"]
LOAD_FACTOR = float(SPEC["demand"]["load_factor"])
LOSS_FACTOR = loss_factor(LOAD_FACTOR)
ADF = sum(1.0 / (1.0 + DISCOUNT) ** y for y in range(1, H + 1))
MV_SIZES = [int(x) for x in SPEC["conductors"]["mv_candidate_areas_mm2"]]
LV_SIZES = [int(x) for x in SPEC["conductors"]["lv_candidate_areas_mm2"]]


def nid(value):
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.12g}"


def load_city(name):
    nodes = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv")
    edges = pd.read_csv(f"{ROOT}/data/processed/{name}/edges.csv")
    graph = nx.Graph()
    for _, row in edges.iterrows():
        graph.add_edge(nid(row.u), nid(row.v), length=float(row.length))
    pos = {nid(row.node): (float(row.x_m), float(row.y_m))
           for _, row in nodes.iterrows()}
    demand = {nid(row.node): float(row.p_kw) for _, row in nodes.iterrows()
              if float(row.p_kw) > 0}
    return graph, pos, demand


def prune(graph, keep):
    out = graph.copy()
    keep = set(keep)
    while True:
        leaves = [node for node in out if out.degree(node) <= 1 and node not in keep]
        if not leaves:
            return out
        out.remove_nodes_from(leaves)


def weighted_steiner(graph, terms, weight_factor, source):
    d_source = nx.single_source_dijkstra_path_length(graph, source, weight="length")
    weighted = nx.Graph()
    for u, v, data in graph.edges(data=True):
        ds = min(d_source.get(u, 1e12), d_source.get(v, 1e12))
        weight = data["length"] * (1.0 + weight_factor * 250.0 / (50.0 + ds))
        weighted.add_edge(u, v, weight=weight)
    complete = nx.Graph()
    paths = {}
    for i, start in enumerate(terms):
        lengths, start_paths = nx.single_source_dijkstra(weighted, start, weight="weight")
        paths[start] = start_paths
        for end in terms[i + 1:]:
            if end in lengths:
                complete.add_edge(start, end, weight=lengths[end])
    if complete.number_of_edges() == 0 or not nx.is_connected(complete):
        return None
    metric_mst = nx.minimum_spanning_tree(complete, weight="weight")
    out = nx.Graph()
    for start, end in metric_mst.edges:
        path = paths[start][end]
        for a, b in zip(path[:-1], path[1:]):
            out.add_edge(a, b, length=float(graph[a][b]["length"]))
    out = nx.minimum_spanning_tree(out, weight="length")
    return prune(out, terms)


def cable_cost_per_m(tier, area):
    base = MV_CABLE_150 if tier == "MV" else LV_CABLE_150
    return base * (float(area) / 150.0) ** CABLE_COST_EXPONENT


def transformer_capex(rating_kva):
    return TRANSFORMER_100 * (float(rating_kva) / 100.0) ** 0.75


def conductor_objective(graph, tier):
    def score(areas, power_flow):
        capex = sum(
            float(data["length"]) * cable_cost_per_m(
                tier, int(areas[tuple(sorted((u, v)))]))
            for u, v, data in graph.edges(data=True))
        loss_npc = (
            float(power_flow["peak_loss_kw"]) * 8760.0 * LOSS_FACTOR
            * ENERGY_JPY_KWH * ADF)
        return capex * (1.0 + OM_FRAC * ADF) + loss_npc
    return score


def inventory_json(inventory):
    return json.dumps(
        {key: round(value, 9) for key, value in sorted(inventory.items())},
        sort_keys=True, separators=(",", ":"))


def service_units(demands, optimize_lv):
    rows = []
    lv_peak_loss = 0.0
    tr_no_load_kw = 0.0
    tr_load_loss_peak_kw = 0.0
    capex_lv_trench = 0.0
    capex_lv_cable = 0.0
    capex_tr = 0.0
    site_input_kw = {node: 0.0 for node in demands}
    conductor_inventory = {}
    design_loading = SPEC["thermal_gates"]["design_transformer_loading_pct"]
    for node, load_kw in sorted(demands.items()):
        count = max(1, int(math.ceil(load_kw / LV_UNIT_KW)))
        unit_kw = load_kw / count
        for unit in range(count):
            tr = choose_transformer(TRANSFORMERS, unit_kw, PF, design_loading)
            s_kva = unit_kw / PF
            tr_loading = 100.0 * s_kva / tr.rating_kva
            tr_drop = transformer_drop_pct(tr, unit_kw, PF)
            lv_graph = nx.Graph()
            secondary = f"{node}::tr{unit}"
            load_node = f"{node}::load{unit}"
            lv_graph.add_edge(secondary, load_node, length=LV_STUB_M)
            areas, lv_pf = size_tree_conductors(
                lv_graph, secondary, {load_node: unit_kw}, "LV", LV_SIZES, LV_V,
                PF, CABLES, SPEC, optimize=optimize_lv,
                objective=(conductor_objective(lv_graph, "LV")
                           if optimize_lv else None))
            issues = list(lv_pf["issues"])
            if tr_loading > SPEC["thermal_gates"]["max_transformer_loading_pct"] + 1e-9:
                issues.append(f"transformer_loading:{tr_loading:.6g}")
            if tr_drop > SPEC["voltage_gates"]["transformer_drop_max_pct"] + 1e-9:
                issues.append(f"transformer_drop:{tr_drop:.6g}")
            edge = tuple(sorted((secondary, load_node)))
            area = int(areas[edge]) if areas else -1
            lv_peak_loss += float(lv_pf.get("peak_loss_kw", math.inf))
            loading_fraction = s_kva / tr.rating_kva
            tr_no_load_kw += tr.no_load_loss_w / 1000.0
            unit_tr_load_loss = (
                tr.load_loss_w / 1000.0 * loading_fraction ** 2)
            tr_load_loss_peak_kw += unit_tr_load_loss
            site_input_kw[node] += (
                unit_kw + float(lv_pf.get("peak_loss_kw", math.inf))
                + tr.no_load_loss_w / 1000.0 + unit_tr_load_loss)
            capex_lv_trench += LV_STUB_M * (EXCAVATION + DUCT)
            capex_lv_cable += LV_STUB_M * cable_cost_per_m("LV", area)
            capex_tr += transformer_capex(tr.rating_kva)
            key = f"LV:{area}"
            conductor_inventory[key] = (
                conductor_inventory.get(key, 0.0) + LV_STUB_M)
            rows.append(dict(
                site=node, unit=unit, site_load_kw=load_kw, unit_load_kw=unit_kw,
                transformer_kva=tr.rating_kva,
                transformer_loading_pct=tr_loading,
                transformer_drop_pct=tr_drop,
                transformer_no_load_loss_w=tr.no_load_loss_w,
                transformer_load_loss_w=tr.load_loss_w, lv_area_mm2=area,
                lv_stub_m=LV_STUB_M,
                lv_drop_pct=float(lv_pf.get("drop_pct", math.inf)),
                lv_loading_pct=float(lv_pf.get("max_loading_pct", math.inf)),
                feasible=not issues, issues=";".join(issues)))
    frame = pd.DataFrame(rows)
    return dict(feasible=bool(frame.feasible.all()), units=frame,
                lv_peak_loss_kw=lv_peak_loss, tr_no_load_kw=tr_no_load_kw,
                tr_load_loss_peak_kw=tr_load_loss_peak_kw,
                capex_lv=capex_lv_trench + capex_lv_cable,
                capex_lv_trench=capex_lv_trench,
                capex_lv_cable=capex_lv_cable,
                capex_transformer=capex_tr, site_input_kw=site_input_kw,
                conductor_inventory=conductor_inventory)


def evaluate_network(graph, source, demands, optimize_mv, optimize_lv):
    service = service_units(demands, optimize_lv)
    mv_demands = service["site_input_kw"]
    mv_areas, mv_pf = size_tree_conductors(
        graph, source, mv_demands, "MV", MV_SIZES, MV_V, PF, CABLES, SPEC,
        optimize=optimize_mv,
        objective=(conductor_objective(graph, "MV")
                   if optimize_mv else None))
    issues = list(mv_pf["issues"])
    if not service["feasible"]:
        issues.append("infeasible_transformer_or_lv_service")
    modeled_loss_kw = (
        mv_pf.get("peak_loss_kw", math.inf) + service["lv_peak_loss_kw"]
        + service["tr_load_loss_peak_kw"] + service["tr_no_load_kw"])
    source_balance_kw = abs(
        mv_pf.get("source_input_kw", math.inf)
        - sum(demands.values()) - modeled_loss_kw)
    if source_balance_kw > \
            SPEC["topology_gates"]["power_balance_tolerance_kw"]:
        issues.append(f"power_balance:{source_balance_kw}")
    min_customer_pu = math.inf
    max_customer_pu = -math.inf
    if mv_pf.get("feasible") and service["feasible"]:
        site_mv_pu = {node: value / MV_V
                      for node, value in mv_pf["voltages_v"].items()}
        for _, unit in service["units"].iterrows():
            customer_pu = (site_mv_pu[unit.site]
                           - unit.transformer_drop_pct / 100.0
                           - unit.lv_drop_pct / 100.0)
            min_customer_pu = min(min_customer_pu, customer_pu)
            max_customer_pu = max(max_customer_pu, customer_pu)
        if min_customer_pu < SPEC["voltage_gates"]["customer_min_pu_on_105v"] - 1e-9:
            issues.append(f"customer_voltage:{min_customer_pu:.6g}<"
                          f"{SPEC['voltage_gates']['customer_min_pu_on_105v']}")
        if max_customer_pu > \
                SPEC["voltage_gates"]["customer_max_pu_on_105v"] + 1e-9:
            issues.append(f"customer_voltage:{max_customer_pu:.6g}>"
                          f"{SPEC['voltage_gates']['customer_max_pu_on_105v']}")
    capex_mv_trench = 0.0
    capex_mv_cable = 0.0
    length_m = 0.0
    upsize_m = 0.0
    conductor_inventory = dict(service["conductor_inventory"])
    if mv_areas:
        for u, v, data in graph.edges(data=True):
            edge = tuple(sorted((u, v)))
            area = int(mv_areas[edge])
            length = float(data["length"])
            capex_mv_trench += length * (EXCAVATION + DUCT)
            capex_mv_cable += length * cable_cost_per_m("MV", area)
            length_m += length
            if area > SPEC["conductors"]["mv_reference_area_mm2"]:
                upsize_m += length
            key = f"MV:{area}"
            conductor_inventory[key] = (
                conductor_inventory.get(key, 0.0) + length)
    capex_mv = capex_mv_trench + capex_mv_cable
    capex = capex_mv + service["capex_lv"] + service["capex_transformer"]
    variable_peak_loss = mv_pf.get("peak_loss_kw", math.inf) + service["lv_peak_loss_kw"]
    variable_loss_kwh_y = (
        variable_peak_loss * 8760.0 * LOSS_FACTOR
        + service["tr_load_loss_peak_kw"] * 8760.0 * LOSS_FACTOR)
    no_load_loss_kwh_y = service["tr_no_load_kw"] * 8760.0
    annual_loss_kwh = variable_loss_kwh_y + no_load_loss_kwh_y
    npc = capex + (annual_loss_kwh * ENERGY_JPY_KWH + capex * OM_FRAC) * ADF
    return dict(
        feasible=not issues, issues=";".join(issues), npc=npc, capex=capex,
        capex_mv=capex_mv, capex_lv=service["capex_lv"],
        capex_trench=capex_mv_trench + service["capex_lv_trench"],
        capex_conductor=capex_mv_cable + service["capex_lv_cable"],
        capex_transformer=service["capex_transformer"], length_m=length_m,
        pl_kw=variable_peak_loss + service["tr_load_loss_peak_kw"]
        + service["tr_no_load_kw"],
        cable_peak_loss_kw=variable_peak_loss,
        transformer_peak_loss_kw=service["tr_load_loss_peak_kw"]
        + service["tr_no_load_kw"],
        eloss_kwh_y=annual_loss_kwh,
        variable_loss_kwh_y=variable_loss_kwh_y,
        no_load_loss_kwh_y=no_load_loss_kwh_y,
        mv_vdrop_pct=mv_pf.get("drop_pct", math.inf),
        lv_vdrop_max=float(service["units"].lv_drop_pct.max()),
        transformer_drop_max=float(service["units"].transformer_drop_pct.max()),
        customer_min_pu=min_customer_pu,
        customer_max_pu=max_customer_pu,
        mv_loading_max_pct=mv_pf.get("max_loading_pct", math.inf),
        lv_loading_max_pct=float(service["units"].lv_loading_pct.max()),
        transformer_loading_max_pct=float(
            service["units"].transformer_loading_pct.max()),
        transformer_units=len(service["units"]), upsize_m=upsize_m,
        power_balance_kw=source_balance_kw,
        conductor_inventory=conductor_inventory,
        area_map=mv_areas, service_units=service["units"],
        edge_results=mv_pf.get("edge_results", pd.DataFrame()))


def mean_metric(results, key):
    return float(np.mean([result[key] for result in results]))


def max_metric(results, key):
    return float(np.max([result[key] for result in results]))


def diagnostic_record(city, cluster, scenario, candidate, result,
                      family="", replicate=-1, weight=np.nan):
    return dict(
        city=city, cluster=cluster, scenario=scenario, candidate=candidate,
        family=family, replicate=replicate, candidate_weight=weight,
        feasible=result["feasible"], issues=result["issues"],
        mv_drop_pct=result["mv_vdrop_pct"],
        lv_drop_pct=result["lv_vdrop_max"],
        transformer_drop_pct=result["transformer_drop_max"],
        customer_min_pu=result["customer_min_pu"],
        customer_max_pu=result["customer_max_pu"],
        mv_loading_pct=result["mv_loading_max_pct"],
        transformer_loading_pct=result["transformer_loading_max_pct"],
        power_balance_kw=result["power_balance_kw"],
        npc_jpy=result["npc"], length_m=result["length_m"],
        capex_trench_jpy=result["capex_trench"],
        capex_conductor_jpy=result["capex_conductor"],
        capex_transformer_jpy=result["capex_transformer"],
        variable_loss_kwh_y=result["variable_loss_kwh_y"],
        no_load_loss_kwh_y=result["no_load_loss_kwh_y"],
        conductor_inventory_json=inventory_json(
            result["conductor_inventory"]))


scenario_rows = []
diagnostic_rows = []
service_rows = []
ablation_rows = []
search_rows = []
for city in ["sano", "kudamatsu", "yasu"]:
    frequency_hz = CITY_FREQUENCY_HZ[city]
    CABLES = BASE_CABLES.copy()
    CABLES["x_ohm_per_km"] *= frequency_hz / float(
        SPEC["system"]["frequency_hz"])
    _, TRANSFORMERS = load_catalogs(ROOT, SPEC, frequency_hz=frequency_hz)
    road, pos, demand_all = load_city(city)
    clusters = pd.read_csv(f"{ROOT}/data/processed/{city}/clusters.csv")
    clusters["node"] = clusters["node"].map(nid)
    reconstruction = pd.read_csv(f"{ROOT}/analysis/reconstruction_summary.csv")
    reconstruction["cluster"] = reconstruction["cluster"].astype(int)
    reconstruction["src"] = reconstruction["src"].map(nid)
    source_map = (reconstruction[reconstruction.city == city]
                  .drop_duplicates("cluster").set_index("cluster").src.to_dict())
    city_results = []
    representative_written = False
    for cluster, group in clusters.groupby("cluster"):
        terminals = [node for node in group.node if node in demand_all]
        if not terminals:
            continue
        demands = {node: demand_all[node] for node in terminals}
        xs = [pos[node][0] for node in terminals]
        ys = [pos[node][1] for node in terminals]
        weights = np.array([demands[node] for node in terminals])
        cx, cy = np.average(xs, weights=weights), np.average(ys, weights=weights)
        source = source_map.get(int(cluster))
        if len(terminals) == 1:
            source = terminals[0]
        if source not in road:
            source = min(road, key=lambda node:
                         (pos[node][0] - cx) ** 2 + (pos[node][1] - cy) ** 2)
        terms = list(dict.fromkeys([source] + terminals))

        legacy = []
        legacy_trees = {}
        for path in sorted(glob.glob(
                f"{ROOT}/data/processed/{city}/recon/"
                f"c{int(cluster):03d}_r*_*csv")):
            edges = pd.read_csv(path)
            tree = nx.Graph()
            for _, row in edges.iterrows():
                a, b = nid(row.u), nid(row.v)
                if road.has_edge(a, b):
                    tree.add_edge(a, b, length=road[a][b]["length"])
            if source not in tree or not set(terminals).issubset(tree):
                continue
            if not nx.is_tree(tree):
                tree = nx.minimum_spanning_tree(tree, weight="length")
            tree = prune(tree, terms)
            fixed = evaluate_network(tree, source, demands, False, False)
            match = re.search(r"_r(\d+)_([AB])_", os.path.basename(path))
            family = (f"{match.group(2)}_"
                      f"{'steiner' if match.group(2) == 'A' else 'incremental'}")
            replicate = int(match.group(1))
            diagnostic_rows.append(diagnostic_record(
                city, cluster, "S1", os.path.basename(path), fixed,
                family=family, replicate=replicate))
            if fixed["feasible"]:
                legacy.append((os.path.basename(path), fixed))
                legacy_trees[os.path.basename(path)] = tree
        if len(terms) == 1:
            tree = nx.Graph()
            tree.add_node(source)
            fixed = evaluate_network(tree, source, demands, False, False)
            diagnostic_rows.append(diagnostic_record(
                city, cluster, "S1", "singleton_co_located_source", fixed,
                family="singleton", replicate=-1))
            if fixed["feasible"]:
                legacy.append(("singleton_co_located_source", fixed))
                legacy_trees["singleton_co_located_source"] = tree
        if not legacy:
            diagnostic_rows.append(dict(
                city=city, cluster=cluster, scenario="cluster",
                candidate="none", feasible=False, issues="no_feasible_S1"))
            continue

        margin = 250.0
        sub_nodes = [
            node for node in road
            if min(xs) - margin <= pos[node][0] <= max(xs) + margin
            and min(ys) - margin <= pos[node][1] <= max(ys) + margin]
        local = road.subgraph(sub_nodes).copy()
        if (not set(terms).issubset(local)
                or not set(terms).issubset(
                    nx.node_connected_component(local, source))):
            local = road.subgraph(nx.node_connected_component(road, source)).copy()
        candidates = {}
        if len(terms) == 1:
            tree = nx.Graph()
            tree.add_node(source)
            candidates[0] = tree
        else:
            for weight in CFG["optimization"]["candidate_weight_grid"]:
                tree = weighted_steiner(local, terms, weight, source)
                if tree is not None and nx.is_tree(tree):
                    candidates[weight] = tree
        fixed_candidates = {}
        optimized_candidates = {}
        candidate_cache = {}
        for weight, tree in candidates.items():
            signature = tuple(sorted(tuple(sorted(edge)) for edge in tree.edges))
            if signature not in candidate_cache:
                candidate_cache[signature] = (
                    evaluate_network(tree, source, demands, False, False),
                    evaluate_network(tree, source, demands, True, True))
            fixed, optimized = candidate_cache[signature]
            if weight == 0:
                diagnostic_rows.append(diagnostic_record(
                    city, cluster, "S1.5", f"weight={weight}", fixed,
                    family="minimum_construction", weight=weight))
            diagnostic_rows.append(diagnostic_record(
                city, cluster, "S2_candidate", f"weight={weight}", optimized,
                family="weighted_steiner", weight=weight))
            if fixed["feasible"]:
                fixed_candidates[weight] = fixed
            if optimized["feasible"]:
                optimized_candidates[weight] = optimized
        if 0 not in fixed_candidates or not optimized_candidates:
            diagnostic_rows.append(dict(
                city=city, cluster=cluster, scenario="cluster",
                candidate="none", feasible=False,
                issues="no_feasible_S1.5_or_S2"))
            continue
        best_weight = min(
            optimized_candidates, key=lambda weight:
            optimized_candidates[weight]["npc"])
        s15 = fixed_candidates[0]
        s15_optimized = optimized_candidates[0]
        s2 = optimized_candidates[best_weight]
        s2_fixed = fixed_candidates[best_weight]
        edge_signatures = {
            tuple(sorted(tuple(sorted(edge)) for edge in tree.edges))
            for tree in candidates.values()}
        search_rows.append(dict(
            city=city, cluster=cluster,
            requested_weight_count=len(
                CFG["optimization"]["candidate_weight_grid"]),
            feasible_fixed_count=len(fixed_candidates),
            feasible_optimized_count=len(optimized_candidates),
            unique_route_count=len(edge_signatures),
            selected_weight=best_weight,
            selected_at_grid_boundary=best_weight in (
                min(CFG["optimization"]["candidate_weight_grid"]),
                max(CFG["optimization"]["candidate_weight_grid"]))))
        s1_fixed_results = [result for _, result in legacy]
        s1_mean_npc = mean_metric(s1_fixed_results, "npc")
        representative_name, representative_fixed = min(
            legacy, key=lambda item: abs(item[1]["npc"] - s1_mean_npc))
        representative_optimized = evaluate_network(
            legacy_trees[representative_name], source, demands, True, True)
        if not representative_optimized["feasible"]:
            raise RuntimeError(
                f"{city} cluster {cluster}: paired legacy route infeasible "
                "after economic conductor search")
        s1_a = [result for name, result in legacy if "_A_" in name] \
            or s1_fixed_results
        s1_b = [result for name, result in legacy if "_B_" in name] \
            or s1_fixed_results
        e_s15 = {tuple(sorted(edge)) for edge in candidates[0].edges}
        e_s2 = {tuple(sorted(edge)) for edge in candidates[best_weight].edges}
        edge_divergence = 1.0 - len(e_s15 & e_s2) / max(
            1, len(e_s15 | e_s2))
        representative_service = s2["service_units"].copy()
        representative_service.insert(0, "city", city)
        representative_service.insert(1, "cluster", cluster)
        service_rows.extend(representative_service.to_dict("records"))
        row = dict(
            city=city, cluster=cluster, frequency_hz=frequency_hz,
            terminals=len(terms),
            demand_kw=sum(demands.values()), transformer_sites=len(demands),
            transformer_units=s2["transformer_units"],
            s1_npc_mean=s1_mean_npc,
            s1_npc_std=float(np.std([result["npc"]
                                     for result in s1_fixed_results])),
            s1B_npc_mean=mean_metric(s1_b, "npc"),
            s1A_npc_mean=mean_metric(s1_a, "npc"),
            s1B_length_mean=mean_metric(s1_b, "length_m"),
            s1_capex_mean=mean_metric(s1_fixed_results, "capex"),
            s1_capex_trench_mean=mean_metric(s1_fixed_results, "capex_trench"),
            s1_capex_conductor_mean=mean_metric(s1_fixed_results, "capex_conductor"),
            s1_capex_transformer_mean=mean_metric(
                s1_fixed_results, "capex_transformer"),
            s1_variable_loss_kwh_y_mean=mean_metric(
                s1_fixed_results, "variable_loss_kwh_y"),
            s1_no_load_loss_kwh_y_mean=mean_metric(
                s1_fixed_results, "no_load_loss_kwh_y"),
            s1_length_mean=mean_metric(s1_fixed_results, "length_m"),
            s1_plkw_mean=mean_metric(s1_fixed_results, "pl_kw"),
            s1_vdrop_max=max_metric(s1_fixed_results, "mv_vdrop_pct"),
            s1_customer_min_pu=min(
                result["customer_min_pu"] for result in s1_fixed_results),
            s1_representative_candidate=representative_name,
            s1_representative_fixed_npc=representative_fixed["npc"],
            s1_conductor_optimized_npc=representative_optimized["npc"],
            s15_npc=s15["npc"], s15_capex=s15["capex"],
            s15_conductor_optimized_npc=s15_optimized["npc"],
            s2_topology_fixed_conductor_npc=s2_fixed["npc"],
            s2_npc=s2["npc"], s2_w=best_weight, s2_capex=s2["capex"],
            s2_capex_trench=s2["capex_trench"],
            s2_capex_conductor=s2["capex_conductor"],
            s2_capex_transformer=s2["capex_transformer"],
            s2_variable_loss_kwh_y=s2["variable_loss_kwh_y"],
            s2_no_load_loss_kwh_y=s2["no_load_loss_kwh_y"],
            s2_plkw=s2["pl_kw"], s2_length=s2["length_m"],
            s2_vdrop=s2["mv_vdrop_pct"],
            s2_customer_min_pu=s2["customer_min_pu"],
            s2_upsize_m=s2["upsize_m"],
            edge_set_divergence=edge_divergence, tld=edge_divergence,
            all_primary_networks_feasible=True)
        row["delta_npc"] = row["s1_npc_mean"] - row["s2_npc"]
        row["delta_npc_B"] = row["s1B_npc_mean"] - row["s2_npc"]
        row["routing_policy_delta_npc"] = (
            row["s1_npc_mean"] - row["s15_npc"])
        row["routing_policy_savings_pct"] = (
            100.0 * row["routing_policy_delta_npc"]
            / row["s1_npc_mean"])
        row["combined_screening_savings_pct"] = (
            100.0 * row["delta_npc"] / row["s1_npc_mean"])
        row["ltp_pct"] = 100.0 * row["delta_npc"] / row["s1_npc_mean"]
        row["ltpB_pct"] = 100.0 * row["delta_npc_B"] / row["s1B_npc_mean"]
        city_results.append(row)
        for label, value in [
            ("representative_legacy_route_conductor_fixed",
             representative_fixed["npc"]),
            ("representative_legacy_route_conductor_optimized",
             representative_optimized["npc"]),
            ("minimum_construction_route_conductor_fixed", s15["npc"]),
            ("minimum_construction_route_conductor_optimized",
             s15_optimized["npc"]),
        ]:
            ablation_rows.append(dict(
                city=city, cluster=cluster, ablation=label, npc_jpy=value))
        if not representative_written and candidates[best_weight].number_of_edges():
            nx.write_edgelist(
                candidates[best_weight],
                f"{ROOT}/data/processed/{city}/s2_representative.edgelist",
                data=["length"])
            with open(
                    f"{ROOT}/data/processed/{city}/"
                    "s2_representative_metadata.json", "w",
                    encoding="utf-8") as handle:
                json.dump(dict(city=city, cluster=int(cluster),
                               selected_weight=best_weight), handle,
                          indent=2)
            representative_written = True
    results = pd.DataFrame(city_results)
    if results.empty:
        raise RuntimeError(f"{city}: no engineering-feasible clusters")
    expected_clusters = int(clusters.cluster.nunique())
    if len(results) != expected_clusters:
        raise RuntimeError(
            f"{city}: only {len(results)}/{expected_clusters} clusters "
            "passed; infeasible clusters cannot be excluded")
    results.to_csv(
        f"{ROOT}/data/processed/{city}/cluster_results.csv", index=False)
    scenario_rows.append(dict(
        city=city, clusters=len(results),
        total_demand_kw=results.demand_kw.sum(),
        transformer_sites=int(results.transformer_sites.sum()),
        transformer_units=int(results.transformer_units.sum()),
        s1_npc=results.s1_npc_mean.sum(), s15_npc=results.s15_npc.sum(),
        s2_npc=results.s2_npc.sum(), delta_npc=results.delta_npc.sum(),
        routing_policy_delta_npc=results.routing_policy_delta_npc.sum(),
        delta_npc_B=results.delta_npc_B.sum(),
        routing_policy_savings_pct=(
            100.0 * results.routing_policy_delta_npc.sum()
            / results.s1_npc_mean.sum()),
        combined_screening_savings_pct=(
            100.0 * results.delta_npc.sum()
            / results.s1_npc_mean.sum()),
        ltp_pct=100.0 * results.delta_npc.sum() / results.s1_npc_mean.sum(),
        ltpB_pct=100.0 * results.delta_npc_B.sum()
        / results.s1B_npc_mean.sum(),
        cluster_positive_fraction=float((results.delta_npc > 0).mean()),
        cluster_positive_fraction_B=float((results.delta_npc_B > 0).mean()),
        mean_edge_set_divergence=float(
            results.edge_set_divergence.mean()),
        mean_tld=float(results.edge_set_divergence.mean()),
        upsize_km=float(results.s2_upsize_m.sum() / 1000.0),
        max_mv_vdrop_pct=float(max(
            results.s1_vdrop_max.max(), results.s2_vdrop.max())),
        min_customer_voltage_pu=float(min(
            results.s1_customer_min_pu.min(),
            results.s2_customer_min_pu.min())),
        all_primary_networks_feasible=bool(
            results.all_primary_networks_feasible.all()),
        s1_plkw=results.s1_plkw_mean.sum(),
        s2_plkw=results.s2_plkw.sum()))
    print(scenario_rows[-1])

pd.DataFrame(scenario_rows).to_csv(
    f"{ROOT}/analysis/scenario_results.csv", index=False)
pd.DataFrame(diagnostic_rows).to_csv(
    f"{ROOT}/analysis/feasibility_diagnostics.csv", index=False)
pd.DataFrame(service_rows).to_csv(
    f"{ROOT}/analysis/transformer_service_units.csv", index=False)
pd.DataFrame(ablation_rows).to_csv(
    f"{ROOT}/analysis/ablation_results.csv", index=False)
pd.DataFrame(search_rows).to_csv(
    f"{ROOT}/analysis/candidate_search_summary.csv", index=False)
print("done")
