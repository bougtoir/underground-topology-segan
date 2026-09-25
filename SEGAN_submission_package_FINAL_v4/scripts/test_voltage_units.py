"""Unit tests for the electrical model (Phase 2 audit deliverable)."""
import math, yaml, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = yaml.safe_load(open(f"{ROOT}/config/ENGINEERING_FEASIBILITY_SPEC.yaml"))
CFG = yaml.safe_load(open(f"{ROOT}/config/study.yaml"))
V_LL = SPEC["power_flow"]["v_ll_v"]; PF = SPEC["power_flow"]["power_factor"]
RHO = SPEC["power_flow"]["rho_ohm_m"]

def current_a(p_kw): return p_kw*1000.0/(math.sqrt(3)*V_LL*PF)
def r_ohm_per_km(a_mm2): return RHO*1000.0/(a_mm2*1e-6)
def drop_pct(p_kw, a_mm2, l_km):
    return math.sqrt(3)*current_a(p_kw)*r_ohm_per_km(a_mm2)*l_km/V_LL*100

def test_resistance_150mm2():
    assert abs(r_ohm_per_km(150) - 0.1884) < 0.002

def test_current_350kw():
    assert 535 < current_a(350) < 550   # ~542 A at 415 V, pf 0.9

def test_drop_direction():
    assert drop_pct(100, 150, 0.1) < drop_pct(200, 150, 0.1)
    assert drop_pct(100, 400, 0.1) < drop_pct(100, 150, 0.1)

def test_ampacity_table_monotonic():
    a = SPEC["feasibility"]["ampacity_a"]
    keys = sorted(a)
    assert all(a[k1] < a[k2] for k1, k2 in zip(keys, keys[1:]))

def test_cluster_scale_feasible():
    # 100 kW raw x 0.6 coincidence = 60 kW: trunk drop over 150 m, 150 mm2
    d = drop_pct(60, 150, 0.15)
    assert d < SPEC["feasibility"]["voltage_drop_max_pct"]

def test_old_scale_infeasible():
    # reproduce the old defect: 350 kW x 0.6 coincident over 250 m trunk
    d = drop_pct(210, 150, 0.25)
    assert d > SPEC["feasibility"]["voltage_drop_max_pct"]

if __name__ == "__main__":
    for f in dir():
        if f.startswith("test_"): globals()[f](); print(f, "PASS")
