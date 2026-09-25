# VOLTAGE_ROOT_CAUSE_AUDIT — why S0/S1 showed 29–38% max voltage drop

## Verdict: structural (model construction), not a unit bug

The reported 29–38% LinDistFlow maximum voltage drop is reproduced and its
cause traced. Three independent structural defects, in decreasing order of
contribution:

### 1. Cluster scale — MV-scale loads on LV radials (dominant cause)
`CLUSTER_KW = 350 kW` (`scripts/p06_reconstruct.py:18`) built ~350 kW raw
clusters. A 350 kW balanced 3-phase load at 415 V / pf 0.9 draws ~540 A.
On 150 mm² Al (R = 0.188 Ω/km) the trunk drop is ~176 V/km ≈ 42 %/km — a
250 m trunk alone breaches any LV limit. In Japan a 415/200 V LV feeder is
a pole/pad transformer zone of ~30–150 kVA; 350 kW is MV-feeder scale.
This is a network-construction error, not a power-flow error.

### 2. No coincidence/diversity factor (amplifier)
Per-node demands are *building-peak estimates* (30–60 W/m² × footprint ×
floors, mean 62 kW, max 554 kW per node). Summing raw building peaks onto
one feeder assumes every building peaks simultaneously — physically wrong.
No diversity was applied anywhere in p05–p07.

### 3. No ampacity or transformer gate (missing feasibility check)
The optimizer priced NPC only. Trunk currents above cable ampacity
(150 mm² Al ≈ 350 A) and loads above transformer rating (default 500 kVA,
never checked) were priced as if feasible. Similarly, nodes >~150 kW
cannot be LV-served at all; they were synthesised anyway.

## Unit/conversion checks (all verified correct)
- `I = Pw_kW·1000/(√3·V_LL·pf)` — correct, V_LL = 415 V line-line.
- Phase drop `I·R`, line-to-line `√3·I·R` — correctly applied.
- ρ = 2.826e-8 Ω·m (Al), A = 150e-6 m² → R = 0.188 Ω/km — correct.
- kW/W/m units consistent; no line-neutral vs line-line mix-up found.
- LinDistFlow itself is fine at this scale once the network is feasible.

## Repair (Phase 3/4, smallest defensible corrections — frozen in
`config/ENGINEERING_FEASIBILITY_SPEC.yaml` BEFORE corrected runs)
- A: coincidence factor 0.6 on building peaks for sizing/voltage (assumed).
- B: nodes >150 kW raw peak marked MV-served, excluded from LV synthesis.
- C: LV cluster target ~100 kW raw (~150 kVA transformer zone).
- Gates: vdrop ≤6%, ampacity per size, transformer loading ≤100%,
  radiality/connectivity/power-balance. Infeasible clusters are excluded
  from the primary estimate with an inclusion/exclusion sensitivity run.
