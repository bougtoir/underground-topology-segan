# REVIEWER GATE v4 (Phase F16) — four independent reviewers

## Reviewer 1 — Distribution-system engineer
- VoF logically coherent? YES: retain-S1 admissible inside the redesign
  set ⇒ nonnegative by construction; measures option value, not forced
  redesign. Text now defines it before ΔNPC (Methods).
- AC claims calibrated? YES: 672 feasible synthesized feeders, all
  converged, max vm err 0.0193 pu vs pre-specified 0.02, agreement 1.00;
  explicitly scoped to synthesized models, not real topology. Iwamoto
  non-convergence moved to Supplement.
- LV/MV scope honest? YES: 75/55/53% LV-modeled demand; MV-served demand
  excluded by design and cancels in contrasts; stated in Results and
  Limitations.
- Issues: none HIGH. MEDIUM (fixed): abstract previously implied
  incumbents "near cost-minimal" — reworded to reconstructed-layouts
  equivalence.

## Reviewer 2 — Optimization / OR
- Estimand design sound? YES: VoF vs forced ΔNPC distinction explicit;
  ensemble-mean-vs-single-candidate asymmetry disclosed.
- Is 1% equivalence margin justified? YES: frozen in
  config/ECONOMIC_EQUIVALENCE_SPEC.yaml before classification; rationale
  from model resolution (±30% capex, surrogate error, unit-price
  variation), now stated in Methods.
- Kudamatsu unambiguous? YES: -10.1% labeled secondary/naive; 5 audit
  conditions stated; never called an economic penalty of offering
  redesign.
- Issues: none HIGH. MEDIUM (fixed): Fig4 previously showed only ΔNPC
  ranges — now overlays primary VoF (dots) vs ΔNPC (bars) with the 1%
  band shaded.

## Reviewer 3 — SEGAN editor / scope
- Fit: distribution planning + grid modernization + engineering
  constraints — in scope.
- Bounded/negative result informative enough? YES: transferable
  methodological contribution (feasibility gating + estimand design can
  manufacture or erase apparent benefits); cover letter sells method,
  not savings.
- Compliance: abstract 249 ≤250; highlights 5×≤85 chars; keywords;
  separate-figure captions; AI declaration; data/code availability;
  supplement separated. Title page present.
- Issues: none HIGH. MEDIUM (fixed): conclusion previously prescribed
  MV/PV reallocation of effort — now restrained suggestion.

## Reviewer 4 — Reproducibility / data integrity
- Numbers traceable? YES: all from analysis/manuscript_values_v3.csv +
  named CSVs; FINAL_V3_VALUE_CHECK.csv passes 18/18.
- Clean-room? YES: fresh venv + /tmp copy reproduces scenario results
  bit-exact (FINAL_REPRODUCIBILITY_REPORT.md).
- Provenance: source_registry.csv checksums; reconstructed never called
  observed.
- Issues: none HIGH/MEDIUM open.

## Verdict
No unresolved HIGH or MEDIUM. SUBMISSION-READY candidate pending
author-completed title page fields and optional graphical abstract.
