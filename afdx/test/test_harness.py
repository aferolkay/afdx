"""Fast tests for the Python harness; no OMNeT++ installation is required."""

import copy
import json
import unittest
from pathlib import Path

from harness.extractor import Extractor
from harness.measure import Measurements, measure
from harness.metrics import RUN_METRICS, SWITCH_METRICS, VL_METRICS
from harness.report import compare


class FakeExtractor(Extractor):
    def virtual_links(self):
        return ["a"]

    def switches(self):
        return ["2"]

    def run_sim_duration(self):
        return 1.0

    def vl_frames_sent(self, vl):
        return 10

    def vl_frames_delivered(self, vl):
        return 9

    def vl_dropped_in_queue(self, vl):
        return 1

    def vl_dropped_by_policer(self, vl):
        return 0

    def vl_latency_max(self, vl):
        return 25.0

    def vl_latency_mean(self, vl):
        return 20.0

    def switch_queueing_time_max(self, switch):
        return 3.0


class HarnessTest(unittest.TestCase):
    def setUp(self):
        self.baseline = measure(FakeExtractor())

    def test_extractor_is_measured_by_scope(self):
        self.assertEqual(self.baseline.run, {"sim_duration": 1.0})
        self.assertEqual(self.baseline.switches, {
            "2": {"queueing_time_max": 3.0},
        })
        self.assertEqual(self.baseline.vls["a"]["frames_sent"], 10)
        self.assertEqual(self.baseline.count, 8)
        self.assertEqual(self.baseline.missing(), [])

    def test_identical_measurements_pass(self):
        self.assertTrue(all(check.ok for check in
                            compare(self.baseline, copy.deepcopy(self.baseline))))

    def test_even_small_numeric_change_fails(self):
        changed = copy.deepcopy(self.baseline)
        changed.vls["a"]["latency_mean"] += 0.000001
        failed = [check for check in compare(self.baseline, changed)
                  if not check.ok]
        self.assertEqual([(check.where, check.metric.name) for check in failed],
                         [("VL a", "latency_mean")])

    def test_unmeasured_value_never_passes(self):
        self.baseline.vls["a"]["latency_max"] = None
        current = copy.deepcopy(self.baseline)
        check = next(check for check in compare(self.baseline, current)
                     if check.metric.name == "latency_max")
        self.assertFalse(check.ok)
        self.assertEqual(check.note, "NOT MEASURED in either run")
        self.assertEqual(current.missing(), ["vls.a.latency_max"])

    def test_added_virtual_link_fails(self):
        changed = copy.deepcopy(self.baseline)
        changed.vls["b"] = copy.deepcopy(changed.vls["a"])
        failed = [check for check in compare(self.baseline, changed)
                  if not check.ok]
        self.assertEqual(len(failed), len(VL_METRICS))
        self.assertTrue(all(check.where == "VL b" for check in failed))

    def test_committed_baselines_match_the_metric_schema(self):
        root = Path(__file__).parent / "networks"
        expected_run = {metric.name for metric in RUN_METRICS}
        expected_switch = {metric.name for metric in SWITCH_METRICS}
        expected_vl = {metric.name for metric in VL_METRICS}
        for path in root.glob("*/baseline.json"):
            with self.subTest(path=path):
                data = json.loads(path.read_text())
                self.assertEqual(set(data["run"]), expected_run)
                self.assertTrue(all(set(values) == expected_switch
                                    for values in data["switches"].values()))
                self.assertTrue(all(set(values) == expected_vl
                                    for values in data["vls"].values()))
                self.assertEqual(Measurements.load(path).missing(), [])


if __name__ == "__main__":
    unittest.main()
