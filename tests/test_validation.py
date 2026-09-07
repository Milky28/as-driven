import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from as_driven_db.validate import (
    AERO_SUFFIXES,
    SHIFT_ACTUATION,
    SIMULATOR_GAME_NAMES,
    SIMULATORS,
    LIVE_OBSERVATION_ID_RE,
    OBSERVING_SIMULATORS,
    _resolve_pointer,
    expand_identity,
    validate_repository,
)
from as_driven_db.schema_validation import validate_instance


ROOT = Path(__file__).parents[1]


class ValidationTests(unittest.TestCase):
    def test_ci_validates_the_default_branch(self):
        """Pushes to main run the suite, and a person can start a run by hand.

        The list also named codex/stabilization while that branch was the
        default. It was deleted once main took over, and a workflow naming a
        branch that does not exist is a rule nothing enforces.
        """
        workflow = (
            ROOT / ".github" / "workflows" / "validate.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("branches: [main]", workflow)
        self.assertNotIn("codex/stabilization", workflow)
        self.assertIn("workflow_dispatch:", workflow)

    def test_display_names_do_not_sort_the_catalog_by_year(self):
        leading_year = re.compile(r"^(?:19|20)\d{2}(?:-(?:19|20)\d{2})?\s")
        offenders = []
        for record_path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            display_name = record["identity"]["display_name"]
            if leading_year.match(display_name):
                offenders.append(record["record_id"])
        self.assertEqual(
            offenders,
            [],
            "display names begin with the car name; year belongs in identity metadata or a suffix",
        )

    def test_a_drive_alone_never_establishes_a_synchromesh_running_clutch(self) -> None:
        """A clutchless shift the simulator accepts is not authentic technique.

        The guided drive asks whether the simulator lets you change gear without
        the clutch, and that answer was written into `authentic_controls` as a
        real-car claim. On a dog box clutchless shifting is how the car is
        driven; on a synchromesh car it is a trick that wears the synchros. 72
        H-pattern records told the driver of a Chevette, a Fusca and a 2002
        turbo that no clutch was needed to change gear.

        A synchromesh record may still say `not-required`, but only if something
        other than the drive supports it.
        """
        # The one record whose own reviewed research reached the opposite
        # conclusion, in as many words: "supports clutchless running upshifts
        # with a throttle lift as ordinary technique". That claim is retained
        # rather than overruled, and named here so it stays a decision somebody
        # made rather than a silent survivor of the correction.
        reviewed_exceptions = {"lamborghini-miura-sv"}
        offenders = []
        for record_path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            if record["record_id"] in reviewed_exceptions:
                continue
            transmission = record["authentic_controls"]["transmission"]
            if transmission.get("gearbox_type") != "synchromesh":
                continue
            for action in ("upshift", "downshift"):
                if transmission[action]["clutch"] == "not-required":
                    offenders.append(f"{record['record_id']} {action}")
        self.assertEqual(
            offenders,
            [],
            "a synchromesh gearbox is shifted with the clutch as authentic "
            "technique; a drive showing the simulator accepts a clutchless shift "
            "belongs in a simulator override, not in authentic_controls",
        )


    def test_data_validation_does_not_depend_on_prose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_repository_data(Path(directory))
            (root / "README.md").write_text("Dataset 0.0.1 contains 1 reviewed record.\n")
            (root / "AGENTS.md").write_text("")
            self.assertEqual([], validate_repository(root))

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
        negated = re.compile(r"^(no|nothing|neither)\b", re.IGNORECASE)
        offenders = []
        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            for claim in record["provenance"]["claims"]:
                if not any(p.endswith("/gearbox_type") for p in claim["paths"]):
                    continue
                sentences = re.split(r"(?<=[.!?])\s+", claim["basis"])
                positive_inference = any(
                    inferred.search(sentence)
                    and not negated.search(sentence.lstrip())
                    for sentence in sentences
                )
                if positive_inference and claim["confidence"] in {"high", "verified"}:
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

    def test_driver_summary_stays_within_the_schema_limit(self) -> None:
        schema = json.loads((ROOT / "schema/v1/car-record.schema.json").read_text())
        limit = schema["properties"]["driver_summary"]["maxLength"]
        for path in sorted((ROOT / "data/v1/cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            summary = record.get("driver_summary")
            if summary is not None:
                self.assertLessEqual(len(summary), limit, record["record_id"])

    def test_schema_rejects_invalid_transmission_values(self) -> None:
        schema = json.loads((ROOT / "schema/v1/car-record.schema.json").read_text())
        record = json.loads((ROOT / "data/v1/cars/f301.json").read_text())
        cases = [
            ("forward_gears", 0), ("forward_gears", 21), ("forward_gears", True),
            ("standing_start_clutch", "maybe"), ("first_gear_position", "middle"),
            ("upshift/clutch", "maybe"), ("upshift/throttle_lift", "maybe"),
            ("downshift/manual_blip", "maybe"), ("upshift/automatic_cut", "maybe"),
            ("downshift/automatic_blip", "maybe"),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                candidate = json.loads(json.dumps(record))
                target = candidate["authentic_controls"]["transmission"]
                parts = field.split("/")
                for part in parts[:-1]:
                    target = target[part]
                target[parts[-1]] = value
                errors = validate_instance(candidate, schema, "car")
                self.assertTrue(any(parts[-1] in error for error in errors), errors)

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
            "dataset_version": "0.4.20",
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
                        # This fixture exists to exercise the source_id
                        # convention, so no record cites it. Declaring that keeps
                        # the uncited-source rule out of the way of this test.
                        "establishes": "nothing",
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
            self.assertEqual(
                _with_source_id(
                    "ams2.local-live-test-car-controls.1.6.9.91.correction-acde1234"
                ),
                [],
            )

            # Other publishers keep their own prefixes.
            self.assertEqual(
                _with_source_id("simhub.local-ams2-identities.9.11.23"), []
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

    def test_a_gearbox_that_disagrees_with_its_blip_says_so(self) -> None:
        """A synchromesh does not need a blip for the gear to engage.

        Where a record demands one anyway and nothing else rev-matches, the two
        facts disagree. That is allowed - the drive found what it found - but it
        must be visible, because the usual explanation is that the simulator
        demands something the real gearbox does not, which is an override
        waiting to be written rather than a value to quietly adjust.

        The check deliberately ignores cars whose automatic blip is yes: a dog
        box that needs rev-matching and gets it electronically is consistent,
        and the two Carrera Cup entries are exactly that.
        """
        undeclared = []
        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            transmission = record["authentic_controls"]["transmission"]
            downshift = transmission["downshift"]
            if downshift["automatic_blip"] == "yes":
                continue
            if transmission["gearbox_type"] != "synchromesh":
                continue
            if downshift["manual_blip"] != "required":
                continue
            prose = json.dumps(record.get("archetype", {})) + json.dumps(
                record["authentic_controls"].get("notes", [])
            )
            if "synchromesh" not in prose:
                undeclared.append(record["record_id"])
        self.assertEqual([], undeclared)

    def test_a_fictionalised_car_is_never_given_a_gearbox_it_cannot_have(self) -> None:
        """The retirement, pinned so a later pass cannot undo it helpfully.

        These cars stand in for an era rather than representing a chassis, so no
        manufacturer, homologation sheet or registry exists to consult. The
        failure mode this guards is the tempting one: filling the field in from
        the era the car evokes, which is reasoning about a period rather than
        evidence about a car. Each record's archetype basis has to say the gap is
        permanent, or the queue will keep collecting them.
        """
        # Keyed on what the record says about itself, not on its name. Keying it
        # on the name is how four fictionalised cars were missed the first time,
        # including one argued back into the queue because its category is real
        # even though the car is not.
        invented = re.compile(
            r"fictionalis|fictionaliz|no real-world chassis"
            r"|unique real-world referent is not established",
            re.IGNORECASE,
        )
        retired = 0
        established = 0
        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            identity = record["identity"].get("real_world_identity_notes") or ""
            if not invented.search(identity):
                continue
            # A series whose regulation leaves the gearbox free is closed for its
            # own reason and is not a retirement.
            if "livre" in json.dumps(record) or "free for all makes" in json.dumps(record):
                continue
            transmission = record["authentic_controls"]["transmission"]
            if transmission["gearbox_type"] == "unknown":
                self.assertIn(
                    "Retired from the gearbox research queue",
                    json.dumps(record["archetype"]),
                    record["record_id"],
                )
                retired += 1
                continue
            # Being fictionalised does not make the field unreachable by itself.
            # Where the mechanism is visible the drive settles it: paddles are
            # visible, and so is a sequential stick moving one gear at a time.
            # What no drive can see, and no chassis exists to research, is
            # whether an H-pattern box engages through synchronisers or dog
            # rings - which is every one of the retired records.
            self.assertNotEqual(
                transmission["shift_actuation"], "h-pattern", record["record_id"]
            )
            established += 1
        self.assertEqual((retired, established), (22, 14))

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

    def test_a_declared_archetype_match_never_fills_an_unknown(self) -> None:
        """A compatible family label is not evidence for a missing field."""
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            path = temp_root / "data" / "v1" / "cars" / "audi-r8-lms-gt3.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                record["authentic_controls"]["transmission"]["upshift"][
                    "automatic_cut"
                ],
                "unknown",
            )
            self.assertEqual(record["archetype"]["classification"], "matches")
            self.assertEqual(validate_repository(temp_root), [])

    def test_throttle_only_cut_audit_stays_retracted(self) -> None:
        """Throttle position cannot uniquely identify an ignition cut."""
        affected = {
            "aston-martin-valkyrie",
            "audi-r8-lms-gt3-evo-ii",
            "audi-r8-lms-gt3",
            "chevrolet-corvette-c8-z06-z07-upgrade",
            "chevrolet-cruze-stock-car-2024",
            "lamborghini-huracan-gt3-evo2",
            "lamborghini-veneno-roadster",
            "maserati-gt2-stradale",
            "renault-r25",
            "renault-r26",
            "renault-r28",
            "toyota-corolla-stock-car-2024",
        }
        for record_id in affected:
            record = json.loads(
                (ROOT / "data" / "v1" / "cars" / f"{record_id}.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                record["authentic_controls"]["transmission"]["upshift"][
                    "automatic_cut"
                ],
                "unknown",
                record_id,
            )
            ams2 = next(
                view for view in record["simulators"] if view["simulator"] == "ams2"
            )
            self.assertEqual(ams2["behavior"]["shift_cut"], "unknown", record_id)

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

    def test_behavior_shift_type_restates_the_actuation_rather_than_respelling_it(
        self,
    ) -> None:
        """`shift_type` was an unconstrained string and grew nine spellings.

        Three mechanisms, spelled nine ways across the AMS2 spreadsheet era:
        h-pattern beside H-pattern and H-Dogleg, sequential-paddles beside
        Paddles and Seq-Paddle, sequential-stick beside Seq-Stick and
        "Sequential stick". None ever disagreed with its own record's actuation,
        so the invariant worth stating is equality, not a list of spellings.

        Two ways to break it: an old spelling of the right mechanism, and the
        right spelling of the wrong one.
        """
        for value in ("Paddles", "h-pattern"):
            with tempfile.TemporaryDirectory() as temp:
                temp_root = self._copy_repository_data(Path(temp))
                path = temp_root / "data" / "v1" / "cars" / "audi-r8-lms-gt3-evo-ii.json"
                record = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    record["authentic_controls"]["transmission"]["shift_actuation"],
                    "sequential-paddles",
                    "fixture car changed; pick another paddle car",
                )
                record["simulators"][0]["behavior"]["shift_type"] = value
                path.write_text(json.dumps(record, indent=2), encoding="utf-8")
                self.assertTrue(
                    any(
                        "does not match the effective shift_actuation" in error
                        for error in validate_repository(temp_root)
                    ),
                    f"{value!r} was accepted as a shift_type",
                )

    def test_every_curated_shift_type_uses_the_actuation_vocabulary(self) -> None:
        """The normalisation itself, asserted over the whole dataset."""
        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            for simulator in record["simulators"]:
                self.assertIn(
                    simulator["behavior"]["shift_type"],
                    SHIFT_ACTUATION,
                    f"{record['record_id']} ({simulator['simulator']})",
                )

    def test_an_undetected_game_version_cannot_reach_a_curated_record(self) -> None:
        """"unknown" is what the plugin writes when it cannot read a version.

        Assetto Corsa EVO exposes none anywhere on disk - its executable has no
        version resource at all - so the first AC EVO drive logged
        `game_version: "unknown"` while the game's own settings screen said
        0.8.1. A draft may carry that honestly; a curated record may not, because
        an observation is only reproducible against an exact build. Only "latest"
        was refused before, so "unknown" would have been curated silently.
        """
        for value in ("unknown", "UNKNOWN", "  ", "latest"):
            with tempfile.TemporaryDirectory() as temp:
                temp_root = self._copy_repository_data(Path(temp))
                path = temp_root / "data" / "v1" / "cars" / "audi-r8-lmp1.json"
                record = json.loads(path.read_text(encoding="utf-8"))
                record["simulators"][0]["verified_game_version"] = value
                path.write_text(json.dumps(record, indent=2), encoding="utf-8")
                self.assertTrue(
                    any(
                        "verified_game_version cannot be" in error
                        for error in validate_repository(temp_root)
                    ),
                    f"{value!r} was accepted as a game version",
                )

    def test_the_aero_suffix_table_and_the_schema_enum_say_the_same_thing(self) -> None:
        """Two lists that must agree, with nothing making them agree.

        `AERO_SUFFIXES` decides what a declared package expands to and the schema's
        `aeroPackage` enum decides which packages a record may declare. A package
        in the enum but not the table used to expand to nothing, which is a car
        that silently stops matching rather than a validation failure.
        """
        schema = json.loads(
            (ROOT / "schema" / "v1" / "car-record.schema.json").read_text(encoding="utf-8")
        )
        enum = set(schema["$defs"]["aeroPackage"]["enum"])
        for simulator, suffixes in AERO_SUFFIXES.items():
            self.assertEqual(
                set(suffixes),
                enum,
                f"{simulator}'s suffix table and the schema enum disagree",
            )

    def test_the_client_and_the_validator_spell_aero_packages_identically(self) -> None:
        """The client builds its own table in C#; a drift there is a silent miss.

        AsDrivenDatabase.BuildAeroSuffixes is the matching side of the same
        contract. If it and AERO_SUFFIXES ever disagree by a character, a car
        matches in validation and not in the plugin, or the reverse.
        """
        source = (
            ROOT / "simhub" / "AsDriven.Core" / "AsDrivenDatabase.cs"
        ).read_text(encoding="utf-8")
        for simulator, suffixes in AERO_SUFFIXES.items():
            for package, suffix in suffixes.items():
                literal = '"' + suffix + '"' if suffix else "string.Empty"
                expected = f'{simulator}["{package}"] = {literal};'
                self.assertIn(
                    expected,
                    source,
                    f"AsDrivenDatabase.cs does not spell {simulator}/{package} as {suffix!r}",
                )

    def test_an_unknown_aero_package_is_a_fault_rather_than_a_dropped_name(self) -> None:
        """Matches AsDrivenDatabase.ExpandIdentity, which throws on the same input.

        Dropping the package would expand the identity to nothing and leave the
        car unmatched at one kind of circuit, with no error anywhere.
        """
        with self.assertRaises(ValueError):
            expand_identity("ams2", "Some Car", ["medium-downforce"])

    def test_a_simulator_without_a_suffix_table_keeps_its_literal_name(self) -> None:
        """Also matching the client: an unknown simulator falls back to the literal.

        Returning an empty list here was the actual bug - the first `ac-evo`
        record to declare packages would have expanded to no names at all.
        """
        self.assertEqual(expand_identity("ac-evo", "Some Car", ["base"]), ["Some Car"])

    def test_a_second_simulators_drive_source_follows_the_naming_convention(self) -> None:
        """The convention was enforced only for source ids beginning `ams2.`.

        An `ac-evo` drive could therefore be named anything at all, which is the
        one thing that had to change before a second simulator's evidence could
        be trusted to be findable from its name.
        """
        self.assertTrue(
            LIVE_OBSERVATION_ID_RE.fullmatch("ac-evo.local-live-porsche-911-gt3-controls.0.1.2")
        )
        self.assertTrue(
            LIVE_OBSERVATION_ID_RE.fullmatch(
                "ac-evo.local-live-porsche-911-gt3-controls.0.1.2.correction-acde1234"
            )
        )
        self.assertTrue(
            LIVE_OBSERVATION_ID_RE.fullmatch(
                "ac.local-live-gt-vortex-v10-controls.14923034.implementation-49377ed1"
            )
        )
        self.assertFalse(LIVE_OBSERVATION_ID_RE.fullmatch("ac-evo.some-drive"))
        self.assertNotIn("other", OBSERVING_SIMULATORS)

    def test_a_cross_simulator_rim_split_is_listed_for_re_verification(self) -> None:
        """A record is one car, so its entries describe one rim.

        Where they disagree it is either a real modelling difference or the
        vocabulary boundary that predates the current definitions, and only a
        look at the cockpit separates those. Neither is a validation error, so
        this test does not forbid the split; it requires the record to be listed
        in the worklist, because an unlisted one is a disagreement nobody is
        going to look at again.
        """
        document = (ROOT / "docs" / "wheel-rim-reverification.md").read_text(
            encoding="utf-8"
        )
        # Scoped to the section about this kind of split. Several of these
        # records appear elsewhere in the file for unrelated reasons, and a
        # mention there would satisfy a whole-file search while leaving the
        # cross-simulator disagreement itself undocumented.
        heading = "## 1b. One car recorded under more than one shape across simulators"
        start = document.index(heading)
        end = document.index("\n## ", start + len(heading))
        worklist = document[start:end]
        unlisted = []
        for record_path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            shapes = {
                (entry.get("behavior", {}).get("wheel_rim_type") or {}).get("normalized")
                for entry in record["simulators"]
            }
            shapes.discard(None)
            if len(shapes) > 1 and f"`{record['record_id']}`" not in worklist:
                unlisted.append(record["record_id"])
        self.assertEqual([], unlisted)

    def test_a_curated_dogleg_always_names_the_side_first_gear_is_on(self) -> None:
        """A dogleg is not proposed until the side is established.

        `dogleg-h` is the most inferable value in the dataset. A car's
        reputation suggests it, period photographs are read at a glance, and a
        gate knob is easy to mis-see. Requiring the side requires a source or a
        clear look, which is the same work that would have caught a wrong
        dogleg, so the requirement is a check on the pattern rather than an
        extra field to fill.

        The client still renders a sideless dogleg, because another consumer's
        data may contain one and the schema still permits it. This is a rule
        about what curation produces. Where the side is not established the
        pattern stays `unknown`.
        """
        offenders = []
        for record_path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            transmission = record["authentic_controls"]["transmission"]
            if transmission.get("shift_pattern") != "dogleg-h":
                continue
            side = transmission.get("first_gear_position")
            if side in (None, "unknown"):
                offenders.append(
                    "%s: dogleg-h without an established side; keep the pattern "
                    "unknown until research settles it" % record["record_id"]
                )
            elif side in ("up-left", "up-right"):
                offenders.append(
                    "%s: a dogleg puts first outside the racing plane, so it "
                    "cannot be up" % record["record_id"]
                )
        self.assertEqual([], offenders)

    def test_python_and_the_client_accept_the_same_game_names(self) -> None:
        """Two copies of the same table, pinned against each other.

        The client canonicalises a game name when a drive is taken; Python does
        it again when a held drive is released. A spelling one accepts and the
        other does not is how a drive gets stranded: filed as `other` by the
        client and never recognised afterwards, or the reverse.
        """
        source = (
            ROOT / "simhub" / "AsDriven.Core" / "AsDrivenDatabase.cs"
        ).read_text(encoding="utf-8")
        start = source.index("public static string CanonicalizeSimulator")
        end = source.index("private static void IndexRecord", start)
        body = source[start:end]

        client: dict[str, set[str]] = {}
        pending: set[str] = set()
        for match in re.finditer(r'compact == "([a-z0-9-]+)"|return "([a-z0-9-]+)";', body):
            spelling, simulator = match.group(1), match.group(2)
            if spelling:
                pending.add(spelling)
            elif simulator != "null":
                client.setdefault(simulator, set()).update(pending)
                pending = set()

        python = {name: set(values) for name, values in SIMULATOR_GAME_NAMES.items()}
        self.assertEqual(python, client)

    def test_a_record_never_denies_a_source_it_cites(self) -> None:
        """The note saying nothing was established used to be a constant.

        It was printed under a line listing the very fields it denied, so the
        Radical SR3 said its real-car sources establish no cut or blip behaviour
        while citing the owner manual that says an auto blipper is fitted. Both
        halves are generated now, and this holds them together: a family the
        note calls unknown must have no value backed by anything other than the
        guided drive.
        """
        families = {
            "launch technique": ["/authentic_controls/transmission/standing_start_clutch"],
            "cut and blip behavior": [
                "/authentic_controls/transmission/upshift/automatic_cut",
                "/authentic_controls/transmission/downshift/automatic_blip",
                "/authentic_controls/transmission/downshift/manual_blip",
            ],
            "selector pattern": ["/authentic_controls/transmission/shift_pattern"],
        }

        def value_at(record, pointer):
            node = record
            for part in pointer.strip("/").split("/"):
                if isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    return None
            return node

        offenders = []
        for record_path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            notes = " ".join(record["authentic_controls"].get("notes", []))
            if "reviewed real-car sources do not establish" not in notes:
                continue
            for family, pointers in families.items():
                if family not in notes:
                    continue
                for pointer in pointers:
                    if value_at(record, pointer) in (None, "unknown"):
                        continue
                    backed = any(
                        (pointer in claim["paths"]
                         or any(pointer.startswith(p + "/") for p in claim["paths"]))
                        and any(".local-live-" not in ref for ref in claim["source_refs"])
                        for claim in record["provenance"]["claims"]
                    )
                    if backed:
                        offenders.append(
                            "%s: note denies %s, but %s is sourced"
                            % (record["record_id"], family, pointer)
                        )
        self.assertEqual([], offenders)

    def test_every_registered_source_is_cited_or_declares_it_settled_nothing(
        self,
    ) -> None:
        """A dropped citation must not hide among the deliberate negatives.

        Research that established nothing is worth registering. The M1's Group 4
        homologation form predates the synchroniser field, so it is silent on
        construction rather than negative about it, and an exterior-only period
        photograph of the exact Alfa chassis rules out no cockpit fitting. Both
        are kept so the negative result is auditable and the same search is not
        run twice.

        That makes an uncited source ordinary, which is the problem: a citation
        deleted by accident lands in the same set and looks like one more
        documented negative. So the negatives declare themselves, and anything
        uncited without the declaration is an error.
        """
        sources = json.loads(
            (ROOT / "data" / "v1" / "sources.json").read_text(encoding="utf-8")
        )["sources"]

        used: set[str] = set()

        def collect(node) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "source_refs" and isinstance(value, list):
                        used.update(value)
                    else:
                        collect(value)
            elif isinstance(node, list):
                for item in node:
                    collect(item)

        for path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            collect(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted((ROOT / "curation").glob("*.json")):
            collect(json.loads(path.read_text(encoding="utf-8")))

        undeclared = [
            source["source_id"]
            for source in sources
            if source["source_id"] not in used
            and source.get("establishes") != "nothing"
        ]
        self.assertEqual([], undeclared)

        # The declaration is not a way to keep a citation quiet either.
        contradictory = [
            source["source_id"]
            for source in sources
            if source.get("establishes") == "nothing" and source["source_id"] in used
        ]
        self.assertEqual([], contradictory)

        # A source that settled nothing still has to say what was examined.
        silent = [
            source["source_id"]
            for source in sources
            if source.get("establishes") == "nothing" and not source.get("notes")
        ]
        self.assertEqual([], silent)

    def test_a_summary_never_denies_technique_the_record_establishes(self) -> None:
        """A summary must not tell the driver the opposite of its own card.

        Five summaries said no source established how the real car was driven
        while the card beside them read "Clutch required" as the real-car
        baseline. Four were made stale by the H-pattern launch derivation and one
        had always overstated: the Mustang required the clutch for every shift
        and still said its technique was established by nothing.

        The wording was defensible read literally - a mechanism established the
        launch clutch, not a source - and that is exactly why it needs a test.
        The driver reads the sentence, not the provenance.
        """
        denial = re.compile(
            r"no (reviewed )?source establishes how the real"
            r"|technique is established by no source"
            r"|real car's technique is (not )?established",
            re.IGNORECASE,
        )
        offenders = []
        for record_path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            summary = record.get("driver_summary") or ""
            if not denial.search(summary):
                continue
            transmission = record["authentic_controls"]["transmission"]
            established = [
                name
                for name, value in (
                    ("standing start clutch", transmission.get("standing_start_clutch")),
                    ("upshift clutch", transmission.get("upshift", {}).get("clutch")),
                    ("downshift clutch", transmission.get("downshift", {}).get("clutch")),
                    ("upshift lift", transmission.get("upshift", {}).get("throttle_lift")),
                    ("downshift blip", transmission.get("downshift", {}).get("manual_blip")),
                )
                if value not in (None, "unknown")
            ]
            if established:
                offenders.append(
                    "%s: the summary denies established technique, but %s"
                    % (record["record_id"], ", ".join(established))
                )
        self.assertEqual([], offenders)

    def test_an_override_describes_the_situation_it_is_actually_in(self) -> None:
        """A gap in the evidence and a departure from the car are not one thing.

        The promoter wrote one sentence for both. "The reviewed real-car sources
        did not establish the same value" is true where the baseline is open and
        false where the baseline says something else, and 35 overrides carried it
        over the second case. It is printed on the public comparison view as the
        reason for the row, so it is the explanation a driver reads.

        A third case is not a difference at all. 42 overrides agreed with a
        baseline that had caught up with them - 30 from the standing-start
        derivation, 10 more from the throttle-lift derivation before it, whose
        conditions still said the lift claim "remains open" after it had been
        settled. Both rules run only over an established baseline: an override
        restating an `unknown` is how a retracted measurement is recorded, and
        RaceRoom's unmeasurable blip depends on it.
        """
        from as_driven_db.validate import _validate_override_conditions

        def check(authentic, override):
            record = {
                "authentic_controls": {"transmission": {"upshift": authentic}},
                "simulators": [{"simulator": "ams2", "overrides": [override]}],
            }
            errors: list[str] = []
            _validate_override_conditions(record, "fixture", errors)
            return errors

        path = "/authentic_controls/transmission/upshift/throttle_lift"
        gap = "...; the reviewed real-car sources did not establish the same value."
        departure = "...; the sources establish a different value."

        # Open baseline: the gap wording is right and the values may agree.
        self.assertEqual([], check({"throttle_lift": "unknown"},
                                   {"path": path, "value": "not-required", "condition": gap}))
        # Established and genuinely different: allowed, with honest wording.
        self.assertEqual([], check({"throttle_lift": "required"},
                                   {"path": path, "value": "not-required", "condition": departure}))
        # Established and different, but the wording denies the evidence exists.
        self.assertEqual(
            1,
            len(check({"throttle_lift": "required"},
                      {"path": path, "value": "not-required", "condition": gap})),
        )
        # Established and identical: not a departure at all.
        restating = check({"throttle_lift": "required"},
                          {"path": path, "value": "required", "condition": departure})
        self.assertEqual(1, len(restating))
        self.assertIn("restates the authentic value", restating[0])

    def test_a_sourced_rim_disagreement_is_an_explicit_audited_override(self) -> None:
        """A photograph of the real car outranks a look at a simulator.

        Where the real rim rests on a manufacturer cockpit photograph, an entry
        observed after the vocabulary was defined must agree with it or carry an
        explicit simulator override and disagreement-audit finding. This keeps a
        real modelling departure representable without letting a later cockpit
        observation silently rewrite the sourced real-car baseline.
        """
        vocabulary_defined = "2026-08-16"
        audit = json.loads(
            (ROOT / "research" / "simulator-disagreement-audit.json").read_text(
                encoding="utf-8"
            )
        )
        findings = {
            (finding["record_id"], finding["path"]): finding
            for finding in audit["findings"]
        }
        offenders = []
        for record_path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            wheel = record["authentic_controls"]["steering"]["wheel_rim"]
            shape = wheel.get("shape")
            if shape in (None, "unknown"):
                continue
            sourced = any(
                any("wheel_rim" in path for path in claim["paths"])
                and any("cockpit-photo" in ref for ref in claim["source_refs"])
                for claim in record["provenance"]["claims"]
            )
            if not sourced:
                continue
            for entry in record["simulators"]:
                observed = (entry["behavior"].get("wheel_rim_type") or {}).get("normalized")
                when = entry.get("verified_at") or ""
                if observed and when >= vocabulary_defined and observed != shape:
                    pointer = "/authentic_controls/steering/wheel_rim/shape"
                    explicit = any(
                        override.get("path") == pointer
                        and override.get("value") == observed
                        for override in entry.get("overrides", [])
                    )
                    finding = findings.get((record["record_id"], pointer))
                    audited = bool(
                        finding
                        and any(
                            view.get("simulator") == entry["simulator"]
                            and view.get("value") == observed
                            and view.get("relationship_to_authentic")
                            == "departs-from-baseline"
                            for view in finding.get("simulator_views", [])
                        )
                    )
                    if not explicit or not audited:
                        offenders.append(
                            "%s: %s saw %s on %s, against a photographed %s"
                            % (
                                record["record_id"],
                                entry["simulator"],
                                observed,
                                when,
                                shape,
                            )
                        )
        self.assertEqual([], offenders)

    def test_a_registered_simulator_reaches_every_place_that_enumerates_one(self) -> None:
        """Registering a simulator is a list of places, so the list is a test.

        Half-registering one fails in the least useful way: drives are accepted
        and then rejected further down, or the site renders a bare id. Each site
        below is named in docs/registering-a-simulator.md, and this test is what
        makes that document true rather than aspirational.

        `other` is deliberately exempt. It is the absence of a registration, so
        it has no product name, no filter label and no canonical spelling.

        A *reserved* id is a third case, and this test is where it stops being
        an inconsistency and becomes a stated one. `ac-rally` sits in the enums
        so that a record naming it would validate, while the client does not
        canonicalise it and nothing has been driven in it. Reserved ids are held
        to the schema enums only; promoting one to live means wiring the client
        sites and deleting it from this set.
        """
        reserved = {"ac-rally"}
        simulators = SIMULATORS - {"other"} - reserved
        missing: list[str] = []

        def require(label: str, text: str, needles: dict[str, str]) -> None:
            for simulator, needle in needles.items():
                if needle not in text:
                    missing.append(f"{label}: {simulator}")

        schema_dir = ROOT / "schema" / "v1"
        for name in (
            "car-record.schema.json",
            "curation-approval.schema.json",
            "verification-observation.schema.json",
        ):
            text = (schema_dir / name).read_text(encoding="utf-8")
            # Reserved ids are required here and nowhere else.
            require(name, text, {s: f'"{s}"' for s in simulators | reserved})

        site = (ROOT / "as_driven_db" / "site.py").read_text(encoding="utf-8")
        for simulator in simulators:
            # Both the product name and the short filter label, which are two
            # separate maps and have been forgotten separately before.
            if site.count(f'"{simulator}": "') < 2:
                missing.append(f"site.py display and filter labels: {simulator}")

        core = ROOT / "simhub" / "AsDriven.Core"
        writer = (core / "VerificationObservation.cs").read_text(encoding="utf-8")
        require("VerificationObservation.cs", writer, {s: f'"{s}"' for s in simulators})

        database = (core / "AsDrivenDatabase.cs").read_text(encoding="utf-8")
        for simulator in simulators:
            # CanonicalizeSimulator plus the product, display and short names.
            if database.count(f'"{simulator}"') < 4:
                missing.append(f"AsDrivenDatabase.cs canonicalise and name maps: {simulator}")

        self.assertEqual([], sorted(missing))

    def test_the_schema_only_states_constraints_the_validator_enforces(self) -> None:
        """A schema keyword nobody checks is worse than no keyword at all.

        The repository's validator is deliberately dependency-free and covers a
        subset of JSON Schema. Anything outside that subset reads as a rule while
        enforcing nothing, so each such keyword must have a real check behind it
        somewhere else. This test does not forbid them; it names them, so that
        adding one is a deliberate act with a stated home rather than an
        assumption that the schema is doing the work.
        """
        supported = {
            "$schema", "$defs", "$ref", "$comment", "title", "description",
            "type", "properties", "required", "enum", "const", "pattern",
            "format", "items", "minItems", "uniqueItems", "minLength",
            "minimum", "maximum", "additionalProperties", "not", "default",
            "examples", "propertyNames",
        }
        # Each of these is enforced by code or by a test rather than by the
        # validator, and is kept in the schema because the schema is the
        # normative contract a standards-compliant consumer would read.
        enforced_elsewhere = {
            # The driver-summary regression reads its limit from the schema.
            # Intake separately checks source_game_name.
            "maxLength",
            "allOf",
            "if",
            "then",
        }
        seen: set[str] = set()

        def walk(node: object) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    seen.add(key)
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        for schema_path in sorted((ROOT / "schema" / "v1").glob("*.json")):
            walk(json.loads(schema_path.read_text(encoding="utf-8")))

        # Keywords are mixed with property names, so only the ones we know to be
        # schema vocabulary are judged.
        vocabulary = supported | enforced_elsewhere | {
            "oneOf", "anyOf", "maxItems", "exclusiveMinimum", "exclusiveMaximum",
            "multipleOf", "maxProperties", "minProperties", "contains",
            "patternProperties", "dependentRequired", "dependentSchemas", "else",
        }
        unaccounted = (seen & vocabulary) - supported - enforced_elsewhere
        self.assertEqual(
            set(),
            unaccounted,
            "schema keywords the validator ignores and nothing else enforces: "
            + ", ".join(sorted(unaccounted)),
        )

    def test_an_established_mechanism_leaves_no_technique_unknown(self) -> None:
        """A mechanism the record establishes settles the technique that follows.

        This runs one way only. An established gearbox decides what the driver
        has to do; what the driver does never decides the gearbox, which is why
        nothing here reads a construction off a technique. Each rule names a
        mechanism already curated on the record and the field it cannot leave
        open:

        - an automatic cut is the thing that removes the upshift lift;
        - an H-pattern with no cut leaves the lift to the driver;
        - an H-pattern gate is a driver-shifted gearbox, and a driver-shifted
          gearbox has to be declutched to pull away from rest;
        - dog rings cannot match the shaft speeds, so the driver must;
        - synchronisers do it for the driver, so the blip is decided rather
          than open. The rule is that the field is settled, not which way: one
          record reads `required` over a synchromesh knowingly, and says so.

        Every record these rules covered was also listing the open field as a
        deviation from its own registered archetype, so the reviewed archetype
        already held the value the record was missing.
        """
        offenders = []
        for record_path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            transmission = record["authentic_controls"]["transmission"]
            upshift = transmission.get("upshift", {})
            downshift = transmission.get("downshift", {})
            lift = upshift.get("throttle_lift")
            blip = downshift.get("manual_blip")
            if upshift.get("automatic_cut") == "yes" and lift == "unknown":
                offenders.append(
                    "%s: an automatic cut is established, so the upshift lift "
                    "cannot stay unknown" % record["record_id"]
                )
            if (
                transmission.get("shift_actuation") == "h-pattern"
                and upshift.get("automatic_cut") == "no"
                and lift == "unknown"
            ):
                offenders.append(
                    "%s: an H-pattern with no automatic cut leaves the lift to "
                    "the driver, so it cannot stay unknown" % record["record_id"]
                )
            if (
                transmission.get("shift_actuation") == "h-pattern"
                and transmission.get("standing_start_clutch") == "unknown"
            ):
                # Alone among these rules this one does not rest on gearbox
                # construction: synchromesh or dog, a car with an H gate is
                # declutched to move off. All 96 curated H-pattern records say
                # required, all five registered H-pattern archetypes say
                # required, and no H-pattern record has ever established
                # anything else.
                offenders.append(
                    "%s: an H-pattern gate is established, so the standing-start "
                    "clutch cannot stay unknown" % record["record_id"]
                )
            if (
                transmission.get("gearbox_type") == "dogbox"
                and transmission.get("shift_actuation") == "h-pattern"
                and blip == "unknown"
            ):
                offenders.append(
                    "%s: a dog box is established, so the downshift blip cannot "
                    "stay unknown" % record["record_id"]
                )
            if transmission.get("gearbox_type") == "synchromesh" and blip == "unknown":
                offenders.append(
                    "%s: a synchromesh is established, so the downshift blip "
                    "cannot stay unknown" % record["record_id"]
                )
        self.assertEqual([], offenders)

    def test_a_derived_launch_clutch_is_not_announced_as_a_simulator_departure(
        self,
    ) -> None:
        """An override must not restate a baseline the record now establishes.

        Each of the nine records whose launch clutch was derived carried a
        simulator override setting the same value, written while the baseline was
        unknown and reading "the reviewed real-car sources did not establish the
        same value". Once the baseline says required, the override makes the card
        announce a departure where the simulator and the car agree. That is the
        same fault as the 142 overrides removed in 0.5.34: only a refusal is a
        departure.
        """
        offenders = []
        for record_path in sorted((ROOT / "data" / "v1" / "cars").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            transmission = record["authentic_controls"]["transmission"]
            if transmission.get("shift_actuation") != "h-pattern":
                continue
            baseline = transmission.get("standing_start_clutch")
            for simulator in record["simulators"]:
                for override in simulator.get("overrides") or []:
                    if not override["path"].endswith("/standing_start_clutch"):
                        continue
                    if override["value"] == baseline:
                        offenders.append(
                            "%s [%s]: the launch-clutch override restates the "
                            "authentic %s"
                            % (record["record_id"], simulator["simulator"], baseline)
                        )
        self.assertEqual([], offenders)

    def test_an_ac_evo_observation_source_must_be_named_by_the_convention(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = self._copy_repository_data(Path(temp))
            path = temp_root / "data" / "v1" / "sources.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["sources"].append(
                {
                    "source_id": "ac-evo.a-drive-i-did",
                    "title": "A drive",
                    "publisher": "local",
                    "url": None,
                    "archive_url": None,
                    "source_type": "in-game-observation",
                    "published_or_updated_at": None,
                    "retrieved_at": "2026-08-20",
                    "reuse_status": "facts-only-review",
                    "notes": "Staged to prove the convention now covers a second simulator.",
                }
            )
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self.assertTrue(
                any(
                    "ac-evo.local-live-<car>-controls" in error
                    for error in validate_repository(temp_root)
                ),
                "an ac-evo observation escaped the naming convention",
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
