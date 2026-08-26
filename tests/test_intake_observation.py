import copy
import json
from pathlib import Path
import shutil
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
        self.assertIn("Keep the `[Observation]:` prefix", form)
        self.assertIn("simulator and telemetry car name", form)
        self.assertIn("does not establish the real car's identity", form)
        self.assertIn("issue and attachment are public", form)
        self.assertIn("Assetto Corsa package details", form)
        self.assertIn("redacted copy", form)
        self.assertNotIn("privacy-reduced", form)
        self.assertIn("label: Permission to share", form)
        permission = form.split("    id: permission", 1)[1]
        self.assertEqual(
            1,
            permission.count("required: true"),
            "the permission section needs one checkbox",
        )
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

    def _dataset(self, temp: Path, record: dict) -> Path:
        """A root holding one curated record, so the case cannot drift.

        These assertions turn on which simulators cover a car, which is exactly
        what promoting a submission changes. Pointed at the real dataset they
        pass until the workflow they describe succeeds, and then fail.
        """

        root = temp / "root"
        (root / "data" / "v1" / "cars").mkdir(parents=True)
        shutil.copytree(ROOT / "schema", root / "schema")
        (root / "data" / "v1" / "cars" / f"{record['record_id']}.json").write_text(
            json.dumps(record), encoding="utf-8"
        )
        (root / "data" / "v1" / "index.json").write_text(
            json.dumps({"records": [f"cars/{record['record_id']}.json"]}), encoding="utf-8"
        )
        (root / "data" / "v1" / "sources.json").write_text(
            json.dumps({"sources": []}), encoding="utf-8"
        )
        return root

    @staticmethod
    def _curated(simulator: str, telemetry_name: str) -> dict:
        return {
            "record_id": "test-miura",
            "identity": {
                "display_name": "Test Miura SV",
                "manufacturer": "Lamborghini",
                "model": "Miura SV",
            },
            "simulators": [
                {
                    "simulator": simulator,
                    "identities": [
                        {"kind": "telemetry-name", "value": telemetry_name},
                    ],
                }
            ],
        }

    def test_a_curated_car_in_another_simulator_is_offered_as_a_candidate(self) -> None:
        """A contributor cannot know the car is already curated elsewhere.

        Assetto Corsa calls it "Lamborghini Miura P400 SV" where the curated
        record's AMS2 name is "Lamborghini Miura SV". Exact matching finds
        nothing and never will, so the case used to open as a new identity with
        the existing record unmentioned.
        """

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            root = self._dataset(temp, self._curated("ams2", "Lamborghini Miura SV"))
            payload = observation("Lamborghini Miura P400 SV")
            payload["simulator"] = "ac"
            payload["observation_id"] = "ac.lamborghini-miura-p400-sv.20260824t120000000z-abcd1234"
            payload["identity"]["internal_id"] = "ks_lamborghini_miura_sv"
            receipt = intake_observation(
                root, self.write(temp, payload, "miura.json"), temp / "inbox"
            )
            self.assertEqual("curated-identity-candidate", receipt["status"])
            self.assertEqual([], receipt["curated_matches"], "it is not a match")
            self.assertEqual("test-miura", receipt["curated_candidates"][0]["record_id"])

    def test_a_candidate_is_not_offered_where_the_simulator_is_already_covered(self) -> None:
        # Once that simulator has an entry an exact match would have found it,
        # and its absence is an answer rather than a gap. This is the state the
        # record above reaches once its submission is promoted.
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            root = self._dataset(temp, self._curated("ac", "Lamborghini Miura P400 SV"))
            payload = observation("Lamborghini Miura P400 SV")
            payload["simulator"] = "ac"
            payload["observation_id"] = "ac.lamborghini-miura-p400-sv.20260824t120000000z-abcd1234"
            receipt = intake_observation(
                root, self.write(temp, payload, "miura.json"), temp / "inbox"
            )
            self.assertEqual([], receipt["curated_candidates"])
            self.assertEqual("test-miura", receipt["curated_matches"][0]["record_id"])

    def test_an_unregistered_simulator_is_held_and_says_which_game(self) -> None:
        """A drive from a game the client does not know is kept, not promoted.

        The evidence is real and the drive is fine. What is missing is the
        project's decision about the game, so the observation waits for it. The
        one thing that must survive is which game it came from: `other` on its
        own is a bucket, and a contributor's forty drives from two different
        simulators would be indistinguishable inside it.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            inbox = temp / "inbox"
            payload = observation("Saleen S7R")
            payload["observation_id"] = (
                "other.saleen-s7r.20260826t043236230z-67fbf819"
            )
            payload["simulator"] = "other"
            payload["source_game_name"] = "RRRE"
            receipt = intake_observation(
                ROOT, self.write(temp, payload, "held.json"), inbox
            )
            self.assertEqual("unregistered-simulator", receipt["status"])
            self.assertTrue(receipt["stored"], "the drive is kept, not discarded")
            self.assertEqual(
                "RRRE", receipt["unregistered_simulator"]["source_game_name"]
            )

    def test_a_registered_simulator_is_never_held(self) -> None:
        # The same payload under a registered id classifies on its identity as
        # usual, which is what registering a simulator has to release.
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            inbox = temp / "inbox"
            payload = observation("Saleen S7R Registered Probe")
            payload["observation_id"] = (
                "raceroom.saleen-s7r.20260826t043236230z-67fbf819"
            )
            payload["simulator"] = "raceroom"
            payload["source_game_name"] = "RRRE"
            receipt = intake_observation(
                ROOT, self.write(temp, payload, "released.json"), inbox
            )
            self.assertNotEqual("unregistered-simulator", receipt["status"])
            self.assertIsNone(receipt["unregistered_simulator"])

    def test_an_other_observation_without_its_game_name_is_rejected(self) -> None:
        # Without it the observation is anonymous, and nothing downstream could
        # ever tell which game to register. The schema refuses it at the door.
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            inbox = temp / "inbox"
            payload = observation("Nameless Car")
            payload["observation_id"] = (
                "other.nameless-car.20260826t043236230z-67fbf820"
            )
            payload["simulator"] = "other"
            with self.assertRaises(IntakeError):
                intake_observation(
                    ROOT, self.write(temp, payload, "anonymous.json"), inbox
                )

    def test_invalid_or_oversized_input_is_not_stored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            path = self.write(temp, {"not": "a draft"}, "bad.json")
            with self.assertRaises(IntakeError):
                intake_observation(ROOT, path, temp / "inbox")
            self.assertFalse((temp / "inbox").exists())


if __name__ == "__main__":
    unittest.main()
