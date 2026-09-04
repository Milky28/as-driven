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

    def test_bug_form_collects_reproducible_client_context(self) -> None:
        form = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "bug-report.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("name: Report a SimHub client problem", form)
        self.assertIn('title: "[Bug]: "', form)
        self.assertIn("label: Versions", form)
        self.assertIn("As Driven client and dataset versions", form)
        self.assertIn("label: How can it be reproduced?", form)
        self.assertIn("live telemetry or an offline preview", form)
        self.assertIn("private security-reporting link", form)
        self.assertIn("Do not attach contribution drafts", form)

    def test_existing_car_research_form_preserves_the_evidence_boundary(self) -> None:
        form = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "existing-car-research.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("name: Improve an existing car", form)
        self.assertIn('title: "[Research]: "', form)
        self.assertIn("label: Existing car record", form)
        self.assertIn("label: Exact car and source applicability", form)
        self.assertIn("label: Fields or claims affected", form)
        self.assertIn("label: Sources and precise locators", form)
        self.assertIn("exact page, section, figure, or video timestamp", form)
        self.assertIn("real-car research, not evidence of how a simulator behaves", form)
        self.assertNotIn("observation-received", form)
        self.assertIsNone(
            re.search(
                r'^\s+(?:label|description|placeholder):\s+[^"\'|>{\[].*:\s',
                form,
                re.MULTILINE,
            ),
            "Issue Form plain scalars containing a second colon must be quoted",
        )

    def test_issue_chooser_offers_private_security_reporting(self) -> None:
        config = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"
        ).read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        private_report_url = (
            "https://github.com/Milky28/as-driven/security/advisories/new"
        )
        self.assertIn(private_report_url, config)
        self.assertIn(private_report_url, security)
        # The chooser must steer a vulnerability away from a public issue, and
        # SECURITY.md must say so too. It used to also explain what to do while
        # the repository was private; private reporting is enabled now, so that
        # paragraph went rather than becoming a stale instruction.
        self.assertIn("Do not open a public issue", security)
        self.assertNotIn("While the repository remains private", security)

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
            # Deliberately a game this project has not registered. RRRE stood
            # here until RaceRoom was registered, at which point this drive
            # started being released rather than held and the test was asserting
            # something that had stopped being true.
            payload = observation("Held Probe Car")
            payload["observation_id"] = (
                "other.held-probe-car.20260826t043236230z-67fbf819"
            )
            payload["simulator"] = "other"
            payload["source_game_name"] = "LeMansUltimate"
            receipt = intake_observation(
                ROOT, self.write(temp, payload, "held.json"), inbox
            )
            self.assertEqual("unregistered-simulator", receipt["status"])
            self.assertTrue(receipt["stored"], "the drive is kept, not discarded")
            self.assertEqual(
                "LeMansUltimate",
                receipt["unregistered_simulator"]["source_game_name"],
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

    def test_registering_a_game_releases_the_drives_waiting_on_it(self) -> None:
        """The rename that source_game_name was kept for.

        A draft's `simulator` field is written by whichever client version took
        the drive and never changes afterwards, so re-running intake on a held
        observation used to hold it again however many simulators had been
        registered since. The promise was that registering a game releases the
        drives waiting on it; this is where that happens.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            payload = observation("BMW M2 CS Racing Probe")
            payload["observation_id"] = (
                "other.bmw-m2-cs-racing.20260826t194202971z-890e7e53"
            )
            payload["simulator"] = "other"
            payload["source_game_name"] = "RFactor2"
            receipt = intake_observation(
                ROOT, self.write(temp, payload, "released.json"), temp / "inbox"
            )
            self.assertEqual("rfactor2", receipt["released_simulator"])
            self.assertIsNone(receipt["unregistered_simulator"])
            self.assertEqual("new-identity", receipt["status"])

    def test_releasing_a_drive_already_in_the_inbox_is_not_a_second_version(self) -> None:
        # The held copy is this submission, byte for byte. Releasing has to step
        # past the duplicate check to answer a verdict that has gone stale, and
        # leaving the stored copy in view made the drive an alternate
        # representation of itself: same observation id, so the relationship
        # check reported a second version of a drive nobody submitted twice.
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            inbox = temp / "inbox"
            payload = observation("Release Twice Probe")
            payload["observation_id"] = (
                "other.release-twice-probe.20260826t194202971z-890e7e55"
            )
            payload["simulator"] = "other"
            payload["source_game_name"] = "RFactor2"
            path = self.write(temp, payload, "twice.json")
            first = intake_observation(ROOT, path, inbox)
            second = intake_observation(ROOT, path, inbox)
            self.assertEqual("new-identity", first["status"])
            self.assertEqual(
                "new-identity",
                second["status"],
                "the same bytes must not become a relationship with themselves",
            )
            self.assertEqual([], second["related_submissions"])

    def test_a_game_still_unregistered_stays_held(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            payload = observation("Some Other Sim Car")
            payload["observation_id"] = "other.some-car.20260826t194202971z-890e7e54"
            payload["simulator"] = "other"
            payload["source_game_name"] = "LeMansUltimate"
            receipt = intake_observation(
                ROOT, self.write(temp, payload, "held.json"), temp / "inbox"
            )
            self.assertIsNone(receipt["released_simulator"])
            self.assertEqual("unregistered-simulator", receipt["status"])

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
