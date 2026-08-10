import json
from pathlib import Path
import tempfile
import unittest

from authentic_controls_db.importers.ams2 import import_ams2_csv
from authentic_controls_db.promote import promote_approved_ams2
from authentic_controls_db.simhub import audit_ams2_identities


FIXTURES = Path(__file__).parent / "fixtures"


class Ams2PromotionTests(unittest.TestCase):
    def _inputs(self) -> tuple[dict, dict, dict]:
        candidates = import_ams2_csv(
            FIXTURES / "ams2.csv",
            source_id="test.ams2",
            verified_game_version="1.5.5.2",
        )
        audit = audit_ams2_identities(candidates, FIXTURES / "simhub-cars")
        f301 = next(
            candidate
            for candidate in candidates["candidates"]
            if candidate["identity"]["display_name"] == "F301"
        )
        approvals = {
            "schema_version": "1.0.0",
            "dataset_version": "0.2.0",
            "approved_at": "2026-08-10",
            "verified_at": "2024-01-17",
            "records": [
                {
                    "source_row": f301["source_row"],
                    "source_display_name": "F301",
                    "record_id": "ams2.f301",
                    "manufacturer": "Dallara",
                    "model": "F301",
                    "telemetry_name": "Dallara F301",
                    "identity_notes": "Fixture identity.",
                }
            ],
        }
        return candidates, audit, approvals

    def test_promotes_only_reviewed_alias_and_updates_index(self) -> None:
        candidates, audit, approvals = self._inputs()
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data" / "v1"
            (data_directory / "cars").mkdir(parents=True)
            (data_directory / "index.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "dataset_version": "0.1.0",
                        "released_at": "2026-08-09",
                        "records": [],
                    }
                ),
                encoding="utf-8",
            )

            outputs = promote_approved_ams2(
                candidates, audit, approvals, data_directory
            )

            self.assertEqual(len(outputs), 1)
            record = json.loads(outputs[0].read_text(encoding="utf-8"))
            self.assertEqual(record["simulators"][0]["identities"][0]["value"], "Dallara F301")
            self.assertEqual(
                record["authentic_controls"]["transmission"]["upshift"]["clutch"],
                "unknown",
            )
            index = json.loads(
                (data_directory / "index.json").read_text(encoding="utf-8")
            )
            self.assertEqual(index["dataset_version"], "0.2.0")
            self.assertEqual(index["records"], ["cars/ams2.f301.json"])

    def test_rejects_alias_not_present_in_audit(self) -> None:
        candidates, audit, approvals = self._inputs()
        approvals["records"][0]["telemetry_name"] = "Invented F301 Name"
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data" / "v1"
            (data_directory / "cars").mkdir(parents=True)
            (data_directory / "index.json").write_text(
                json.dumps({"records": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "not backed"):
                promote_approved_ams2(
                    candidates, audit, approvals, data_directory
                )


if __name__ == "__main__":
    unittest.main()
