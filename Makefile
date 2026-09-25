PY := .venv/bin/python

.PHONY: all final prepare provenance catalogs data benchmark gis reconstruct optimize sensitivity audit freeze manuscript inline inventory package test

all: final

final: prepare provenance catalogs data benchmark gis reconstruct optimize audit sensitivity freeze manuscript inline inventory test package

prepare:
	mkdir -p analysis audit data/processed figures manuscript municipality provenance tables

provenance:
	$(PY) scripts/p19_raw_provenance.py

catalogs:
	$(PY) scripts/p16_catalogs.py

data:
	$(PY) scripts/p03_data_audit.py

benchmark:
	$(PY) scripts/p04_benchmark.py

gis:
	$(PY) scripts/p05_gis_demand.py

reconstruct:
	$(PY) scripts/p06_reconstruct.py

optimize:
	$(PY) scripts/p07_optimize.py

audit:
	$(PY) scripts/p17_results_audit.py
	$(PY) scripts/p18_provenance_convergence.py

sensitivity:
	$(PY) scripts/p10_sensitivity.py

freeze:
	$(PY) scripts/p11_freeze.py

manuscript:
	$(PY) scripts/p12_figures.py
	$(PY) scripts/p13_manuscript.py

inline:
	$(PY) scripts/p15_inline_docx.py

inventory:
	$(PY) scripts/p00_forensic_inventory.py

package: test
	$(PY) scripts/p14_package.py

test:
	$(PY) -m unittest discover -s tests -v
	$(PY) -m py_compile scripts/*.py tests/*.py
