"""Auditable radial MV/LV engineering calculations for the SEGAN reanalysis."""
from dataclasses import dataclass
import math

import networkx as nx
import pandas as pd
import yaml


@dataclass(frozen=True)
class Cable:
    tier: str
    area_mm2: int
    r_ohm_per_km: float
    x_ohm_per_km: float
    ampacity_a: float


@dataclass(frozen=True)
class Transformer:
    rating_kva: int
    no_load_loss_w: float
    load_loss_w: float
    impedance_pct: float
    regulation_pct: float


def load_spec(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_catalogs(root, spec, frequency_hz=None):
    cable_df = pd.read_csv(f"{root}/{spec['conductors']['catalog']}")
    tr_df = pd.read_csv(f"{root}/{spec['transformers']['catalog']}")
    tr_cfg = spec["transformers"]
    tr_df = tr_df[
        (tr_df["phases"] == tr_cfg["phases"])
        & (tr_df["freq_hz"] == (
            spec["system"]["frequency_hz"] if frequency_hz is None else frequency_hz))
        & (tr_df["secondary_v"].astype(str) == str(tr_cfg["secondary_v"]))
        & (tr_df["rating_kva"].isin(tr_cfg["allowed_ratings_kva"]))
    ].copy()
    return cable_df, tr_df


def cable(catalog, tier, area_mm2, spec):
    row = catalog[(catalog.tier == tier) & (catalog.area_mm2 == area_mm2)]
    if len(row) != 1:
        raise ValueError(f"no unique {tier} {area_mm2} mm2 cable")
    r = row.iloc[0]
    return Cable(tier=tier, area_mm2=int(area_mm2),
                 r_ohm_per_km=float(r.r90_ohm_per_km),
                 x_ohm_per_km=float(r.x_ohm_per_km),
                 ampacity_a=float(r.ampacity_air40_a)
                 * float(spec["thermal_gates"]["ampacity_derating_duct"]))


def transformer(catalog, rating_kva):
    row = catalog[catalog.rating_kva == rating_kva].sort_values("load_loss_w")
    if row.empty:
        raise ValueError(f"no transformer {rating_kva} kVA")
    r = row.iloc[0]
    return Transformer(rating_kva=int(rating_kva),
                       no_load_loss_w=float(r.no_load_loss_w),
                       load_loss_w=float(r.load_loss_w),
                       impedance_pct=float(r.impedance_pct),
                       regulation_pct=float(r.regulation_pct))


def choose_transformer(catalog, load_kw, pf, design_loading_pct):
    required = load_kw / pf / (design_loading_pct / 100.0)
    available = sorted(int(v) for v in catalog.rating_kva.unique())
    for kva in available:
        if kva + 1e-9 >= required:
            return transformer(catalog, kva)
    raise ValueError(f"load {load_kw:.3f} kW requires {required:.3f} kVA; no unit")


def transformer_drop_pct(tr, load_kw, pf):
    """Approximate transformer drop from catalogue regulation and %Z.

    Catalogue regulation is measured at pf=1. We derive R%=regulation%, then
    X%=sqrt(Z%^2-R%^2), and apply R%*pf+X%*sin(phi), scaled by kVA loading.
    """
    s_kva = load_kw / pf
    loading = s_kva / tr.rating_kva
    r_pct = min(tr.regulation_pct, tr.impedance_pct)
    x_pct = math.sqrt(max(tr.impedance_pct ** 2 - r_pct ** 2, 0.0))
    return loading * (r_pct * pf + x_pct * math.sqrt(1.0 - pf ** 2))


def transformer_peak_loss_kw(tr, load_kw, pf):
    loading = load_kw / pf / tr.rating_kva
    return (tr.no_load_loss_w + tr.load_loss_w * loading ** 2) / 1000.0


def validate_radial_tree(graph, source, demands_kw):
    demand_nodes = [n for n, p in demands_kw.items() if p > 0]
    if source not in graph:
        return ["source_missing"]
    if graph.number_of_nodes() == 0 or not nx.is_connected(graph):
        return ["not_connected"]
    if graph.number_of_edges() != graph.number_of_nodes() - 1:
        return ["not_radial"]
    missing = sorted(set(demand_nodes) - set(graph.nodes))
    return [f"demand_missing:{','.join(missing)}"] if missing else []


def downstream_power(graph, source, demands_kw):
    parent = {source: None}
    order = [source]
    for u in order:
        for v in graph.neighbors(u):
            if v == parent[u]:
                continue
            if v in parent:
                raise ValueError("graph is not radial")
            parent[v] = u
            order.append(v)
    p_kw = {n: float(demands_kw.get(n, 0.0)) for n in graph.nodes}
    for n in reversed(order[1:]):
        p_kw[parent[n]] += p_kw[n]
    return parent, order, p_kw


def radial_power_flow(graph, source, demands_kw, system_v_ll, pf,
                      area_by_edge, cable_catalog, spec, tier):
    """Iterative radial P/Q flow including conductor losses.

    MV uses a balanced three-phase line-line model. LV uses the configured
    single-phase 210-105 V three-wire equivalent represented on the 210 V
    outer-conductor base.
    """
    issues = validate_radial_tree(graph, source, demands_kw)
    if issues:
        return {"feasible": False, "issues": issues}
    parent, order, _ = downstream_power(graph, source, demands_kw)
    q_factor = math.tan(math.acos(pf))
    phases = int(spec["system"]["mv_phases"] if tier == "MV"
                 else spec["system"]["lv_phases"])
    if phases not in (1, 3):
        raise ValueError(f"unsupported phase count: {phases}")
    edge_p_loss = {tuple(sorted(edge)): 0.0 for edge in graph.edges}
    edge_q_loss = {tuple(sorted(edge)): 0.0 for edge in graph.edges}
    converged = False
    edge_rows = []
    v_ll = {}
    p_down = {}
    q_down = {}
    for _ in range(100):
        p_down = {node: float(demands_kw.get(node, 0.0))
                  for node in graph.nodes}
        q_down = {node: float(demands_kw.get(node, 0.0)) * q_factor
                  for node in graph.nodes}
        for node in reversed(order[1:]):
            upstream = parent[node]
            edge = tuple(sorted((upstream, node)))
            p_down[upstream] += p_down[node] + edge_p_loss[edge]
            q_down[upstream] += q_down[node] + edge_q_loss[edge]
        v_ll = {source: float(system_v_ll)}
        next_p_loss = {}
        next_q_loss = {}
        edge_rows = []
        for node in order[1:]:
            upstream = parent[node]
            edge = tuple(sorted((upstream, node)))
            area = int(area_by_edge[edge])
            cab = cable(cable_catalog, tier, area, spec)
            length_km = float(graph[upstream][node]["length"]) / 1000.0
            p_kw = p_down[node] + edge_p_loss[edge]
            q_kvar = q_down[node] + edge_q_loss[edge]
            s_kva = math.hypot(p_kw, q_kvar)
            divisor = (math.sqrt(3.0) if phases == 3 else 1.0)
            current_a = s_kva * 1000.0 / (
                divisor * max(v_ll[upstream], 1e-12))
            loading_pct = 100.0 * current_a / cab.ampacity_a
            r = cab.r_ohm_per_km * length_km
            x = cab.x_ohm_per_km * length_km
            cos_phi = p_kw / max(s_kva, 1e-12)
            sin_phi = q_kvar / max(s_kva, 1e-12)
            drop_multiplier = math.sqrt(3.0) if phases == 3 else 2.0
            drop_v = drop_multiplier * current_a * (
                r * cos_phi + x * sin_phi)
            v_ll[node] = v_ll[upstream] - drop_v
            loss_multiplier = 3.0 if phases == 3 else 2.0
            loss_kw = loss_multiplier * current_a ** 2 * r / 1000.0
            loss_kvar = loss_multiplier * current_a ** 2 * x / 1000.0
            next_p_loss[edge] = loss_kw
            next_q_loss[edge] = loss_kvar
            edge_rows.append(dict(
                u=upstream, v=node, area_mm2=area,
                length_m=length_km * 1000.0, p_kw=p_kw, q_kvar=q_kvar,
                current_a=current_a, loading_pct=loading_pct, drop_v=drop_v,
                receiving_v=v_ll[node], peak_loss_kw=loss_kw,
                reactive_loss_kvar=loss_kvar))
        change = max(
            [abs(next_p_loss[edge] - edge_p_loss[edge])
             for edge in edge_p_loss] + [0.0])
        edge_p_loss = next_p_loss
        edge_q_loss = next_q_loss
        if change <= 1e-9:
            converged = True
            break
    max_loading = max(
        [row["loading_pct"] for row in edge_rows] + [0.0])
    peak_loss_kw = sum(edge_p_loss.values())
    thermal = spec["thermal_gates"]
    min_v = min(v_ll.values())
    drop_pct = 100.0 * (system_v_ll - min_v) / system_v_ll
    voltage_gate = (spec["voltage_gates"]["mv_drop_max_pct"] if tier == "MV"
                    else spec["voltage_gates"]["lv_drop_max_pct"])
    issues = []
    if not converged:
        issues.append(f"{tier.lower()}_power_flow_nonconvergence")
    if drop_pct > voltage_gate + 1e-9:
        issues.append(f"{tier.lower()}_drop:{drop_pct:.6g}>{voltage_gate}")
    if max_loading > thermal["max_cable_loading_pct"] + 1e-9:
        issues.append(f"{tier.lower()}_thermal:{max_loading:.6g}>"
                      f"{thermal['max_cable_loading_pct']}")
    source_input_kw = sum(demands_kw.values()) + peak_loss_kw
    source_input_kvar = (
        sum(demands_kw.values()) * q_factor + sum(edge_q_loss.values()))
    power_balance_kw = abs(
        source_input_kw - sum(demands_kw.values()) - peak_loss_kw)
    return dict(feasible=not issues, issues=issues, min_voltage_v=min_v,
                drop_pct=drop_pct, max_loading_pct=max_loading,
                peak_loss_kw=peak_loss_kw, voltages_v=v_ll,
                edge_results=pd.DataFrame(edge_rows),
                source_input_kw=source_input_kw,
                source_input_kvar=source_input_kvar,
                reactive_loss_kvar=sum(edge_q_loss.values()),
                power_balance_kw=power_balance_kw)


def size_tree_conductors(graph, source, demands_kw, tier, candidates,
                         system_v_ll, pf, cable_catalog, spec,
                         optimize=True, objective=None):
    """Select the smallest thermally feasible conductor, then upsize until
    the complete tree passes voltage and thermal gates.
    """
    parent, order, p_down = downstream_power(graph, source, demands_kw)
    q_factor = math.tan(math.acos(pf))
    areas = {}
    for v in order[1:]:
        u = parent[v]
        edge = tuple(sorted((u, v)))
        if not optimize:
            areas[edge] = int(spec["conductors"][f"{tier.lower()}_reference_area_mm2"])
            continue
        current = math.hypot(p_down[v], p_down[v] * q_factor) * 1000.0 / (
            math.sqrt(3.0) * system_v_ll)
        target = spec["thermal_gates"]["design_cable_loading_pct"] / 100.0
        feasible = [a for a in candidates
                    if current <= cable(cable_catalog, tier, a, spec).ampacity_a * target]
        if not feasible:
            return None, {"feasible": False,
                          "issues": [f"{tier.lower()}_no_thermal_size:{current:.6g}A"]}
        areas[edge] = min(feasible)
    # Greedy global upsizing of the edge with the largest drop contribution.
    for _ in range(len(areas) * len(candidates) + 1):
        result = radial_power_flow(graph, source, demands_kw, system_v_ll, pf,
                                   areas, cable_catalog, spec, tier)
        if result["feasible"]:
            if objective is None:
                return areas, result
            break
        if not optimize or result["edge_results"].empty:
            return areas, result
        edge_results = result["edge_results"].sort_values("drop_v", ascending=False)
        changed = False
        for _, r in edge_results.iterrows():
            edge = tuple(sorted((r.u, r.v)))
            current_area = areas[edge]
            bigger = [a for a in candidates if a > current_area]
            if bigger:
                areas[edge] = min(bigger)
                changed = True
                break
        if not changed:
            return areas, result
    else:
        raise RuntimeError("conductor sizing iteration exceeded bound")

    current_score = objective(areas, result)
    for _ in range(len(areas) * max(len(candidates) - 1, 1)):
        best = None
        for edge, current_area in sorted(areas.items()):
            bigger = [area for area in candidates if area > current_area]
            if not bigger:
                continue
            trial_areas = dict(areas)
            trial_areas[edge] = min(bigger)
            trial = radial_power_flow(
                graph, source, demands_kw, system_v_ll, pf, trial_areas,
                cable_catalog, spec, tier)
            if not trial["feasible"]:
                continue
            score = objective(trial_areas, trial)
            if score < current_score - 1e-6 and (
                    best is None or score < best[0]):
                best = (score, trial_areas, trial)
        if best is None:
            return areas, result
        current_score, areas, result = best
    return areas, result


def loss_factor(load_factor):
    return 0.3 * load_factor + 0.7 * load_factor ** 2
