# FINAL_QC_REPORT v4

## Freeze check (F0)
18/18 frozen values match `analysis/manuscript_values_v3.csv`
(`analysis/FINAL_V3_VALUE_CHECK.csv`).

## Wording audit (F1/F5/F6)
- Removed: "near cost-minimal", "analysis effort is better spent on
  MV-level planning and PV integration", "sobering".
- "economically equivalent" always qualified by the pre-registered 1%
  margin; margin rationale (frozen before classification) now in Methods.
- Scope limited to LV renewal planning, modeled design space,
  reconstructed ensembles, three selected zones; MV-served demand
  exclusion and 75/55/53% LV coverage kept visible.

## Terminology (F2)
VoF = primary, ΔNPC = secondary naive contrast, TDD = edge-set distance.
No "LTP"/"TLD" strings remain in the manuscript (checked docx text).

## Estimand/Kudamatsu (F3)
VoF equation in Methods exactly matches implementation
(mean_r max(0, NPC(S1_r) − min(NPC(S1_r), NPC(S2)))); retain-S1
admissibility and nonnegativity explained. −10.1% retained only as the
secondary contrast with all five required disclosures.

## AC (F4)
672 feasible synthesized feeders, all converged; max vm deviation
0.0193 pu vs 0.02 tolerance; agreement 1.00; explicitly validates
synthesized models only. Iwamoto note in Supplement.

## References (F9)
12 crossref-verified refs; volume artifacts ("214.0", "22.0", "3.0",
"4.0") fixed; empty issues/pages handled; `&amp;` unescaped;
double-period author endings fixed; citation order = appearance order
(Vancouver); every ref cited.

## Figures/tables (F10)
4 main figures (PNG, 300 dpi) + Supplementary Figure S1. Fig3: VoF
primary bars + MC mean of secondary ΔNPC. Fig4: ΔNPC bars vs VoF dots,
1% band shaded. Table 2 v4: primary/secondary-labeled columns, no
machine labels.

## DOCX (F11)
Native OMML equations (4). No replacement chars, no full-width/CJK
chars, no LaTeX literals in visible text. Abstract 249/250 words.

## Compliance (F13)
SEGAN guide re-verified 2026-09-25: abstract ≤250, highlights 3–5 ×≤85
chars (separate editable file), keywords, title page, separate-figure
submission, supplement, AI-use declaration, data/code availability.

## Reviewer gate (F16)
audit_v2/REVIEWER_GATE_v4.md — no unresolved HIGH/MEDIUM.

## Reproducibility (F17)
FINAL_REPRODUCIBILITY_REPORT.md — clean-room fresh-venv rerun
bit-exact.
