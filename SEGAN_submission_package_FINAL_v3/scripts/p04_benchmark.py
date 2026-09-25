"""Phase 4: engineering benchmark validation.
Benchmarks: (1) case11_iwamoto - Japanese 11-bus distribution test feeder
(Iwamoto & Tamura, documented Japanese benchmark); (2) CIGRE LV network
(European reference). Runs AC power flow and records summary metrics."""
import pandapower as pp
import pandapower.networks as pn
import pandas as pd, os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = []

def summarize(name, net):
    try:
        pp.runpp(net, verbose=False)
    except Exception:
        try:
            pp.runpp(net, init="dc", verbose=False)
        except Exception as e2:
            rows.append(dict(benchmark=name, n_bus=len(net.bus), n_line=len(net.line),
                             n_load=len(net.load),
                             n_trafo=len(net.trafo) if hasattr(net, "trafo") else 0,
                             vm_pu_min=float("nan"), vm_pu_max=float("nan"),
                             pl_mw=float("nan"),
                             total_load_mw=float(net.load.p_mw.sum()) if len(net.load) else 0.0,
                             converged=False))
            print(f"{name}: AC power flow did not converge ({e2})")
            return
    rows.append(dict(
        benchmark=name,
        n_bus=len(net.bus), n_line=len(net.line), n_load=len(net.load),
        n_trafo=len(net.trafo) if hasattr(net, "trafo") else 0,
        vm_pu_min=float(net.res_bus.vm_pu.min()),
        vm_pu_max=float(net.res_bus.vm_pu.max()),
        pl_mw=float(net.res_line.pl_mw.sum()) if "pl_mw" in net.res_line else float("nan"),
        total_load_mw=float(net.load.p_mw.sum()),
        converged=True))

# Japanese benchmark: Iwamoto & Tamura 11-bus 6.6 kV-class distribution case
net = pn.case11_iwamoto()
summarize("case11_iwamoto", net)

# European LV reference for LV-side sanity
net2 = pn.create_cigre_network_lv()
summarize("cigre_lv", net2)

df = pd.DataFrame(rows)
out = f"{ROOT}/analysis/benchmark_validation.csv"
df.to_csv(out, index=False)
print(df.to_string(index=False))
with open(f"{ROOT}/analysis/benchmark_notes.txt", "w") as f:
    f.write("case11_iwamoto: Iwamoto & Tamura Japanese 11-bus distribution benchmark "
            "(as shipped in pandapower.networks; power_system_test_cases). "
            "cigre_lv: CIGRE Task Force C6.04.02 LV European benchmark via pandapower.\n")
print("wrote", out)
