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

    def test_new_launch_batch_is_supported_by_exact_car_evidence(self) -> None:
        expected_sources = {
            "mercedes-amg-gt3-evo--transmission-standing-start-clutch": [
                "mercedes-amg.gt3-evo-2020.operation-manual-r01"
            ],
            "mercedes-amg-gt4--transmission-standing-start-clutch": [
                "mercedes-amg.gt4.drivetrain-manual-r10"
            ],
            "bmw-m6-gt3--transmission-standing-start-clutch": [
                "bmw.m6-gt3-m4-gt3-comparison"
            ],
        }
        for finding_id, primary_sources in expected_sources.items():
            with self.subTest(finding=finding_id):
                finding = self.finding(finding_id)
                baseline = finding["authentic_baseline"]
                self.assertEqual("required", baseline["value"])
                self.assertEqual("high", baseline["confidence"])
                self.assertEqual(primary_sources, baseline["primary_source_refs"])
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

    def test_completed_provisional_review_keeps_only_reviewed_provisional(self) -> None:
        provisional = {
            finding["finding_id"]
            for finding in self.checked_in["findings"]
            if finding["adjudication"]["status"] == "provisional-departure"
        }
        self.assertEqual(
            {
                "milano-gt55--transmission-downshift-manual-blip",
                "porsche-911-rsr-1974--transmission-shift-pattern",
                "saleen-s7-r-gt1--transmission-downshift-manual-blip",
                # The Miura's Assetto Corsa entry arrived with the manual blip
                # its drive demanded, over an authentic value of optional that
                # rests on a guided drive rather than a primary source. That is
                # the same shape as the two blip departures above and is handled
                # the documented way: the authentic value stays optional and the
                # simulator's demand is an override.
                "lamborghini-miura-sv--transmission-downshift-manual-blip",
                # The RSR's blip became a departure only once the authentic
                # value stopped being unknown. It is optional at medium, derived
                # from a synchromesh the record reads off the 915 family rather
                # than off a source about the 915/08, while AC refuses the shift
                # without a blip. Provisional is the honest status: a departure
                # from a baseline that a period workshop manual could still move.
                "porsche-911-rsr-1974--transmission-downshift-manual-blip",
            },
            provisional,
        )
        self.assertEqual(
            {
                "authentic-baseline-open": 15,
                "provisional-departure": 5,
                "supported-departure": 7,
            },
            self.checked_in["summary"]["by_status"],
        )

    def test_exact_cockpit_photos_settle_two_wheel_departures(self) -> None:
        expected = {
            "nissan-gt-r-nismo-gt3--steering-wheel-rim-shape": ("acc", "ams2"),
            "porsche-911-gt3-r--steering-wheel-rim-shape": ("acc", "ams2"),
        }
        for finding_id, (matching, departing) in expected.items():
            with self.subTest(finding=finding_id):
                finding = self.finding(finding_id)
                self.assertEqual("gt-formula", finding["authentic_baseline"]["value"])
                self.assertEqual("high", finding["authentic_baseline"]["confidence"])
                self.assertTrue(finding["authentic_baseline"]["primary_source_refs"])
                self.assertEqual(
                    "supported-departure", finding["adjudication"]["status"]
                )
                self.assertEqual(
                    [matching], finding["adjudication"]["matching_simulators"]
                )
                self.assertEqual(
                    [departing], finding["adjudication"]["departing_simulators"]
                )

    def test_open_findings_do_not_inherit_a_simulator_answer(self) -> None:
        expected = {
            "audi-r8-lms-gt4--steering-wheel-rim-open-top",
            "bmw-m6-gt3--steering-wheel-rim-shift-lights",
            "ginetta-g55-gt4--steering-wheel-rim-integrated-display",
            "ginetta-g55-gt4--steering-wheel-rim-shift-lights",
            "lister-storm-gtm--transmission-downshift-manual-blip",
            "lotus-renault-98t--transmission-forward-gears",
            "maserati-mc12-gt1--transmission-downshift-manual-blip",
            "mclaren-720s-gt3--transmission-standing-start-clutch",
            "mclaren-720s-gt3-evo--transmission-standing-start-clutch",
            "nissan-gt-r-nismo-gt3--transmission-standing-start-clutch",
            "nissan-r390-gt1--steering-wheel-rim-shape",
            "nissan-r390-gt1--steering-wheel-rim-shift-lights",
            "nissan-r390-gt1--transmission-downshift-automatic-blip",
            "nissan-r390-gt1--transmission-downshift-manual-blip",
            "porsche-911-gt1-98--transmission-downshift-manual-blip",
        }
        actual = {
            finding["finding_id"]
            for finding in self.checked_in["findings"]
            if finding["adjudication"]["status"] == "authentic-baseline-open"
        }
        self.assertEqual(expected, actual)

        for finding in self.checked_in["findings"]:
            if finding["adjudication"]["status"] != "authentic-baseline-open":
                continue
            with self.subTest(finding=finding["finding_id"]):
                self.assertIn(finding["authentic_baseline"]["value"], {None, "unknown"})
                self.assertEqual([], finding["adjudication"]["matching_simulators"])
                self.assertEqual([], finding["adjudication"]["departing_simulators"])


if __name__ == "__main__":
    unittest.main()
