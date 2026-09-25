# Corrected SEGAN reproduction

The reference build used Python 3.10.12. Create an isolated
environment with that Python version and install `requirements.lock.txt`.
Archived public inputs are under `data/raw/`; canonical checksums are recorded
under `audit/`.

Run:

```bash
make final
```

The build regenerates provenance, catalogues, audits, the benchmark,
geospatial demand, reconstruction, feasibility-gated optimization,
conditional scenario sampling, the frozen value ledger, figures, manuscripts,
tests, inventories and the allowlisted ZIP. Runtime is dominated by
reconstruction candidates and bounded conductor search.
