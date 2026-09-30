# Clean-room reproduction record

## Verdict

PASS. The final allowlisted package completed the documented build in a fresh
Python 3.10 environment. Unit tests, Python compilation, package QC, and ZIP
integrity passed. The reconstructed networks and all checked quantitative
outputs were byte-identical to the active reference build.

## Environment

- Run date (UTC): 2026-09-24
- Isolated directory: `/home/ubuntu/cleanroom-segan-final`
- Python: 3.10.12
- Dependency lock: `requirements.lock.txt`
- Dependency-lock SHA-256:
  `b776e326b58b0df996a1aa32622cab51bf75df6d506d0f9f5c7c47af5fb6d62c`
- Tested input package SHA-256:
  `2b5136a4cc676a40f8dcf161ad913f988d9489f787ce44bda0e78bc7ebe83c15`

## Commands

```bash
mkdir -p /home/ubuntu/cleanroom-segan-final
unzip -q SEGAN_submission_package_FINAL.zip \
  -d /home/ubuntu/cleanroom-segan-final
python3.10 -m venv /home/ubuntu/cleanroom-segan-final/.venv
/home/ubuntu/cleanroom-segan-final/.venv/bin/pip install \
  -r /home/ubuntu/cleanroom-segan-final/requirements.lock.txt
make final
```

The `make final` chain ran the eight-test unit suite, compiled all scripts and
tests, reported `QC pass`, and generated a 127-file ZIP without CRC errors.

## Byte-identical output checks

| Output | SHA-256 |
|---|---|
| `analysis/reconstruction_summary.csv` | `3801bb298a0024ff1e039fe1b0670eefe1640b285415d42ded439dc649f0545e` |
| `analysis/scenario_results.csv` | `30724ec694913e5f0b7e864edf704943ba03700485ad25b5922589257ef38fcb` |
| `analysis/sensitivity_mc.csv` | `4865075d4771ce92b4ef13f4dcee47ed863731bf881ef66c4985f65b88055373` |
| `analysis/ablation_decomposition.csv` | `a6e8901e4fa89161ffa1db0aaee062d41f75391a681740bf1f24814f36249051` |
| `FINAL_MANUSCRIPT_VALUES.csv` | `1c661dd891c2d23a0727d7b778a5893b7b2bbf132c0015ad8374827b411a13cb` |
| `figures/fig2_topology_example.png` | `d69486e0bc273404c3d8b3e8521375b7c12c0e938995882553e941c022270673` |

`FINAL_QC_MACHINE.json` differed only in its generated UTC timestamp.
