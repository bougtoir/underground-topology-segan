# FINAL QC REPORT v3 — 2026-09-25T01:15:04.466556Z

## Phase status
- R0 v2 verification: PASS (37/37 checks, V2_HANDOFF_VERIFICATION.csv)
- R1 AC validation: PASS — 672 feeders, 0 non-converged, max |vm_ac-vm_lin| 0.0193 pu (tol 0.02),
  max loss rel err 0.226 (tol 0.25), feasibility agreement 1.000
- R2 assumption sensitivity: PASS — ENGINEERING_ASSUMPTION_SENSITIVITY.csv; MV-threshold is the
  only sign-flipping assumption (disclosed, estimand-scoped)
- R3 equivalence spec: FROZEN (1% margin, config/ECONOMIC_EQUIVALENCE_SPEC.yaml)
- R4 Kudamatsu mechanism: PASS — 5 clusters drive negative ΔNPC; capex artifact
- R5 counterfactual fairness: PASS — S1 excluded from S2 candidate set + mean-vs-single defect
- R6 estimand freeze: PASS — VoF >= 0 by construction, PRIMARY_ESTIMAND_SPEC.md
- R7 coverage: PASS — MV-served cancels; LV-modeled 75/55/53% of demand; degenerate zones included
- R8 robustness: PASS — rep24 stable; family ratio ~1.00
- R9 cost mechanism: PASS — capex-dominant regime; loss NPV ~1.77M JPY/kW makes ~0.1-0.3kW deltas irrelevant
- R10 DG: PASS — kept secondary; no PV rescue
- R11 novelty: PASS — NEGATIVE_RESULT_NOVELTY_MATRIX.csv
- R12 freeze: PASS — 185 values, manuscript_values_v3.csv
- R13 figures: PASS — v3_fig1-5, all cited in text
- R14 manuscript: PASS — manuscript_draft_v3.docx, 240-word abstract, 12 refs Vancouver order
- R15 this audit: all citable values machine-readable; no hardcoded results; no stale terminology (LTP/TLD absent)
- R16 journal adaptation: Elsevier genAI declaration present; single-anonymized; highlights <=85 chars
- R17 municipality outputs: municipality_v3/, planning-support framing only
- R18 reviewer gate: see audit_v2/REVIEWER_GATE.md — no unresolved HIGH
- R19 reproducibility: pipeline Makefile + tagged p06b/p07b env runs; all artifacts regenerate from scripts
