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
        # The plain identity is now covered, but only because the alias is
        # written into the record and disclosed in its approval. Coverage must
        # never come from the generator inferring the relationship.
        self.assertEqual(entry["coverage_disposition"], "covered-exact")
        self.assertEqual(entry["related_record_id"], "ams2.formula-edge-model1-high-downforce")

        record = json.loads(
            (
                ROOT / "data" / "v1" / "cars" / "ams2.formula-edge-model1-high-downforce.json"
            ).read_text(encoding="utf-8")
        )
        names = [
            item["value"]
            for item in record["simulators"][0]["identities"]
            if item["kind"] == "telemetry-name"
        ]
        self.assertIn("Formula Edge Model1", names)
        self.assertIn("Formula Edge Model1 - High Downforce", names)

        approval = json.loads(
            (
                ROOT / "curation" / "ams2-approved-formula-edge-model1-high-downforce.json"
            ).read_text(encoding="utf-8")
        )
        disclosed = [
            item["value"] for item in approval.get("additional_telemetry_names", [])
        ]
        self.assertIn("Formula Edge Model1", disclosed)

    def test_reviewed_identities_are_data_not_generator_heuristics(self):
        manifest = json.loads(
            (ROOT / "research" / "ams2-coverage-manifest.json").read_text(encoding="utf-8")
        )
        decisions = json.loads(
            (ROOT / "research" / "ams2-identity-decisions.json").read_text(encoding="utf-8")
        )
        reviewed = {
            item["telemetry_name"]: item["disposition"]
            for item in decisions["decisions_list"]
        }
        entries = {entry["telemetry_name"]: entry for entry in manifest["entries"]}

        # Every retired or out-of-scope disposition must come from a checked-in
        # decision carrying a written basis, never from a hardcoded name list.
        for entry in manifest["entries"]:
            disposition = entry["coverage_disposition"]
            if disposition in {"retired-identity", "out-of-scope", "third-party-content"}:
                self.assertIn(entry["telemetry_name"], reviewed)
                self.assertEqual(reviewed[entry["telemetry_name"]], disposition)

        sources = json.loads(
            (ROOT / "data" / "v1" / "sources.json").read_text(encoding="utf-8")
        )
        source_ids = {item["source_id"] for item in sources["sources"]}
        record_ids = {
            json.loads(path.read_text(encoding="utf-8"))["record_id"]
            for path in (ROOT / "data" / "v1" / "cars").glob("*.json")
        }
        for item in decisions["decisions_list"]:
            self.assertTrue(item["basis"].strip(), item["telemetry_name"])
            self.assertEqual(
                entries[item["telemetry_name"]]["coverage_disposition"],
                item["disposition"],
            )
            # A cited source must be registered, and a named successor record
            # must exist, so a decision cannot point at something imaginary.
            for ref in item.get("source_refs", []):
                self.assertIn(ref, source_ids, item["telemetry_name"])
            if item["related_record_id"] is not None:
                self.assertIn(item["related_record_id"], record_ids, item["telemetry_name"])

        # A retired identity is never aliased onto a curated record.
        for item in decisions["decisions_list"]:
            if item["disposition"] != "retired-identity":
                continue
            self.assertNotIn(
                item["telemetry_name"],
                {
                    name
                    for path in (ROOT / "data" / "v1" / "cars").glob("*.json")
                    for record in [json.loads(path.read_text(encoding="utf-8"))]
                    for simulator in record["simulators"]
                    for identity in simulator["identities"]
                    if identity["kind"] == "telemetry-name"
                    for name in [identity["value"]]
                },
            )


if __name__ == "__main__":
    unittest.main()
