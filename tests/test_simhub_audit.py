from pathlib import Path
import csv
import tempfile
import unittest

from authentic_controls_db.importers.ams2 import import_ams2_csv
from authentic_controls_db.simhub import (
    _normalized_name,
    audit_ams2_identities,
    write_alias_review_csv,
)


FIXTURES = Path(__file__).parent / "fixtures"


class SimHubIdentityAuditTests(unittest.TestCase):
    def test_exact_matches_only_and_reports_identity_contract(self) -> None:
        candidates = import_ams2_csv(
            FIXTURES / "ams2.csv",
            source_id="test.ams2",
            verified_game_version="1.5.5.2",
        )
        audit = audit_ams2_identities(
            candidates,
            FIXTURES / "simhub-cars",
            simhub_version="test",
        )
        stats = audit["stats"]
        self.assertEqual(stats["candidate_rows"], 3)
        self.assertEqual(stats["observed_simhub_identities"], 2)
        self.assertEqual(stats["candidate_rows_with_exact_match"], 1)
        self.assertEqual(stats["observed_car_id_equals_car_model"], 2)
        self.assertEqual(stats["alias_suggestions"], 1)
        self.assertEqual(audit["exact_matches"][0]["display_name"], "McLaren F1 GTR")
        self.assertEqual(audit["alias_suggestions"][0]["display_name"], "F301")
        self.assertEqual(
            audit["alias_suggestions"][0]["rule"],
            "chassis-manufacturer-prefix",
        )
        self.assertEqual(
            audit["alias_suggestions"][0]["telemetry_name"], "Dallara F301"
        )
        self.assertEqual(
            audit["identity_contract"]["sdk_car_model"],
            "GameData.NewData.CarModel",
        )

    def test_name_normalization_is_formatting_only(self) -> None:
        self.assertEqual(_normalized_name("Fórmula Inter MG15"), "formulaintermg15")
        self.assertEqual(_normalized_name("Formula Inter MG-15"), "formulaintermg15")

    def test_writes_suggestions_and_manual_queue(self) -> None:
        candidates = import_ams2_csv(
            FIXTURES / "ams2.csv",
            source_id="test.ams2",
            verified_game_version="1.5.5.2",
        )
        audit = audit_ams2_identities(candidates, FIXTURES / "simhub-cars")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "review.csv"
            write_alias_review_csv(audit, output)
            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["status"], "suggested")
        self.assertEqual(rows[0]["sheet_name"], "F301")
        self.assertTrue(any(row["status"] == "manual-review" for row in rows))


if __name__ == "__main__":
    unittest.main()
