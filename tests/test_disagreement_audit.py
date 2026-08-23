import json
from pathlib import Path
import unittest

from as_driven_db.site import collect
from research.build_simulator_disagreement_audit import build_audit


ROOT = Path(__file__).parents[1]
AUDIT_PATH = ROOT / "research" / "simulator-disagreement-audit.json"


class SimulatorDisagreementAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.checked_in = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    def test_checked_in_audit_is_the_current_deterministic_result(self) -> None:
        self.assertEqual(self.checked_in, build_audit(ROOT))
        index = json.loads(
            (ROOT / "data" / "v1" / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(self.checked_in["dataset_version"], index["dataset_version"])

    def test_every_site_conflict_is_audited_once(self) -> None:
        cars = collect(ROOT)["cars"]
        calculated = {
            (car["id"], disagreement["path"])
            for car in cars
            for disagreement in car["simulator_disagreements"]
        }
        audited = {
            (finding["record_id"], finding["path"])
            for finding in self.checked_in["findings"]
        }
        self.assertEqual(audited, calculated)
        self.assertEqual(len(audited), len(self.checked_in["findings"]))
        self.assertEqual(
            self.checked_in["summary"]["cars_with_disagreements"],
            len({record_id for record_id, _ in audited}),
        )

    def test_a_supported_departure_requires_primary_real_car_evidence(self) -> None:
        allowed = {
            "supported-departure",
            "provisional-departure",
            "authentic-baseline-open",
        }
        for finding in self.checked_in["findings"]:
            with self.subTest(finding=finding["finding_id"]):
                status = finding["adjudication"]["status"]
                self.assertIn(status, allowed)
                baseline = finding["authentic_baseline"]
                if status == "supported-departure":
                    self.assertIn(baseline["confidence"], {"verified", "high"})
                    self.assertTrue(baseline["primary_source_refs"])
                elif status == "authentic-baseline-open":
                    self.assertIn(baseline["value"], {None, "unknown"})

    def test_a_finding_keeps_versions_and_layers_separate(self) -> None:
        for finding in self.checked_in["findings"]:
            with self.subTest(finding=finding["finding_id"]):
                views = finding["simulator_views"]
                established = {
                    json.dumps(view["value"], sort_keys=True)
                    for view in views
                    if view["value"] not in {None, "unknown"}
                }
                self.assertGreaterEqual(len(established), 2)
                for view in views:
                    self.assertTrue(view["verified_game_version"])
                    self.assertTrue(view["verified_at"])
                    self.assertTrue(view["source_refs"])

    def finding(self, finding_id: str) -> dict:
        return next(
            item
            for item in self.checked_in["findings"]
            if item["finding_id"] == finding_id
        )

    def test_audi_launch_is_a_supported_departure(self) -> None:
        finding = self.finding(
            "audi-r8-lms-gt3-evo-ii--transmission-standing-start-clutch"
        )
        self.assertEqual("required", finding["authentic_baseline"]["value"])
        self.assertEqual("high", finding["authentic_baseline"]["confidence"])
        self.assertEqual(
            ["audi.r8-lms-gt3-evo2.technical"],
            finding["authentic_baseline"]["primary_source_refs"],
        )
        adjudication = finding["adjudication"]
        self.assertEqual("supported-departure", adjudication["status"])
        self.assertEqual(["ac"], adjudication["matching_simulators"])
        self.assertEqual(
            ["ams2", "ac-evo", "acc"],
            adjudication["departing_simulators"],
        )

    def test_mercedes_launch_is_a_supported_departure(self) -> None:
        finding = self.finding(
            "mercedes-amg-gt3--transmission-standing-start-clutch"
        )
        baseline = finding["authentic_baseline"]
        self.assertEqual("required", baseline["value"])
        self.assertEqual("high", baseline["confidence"])
        self.assertEqual(
            ["mercedes-amg.gt3.operation-manual-v03"],
            baseline["primary_source_refs"],
        )
        adjudication = finding["adjudication"]
        self.assertEqual("supported-departure", adjudication["status"])
        self.assertEqual(["acc"], adjudication["matching_simulators"])
        self.assertEqual(["ams2"], adjudication["departing_simulators"])

    def test_lotus_variants_keep_the_authentic_baseline_open(self) -> None:
        finding = self.finding(
            "lotus-renault-98t--transmission-forward-gears"
        )
        self.assertIsNone(finding["authentic_baseline"]["value"])
        self.assertEqual(
            "authentic-baseline-open", finding["adjudication"]["status"]
        )
        self.assertEqual([], finding["adjudication"]["matching_simulators"])
        self.assertEqual([], finding["adjudication"]["departing_simulators"])
        self.assertEqual(
            {"ams2": 5, "ac": 6},
            {
                view["simulator"]: view["value"]
                for view in finding["simulator_views"]
            },
        )

    def test_porsche_gate_stays_provisional_without_an_exact_rsr_diagram(self) -> None:
        finding = self.finding(
            "porsche-911-rsr-1974--transmission-shift-pattern"
        )
        baseline = finding["authentic_baseline"]
        self.assertEqual("standard-h", baseline["value"])
        self.assertEqual("medium", baseline["confidence"])
        self.assertTrue(baseline["primary_source_refs"])
        adjudication = finding["adjudication"]
        self.assertEqual("provisional-departure", adjudication["status"])
        self.assertEqual(["ams2"], adjudication["matching_simulators"])
        self.assertEqual(["ac"], adjudication["departing_simulators"])


if __name__ == "__main__":
    unittest.main()
