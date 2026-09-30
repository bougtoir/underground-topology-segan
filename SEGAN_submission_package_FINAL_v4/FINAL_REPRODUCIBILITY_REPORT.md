# FINAL_REPRODUCIBILITY_REPORT (v4, Phase F17)

## Method
Clean-room rerun: project copied to `/tmp/cleanroom_v4` (no `.venv`), fresh
`python3 -m venv` + `pip install -r requirements.lock.txt`, then the core
pipeline re-executed against committed inputs only:

    TAG=cr INTAG=v2 ./.venv/bin/python scripts/p07b_optimize_v2.py

This reruns feasibility gating, S1 ensemble evaluation, S2 optimization,
VoF and naive ΔNPC for all three cities from `data/processed/`, `config/`
and `analysis/reconstruction_summary_v2.csv` — no session-local artifacts.

## Result: EXACT reproduction (full float precision)

| city | metric | frozen | clean-room | match |
|------|--------|--------|------------|-------|
| sano | VoF % | 0.0144897742419492 | 0.0144897742419492 | exact |
| kudamatsu | VoF % | 0.3935389350285189 | 0.3935389350285189 | exact |
| yasu | VoF % | 0.2009821342115532 | 0.20098213421155328 | exact |
| sano | ΔNPC % | 0.0144897742419505 | 0.014489774241950524 | exact |
| kudamatsu | ΔNPC % | -10.061993614831731 | -10.061993614831733 | exact |
| yasu | ΔNPC % | 0.2009821342115523 | 0.20098213421155237 | exact |
| sano | feasible | 360 | 360 | exact |
| kudamatsu | feasible | 88 | 88 | exact |
| yasu | feasible | 106 | 106 | exact |

Deterministic reconstruction/optimization (seeded jitter; sorted glob
order) reproduces bit-identical scenario results. Manuscript figures,
tables and DOCX are regenerated deterministically from
`analysis/manuscript_values_v3.csv` by `p12d_figures_v4.py`,
`p13d_manuscript_v4.py`, `p14d_package_v4.py`.

## Scope of this check
Covers the full inference chain that produces every reported number
(clusters → feasibility gates → S1/S2 NPC → VoF/ΔNPC) plus document
regeneration. Municipal raw-data acquisition (OSM/city open-data
downloads) is pinned by `provenance/source_registry.csv` checksums, not
re-downloaded in clean-room (recorded as an intentional bound, not a gap:
raw snapshots are committed under `data/`).
