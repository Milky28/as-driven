import json
import tempfile
import unittest
from pathlib import Path

from research.build_ams2_coverage_manifest import build


ROOT = Path(__file__).resolve().parents[1]


class AMS2CoverageManifestTests(unittest.TestCase):
    def test_checked_in_manifest_covers_every_observed_identity_once(self):
        manifest = json.loads(
            (ROOT / "research" / "ams2-coverage-manifest.json").read_text(encoding="utf-8")
        )
        audit = json.loads(
            (ROOT / "build" / "ams2-simhub-identity-audit.json").read_text(encoding="utf-8")
        )
        names = [entry["telemetry_name"] for entry in manifest["entries"]]
        observed = [entry["car_model"] for entry in audit["observed_identities"]]
        self.assertEqual(sorted(names), sorted(observed))
        self.assertEqual(len(names), len(set(names)))
        # Derived from the index so a dataset release does not fail this test;
        # it still catches a manifest that was not regenerated after promotion.
        index = json.loads(
            (ROOT / "data" / "v1" / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["dataset_version"], index["dataset_version"])

    def test_low_downforce_inheritance_requires_an_exact_base(self):
        manifest = json.loads(
            (ROOT / "research" / "ams2-coverage-manifest.json").read_text(encoding="utf-8")
        )
        entries = {entry["telemetry_name"]: entry for entry in manifest["entries"]}

        # The rule, asserted over every aero variant rather than over one car,
        # because an individual identity moves between states as it is promoted.
        # An aero variant may only point at a base record once that base is
        # curated; otherwise it stays pending, or needs its own verification
        # when no base identity was ever observed.
        linked = {"aero-inheritance-ready", "covered-exact"}
        unlinked = {"aero-inheritance-after-base", "full-guided-verification"}
        for name, entry in entries.items():
            if not name.endswith(" - Low Downforce"):
                continue
            disposition = entry["coverage_disposition"]
            if entry["related_record_id"] is None:
                self.assertIn(disposition, unlinked, name)
            else:
                self.assertIn(disposition, linked, name)

        # A base car that is not yet curated keeps its Low Downforce alias pending.
        nissan = entries["Nissan R89C - Low Downforce"]
        self.assertEqual(nissan["coverage_disposition"], "aero-inheritance-after-base")
        self.assertIsNone(nissan["related_record_id"])
        # Once the base car carries the alias as an explicit identity, the
        # Low Downforce identity is covered exactly rather than inherited silently.
        bmw = entries["BMW M Hybrid V8 - Low Downforce"]
        self.assertEqual(bmw["coverage_disposition"], "covered-exact")
        self.assertEqual(bmw["related_record_id"], "ams2.bmw-m-hybrid-v8")
        audi = entries["Audi R8 LMP1 - Low Downforce"]
        self.assertEqual(audi["coverage_disposition"], "covered-exact")
        self.assertEqual(audi["related_record_id"], "ams2.audi-r8-lmp1")

    def test_qualified_formula_does_not_create_a_silent_plain_alias(self):
        manifest = json.loads(
            (ROOT / "research" / "ams2-coverage-manifest.json").read_text(encoding="utf-8")
        )
        entry = next(
            item for item in manifest["entries"] if item["telemetry_name"] == "Formula Edge Model1"
        )
        self.assertEqual(entry["coverage_disposition"], "configuration-inheritance-review")
        self.assertEqual(entry["related_record_id"], "ams2.formula-edge-model1-high-downforce")


if __name__ == "__main__":
    unittest.main()
