# R5 — counterfactual / optimizer fairness audit

## Defect found
v2's S2 = min-NPC over the weighted-Steiner candidate set ONLY. The
candidate set does NOT contain the S1 reconstructed trees. Worse, the S1
benchmark is the mean over 12 reconstruction replicates while S2 is a
single candidate — so "DeltaNPC = NPC(S1 mean) - NPC(S2 best)" compares
an ensemble mean to a single tree and can legitimately go negative.

Logically, if the scientific question is "value of allowing redesign",
the feasible set must include retain-S1, giving VoF >= 0 by
construction. Kudamatsu -10.3% therefore measures FORCED redesign vs the
ensemble mean — a different estimand, not evidence that redesign
destroys value.

Also audited for fairness: identical demands (coincident), transformer
capex, sources, conductor menu, cost rules, and constraints applied to
both arms — no asymmetry besides the candidate-set defect above.

## Resolution (frozen in PRIMARY_ESTIMAND_SPEC.md)
Primary estimand: VoF = mean_reps max(0, NPC(rep) - NPC(best S2)),
nonnegative by construction. Forced-redesign DeltaNPC retained as a
secondary mechanistic result. Both reported per city in v3 outputs.
