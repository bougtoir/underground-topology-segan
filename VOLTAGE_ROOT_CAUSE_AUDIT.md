# Voltage root-cause audit

## Finding

The quarantined voltage-drop results were caused by both an implementation defect and a structural network-model defect. They were not a valid comparison between engineering-feasible alternatives.

## Implementation defects

- The legacy evaluator treated road-tree edges as one low-voltage feeder.
- Reactive power, cable reactance, transformer behavior and line-loss feedback into upstream flow were omitted.
- There were no binding ampacity, voltage, connectivity, radiality, complete-service or source-power-balance gates.
- Node-identifier conversion and disconnected-component handling could silently remove modeled demand.

## Structural defects

Large aggregated loads were assigned to an LV-only tree without explicit MV primaries, transformer placement/capacity, service units or LV reach. The corrected model instead uses balanced 6.6-kV MV trees, catalogued single-phase 6.6-kV/210–105-V transformers, conservative parallel service units and equivalent 210-V LV stubs. Each connected cluster has its own idealized source; shared upstream utility assets remain outside scope.

## Quantitative resolution

| Municipality | Quarantined maximum drop | Corrected maximum MV drop | Corrected minimum customer voltage |
| --- | ---: | ---: | ---: |
| Sano | 29.16% | 0.322% | 0.9737 pu |
| Kudamatsu | 31.12% | 0.593% | 0.9700 pu |
| Yasu | 37.78% | 0.433% | 0.9710 pu |

All clusters entering the reported scenario summaries pass the frozen screening gates; failed clusters may not be excluded.

## Interpretation

The corrected outputs establish internal feasibility of the declared local-source screening model. They do not establish actual municipal feeder topology, shared-substation feasibility, construction readiness, or global optimization. Routing-policy savings and combined routing-and-sizing savings are reported separately.
