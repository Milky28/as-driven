import json
from pathlib import Path
import unittest

from as_driven_db.audit_boundaries import audit_evidence_boundaries
from as_driven_db.split_claims import split_claims, split_record


ROOT = Path(__file__).parents[1]


def _indexed_record_count() -> int:
    index = json.loads((ROOT / "data" / "v1" / "index.json").read_text(encoding="utf-8"))
    return len(index["records"])


class BoundaryAuditTests(unittest.TestCase):
    def test_current_migration_debt_is_reported_without_changing_data(self) -> None:
        report = audit_evidence_boundaries(ROOT)
        self.assertEqual(report["audit"], "evidence-boundaries")
        # Derived from the index so promoting a record does not fail this test.
        self.assertEqual(report["stats"]["records"], _indexed_record_count())
        self.assertGreater(report["stats"]["simulator_only_authentic_claims"], 0)
        self.assertTrue(
            all(item["code"] == "authentic-claim-simulator-only" for item in report["findings"])
        )


class ClaimLayerTests(unittest.TestCase):
    """A claim carries one confidence, so it may describe only one layer.

    Promotions before `sourced_control_paths` wrote a single claim over both
    `/authentic_controls/...` and `/simulators/N/behavior`. A reviewed guided
    drive is verified evidence about the simulator and no evidence at all about
    the real car, so the real-car half inherited a confidence its own sources
    never supported.
    """

    def test_no_curated_claim_spans_both_layers(self) -> None:
        index = json.loads(
            (ROOT / "data" / "v1" / "index.json").read_text(encoding="utf-8")
        )
        offenders = []
        for relative in index["records"]:
            record = json.loads(
                (ROOT / "data" / "v1" / relative).read_text(encoding="utf-8-sig")
            )
            for position, claim in enumerate(record["provenance"]["claims"]):
                paths = claim["paths"]
                authentic = [p for p in paths if p.startswith("/authentic_controls")]
                if authentic and len(authentic) != len(paths):
                    offenders.append(f"{record['record_id']} claims[{position}]")
        self.assertEqual([], offenders, "run: python -m as_driven_db split-layer-claims")

    def test_splitting_keeps_each_half_on_its_own_evidence(self) -> None:
        claim = {
            "paths": [
                "/authentic_controls/transmission/upshift",
                "/simulators/0/behavior",
            ],
            "source_refs": ["ams2.local-live-example-controls.1.0"],
            "confidence": "verified",
            "basis": "Directly observed during the guided drive.",
        }
        rewritten, splits = split_claims([claim])
        self.assertEqual(2, len(rewritten))
        self.assertEqual(1, len(splits))
        self.assertEqual(
            ["/authentic_controls/transmission/upshift"], rewritten[0]["paths"]
        )
        self.assertEqual(["/simulators/0/behavior"], rewritten[1]["paths"])
        # Mechanical: sources, confidence and basis are carried, never judged.
        for half in rewritten:
            self.assertEqual(claim["source_refs"], half["source_refs"])
            self.assertEqual("verified", half["confidence"])
            self.assertEqual(claim["basis"], half["basis"])

    def test_a_single_layer_claim_is_left_exactly_as_it_is(self) -> None:
        claim = {
            "paths": ["/authentic_controls/transmission/gearbox_type"],
            "source_refs": ["manufacturer.example"],
            "confidence": "high",
            "basis": "The manual states a five-speed dog box.",
        }
        rewritten, splits = split_claims([claim])
        self.assertEqual([], splits)
        self.assertIs(claim, rewritten[0])

    def test_a_record_with_nothing_to_split_is_returned_untouched(self) -> None:
        record = {
            "record_id": "example",
            "provenance": {
                "claims": [
                    {
                        "paths": ["/simulators/0/behavior"],
                        "source_refs": ["ams2.local-live-example-controls.1.0"],
                        "confidence": "verified",
                        "basis": "Observed.",
                    }
                ]
            },
        }
        updated, splits = split_record(record)
        self.assertEqual([], splits)
        self.assertIs(record, updated)


if __name__ == "__main__":
    unittest.main()
