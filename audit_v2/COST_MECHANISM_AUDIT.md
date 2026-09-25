# Cost mechanism audit (R9)

npc = capex(trench+duct+cable, conductor-scaled) + transformer 3.5M JPY + O&M + loss NPV.
Loss NPV per kW ~= 8760h x LF 0.35 x 25 JPY/kWh x ADF(40y,3%)~23.1 ~ 1.77 M JPY/kW.

Observed: loss differences between S1 and S2 are ~0.0-0.3 kW per cluster (capex-dominant regime),
so delta_npc is almost exactly a CAPEX delta: rewiring pays iff it physically shortens the
trench+conductor route vs the incumbent corridor. In sano/yasu incumbent corridors are already
near-minimal (delta +0.01%/+0.20%, inside the 1% equivalence margin); in kudamatsu every
Steiner-tree alternative requires longer new trenching (s2_capex +347 M vs s1 mean).

Break-even statement (machine-checkable): re-planning is beneficial only when
route_length_reduction_m x ~162k JPY/m > added conductor cost; the optimizer's
topology candidates produce ~0-3 m mean reduction per cluster -> economically equivalent.
