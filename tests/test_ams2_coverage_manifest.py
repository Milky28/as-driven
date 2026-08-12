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
        self.assertEqual(manifest["dataset_version"], "0.3.18")

    def test_low_downforce_inheritance_requires_an_exact_base(self):
        manifest = json.loads(
            (ROOT / "research" / "ams2-coverage-manifest.json").read_text(encoding="utf-8")
        )
        entries = {entry["telemetry_name"]: entry for entry in manifest["entries"]}
        audi = entries["Audi R8 LMP1 - Low Downforce"]
        bmw = entries["BMW M Hybrid V8 - Low Downforce"]
        self.assertEqual(audi["coverage_disposition"], "aero-inheritance-ready")
        self.assertEqual(audi["related_record_id"], "ams2.audi-r8-lmp1")
        self.assertEqual(bmw["coverage_disposition"], "aero-inheritance-after-base")
        self.assertIsNone(bmw["related_record_id"])

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
