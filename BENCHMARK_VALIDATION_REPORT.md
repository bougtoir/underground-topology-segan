# Benchmark validation report

## Benchmark and environment

- Benchmark: CIGRE Task Force C6.04.02 European low-voltage network as
  implemented by `pandapower.networks.create_cigre_network_lv`.
- pandapower version: 3.5.5.
- Reference calculation: Newton-Raphson AC power flow with tolerance
  \(10^{-10}\) MVA.
- Independent AC checks: backward/forward sweep and Iwamoto Newton-Raphson.
- Radial-model tolerances fixed before inspection: absolute minimum-voltage
  error <= 0.003 pu and relative line-loss error <=
  10%.

## AC solver agreement

| algorithm | converged | vm_pu_min | vm_pu_max | line_loss_mw | transformer_loss_mw | ext_grid_p_mw | ext_grid_q_mvar | max_line_current_ka | max_transformer_loading_pct | validated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nr | True | 0.91226896 | 1 | 0.021821754 | 0.0065074665 | 0.71492922 | 0.31876011 | 0.31716218 | 85.25464 | True |
| bfsw | True | 0.91226896 | 1 | 0.021821753 | 0.0065074665 | 0.71492922 | 0.31876011 | 0.31716218 | 85.25464 | True |
| iwamoto_nr | True | 0.91226896 | 1 | 0.021821754 | 0.0065074665 | 0.71492922 | 0.31876011 | 0.31716218 | 85.25464 | True |

All three AC algorithms agree within 1e-07 pu for minimum
voltage and 1e-07 MW for line loss.

## Corrected radial P/Q model versus AC power flow

The comparison starts each radial LV feeder at the AC-calculated transformer
secondary voltage so that it isolates the line model from transformer-model
differences. It uses the benchmark's exact per-edge resistance, reactance,
active load and reactive load; no voltage clipping is applied.

| source_name | p_load_kw | q_load_kvar | ac_min_voltage_pu | linear_min_voltage_pu | voltage_abs_error_pu | ac_line_loss_kw | linear_line_loss_kw | loss_relative_error | validated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bus R1 | 383.8 | 126.14896 | 0.91689555 | 0.91916946 | 0.0022739052 | 10.785211 | 10.085726 | 0.064855983 | True |
| Bus I1 | 85 | 52.678269 | 0.94345834 | 0.94479432 | 0.001335979 | 3.717222 | 3.4518291 | 0.071395497 | True |
| Bus C1 | 217.8 | 105.48535 | 0.91226896 | 0.91482589 | 0.0025569257 | 7.3193201 | 6.7767609 | 0.074126993 | True |

All three feeders satisfy the declared tolerances. The corrected radial model
is therefore quantitatively validated for its stated screening role. The
CIGRE network itself reaches 0.9123 pu; convergence is not
misrepresented as compliance with this study's planning voltage gate.

## Iwamoto 11-bus diagnosis

| algorithm | converged | vm_pu_min |
| --- | --- | --- |
| nr | False | nan |
| bfsw | False | nan |
| iwamoto_nr | False | nan |

The packaged `case11_iwamoto` does not converge with Newton-Raphson,
backward/forward sweep, or Iwamoto Newton-Raphson under the pinned environment.
It is a difficult generic power-flow stress case with a 1 kV base, not a
documented Japanese 6.6 kV distribution-design reference for the present
model. It is retained as a diagnosed negative control and removed from the
paper's validation claim.
