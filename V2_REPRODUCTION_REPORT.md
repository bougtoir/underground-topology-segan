# R0 — V2 reproduction report

All FINAL_HANDOFF_v2 headline values independently recomputed from stored
cluster-level outputs (V2_HANDOFF_VERIFICATION.csv, 37/37 checks pass):

- Feasible clusters: 185/210 Sano, 69/77 Kudamatsu, 82/84 Yasu.
- Max voltage drop after correction: 2.50 / 4.93 / 1.76 %, all ≤6% gate.
- Demand coverage: 70 / 89 / 85 % of LV-modeled demand.
- ΔNPC: +0.017% (Sano), −10.26% (Kudamatsu), +0.21% (Yasu), recomputed
  from feasible-cluster sums.
- MC P(ΔNPC>0) = 1.00 / 0.00 / 1.00 (sensitivity_mc_v2.csv).
- Conductor upsizing ≈ 0 km; figures v2_fig1..5 and package zip present.

v2 canonical state confirmed reproducible from stored outputs.
