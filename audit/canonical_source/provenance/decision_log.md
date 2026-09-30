# Decision Log — Beyond Like-for-Like Undergrounding

Format: `YYYY-MM-DD | phase | decision | rationale | status`

2026-09-24 | P0 | Project root `underground_topology_segan/` inside bougtoir/wip | Matches workspace convention for paper pipelines | active
2026-09-24 | P0 | Python 3.10 venv `.venv`; deps in requirements.lock.txt | Reproducibility without commercial software | active
2026-09-24 | P0 | Primary NPC horizon = 40 yr | Japanese civil works life-cycle convention; 30/50 in sensitivity | frozen
2026-09-24 | P0 | TLD primary = unweighted edge symmetric-difference (1 - |E_C ∩ E_L|/|E_C ∪ E_L|) | Prompt default; weighted variants in sensitivity | frozen
2026-09-24 | P4 | case11_iwamoto failed AC convergence in pandapower 3.5.5 -> kept as documented non-converging benchmark; cigre_lv used as convergent validation benchmark; Japanese feeder topology built from municipal/OSM data instead | honest-failure logged
