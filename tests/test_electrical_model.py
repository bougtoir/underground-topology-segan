import math
import os
import sys
import unittest

import networkx as nx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/scripts")

from electrical_model import (  # noqa: E402
    cable,
    choose_transformer,
    load_catalogs,
    load_spec,
    radial_power_flow,
    size_tree_conductors,
    transformer_drop_pct,
    validate_radial_tree,
)


class ElectricalModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = load_spec(f"{ROOT}/ENGINEERING_FEASIBILITY_SPEC.yaml")
        cls.cables, cls.transformers = load_catalogs(ROOT, cls.spec)

    def line(self, length=100.0):
        graph = nx.Graph()
        graph.add_edge("s", "l", length=length)
        return graph

    def test_catalog_voltage_bases_and_primary_source_rows(self):
        self.assertEqual(self.spec["system"]["mv_nominal_kv"], 6.6)
        self.assertEqual(self.spec["system"]["lv_nominal_v"], 210)
        self.assertEqual(self.spec["system"]["lv_phases"], 1)
        self.assertIn(150, set(self.cables[self.cables.tier == "MV"].area_mm2))
        self.assertIn(100, set(self.transformers.rating_kva))

    def test_municipality_frequency_selects_matching_transformers(self):
        _, transformers_50 = load_catalogs(ROOT, self.spec, frequency_hz=50)
        self.assertEqual(set(transformers_50.freq_hz), {50.0})
        self.assertEqual(set(self.transformers.freq_hz), {60.0})

    def test_single_phase_210_105v_current_and_reactive_drop(self):
        graph = self.line()
        areas = {("l", "s"): 150}
        result = radial_power_flow(
            graph, "s", {"l": 60.0}, 210.0, 0.9, areas,
            self.cables, self.spec, "LV")
        minimum_current = 60_000 / (210 * 0.9)
        self.assertGreater(
            result["edge_results"].iloc[0].current_a, minimum_current)
        conductor = cable(self.cables, "LV", 150, self.spec)
        resistance = conductor.r_ohm_per_km * 0.1
        active_only = 2 * minimum_current * resistance * 0.9
        self.assertGreater(result["edge_results"].iloc[0].drop_v, active_only)

    def test_ampacity_is_enforced(self):
        graph = self.line(25.0)
        result = radial_power_flow(
            graph, "s", {"l": 200.0}, 210.0, 0.9, {("l", "s"): 60},
            self.cables, self.spec, "LV")
        self.assertFalse(result["feasible"])
        self.assertTrue(any("thermal" in issue for issue in result["issues"]))

    def test_sizing_repairs_thermal_and_voltage_without_clipping(self):
        graph = self.line(25.0)
        areas, result = size_tree_conductors(
            graph, "s", {"l": 60.0}, "LV",
            self.spec["conductors"]["lv_candidate_areas_mm2"], 210.0, 0.9,
            self.cables, self.spec, optimize=True)
        self.assertTrue(result["feasible"])
        self.assertGreaterEqual(areas[("l", "s")], 100)
        self.assertGreater(result["min_voltage_v"], 0)
        self.assertLessEqual(
            result["drop_pct"], self.spec["voltage_gates"]["lv_drop_max_pct"])

    def test_connectivity_and_radiality_are_enforced(self):
        cyclic = nx.Graph()
        cyclic.add_edges_from([("s", "a"), ("a", "b"), ("b", "s")])
        self.assertIn("not_radial", validate_radial_tree(cyclic, "s", {"b": 1}))
        disconnected = nx.Graph()
        disconnected.add_nodes_from(["s", "b"])
        self.assertIn(
            "not_connected", validate_radial_tree(disconnected, "s", {"b": 1}))

    def test_transformer_sizing_loading_and_drop(self):
        tr = choose_transformer(self.transformers, 60.0, 0.9, 80.0)
        self.assertGreaterEqual(tr.rating_kva, 60 / 0.9 / 0.8)
        loading_pct = 100 * (60 / 0.9) / tr.rating_kva
        self.assertLessEqual(loading_pct, 80.0 + 1e-9)
        self.assertLessEqual(
            transformer_drop_pct(tr, 60.0, 0.9),
            self.spec["voltage_gates"]["transformer_drop_max_pct"])

    def test_power_balance_and_source_voltage(self):
        graph = nx.Graph()
        graph.add_edge("s", "a", length=30.0)
        graph.add_edge("a", "b", length=20.0)
        areas = {("a", "s"): 150, ("a", "b"): 150}
        result = radial_power_flow(
            graph, "s", {"a": 10.0, "b": 20.0}, 6600.0, 0.9, areas,
            self.cables, self.spec, "MV")
        self.assertAlmostEqual(result["voltages_v"]["s"], 6600.0)
        self.assertAlmostEqual(result["power_balance_kw"], 0.0)
        self.assertGreater(result["source_input_kw"], 30.0)
        self.assertGreater(result["voltages_v"]["a"], result["voltages_v"]["b"])


if __name__ == "__main__":
    unittest.main()
