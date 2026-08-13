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
        "record_id": "ams2.test-prototype",
        "bundle": "build/bundle.json",
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


class PromoteObservationTests(unittest.TestCase):
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

            record_path = temp / "data" / "v1" / "cars" / "ams2.test-prototype.json"
            self.assertTrue(record_path.exists())
            self.assertTrue(
                (temp / "curation" / "ams2-approved-test-prototype.json").exists()
            )

            index = json.loads(
                (temp / "data" / "v1" / "index.json").read_text(encoding="utf-8")
            )
            self.assertEqual(index["dataset_version"], "9.9.9")
            self.assertIn("cars/ams2.test-prototype.json", index["records"])

            # The whole point: the promoted pair survives the real validator.
            self.assertEqual(validate_repository(temp), [])

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
                (temp / "data" / "v1" / "cars" / "ams2.test-prototype.json").read_text(
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
                (temp / "data" / "v1" / "cars" / "ams2.test-prototype.json").read_text(
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
