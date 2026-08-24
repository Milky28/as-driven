import copy
import json
from pathlib import Path
import re
import tempfile
import unittest

from as_driven_db.intake_observation import IntakeError, intake_observation


ROOT = Path(__file__).parents[1]


def observation(name: str = "Intake Test Car") -> dict:
    return {
        "$schema": "urn:as-driven:schema:v1:verification-observation",
        "schema_version": "1.0.0",
        "observation_id": "ams2.intake-test-car.20260823t120000000z-abcd1234",
        "simulator": "ams2",
        "game_version": "1.6.9.91",
        "client_version": "SimHub 9.11.22; As Driven 0.19.0",
        "dataset_version": "0.4.20",
        "observed_at": "2026-08-23T12:00:00.0000000Z",
        "observer": "Test observer",
        "identity": {
            "telemetry_name": name,
            "telemetry_class": "TEST_CLASS",
            "internal_id": name,
        },
        "assists": {
            "automatic_clutch": "disabled",
            "automatic_shifting": "disabled",
            "automatic_throttle_blip": "unavailable",
        },
        "tests": {
            "move_off_without_physical_clutch": "no",
            "forward_gears": 6,
            "direct_gear_selection_behavior": "not-applicable",
            "clutchless_upshift": "yes",
            "automatic_cut": "unknown",
            "clutchless_downshift": "yes",
            "automatic_blip": "yes",
        },
        "cockpit": {
            "visible_shift_actuators": ["paddles"],
            "primary_shift_actuation": "sequential-paddles",
            "shift_pattern": "sequential",
            "wheel_rim": {
                "shape": "gt-formula",
                "integrated_display": "yes",
                "shift_lights": "yes",
                "open_top": "no",
            },
        },
        "review_status": "draft",
    }


class ObservationIntakeTests(unittest.TestCase):
    def write(self, directory: Path, payload: dict, name: str) -> Path:
        path = directory / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def test_exact_bytes_are_the_only_automatic_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            inbox = temp / "inbox"
            path = self.write(temp, observation(), "first.json")
            first = intake_observation(ROOT, path, inbox)
            second = intake_observation(ROOT, path, inbox)
            self.assertEqual("new-identity", first["status"])
            self.assertEqual("exact-resubmission", second["status"])
            self.assertFalse(second["stored"])

    def test_independent_compatible_drive_is_corroboration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            inbox = temp / "inbox"
            first = observation()
            second = copy.deepcopy(first)
            second["observation_id"] = (
                "ams2.intake-test-car.20260823t130000000z-efab5678"
            )
            second["observed_at"] = "2026-08-23T13:00:00.0000000Z"
            second["tests"]["automatic_cut"] = "not-tested"
            intake_observation(ROOT, self.write(temp, first, "first.json"), inbox)
            receipt = intake_observation(
                ROOT, self.write(temp, second, "second.json"), inbox
            )
            self.assertEqual("corroboration", receipt["status"])
            self.assertEqual([], receipt["related_submissions"][0]["conflicting_paths"])

    def test_incompatible_established_fact_is_a_contradiction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            inbox = temp / "inbox"
            first = observation()
            second = copy.deepcopy(first)
            second["observation_id"] = (
                "ams2.intake-test-car.20260823t140000000z-1234efab"
            )
            second["observed_at"] = "2026-08-23T14:00:00.0000000Z"
            second["tests"]["forward_gears"] = 5
            intake_observation(ROOT, self.write(temp, first, "first.json"), inbox)
            receipt = intake_observation(
                ROOT, self.write(temp, second, "second.json"), inbox
            )
            self.assertEqual("contradiction", receipt["status"])
            self.assertIn(
                "/tests/forward_gears",
                receipt["related_submissions"][0]["conflicting_paths"],
            )

    def test_new_package_digest_is_a_changed_implementation_not_a_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            inbox = temp / "inbox"
            first = observation()
            first["simulator"] = "ac"
            first["implementation"] = {
                "content_id": "test_mod",
                "author": "Test author",
                "declared_version": "1.0",
                "fingerprint": {
                    "scope": "data-acd",
                    "algorithm": "sha256",
                    "digest": "a" * 64,
                },
            }
            second = copy.deepcopy(first)
            second["observation_id"] = (
                "ac.intake-test-car.20260823t150000000z-5678abcd"
            )
            second["observed_at"] = "2026-08-23T15:00:00.0000000Z"
            second["implementation"]["declared_version"] = "1.1"
            second["implementation"]["fingerprint"]["digest"] = "b" * 64
            intake_observation(ROOT, self.write(temp, first, "first.json"), inbox)
            receipt = intake_observation(
                ROOT, self.write(temp, second, "second.json"), inbox
            )
            self.assertEqual("changed-implementation", receipt["status"])

    def test_issue_form_names_the_public_evidence_boundary(self) -> None:
        form = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "simulator-observation.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("label: Guided-drive draft JSON", form)
        self.assertIn("Drag the exact As Driven JSON", form)
        self.assertIn("Drop one .json draft here", form)
        self.assertIn("simulator evidence, not proof", form)
        self.assertIn("package's content ID", form)
        self.assertIn("redacted copy", form)
        self.assertNotIn("privacy-reduced", form)
        self.assertIn("CC BY 4.0", form)
        self.assertIsNone(
            re.search(
                r'^\s+(?:label|description|placeholder):\s+[^"\'|>{\[].*:\s',
                form,
                re.MULTILINE,
            ),
            "Issue Form plain scalars containing a second colon must be quoted",
        )

    def test_exact_curated_identity_routes_to_comparison_not_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            payload = observation("BMW M6 GT3")
            payload["identity"]["internal_id"] = "BMW M6 GT3"
            receipt = intake_observation(
                ROOT,
                self.write(temp, payload, "bmw.json"),
                temp / "inbox",
            )
            self.assertEqual("curated-identity-comparison", receipt["status"])
            self.assertEqual("bmw-m6-gt3", receipt["curated_matches"][0]["record_id"])

    def test_invalid_or_oversized_input_is_not_stored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            path = self.write(temp, {"not": "a draft"}, "bad.json")
            with self.assertRaises(IntakeError):
                intake_observation(ROOT, path, temp / "inbox")
            self.assertFalse((temp / "inbox").exists())


if __name__ == "__main__":
    unittest.main()
