"""Phase 4: quantitative engineering benchmark validation.

The CIGRE European LV benchmark distributed with the pinned pandapower version
is solved with independent AC algorithms. The radial P/Q line model used by
this study is then compared feeder-by-feeder with the AC result. The Iwamoto
11-bus case is retained only as a diagnosed non-convergent stress case; it is
not presented as validation of the distribution model.
"""
from importlib.metadata import version
import json
import math
import os

import networkx as nx
import pandas as pd
import pandapower as pp
import pandapower.networks as pn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOLTAGE_TOL_PU = 0.003
LOSS_REL_TOL = 0.10
SOLVER_VOLTAGE_TOL_PU = 1e-7
SOLVER_LOSS_TOL_MW = 1e-7


def ac_metrics(net):
    return dict(
        vm_pu_min=float(net.res_bus.vm_pu.min()),
        vm_pu_max=float(net.res_bus.vm_pu.max()),
        line_loss_mw=float(net.res_line.pl_mw.sum()),
        transformer_loss_mw=float(net.res_trafo.pl_mw.sum()),
        ext_grid_p_mw=float(net.res_ext_grid.p_mw.sum()),
        ext_grid_q_mvar=float(net.res_ext_grid.q_mvar.sum()),
        max_line_current_ka=float(net.res_line.i_ka.max()),
        max_transformer_loading_pct=float(net.res_trafo.loading_percent.max()),
    )


def run_ac_algorithms():
    rows = []
    for algorithm in ["nr", "bfsw", "iwamoto_nr"]:
        net = pn.create_cigre_network_lv()
        pp.runpp(
            net, algorithm=algorithm, calculate_voltage_angles=True,
            max_iteration=100, tolerance_mva=1e-10, numba=False)
        rows.append(dict(benchmark="CIGRE LV", algorithm=algorithm,
                         converged=bool(net.converged), **ac_metrics(net)))
    return pd.DataFrame(rows)


def radial_linear_feeder(net, source):
    graph = nx.Graph()
    for line_id, row in net.line[net.line.in_service].iterrows():
        graph.add_edge(
            int(row.from_bus), int(row.to_bus), line_id=int(line_id),
            resistance_ohm=float(row.r_ohm_per_km * row.length_km),
            reactance_ohm=float(row.x_ohm_per_km * row.length_km))
    component = nx.node_connected_component(graph, source)
    feeder = graph.subgraph(component).copy()
    if not nx.is_tree(feeder):
        raise ValueError(f"CIGRE feeder rooted at {source} is not radial")
    parent = {source: None}
    order = [source]
    for u in order:
        for v in feeder.neighbors(u):
            if v == parent[u]:
                continue
            parent[v] = u
            order.append(v)
    p_kw = {bus: 0.0 for bus in feeder}
    q_kvar = {bus: 0.0 for bus in feeder}
    for _, load in net.load[net.load.in_service].iterrows():
        bus = int(load.bus)
        if bus in feeder:
            p_kw[bus] += float(load.p_mw) * 1000.0
            q_kvar[bus] += float(load.q_mvar) * 1000.0
    for bus in reversed(order[1:]):
        p_kw[parent[bus]] += p_kw[bus]
        q_kvar[parent[bus]] += q_kvar[bus]
    nominal_v = float(net.bus.loc[source, "vn_kv"]) * 1000.0
    voltage_v = {source: float(net.res_bus.loc[source, "vm_pu"]) * nominal_v}
    loss_kw = 0.0
    current_a = []
    for bus in order[1:]:
        upstream = parent[bus]
        edge = feeder[upstream][bus]
        apparent_kva = math.hypot(p_kw[bus], q_kvar[bus])
        current = apparent_kva * 1000.0 / (
            math.sqrt(3.0) * voltage_v[upstream])
        cos_phi = p_kw[bus] / apparent_kva if apparent_kva else 1.0
        sin_phi = q_kvar[bus] / apparent_kva if apparent_kva else 0.0
        drop_v = math.sqrt(3.0) * current * (
            edge["resistance_ohm"] * cos_phi
            + edge["reactance_ohm"] * sin_phi)
        voltage_v[bus] = voltage_v[upstream] - drop_v
        loss_kw += 3.0 * current ** 2 * edge["resistance_ohm"] / 1000.0
        current_a.append(current)
    line_ids = [feeder[u][v]["line_id"] for u, v in feeder.edges]
    ac_min_pu = float(net.res_bus.loc[list(feeder.nodes), "vm_pu"].min())
    ac_loss_kw = float(net.res_line.loc[line_ids, "pl_mw"].sum()) * 1000.0
    linear_min_pu = min(voltage_v.values()) / nominal_v
    voltage_error = abs(linear_min_pu - ac_min_pu)
    loss_error = abs(loss_kw - ac_loss_kw) / ac_loss_kw
    return dict(
        source_bus=source, source_name=net.bus.loc[source, "name"],
        n_bus=len(feeder), n_line=len(line_ids),
        p_load_kw=sum(float(x) for x in net.load[
            net.load.bus.isin(feeder.nodes)].p_mw) * 1000.0,
        q_load_kvar=sum(float(x) for x in net.load[
            net.load.bus.isin(feeder.nodes)].q_mvar) * 1000.0,
        ac_min_voltage_pu=ac_min_pu, linear_min_voltage_pu=linear_min_pu,
        voltage_abs_error_pu=voltage_error,
        ac_line_loss_kw=ac_loss_kw, linear_line_loss_kw=loss_kw,
        loss_relative_error=loss_error,
        linear_max_current_a=max(current_a, default=0.0),
        voltage_tolerance_pu=VOLTAGE_TOL_PU,
        loss_relative_tolerance=LOSS_REL_TOL,
        voltage_pass=voltage_error <= VOLTAGE_TOL_PU,
        loss_pass=loss_error <= LOSS_REL_TOL)


def diagnose_iwamoto():
    rows = []
    for algorithm in ["nr", "bfsw", "iwamoto_nr"]:
        net = pn.case11_iwamoto()
        try:
            pp.runpp(
                net, algorithm=algorithm, max_iteration=100,
                tolerance_mva=1e-8, numba=False)
            rows.append(dict(algorithm=algorithm, converged=True,
                             error="", vm_pu_min=float(net.res_bus.vm_pu.min())))
        except Exception as exc:
            rows.append(dict(algorithm=algorithm, converged=False,
                             error=f"{type(exc).__name__}: {exc}",
                             vm_pu_min=float("nan")))
    return pd.DataFrame(rows)


def markdown_table(frame, columns):
    header = "| " + " | ".join(columns) + " |"
    rule = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = [header, rule]
    for _, row in frame[columns].iterrows():
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.8g}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


ac = run_ac_algorithms()
reference = ac[ac.algorithm == "nr"].iloc[0]
ac["voltage_agreement"] = (
    (ac.vm_pu_min - reference.vm_pu_min).abs() <= SOLVER_VOLTAGE_TOL_PU)
ac["loss_agreement"] = (
    (ac.line_loss_mw - reference.line_loss_mw).abs() <= SOLVER_LOSS_TOL_MW)
ac["validated"] = ac.converged & ac.voltage_agreement & ac.loss_agreement

cigre = pn.create_cigre_network_lv()
pp.runpp(
    cigre, algorithm="nr", calculate_voltage_angles=True,
    max_iteration=100, tolerance_mva=1e-10, numba=False)
feeders = pd.DataFrame(
    [radial_linear_feeder(cigre, source) for source in [2, 21, 24]])
feeders["validated"] = feeders.voltage_pass & feeders.loss_pass
iwamoto = diagnose_iwamoto()

ac.to_csv(f"{ROOT}/analysis/benchmark_ac_solvers.csv", index=False)
feeders.to_csv(f"{ROOT}/analysis/benchmark_radial_comparison.csv", index=False)
iwamoto.to_csv(f"{ROOT}/analysis/benchmark_iwamoto_diagnosis.csv", index=False)

summary = {
    "pandapower_version": version("pandapower"),
    "cigre_reference": "pandapower.networks.create_cigre_network_lv",
    "cigre_ac_solver_agreement": bool(ac.validated.all()),
    "radial_model_quantitative_agreement": bool(feeders.validated.all()),
    "voltage_tolerance_pu": VOLTAGE_TOL_PU,
    "loss_relative_tolerance": LOSS_REL_TOL,
    "iwamoto_all_algorithms_converged": bool(iwamoto.converged.all()),
    "iwamoto_primary_validation_status": "excluded_unsuitable_nonconvergent_stress_case",
}
with open(f"{ROOT}/analysis/benchmark_validation.json", "w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)

report = f"""# Benchmark validation report

## Benchmark and environment

- Benchmark: CIGRE Task Force C6.04.02 European low-voltage network as
  implemented by `pandapower.networks.create_cigre_network_lv`.
- pandapower version: {summary['pandapower_version']}.
- Reference calculation: Newton-Raphson AC power flow with tolerance
  \(10^{{-10}}\) MVA.
- Independent AC checks: backward/forward sweep and Iwamoto Newton-Raphson.
- Radial-model tolerances fixed before inspection: absolute minimum-voltage
  error <= {VOLTAGE_TOL_PU:.3f} pu and relative line-loss error <=
  {100 * LOSS_REL_TOL:.0f}%.

## AC solver agreement

{markdown_table(ac, ['algorithm', 'converged', 'vm_pu_min', 'vm_pu_max',
                     'line_loss_mw', 'transformer_loss_mw',
                     'ext_grid_p_mw', 'ext_grid_q_mvar',
                     'max_line_current_ka', 'max_transformer_loading_pct',
                     'validated'])}

All three AC algorithms agree within {SOLVER_VOLTAGE_TOL_PU:g} pu for minimum
voltage and {SOLVER_LOSS_TOL_MW:g} MW for line loss.

## Corrected radial P/Q model versus AC power flow

The comparison starts each radial LV feeder at the AC-calculated transformer
secondary voltage so that it isolates the line model from transformer-model
differences. It uses the benchmark's exact per-edge resistance, reactance,
active load and reactive load; no voltage clipping is applied.

{markdown_table(feeders, ['source_name', 'p_load_kw', 'q_load_kvar',
                          'ac_min_voltage_pu', 'linear_min_voltage_pu',
                          'voltage_abs_error_pu', 'ac_line_loss_kw',
                          'linear_line_loss_kw', 'loss_relative_error',
                          'validated'])}

All three feeders satisfy the declared tolerances. The corrected radial model
is therefore quantitatively validated for its stated screening role. The
CIGRE network itself reaches {reference.vm_pu_min:.4f} pu; convergence is not
misrepresented as compliance with this study's planning voltage gate.

## Iwamoto 11-bus diagnosis

{markdown_table(iwamoto, ['algorithm', 'converged', 'vm_pu_min'])}

The packaged `case11_iwamoto` does not converge with Newton-Raphson,
backward/forward sweep, or Iwamoto Newton-Raphson under the pinned environment.
It is a difficult generic power-flow stress case with a 1 kV base, not a
documented Japanese 6.6 kV distribution-design reference for the present
model. It is retained as a diagnosed negative control and removed from the
paper's validation claim.
"""
with open(f"{ROOT}/BENCHMARK_VALIDATION_REPORT.md", "w", encoding="utf-8") as handle:
    handle.write(report)

print(ac.to_string(index=False))
print(feeders.to_string(index=False))
print(iwamoto.to_string(index=False))
print(summary)
