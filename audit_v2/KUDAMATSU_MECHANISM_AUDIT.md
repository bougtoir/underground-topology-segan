# Kudamatsu mechanism audit (R4)

Question: why is delta_npc (S1-S2) NEGATIVE in kudamatsu (-10.1% of S1 NPC) while ~0 elsewhere?

## Answer (machine-readable evidence: analysis/BENEFIT_DECOMPOSITION.csv)
- In kudamatsu the best S2 candidate has HIGHER capex than the S1 ensemble mean
  (s2_capex 3.464 bn vs s1 3.117 bn JPY)
  and essentially NO compensating loss reduction (pl_kw 22.0 vs 21.7 kW).
- The deficit is concentrated: 5 clusters (27,59,62,53,99) contribute ~-848 M JPY of the -468 M net,
  while the remaining clusters net +380 M. These are small wide-area clusters where
  ANY rewiring costs far more than the reconstructed existing corridor (s2 capex 2-10x s1) and
  conductor/loss gains are ~0.
- Mechanism: in kudamatsu the existing corridor set is already close to cost-minimal;
  every Steiner-tree candidate requires expensive new trenching. Optimization still
  'chooses' them because npc_value prices conductor upsize + trenching vs loss savings,
  and candidate trees only win on topology, not on the binding cost term.
- Fairness note (R5): S1 trees are NOT in the S2 candidate set and s1 is an ensemble mean
  vs a single s2 candidate - so delta_npc<0 is an estimand artifact, not irrationality.
  Under the frozen VoF estimand (retain-S1 admissible) kudamatsu VoF = +0.39% (>=0), i.e.
  the optimizer correctly finds near-zero upgradeable value, not negative value.
- Cross-check vs sensitivity: the negative delta inverts at mv200 (+0.27%) - so the
  -10% figure is specific to the frozen LV/MV boundary; reported as such, not generalized.
