# Beyond Like-for-Like Undergrounding

Reproducible study pipeline for:
**"Beyond Like-for-Like Undergrounding: Life-Cycle Optimization of Distribution Network Topology During Infrastructure Renewal"**
Target journal: *Sustainable Energy, Grids and Networks* (SEGAN), Elsevier.

## Layout
- `config/study.yaml` — frozen parameters (single source of truth)
- `provenance/` — source_registry.csv, municipality_candidates.csv, decision_log.md, CHARACTER_AUDIT.txt
- `data/raw/` — immutable downloaded data + per-file sha256 (never overwrite originals)
- `data/processed/` — derived artifacts
- `scripts/` — numbered phase scripts (run in order)
- `analysis/` — machine-readable outputs (feeds manuscript_values.csv)
- `manuscript/` — DOCX build + submission package
- `tests/` — unit/integration tests

## Reproduce
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock.txt
make all
```

## Labels
Every quantity is labelled observed / reconstructed / modeled / assumed / sensitivity.
Never call a reconstructed network an observed utility network.

## CEUS manuscript pipeline

The CEUS submission figures/tables/document are rebuilt by, in order:

```
.venv/bin/python scripts/p15b_ceus_morphology_v2.py   # morphology descriptors (feasible cohort)
.venv/bin/python scripts/p16_ceus_figures.py          # Figures 3-6 raster assets
.venv/bin/python scripts/p20_geographic_context_fig.py # Figure 2 (needs data/raw/geoboundaries + naturalearth)
.venv/bin/python scripts/p19_ceus_figure_finish.py    # Figure 1 pipeline diagram
.venv/bin/python scripts/p17_manuscript_ceus.py       # canonical DOCX
.venv/bin/python scripts/p18_package_ceus.py          # package + inline DOCX
```

Map inputs: `data/raw/geoboundaries/geoBoundaries-JPN-ADM1.geojson`
(geoBoundaries, CC-BY-4.0) and `data/raw/naturalearth/ne_10m_land/`
(Natural Earth 10m land, public domain).
