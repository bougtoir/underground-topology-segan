# Phase R6 — frozen primary estimand

Question: "What is the value of ALLOWING topology redesign during
undergrounding renewal?"

Primary estimand (per cluster, per municipality aggregate):
  VoF = mean_over_reps[ max(0, NPC(rep_S1) - NPC(best feasible S2)) ]

i.e., the feasible S2 candidate set ALWAYS includes the S1 legacy option
(retain-S1 is admissible), so VoF >= 0 by construction. This is the
value-of-flexibility estimand.

Secondary (mechanistic) estimand — FORCED redesign:
  DeltaNPC_forced = NPC(S1) - NPC(best feasible S2 excluding S1)
which CAN be negative; reported to explain why forced rerouting can be
costlier. Kudamatsu's v2 -10.3% is a forced-redesign value, not a value
of flexibility.
