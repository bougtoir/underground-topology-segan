# Decision Log — Beyond Like-for-Like Undergrounding

Format: `YYYY-MM-DD | phase | decision | rationale | status`

2026-09-24 | P0 | Project root `underground_topology_segan/` inside bougtoir/wip | Matches workspace convention for paper pipelines | active
2026-09-24 | P0 | Python 3.10 venv `.venv`; deps in requirements.lock.txt | Reproducibility without commercial software | active
2026-09-24 | P0 | Primary NPC horizon = 40 yr | Japanese civil works life-cycle convention; 30/50 in sensitivity | frozen
2026-09-24 | P0 | TLD primary = unweighted edge symmetric-difference (1 - |E_C ∩ E_L|/|E_C ∪ E_L|) | Prompt default; weighted variants in sensitivity | frozen
2026-09-24 | P4 | case11_iwamoto failed AC convergence in pandapower 3.5.5 -> kept as documented non-converging benchmark; cigre_lv used as convergent validation benchmark; Japanese feeder topology built from municipal/OSM data instead | honest-failure logged

## Forensic reanalysis (v2) — key decisions
- 29–38% voltage drop diagnosed STRUCTURAL: 350 kW undiversified LV clusters on 415 V (see audit_v2/VOLTAGE_ROOT_CAUSE_AUDIT.md).
- ENGINEERING_FEASIBILITY_SPEC.yaml frozen BEFORE corrected runs: coincidence 0.6, MV threshold 150 kW, cluster target 100 kW, 150 kVA transformer, ampacity + 6% vdrop + radiality gates.
- Corrected result: ΔNPC +0.02% (Sano), -10.3% (Kudamatsu), +0.21% (Yasu); MC P(ΔNPC>0) = 1.00/0.00/1.00. Conductor sizing ≈0 effect.
- Terminology: LTP→"life-cycle renewal benefit (ΔNPC)"; TLD→"topology divergence distance (TDD)".
- Kudamatsu result is robustly negative; paper reframed as negative/cautionary finding. No manuscript language references earlier versions.
- Ross reference completed: Wiley book, DOI 10.1002/9781119125204.
- DeepL/language pass: no external API used; language QC manual (recorded as unavailable).

## v3 negative-result consolidation (R0-R21) — 2026-09-25
- R0: v2 verified 37/37. R1: LinDistFlow validated vs pandapower AC on all 672 feasible feeders
  (max vm err 0.0193 pu, feasibility agreement 1.00) — primary calcs kept.
- R5/R6: negative ΔNPC traced to estimand defect (S1 not in S2 candidate set; mean-vs-single).
  Froze PRIMARY_ESTIMAND_SPEC.md: VoF = mean_r max(0, NPC_r - NPC_bestS2) >= 0.
- R7: degenerate single-customer zones included (S1=S2, delta=0); LV-modeled share = 75/55/53%,
  MV-served cancels by design.
- R2/R8: coincidence & cluster-size robust; MV threshold moves ΔNPC (not VoF ordering) — disclosed.
- R4: Kudamatsu -10% = 5 clusters with 2-10x rewiring capex; not generalized.
- R12-R14: VoF primary results 0.01%/0.39%/0.20% — all economically_equivalent (1% margin frozen).
  Manuscript rewritten (240-word abstract), figures v3, package SEGAN_submission_package_FINAL_v3.zip.
