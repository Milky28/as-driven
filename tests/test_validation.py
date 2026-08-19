import json
from pathlib import Path
import shutil
import tempfile
import unittest

from as_driven_db.validate import (
    _resolve_pointer,
    expand_identity,
    validate_repository,
)
from as_driven_db.schema_validation import validate_instance


ROOT = Path(__file__).parents[1]


class ValidationTests(unittest.TestCase):
    def test_repository_is_valid(self) -> None:
        self.assertEqual(validate_repository(ROOT), [])

    def test_no_real_world_claim_rests_on_a_simulator_source(self) -> None:
        """The simulator's own material cannot establish a real car's controls.

        ams2cars.info is generated from Coanda's AMS2 spreadsheet, so it reports
        what the game models while reading as independent research. Four records
        cited it for /authentic_controls/transmission values.

        This is deliberately narrow. Recording an authentic control from a
        guided drive where no real-world source reaches it is this project's
        documented practice, and `audit-boundaries` already tracks those; the
        rule here is only that material published by or derived from the
        simulator may not be dressed up as evidence about the real car.
        """
        sources = json.loads(
            (ROOT / "data" / "v1" / "sources.json").read_text(encoding="utf-8")
        )["sources"]
        # in-game-observation is this project's own guided drives, which are how
        # the simulator layer is evidenced and are cited by design.
        # official-simulator is the simulator's own published material, which
        # describes what the game models and can never establish a real car.
        by_type = {source["source_id"]: source["source_type"] for source in sources}
        simulator_side = {
            source_id for source_id, kind in by_type.items()
            if kind == "official-simulator"
        }
        # This project's own guided drives evidence the simulator layer and are
        # cited on authentic paths by design, so they are neither the offence
        # nor the independent support that excuses one.
        own_drives = {
            source_id for source_id, kind in by_type.items()
            if kind == "in-game-observation"
        }
        self.assertTrue(simulator_side, "expected at least one simulator-side source")

        offenders = []
        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            for claim in record["provenance"]["claims"]:
                # Notes are prose about the record, not control values; a
                # release note legitimately supports one.
                real_world = [
                    pointer for pointer in claim["paths"]
                    if pointer.startswith("/authentic_controls")
                    and not pointer.startswith("/authentic_controls/notes")
                ]
                if not real_world:
                    continue
                refs = set(claim["source_refs"])
                cited = refs & simulator_side
                independent = refs - simulator_side - own_drives
                # Simulator material may sit beside real research as context.
                # It may not be the only thing holding a real-world claim up.
                if cited and not independent:
                    offenders.append(f"{record['record_id']}: {sorted(cited)}")
        self.assertEqual([], offenders)

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

            target = temp_root / "data" / "v1" / "cars" / "f301.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["simulators"][0]["source_refs"] = ["missing.source"]
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(any("unknown source_id" in error for error in errors))

    def test_schema_rejects_invalid_shift_actuation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            target = temp_root / "data" / "v1" / "cars" / "f301.json"
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
            target = temp_root / "data" / "v1" / "cars" / "f301.json"
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
            target = temp_root / "data" / "v1" / "cars" / "audi-r8-lmp1.json"
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
            "observation_id": "test-car.20260811t120000000z-1234abcd",
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

    def test_an_emptied_status_document_is_reported(self) -> None:
        # Dataset 0.3.65 shipped README.md, CLAUDE.md, AGENTS.md and
        # EARLY_ACCESS.md truncated to nothing by a bad version bump, and
        # validation passed: an empty file states no version to disagree with.
        for name in ("README.md", "CLAUDE.md", "AGENTS.md", "EARLY_ACCESS.md"):
            with self.subTest(name), tempfile.TemporaryDirectory() as directory:
                temp_root = self._copy_repository_data(Path(directory))
                index = json.loads(
                    (temp_root / "data" / "v1" / "index.json").read_text(encoding="utf-8")
                )
                version = index["dataset_version"]
                for other in ("README.md", "CLAUDE.md", "AGENTS.md", "EARLY_ACCESS.md"):
                    (temp_root / other).write_text(f"Dataset {version}\n", encoding="utf-8")

                self.assertEqual(validate_repository(temp_root), [])

                (temp_root / name).write_text("", encoding="utf-8")
                errors = validate_repository(temp_root)
                self.assertTrue(
                    any(name in error and "empty" in error for error in errors),
                    f"expected {name} to be reported as empty, got {errors}",
                )

    def test_every_dogleg_records_which_side_first_gear_sits_on(self) -> None:
        # A dogleg only establishes that first is outside the racing plane. The
        # McLaren MP4/4 mirrors the gate, so a record that leaves the side unset
        # must not have the side guessed for it downstream.
        cars = ROOT / "data" / "v1" / "cars"
        missing = []
        for path in sorted(cars.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            transmission = record["authentic_controls"]["transmission"]
            if transmission["shift_pattern"] != "dogleg-h":
                continue
            if transmission.get("first_gear_position") in (None, "unknown"):
                missing.append(record["record_id"])
        self.assertEqual(missing, [], "dogleg records must state which side first gear is on")

    def test_a_dogleg_cannot_put_first_gear_up(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            path = temp_root / "data" / "v1" / "cars" / "bmw-m1-procar.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["authentic_controls"]["transmission"]["first_gear_position"] = "up-left"
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            errors = validate_repository(temp_root)
            self.assertTrue(
                any("first_gear_position" in error for error in errors),
                f"expected a first_gear_position error, got {errors}",
            )

    def test_archetypes_in_the_registry_are_fully_specified_and_unique(self) -> None:
        """An archetype that is itself uncertain cannot describe anything.

        The registry is the one place where every field has to be settled: a
        record may carry gaps, but the thing it is compared against may not.
        """
        payload = json.loads(
            (ROOT / "data" / "v1" / "archetypes.json").read_text(encoding="utf-8")
        )
        identifiers = [entry["archetype_id"] for entry in payload["archetypes"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for entry in payload["archetypes"]:
            self.assertNotIn(
                "unknown",
                json.dumps(entry["transmission"]),
                entry["archetype_id"],
            )
            # An archetype names a mechanism. Racing class predicts one badly
            # enough that the dataset disproves it, so a class name in an id
            # would re-import an error the GT4 records already settle.
            self.assertNotRegex(entry["archetype_id"], r"(?:^|-)gt[0-9](?:-|$)")

    def test_a_declared_archetype_match_must_actually_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            path = temp_root / "data" / "v1" / "cars" / "milano-gt55.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            # milano-gt55 is the only curated record needing the clutch on a
            # downshift, so it cannot match the archetype it otherwise shares.
            record["archetype"] = {
                "archetype_id": "stick-6-seq-clutch-start-flat-up-blip-down",
                "classification": "matches",
            }
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            errors = validate_repository(temp_root)
            self.assertTrue(
                any(
                    "declared as matched" in error
                    and "/authentic_controls/transmission/downshift/clutch" in error
                    for error in errors
                ),
                f"expected a match error naming the downshift clutch, got {errors}",
            )

    def test_a_declared_deviation_records_the_departure_and_nothing_else(self) -> None:
        """Classifying a record adds no claim, so it needs no further approval.

        The archetype block sits outside `authentic_controls` and only describes
        values the record already states and an approval already covers. This
        copies `curation/` in so the approval checks actually run: a classified
        record must stay valid against the approval it already had.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory), include_curation=True)
            path = temp_root / "data" / "v1" / "cars" / "milano-gt55.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["archetype"] = {
                "archetype_id": "stick-6-seq-clutch-start-flat-up-blip-down",
                "classification": "deviates",
                "deviations": [
                    {
                        "path": "/authentic_controls/transmission/downshift/clutch",
                        "basis": "The real car requires the clutch for every downshift.",
                    }
                ],
            }
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            self.assertEqual(validate_repository(temp_root), [])

    def test_an_undeclared_departure_from_an_archetype_is_reported(self) -> None:
        """The rule the whole mechanism rests on.

        A record that quietly stops agreeing with its archetype has to fail,
        or an unintended change reads as one more car that happens to differ.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            path = temp_root / "data" / "v1" / "cars" / "milano-gt55.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["archetype"] = {
                "archetype_id": "stick-6-seq-clutch-start-flat-up-blip-down",
                "classification": "deviates",
                "deviations": [
                    {
                        "path": "/authentic_controls/transmission/forward_gears",
                        "basis": "Wrong field: the gear count agrees with the archetype.",
                    }
                ],
            }
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            errors = validate_repository(temp_root)
            self.assertTrue(
                any("undeclared departure" in error for error in errors),
                f"expected an undeclared departure error, got {errors}",
            )
            # And the reverse: naming a field that agrees is just as wrong,
            # because it describes a finding the record does not contain.
            self.assertTrue(
                any("where the record agrees" in error for error in errors),
                f"expected a spurious-deviation error, got {errors}",
            )

    def test_undetermined_needs_a_gap_that_leaves_the_choice_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))

            # formula-retro-gen2 leaves the gearbox and the downshift blip open,
            # and those are exactly what separate the five-speed synchromesh
            # archetype from the five-speed dog box. A drive settles it.
            open_choice = temp_root / "data" / "v1" / "cars" / "formula-retro-gen2.json"
            record = json.loads(open_choice.read_text(encoding="utf-8"))
            record["archetype"] = {
                "classification": "undetermined",
                "basis": "gearbox_type is unknown, which is what separates the two candidates.",
            }
            open_choice.write_text(json.dumps(record, indent=2), encoding="utf-8")
            self.assertEqual(validate_repository(temp_root), [])

            # bmw-m4-gt3 has a gap too, but only one archetype survives it, so
            # there is nothing left for a drive to decide.
            settled = temp_root / "data" / "v1" / "cars" / "bmw-m4-gt3.json"
            record = json.loads(settled.read_text(encoding="utf-8"))
            record["archetype"] = {
                "classification": "undetermined",
                "basis": "upshift throttle lift is unknown.",
            }
            settled.write_text(json.dumps(record, indent=2), encoding="utf-8")
            errors = validate_repository(temp_root)
            self.assertTrue(
                any("at least two candidate archetypes" in error for error in errors),
                f"expected a candidate-count error, got {errors}",
            )

    def test_an_unclassified_record_never_names_an_archetype(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            path = temp_root / "data" / "v1" / "cars" / "milano-gt55.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["archetype"] = {
                "archetype_id": "stick-6-seq-clutch-start-flat-up-blip-down",
                "classification": "no-archetype",
                "basis": "Reviewed and found to match none.",
            }
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            errors = validate_repository(temp_root)
            self.assertTrue(
                any("must be absent when classification" in error for error in errors),
                f"expected an archetype_id error, got {errors}",
            )

    def test_an_archetype_with_a_gap_in_it_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            path = temp_root / "data" / "v1" / "archetypes.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["archetypes"][0]["transmission"]["gearbox_type"] = "unknown"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            errors = validate_repository(temp_root)
            self.assertTrue(
                any("must be fully specified" in error for error in errors),
                f"expected a fully-specified error, got {errors}",
            )

    def test_declared_aero_packages_reproduce_the_written_identities(self) -> None:
        """The migration's safety proof, kept as a test.

        Declaring packages is only sound if expanding them gives back exactly the
        strings the records used to spell out. Every curated AMS2 telemetry name
        is grouped back into a base name and its packages, expanded again, and
        required to match what the record actually carries.
        """
        suffixes = {
            " - High Downforce": "high-downforce",
            " - Low Downforce": "low-downforce",
            " - Superspeedway": "superspeedway",
            " - Speedway": "speedway",
        }
        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            for simulator in record["simulators"]:
                if simulator["simulator"] != "ams2":
                    continue
                names = [
                    identity["value"]
                    for identity in simulator["identities"]
                    if identity["kind"] == "telemetry-name"
                ]
                groups: dict[str, set[str]] = {}
                for name in names:
                    for suffix, package in suffixes.items():
                        if name.endswith(suffix):
                            groups.setdefault(name[: -len(suffix)], set()).add(package)
                            break
                    else:
                        groups.setdefault(name, set()).add("base")
                rebuilt: set[str] = set()
                for base, packages in groups.items():
                    rebuilt.update(expand_identity("ams2", base, sorted(packages)))
                self.assertEqual(rebuilt, set(names), record["record_id"])

    def test_an_identity_two_records_both_claim_is_rejected(self) -> None:
        """The client throws on a duplicate exact identity while loading.

        Nothing on this side used to notice, so a dataset could validate and then
        fail to open. Expansion makes the collision easier to write by accident,
        which is what makes the check worth having now.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            path = temp_root / "data" / "v1" / "cars" / "bmw-m4-gt3.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["simulators"][0]["identities"].append(
                {"kind": "telemetry-name", "value": "Audi R8 LMS GT3"}
            )
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            errors = validate_repository(temp_root)
            self.assertTrue(
                any("is already claimed by" in error for error in errors),
                f"expected a collision error, got {errors}",
            )

    def test_a_record_cannot_claim_the_same_identity_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            path = temp_root / "data" / "v1" / "cars" / "bmw-m4-gt3.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            # A declared package alongside the hand-written spelling it replaces
            # is what a half-finished migration looks like.
            record["simulators"][0]["identities"].append(
                {
                    "kind": "telemetry-name",
                    "value": "BMW M4 GT3",
                    "aero_packages": ["base"],
                }
            )
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            errors = validate_repository(temp_root)
            self.assertTrue(
                any("claimed twice by this record" in error for error in errors),
                f"expected a self-duplicate error, got {errors}",
            )

    def test_aero_packages_expand_a_base_name_on_a_telemetry_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            path = temp_root / "data" / "v1" / "cars" / "bmw-m4-gt3.json"
            base = json.loads(path.read_text(encoding="utf-8"))

            # A name that already carries a package would expand to a doubled one.
            record = json.loads(json.dumps(base))
            record["simulators"][0]["identities"].append(
                {
                    "kind": "telemetry-name",
                    "value": "Something - Low Downforce",
                    "aero_packages": ["base"],
                }
            )
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            self.assertTrue(
                any(
                    "aero_packages expands a base name" in error
                    for error in validate_repository(temp_root)
                )
            )

            # A class is not a name, so it has no package to expand.
            record = json.loads(json.dumps(base))
            record["simulators"][0]["identities"].append(
                {"kind": "class-id", "value": "Made_Up", "aero_packages": ["base"]}
            )
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            self.assertTrue(
                any(
                    "only valid on a telemetry-name" in error
                    for error in validate_repository(temp_root)
                )
            )

    @staticmethod
    def _copy_repository_data(directory: Path, include_curation: bool = False) -> Path:
        shutil.copytree(ROOT / "schema", directory / "schema")
        shutil.copytree(ROOT / "data", directory / "data")
        if include_curation:
            shutil.copytree(ROOT / "curation", directory / "curation")
        return directory


if __name__ == "__main__":
    unittest.main()
