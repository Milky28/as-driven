from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from as_driven_db.importers.observation import import_observation
from as_driven_db.promote_observation import promote_observations
from as_driven_db.validate import validate_repository


ROOT = Path(__file__).parents[1]


def _observation() -> dict:
    return {
        "schema_version": "1.0.0",
        "observation_id": "ams2.test-prototype.20260813t120000000z-abcd1234",
        "simulator": "ams2",
        "game_version": "1.6.9.91",
        "client_version": "SimHub 9.11.22; As Driven 0.16.0",
        "observed_at": "2026-08-13T12:00:00.0000000Z",
        "observer": "Test observer",
        "identity": {
            "telemetry_name": "Test Prototype",
            "telemetry_class": "TESTP1",
            "internal_id": "Test Prototype",
        },
        "assists": {
            "automatic_clutch": "disabled",
            "automatic_shifting": "disabled",
            "automatic_throttle_blip": "unavailable",
        },
        "tests": {
            "move_off_without_physical_clutch": "yes",
            "forward_gears": 6,
            "direct_gear_selection_behavior": "not-applicable",
            "clutchless_upshift": "yes",
            "automatic_cut": "yes",
            "clutchless_downshift": "yes",
            "automatic_blip": "yes",
        },
        "cockpit": {
            "visible_shift_actuators": ["paddles"],
            "primary_shift_actuation": "sequential-paddles",
            "wheel_rim": {
                "shape": "prototype",
                "integrated_display": "yes",
                "shift_lights": "yes",
                "open_top": "no",
            },
        },
        "review_status": "draft",
    }


def _review_entry() -> dict:
    return {
        "record_id": "test-prototype",
        "bundle": "build/bundle.json",
        "class": "Test Prototype Cup",
        "manufacturer": "Test Motors",
        "model": "Prototype",
        "year": {"from": 2024, "label": "2024 test season"},
        "real_world_identity_notes": "A fictional prototype used only by the tests.",
        "real_world_source_refs": ["test.prototype.reference"],
        "confidence": "verified",
        "confidence_basis": "Behavior observed live; identity supported by a registered source.",
        "identity_basis": "Registered reference plus the exact observed telemetry identity.",
        "specification_basis": "Six sequential paddle gears confirmed by the reference and the drive.",
        "confidence_notes": "Controls directly observed with assists disabled.",
        "live_source_url": "https://example.invalid/test-drive",
    }


def _second_simulator_observation() -> dict:
    """The same real car, driven in a different simulator."""
    observation = _observation()
    observation["observation_id"] = "ac-evo.test-prototype.20260817t120000000z-beef5678"
    observation["simulator"] = "ac-evo"
    observation["game_version"] = "0.3.1"
    return observation


class PromoteObservationTests(unittest.TestCase):
    def _add_bundle(self, temp: Path, observation: dict, name: str) -> str:
        bundle = import_observation(observation, imported_at="2026-08-17")
        (temp / "build" / name).write_text(
            json.dumps(bundle, indent=2), encoding="utf-8"
        )
        return f"build/{name}"

    def _prepare(self, temp: Path) -> Path:
        shutil.copytree(ROOT / "schema", temp / "schema")
        shutil.copytree(ROOT / "data", temp / "data")
        shutil.copytree(ROOT / "curation", temp / "curation")
        (temp / "build").mkdir()

        bundle = import_observation(_observation(), imported_at="2026-08-13")
        (temp / "build" / "bundle.json").write_text(
            json.dumps(bundle, indent=2), encoding="utf-8"
        )

        sources_path = temp / "data" / "v1" / "sources.json"
        sources = json.loads(sources_path.read_text(encoding="utf-8"))
        sources["sources"].append(
            {
                "source_id": "test.prototype.reference",
                "title": "Test prototype reference",
                "publisher": "Tests",
                "url": "https://example.invalid/reference",
                "archive_url": None,
                "source_type": "secondary",
                "published_or_updated_at": None,
                "retrieved_at": "2026-08-13",
                "reuse_status": "facts-only-review",
                "notes": "Fixture source used only by the promotion tests.",
            }
        )
        sources_path.write_text(json.dumps(sources, indent=2), encoding="utf-8")
        return temp

    def _promote(self, temp: Path, review: dict) -> list[Path]:
        return promote_observations(
            review,
            root=temp,
            data_directory=temp / "data" / "v1",
            curation_directory=temp / "curation",
        )

    def _manifest(self, entry: dict) -> dict:
        return {
            "dataset_version": "9.9.9",
            "approved_at": "2026-08-13",
            "records": [entry],
        }

    def test_promoted_record_and_approval_pass_full_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._promote(temp, self._manifest(_review_entry()))

            record_path = temp / "data" / "v1" / "cars" / "test-prototype.json"
            self.assertTrue(record_path.exists())
            self.assertTrue(
                (temp / "curation" / "ams2-approved-test-prototype.json").exists()
            )

            index = json.loads(
                (temp / "data" / "v1" / "index.json").read_text(encoding="utf-8")
            )
            self.assertEqual(index["dataset_version"], "9.9.9")
            self.assertIn("cars/test-prototype.json", index["records"])

            # The whole point: the promoted pair survives the real validator.
            self.assertEqual(validate_repository(temp), [])

    def test_a_known_class_needs_no_answer_from_the_driver(self) -> None:
        """The class name is a property of the class, not of each car.

        Reading it means leaving a running session for the car-select screen,
        once per car, so it is recorded once per class and inherited.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            names = json.loads(
                (temp / "curation" / "simulator-class-names.json").read_text(encoding="utf-8")
            )
            names["classes"].append(
                {"simulator": "ams2", "class_id": "TESTP1", "name": "Test Prototype Cup",
                 "records": 0, "overridden_by": []}
            )
            (temp / "curation" / "simulator-class-names.json").write_text(
                json.dumps(names, indent=2), encoding="utf-8"
            )

            entry = _review_entry()
            del entry["class"]
            self._promote(temp, self._manifest(entry))
            record = json.loads(
                (temp / "data" / "v1" / "cars" / "test-prototype.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(record["identity"]["class"], "Test Prototype Cup")

    def test_an_entry_may_override_the_class_map(self) -> None:
        # A real Grand Prix car sits in an AMS2 formula class beside Reiza's
        # fictional ones, and belongs to Formula One rather than to that class.
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            entry = dict(_review_entry(), **{"class": "Formula One"})
            self._promote(temp, self._manifest(entry))
            record = json.loads(
                (temp / "data" / "v1" / "cars" / "test-prototype.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(record["identity"]["class"], "Formula One")

    def test_promotion_refuses_a_simulator_class_token(self) -> None:
        """The staged class is AMS2's token; a real category is a human call.

        AMS2's TC60S is called Vintage Cars Tier 1 in game and nothing in a
        draft says so, and the client draws the class onto the overlay.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            entry = _review_entry()
            del entry["class"]
            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(entry))
            self.assertIn("class", str(caught.exception))

    def test_promoted_class_is_the_reviewers_not_the_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._promote(temp, self._manifest(_review_entry()))
            record = json.loads(
                (temp / "data" / "v1" / "cars" / "test-prototype.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(record["identity"]["class"], "Test Prototype Cup")
            self.assertNotEqual(record["identity"]["class"], "TESTP1")

    def test_a_second_simulator_joins_the_record_instead_of_forking_it(self) -> None:
        """One real car, one record, an entry per simulator.

        This is what the ``ams2.`` prefix used to prevent: the same car verified
        in a second simulator would have been a second record, and the client
        would have had two answers for one car.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._promote(temp, self._manifest(_review_entry()))

            entry = _review_entry()
            entry["bundle"] = self._add_bundle(
                temp, _second_simulator_observation(), "bundle-ac-evo.json"
            )
            self._promote(temp, self._manifest(entry))

            cars = sorted(p.name for p in (temp / "data" / "v1" / "cars").glob("*.json"))
            self.assertEqual(cars.count("test-prototype.json"), 1)
            self.assertNotIn("ac-evo.test-prototype.json", cars)

            record = json.loads(
                (temp / "data" / "v1" / "cars" / "test-prototype.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                [item["simulator"] for item in record["simulators"]], ["ams2", "ac-evo"]
            )
            self.assertEqual(record["simulators"][1]["verified_game_version"], "0.3.1")

            # The second entry's claims must point at it, not at the first.
            second = [
                claim
                for claim in record["provenance"]["claims"]
                if any(p.startswith("/simulators/1") for p in claim["paths"])
            ]
            self.assertTrue(second, "expected claims scoped to the second simulator")
            self.assertFalse(
                any(
                    p.startswith("/authentic_controls")
                    for claim in second
                    for p in claim["paths"]
                ),
                "a second simulator must not restate the real car's claims",
            )

            # One approval per simulator, each naming its own.
            approvals = sorted(p.name for p in (temp / "curation").glob("*-test-prototype.json"))
            self.assertEqual(
                approvals,
                ["ac-evo-approved-test-prototype.json", "ams2-approved-test-prototype.json"],
            )
            self.assertEqual(validate_repository(temp), [])

    def test_the_same_simulator_cannot_be_promoted_onto_a_record_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._promote(temp, self._manifest(_review_entry()))
            with self.assertRaises(FileExistsError):
                self._promote(temp, self._manifest(_review_entry()))

    def test_a_second_simulator_may_not_quietly_rewrite_the_real_car(self) -> None:
        """A disagreement is a review decision, not a silent overwrite."""
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._promote(temp, self._manifest(_review_entry()))

            observation = _second_simulator_observation()
            observation["tests"]["forward_gears"] = 5
            entry = _review_entry()
            entry["bundle"] = self._add_bundle(temp, observation, "bundle-disagree.json")

            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(entry))
            self.assertIn("forward_gears", str(caught.exception))

    def test_aero_alias_becomes_an_exact_record_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            entry = _review_entry()
            entry["additional_telemetry_names"] = [
                {
                    "value": "Test Prototype - Low Downforce",
                    "basis": "Approved aero alias inheriting the verified base controls.",
                }
            ]
            self._promote(temp, self._manifest(entry))

            record = json.loads(
                (temp / "data" / "v1" / "cars" / "test-prototype.json").read_text(
                    encoding="utf-8"
                )
            )
            names = [
                item["value"]
                for item in record["simulators"][0]["identities"]
                if item["kind"] == "telemetry-name"
            ]
            self.assertIn("Test Prototype - Low Downforce", names)
            # class-id must remain present for the approval cross-check.
            kinds = {item["kind"] for item in record["simulators"][0]["identities"]}
            self.assertIn("class-id", kinds)
            self.assertEqual(validate_repository(temp), [])

    def test_simulator_override_is_written_and_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            entry = _review_entry()
            # The real car has no clutch pedal, but the simulator requires clutch
            # input to move off. The record keeps the real value and states the
            # deviation explicitly.
            entry["control_overrides"] = {"standing_start_clutch": "not-required"}
            entry["simulator_overrides"] = [
                {
                    "path": "/authentic_controls/transmission/standing_start_clutch",
                    "value": "required",
                    "condition": "AMS2 1.6.9.91 requires clutch input to move off.",
                    "confidence": {"level": "verified", "basis": "Observed in the guided drive."},
                }
            ]
            self._promote(temp, self._manifest(entry))

            record = json.loads(
                (temp / "data" / "v1" / "cars" / "test-prototype.json").read_text(
                    encoding="utf-8"
                )
            )
            transmission = record["authentic_controls"]["transmission"]
            self.assertEqual("not-required", transmission["standing_start_clutch"])
            overrides = record["simulators"][0]["overrides"]
            self.assertEqual(1, len(overrides))
            self.assertEqual("required", overrides[0]["value"])
            # The live source is attached automatically when none is given.
            self.assertTrue(overrides[0]["source_refs"])
            self.assertEqual(validate_repository(temp), [])

    def test_override_must_target_the_authentic_layer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            entry = _review_entry()
            entry["simulator_overrides"] = [
                {
                    "path": "/simulators/0/behavior/auto_blip",
                    "value": "no",
                    "condition": "irrelevant",
                    "confidence": {"level": "low", "basis": "test"},
                }
            ]
            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(entry))
            self.assertIn("/authentic_controls/", str(caught.exception))

    def test_incomplete_review_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            entry = _review_entry()
            del entry["manufacturer"]
            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(entry))
            self.assertIn("manufacturer", str(caught.exception))

    def test_unregistered_source_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            entry = _review_entry()
            entry["real_world_source_refs"] = ["test.not.registered"]
            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(entry))
            self.assertIn("not registered", str(caught.exception))

    def test_existing_record_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._promote(temp, self._manifest(_review_entry()))
            with self.assertRaises(FileExistsError):
                self._promote(temp, self._manifest(_review_entry()))

    def test_control_override_keeps_approval_in_agreement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            entry = _review_entry()
            entry["control_overrides"] = {"gearbox_type": "dual-clutch"}
            self._promote(temp, self._manifest(entry))

            record = json.loads(
                (temp / "data" / "v1" / "cars" / "test-prototype.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                record["authentic_controls"]["transmission"]["gearbox_type"],
                "dual-clutch",
            )
            self.assertEqual(validate_repository(temp), [])


if __name__ == "__main__":
    unittest.main()
