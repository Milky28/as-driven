from pathlib import Path
import csv
import json
import tempfile
import unittest

from as_driven_db.importers.ams2 import import_ams2_csv
from as_driven_db.simhub import (
    _normalized_name,
    audit_ams2_identities,
    review_unmatched_ams2_observations,
    write_alias_review_csv,
    write_unmatched_review_csv,
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

    def test_reviews_unmatched_jsonl_without_promoting(self) -> None:
        candidates = import_ams2_csv(
            FIXTURES / "ams2.csv",
            source_id="test.ams2",
            verified_game_version="1.5.5.2",
        )
        base = {
            "game_name": "Automobilista2",
            "dataset_version": "0.3.2",
            "simhub_version": "9.11.22",
        }
        observations = [
            {
                **base,
                "observed_at_utc": "2026-08-10T23:00:00Z",
                "game_version": "1.6.9.91",
                "car_model": "Dallara F301",
                "car_id": "Dallara F301",
                "car_class": "F301",
            },
            {
                **base,
                "observed_at_utc": "2026-08-10T23:01:00Z",
                "game_version": "unknown",
                "car_model": "Dodge Viper GTS-R",
                "car_id": "Dodge Viper GTS-R",
                "car_class": "GT1_05",
            },
            {
                **base,
                "observed_at_utc": "2026-08-10T23:02:00Z",
                "game_version": "1.6.9.91",
                "car_model": "Dodge Viper GTS-R",
                "car_id": "Dodge Viper GTS-R",
                "car_class": "GT1_05",
            },
            {
                **base,
                "observed_at_utc": "2026-08-10T23:03:00Z",
                "game_name": "iRacing",
                "game_version": "2026.08",
                "car_model": "Other car",
                "car_id": "other",
                "car_class": "Other",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "unmatched.jsonl"
            lines = [json.dumps(observations[0]), json.dumps(observations[0])]
            lines.extend(json.dumps(value) for value in observations[1:])
            lines.append("{invalid-json}")
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            review = review_unmatched_ams2_observations(candidates, log_path)
            output = Path(directory) / "review.csv"
            write_unmatched_review_csv(review, output)
            with output.open(encoding="utf-8-sig", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))

        self.assertEqual(review["stats"]["parsed_ams2_observations"], 3)
        self.assertEqual(review["stats"]["unique_raw_identities"], 2)
        self.assertEqual(review["stats"]["duplicate_lines"], 1)
        self.assertEqual(review["stats"]["unsupported_game_observations"], 1)
        self.assertEqual(review["stats"]["parse_errors"], 1)
        items = {item["car_model"]: item for item in review["review_items"]}
        self.assertEqual(items["Dallara F301"]["status"], "suggested-candidate")
        self.assertEqual(
            items["Dallara F301"]["rule"], "chassis-manufacturer-prefix"
        )
        self.assertEqual(items["Dodge Viper GTS-R"]["status"], "no-candidate")
        self.assertEqual(
            items["Dodge Viper GTS-R"]["preferred_game_version"], "1.6.9.91"
        )
        self.assertEqual(
            items["Dodge Viper GTS-R"]["preferred_simhub_version"], "9.11.22"
        )
        self.assertEqual(
            items["Dodge Viper GTS-R"]["preferred_dataset_version"], "0.3.2"
        )
        self.assertEqual(items["Dodge Viper GTS-R"]["observation_count"], 2)
        self.assertEqual(len(csv_rows), 2)
        self.assertEqual(
            next(row for row in csv_rows if row["car_model"] == "Dodge Viper GTS-R")["status"],
            "no-candidate",
        )

    def test_marks_an_exact_logged_identity_already_curated(self) -> None:
        candidates = import_ams2_csv(
            FIXTURES / "ams2.csv",
            source_id="test.ams2",
            verified_game_version="1.5.5.2",
        )
        observation = {
            "observed_at_utc": "2026-08-10T23:00:00Z",
            "game_name": "Automobilista2",
            "game_version": "1.6.9.91",
            "car_model": "Dallara F301",
            "car_id": "Dallara F301",
            "car_class": "F301",
            "dataset_version": "0.3.2",
            "simhub_version": "9.11.22",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path = root / "unmatched.jsonl"
            log_path.write_text(json.dumps(observation) + "\n", encoding="utf-8")
            data_directory = root / "data" / "v1"
            cars = data_directory / "cars"
            cars.mkdir(parents=True)
            (data_directory / "index.json").write_text(
                json.dumps({"records": ["cars/f301.json"]}), encoding="utf-8"
            )
            (cars / "f301.json").write_text(
                json.dumps(
                    {
                        "record_id": "ams2.f301",
                        "simulators": [
                            {
                                "simulator": "ams2",
                                "identities": [
                                    {"kind": "telemetry-name", "value": "Dallara F301"}
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            review = review_unmatched_ams2_observations(
                candidates,
                log_path,
                curated_data_directory=data_directory,
            )

        item = review["review_items"][0]
        self.assertEqual(item["status"], "already-curated")
        self.assertEqual(item["curated_record_id"], "ams2.f301")


if __name__ == "__main__":
    unittest.main()
