import json
from pathlib import Path
import shutil
import tempfile
import unittest

from as_driven_db.validate import _resolve_pointer, validate_repository
from as_driven_db.schema_validation import validate_instance


ROOT = Path(__file__).parents[1]


class ValidationTests(unittest.TestCase):
    def test_repository_is_valid(self) -> None:
        self.assertEqual(validate_repository(ROOT), [])

    def test_an_inferred_gearbox_is_never_claimed_at_high_confidence(self) -> None:
        """A mechanism nobody sourced cannot be a high-confidence claim.

        Eight Hewland cars stated dog-ring construction at high confidence
        while their own notes called it inferred from Hewland's design
        approach. The claim now sits at medium, which is both honest and
        checkable - unlike the prose hedge, which nothing could key off.
        """
        import re

        inferred = re.compile(
            r"(is inferred|rather than stated by (the|a) (reviewed )?source"
            r"|is the ordinary reading of)",
            re.IGNORECASE,
        )
        offenders = []
        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            for claim in record["provenance"]["claims"]:
                if not any(p.endswith("/gearbox_type") for p in claim["paths"]):
                    continue
                if inferred.search(claim["basis"]) and claim["confidence"] in {"high", "verified"}:
                    offenders.append(f"{record['record_id']}: {claim['confidence']}")
        self.assertEqual([], offenders)

    def test_driver_summary_never_asserts_a_mechanism_that_was_inferred(self) -> None:
        """The card's prose may not be firmer than the claim behind it.

        This now reads the claim's confidence rather than matching sentences
        in the notes, so it holds for any wording a future summary uses.
        """
        import re

        asserts_mechanism = re.compile(
            r"(the dog rings engage|^synchronised gearbox\.)", re.IGNORECASE
        )
        offenders = []
        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            summary = record.get("driver_summary") or ""
            if not summary or not asserts_mechanism.search(summary):
                continue
            claim = next(
                (c for c in record["provenance"]["claims"]
                 if any(p.endswith("/gearbox_type") for p in c["paths"])),
                None,
            )
            if claim is not None and claim["confidence"] not in {"high", "verified"}:
                offenders.append(record["record_id"])
        self.assertEqual([], offenders)

    def test_driver_summary_stays_within_the_length_the_card_can_draw(self) -> None:
        # The overlay draws three pre-broken lines; beyond that the last one
        # ellipsises, which loses the reason the summary exists to give.
        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            summary = record.get("driver_summary")
            if summary is None:
                continue
            self.assertLessEqual(len(summary), 300, record["record_id"])
            self.assertEqual(summary, summary.strip(), record["record_id"])

    def test_json_pointer_resolution(self) -> None:
        document = {"simulators": [{"behavior": {"shift_cut": "yes"}}]}
        self.assertTrue(_resolve_pointer(document, "/simulators/0/behavior/shift_cut"))
        self.assertFalse(_resolve_pointer(document, "/simulators/1/behavior/shift_cut"))

    def test_unknown_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))

            target = temp_root / "data" / "v1" / "cars" / "ams2.f301.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["simulators"][0]["source_refs"] = ["missing.source"]
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(any("unknown source_id" in error for error in errors))

    def test_schema_rejects_invalid_shift_actuation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            target = temp_root / "data" / "v1" / "cars" / "ams2.f301.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["authentic_controls"]["transmission"]["shift_actuation"] = "magic"
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(
                any("shift_actuation: invalid value 'magic'" in error for error in errors)
            )

    def test_schema_rejects_unexpected_record_property(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            target = temp_root / "data" / "v1" / "cars" / "ams2.f301.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["unreviewed_guess"] = True
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(any("unreviewed_guess: unexpected property" in error for error in errors))

    def test_schema_rejects_invalid_source_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            target = temp_root / "data" / "v1" / "sources.json"
            sources = json.loads(target.read_text(encoding="utf-8"))
            sources["sources"][0]["source_type"] = "rumor"
            target.write_text(json.dumps(sources), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(any("source_type: invalid value 'rumor'" in error for error in errors))

    def test_approval_must_match_curated_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory), include_curation=True)
            target = temp_root / "curation" / "ams2-approved-audi-r8-lmp1.json"
            approval = json.loads(target.read_text(encoding="utf-8"))
            approval["approved_controls"]["forward_gears"] = 7
            target.write_text(json.dumps(approval), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(
                any("forward_gears: approved 7 does not match curated value 6" in error for error in errors)
            )

    def test_simulator_approval_checks_simulator_cut_not_authentic_cut(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory), include_curation=True)
            target = temp_root / "data" / "v1" / "cars" / "ams2.audi-r8-lmp1.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["authentic_controls"]["transmission"]["upshift"]["automatic_cut"] = "no"
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertFalse(
                any("approved_controls.automatic_cut" in error for error in errors),
                errors,
            )

    def test_guided_verification_draft_contract(self) -> None:
        schema = json.loads(
            (ROOT / "schema" / "v1" / "verification-observation.schema.json").read_text(
                encoding="utf-8"
            )
        )
        observation = {
            "$schema": "urn:as-driven:schema:v1:verification-observation",
            "schema_version": "1.0.0",
            "observation_id": "ams2.test-car.20260811t120000000z-1234abcd",
            "simulator": "ams2",
            "game_version": "1.6.9.91",
            "client_version": "SimHub 9.11.22; As Driven 0.11.0",
            "observed_at": "2026-08-11T12:00:00.0000000Z",
            "observer": "Test observer",
            "identity": {
                "telemetry_name": "Test Car",
                "telemetry_class": "TEST_CLASS",
                "internal_id": "Test Car",
            },
            "assists": {
                "automatic_clutch": "disabled",
                "automatic_shifting": "disabled",
                "automatic_throttle_blip": "unavailable",
            },
            "tests": {
                "move_off_without_physical_clutch": "no",
                "forward_gears": 6,
                "direct_gear_selection_behavior": "not-tested",
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
        self.assertEqual(validate_instance(observation, schema, "observation"), [])

        observation["review_status"] = "auto-approved"
        errors = validate_instance(observation, schema, "observation")
        self.assertTrue(any("review_status: invalid value 'auto-approved'" in error for error in errors))

        observation["review_status"] = "draft"
        observation["tests"]["direct_gear_selection_behavior"] = "sequential-ish"
        errors = validate_instance(observation, schema, "observation")
        self.assertTrue(any("direct_gear_selection_behavior: invalid value" in error for error in errors))

        observation["tests"]["direct_gear_selection_behavior"] = "not-tested"
        observation["tests"]["direct_gear_selection_behavior"] = "not-applicable"
        self.assertEqual(validate_instance(observation, schema, "observation"), [])

        observation["observed_at"] = "2026-08-11T12:00:00"
        errors = validate_instance(observation, schema, "observation")
        self.assertTrue(any("expected an ISO date-time with timezone" in error for error in errors))

    def test_live_observation_source_id_convention_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            sources_path = temp_root / "data" / "v1" / "sources.json"
            sources = json.loads(sources_path.read_text(encoding="utf-8"))

            def _with_source_id(source_id: str) -> list[str]:
                payload = json.loads(json.dumps(sources))
                payload["sources"].append(
                    {
                        "source_id": source_id,
                        "title": "Convention fixture",
                        "publisher": "Tests",
                        "url": "https://example.invalid/drive",
                        "archive_url": None,
                        "source_type": "in-game-observation",
                        "published_or_updated_at": None,
                        "retrieved_at": "2026-08-13",
                        "reuse_status": "facts-only-review",
                        "notes": "Fixture.",
                    }
                )
                sources_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                return validate_repository(temp_root)

            # The retired conventions are rejected.
            for retired in (
                "ams2.local-guided-test-car-controls.1.6.9.91",
                "ams2.test-car.local-guided-controls.1.6.9.91",
            ):
                errors = _with_source_id(retired)
                self.assertTrue(
                    any("must be ams2.local-live-" in error for error in errors),
                    (retired, errors),
                )

            # The chosen convention is accepted.
            self.assertEqual(
                _with_source_id("ams2.local-live-test-car-controls.1.6.9.91"), []
            )

            # Other publishers keep their own prefixes.
            self.assertEqual(
                _with_source_id("simhub.local-ams2-identities.9.11.23"), []
            )

    def test_documented_release_must_match_the_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            index = json.loads(
                (temp_root / "data" / "v1" / "index.json").read_text(encoding="utf-8")
            )
            version = index["dataset_version"]
            count = len(index["records"])

            readme = temp_root / "README.md"
            readme.write_text(
                f"Dataset {version} contains {count} curated records.\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_repository(temp_root), [])

            # A stale count is reported.
            readme.write_text(
                f"Dataset {version} contains {count + 1} curated records.\n",
                encoding="utf-8",
            )
            errors = validate_repository(temp_root)
            self.assertTrue(
                any("documented record count" in error for error in errors), errors
            )

            # A stale version is reported.
            readme.write_text(
                f"Dataset 0.0.1 contains {count} curated records.\n", encoding="utf-8"
            )
            errors = validate_repository(temp_root)
            self.assertTrue(
                any("documented dataset version" in error for error in errors), errors
            )

            # Historical release notes are deliberately not checked.
            readme.write_text(
                f"Dataset {version} contains {count} curated records.\n"
                "Dataset 0.3.12 promotes four separately reviewed drafts.\n"
                "Dataset 0.3.15 adds three exact identities.\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_repository(temp_root), [])

    @staticmethod
    def _copy_repository_data(directory: Path, include_curation: bool = False) -> Path:
        shutil.copytree(ROOT / "schema", directory / "schema")
        shutil.copytree(ROOT / "data", directory / "data")
        if include_curation:
            shutil.copytree(ROOT / "curation", directory / "curation")
        return directory


if __name__ == "__main__":
    unittest.main()
