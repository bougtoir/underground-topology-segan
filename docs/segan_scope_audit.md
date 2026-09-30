# SEGAN desk-reject defense audit (Phase 1, re-checked Phase 14)

- [x] Local-case-study framing -> mitigated: paper positioned as method + conditions under which renewal-time redesign has value; municipalities = validation environments.
- [x] Generic techno-economic undergrounding framing -> mitigated: LTP + reconstruction uncertainty + joint topology-DG are the novelty axes, not "should we underground".
- [x] Novelty = applying an existing optimizer -> mitigated: novelty is the renewal-decision framing, reconstruction-uncertainty propagation, and LTP/TLD definitions; optimizer is a tool.
- [x] Metaheuristic-comparison framing -> avoided: exact/structured optimization (MILP via HiGHS; graph algorithms) only.
- [x] Superficial power-system constraints -> voltage/thermal/radiality/balance constraints enforced; AC power-flow validation via pandapower on final candidates.
- [x] Misrepresentation of municipal anchors as utility topology -> labels: reconstructed, never "observed utility network"; Tier-2 anchors (security lights) never equated with poles.
- [x] Decorative DG -> DG enters only via S3 with siting/sizing + extended-routing break-even; can be dropped if not materially supported.
- [x] No AC validation -> pandapower AC load flow on final candidate designs (LV approximated; document limits).
- [x] Economics dominating without uncertainty -> global Monte Carlo sensitivity over all cost drivers; P(LTP>0) reported as model/scenario uncertainty only.
- [x] Lack of generalizable insight -> conditions-governing-LTP analysis + synthetic morphology experiments; municipalities treated as sample points, not the result.
