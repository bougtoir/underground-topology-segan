# REVIEWER GATE v3 — 2026-09-25T01:15:04.466556Z

Hostile-reviewer findings adjudication:

1. "Negative result contradicts optimizer logic" — RESOLVED: R5 audit shows ΔNPC<0 arises because
   the S2 candidate set excludes S1 and compares an ensemble mean to single candidates.
   Primary estimand VoF >= 0 by construction; reported as the headline.
2. "-10% generalized without mechanism" — RESOLVED: KUDAMATSU_MECHANISM_AUDIT.md decomposes the
   contrast to 5 clusters with 2-10x rewiring capex; not robust to MV threshold (mv200 flips sign).
3. "LinDistFlow unvalidated" — RESOLVED: AC power-flow validation on all 672 feasible feeders,
   all pre-specified tolerances met (AC_VALIDATION_REPORT.md).
4. "30% demand unmodeled" — RESOLVED: degenerate single-customer zones included (S1=S2, delta=0);
   MV-served demand excluded by design and cancels; coverage audit quantifies LV share.
5. "Engineering assumptions arbitrary" — PARTIALLY OPEN (documented): coincidence 0.6, LV/MV 150kW,
   cluster 100kW are spec-frozen assumptions; sensitivity table shows VoF ordering robust,
   ΔNPC sign NOT robust to MV threshold — disclosed in manuscript and abstract.
6. "PV rescues the paper" — RESOLVED: DG kept strictly secondary.
No unresolved HIGH findings.
