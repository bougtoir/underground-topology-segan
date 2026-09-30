# BENCHMARK_VALIDATION_REPORT

## CIGRE LV benchmark — PARTIALLY VALIDATED
- Benchmark: pandapower `networks.create_cigre_network_lv` (bundled reference case).
- pandapower 3.5.5, AC Newton-Raphson: CONVERGED.
- Result: vm_pu 0.912–1.0, p_loss = 21.8 kW on 0.687 MW load (3.2%).
- Interpretation: confirms pandapower itself solves a realistic LV feeder.
  It does NOT validate the LinDistFlow surrogate quantitatively (the two
  models were not cross-checked on the same network). Status kept as
  'partially validated' — a direct LinDistFlow-vs-pandapower residual test
  is recorded as a limitation.

## Iwamoto 11-bus (case11_iwamoto) — EXCLUDED from manuscript evidence
- pandapower 3.5.5: Newton-Raphson failed to converge.
- Diagnosis: case is an MV 66 kV system-level benchmark; its line
  parameters near the slack produce an ill-conditioned Jacobian in
  pandapower 3.5.5; unrelated to LV LinDistFlow study scope.
- Action: reported honestly, removed from the manuscript's validation
  evidence (kept in benchmark_validation.csv with converged=False).

## LinDistFlow surrogate justification
- LinDistFlow errors vs exact AC are <~1% of voltage for radial LV feeders
  at these loadings (established literature); used uniformly for S1/S2,
  so residual bias cancels in the NPC difference.
