from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from as_driven_db.importers.observation import import_observation
from as_driven_db.promote_observation import (
    merge_simulator_entry,
    promote_observations,
    resolve_class,
)
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

    def test_a_simulator_with_no_class_says_so_instead_of_sending_the_reviewer_hunting(
        self,
    ) -> None:
        """Assetto Corsa EVO reports an empty class through SimHub.

        Observed on the first AC EVO drive: the Huracan Super Trofeo logged
        `car_class: ""` where AMS2 gives "Super Trofeo". With no class token
        there is nothing to key a name on, so the standing advice - add a row to
        the class-names file - sends the reviewer looking for a row they cannot
        write. The advice has to change with the situation.
        """
        bundle = {
            "record": {
                "record_id": "huracan-under-test",
                "simulators": [
                    {
                        "simulator": "ac-evo",
                        "identities": [
                            {"kind": "telemetry-name", "value": "Lamborghini Huracan ST EVO2"}
                        ],
                    }
                ],
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError) as caught:
                resolve_class({}, bundle, Path(directory))
        message = str(caught.exception)
        self.assertIn("reports no class", message)
        self.assertIn("Set 'class' on this entry", message)
        self.assertNotIn("car-select screen", message)

    def test_a_missing_class_name_still_points_at_the_class_map(self) -> None:
        """The other branch keeps its own advice: here there is a token to key on."""
        bundle = {
            "record": {
                "record_id": "car-under-test",
                "simulators": [
                    {
                        "simulator": "ams2",
                        "identities": [{"kind": "class-id", "value": "NEVER_SEEN"}],
                    }
                ],
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError) as caught:
                resolve_class({}, bundle, Path(directory))
        self.assertIn("car-select screen", str(caught.exception))

    def _merge(self, existing_controls: dict, incoming_controls: dict, **kwargs):
        existing = {
            "record_id": "car",
            "authentic_controls": existing_controls,
            "simulators": [{"simulator": "ams2"}],
            "provenance": {"claims": []},
            "updated_at": "2026-08-01",
        }
        incoming = {
            "record_id": "car",
            "authentic_controls": incoming_controls,
            "simulators": [{"simulator": "ac-evo", "identities": []}],
            "provenance": {"claims": []},
            "updated_at": "2026-08-21",
        }
        return merge_simulator_entry(existing, incoming, label="test", **kwargs)

    def _creation_bundle(self, temp: Path) -> dict:
        """A drive whose derived id names a package rather than a car."""
        observation = _observation()
        observation["simulator"] = "ac"
        observation["observation_id"] = "ac.acl-gtr-thing.20260822t120000000z-abcd1234"
        observation["identity"]["telemetry_name"] = "ACL GTR Some Mod Car"
        bundle = import_observation(observation, imported_at="2026-08-22")
        (temp / "build" / "mod.json").write_text(
            json.dumps(bundle, indent=2), encoding="utf-8"
        )
        return bundle

    def test_a_new_record_under_another_name_must_be_asked_for(self) -> None:
        """A mod's name is not a car's name, and a typo is not a rename.

        Assetto Corsa reports whatever an author typed, so a bundle derives
        `acl-gtr-...` from a package by AC Legends. Promoting a real Porsche under
        that id would put a mod pack's initials permanently into a
        simulator-independent database - but silently accepting any unknown id
        would let a typo mint a record naming nothing.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._creation_bundle(temp)
            entry = dict(
                _review_entry(),
                record_id="porsche-911-carrera-rsr-2-8-1973",
                bundle="build/mod.json",
            )
            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(entry))
            self.assertIn("create_new_record", str(caught.exception))

    def test_the_staged_id_is_repeated_back_so_the_bundle_cannot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._creation_bundle(temp)
            entry = dict(
                _review_entry(),
                record_id="porsche-911-carrera-rsr-2-8-1973",
                bundle="build/mod.json",
                create_new_record={
                    "staged_record_id": "something-else-entirely",
                    "basis": "Identity research establishes the represented car.",
                },
            )
            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(entry))
            self.assertIn("derived", str(caught.exception))

    def test_a_rename_needs_a_reason_and_keeps_what_it_was_renamed_from(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._creation_bundle(temp)
            base = dict(
                _review_entry(),
                record_id="porsche-911-carrera-rsr-2-8-1973",
                bundle="build/mod.json",
            )
            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(dict(
                    base,
                    create_new_record={"staged_record_id": "acl-gtr-some-mod-car"},
                )))
            self.assertIn("basis", str(caught.exception))

            self._promote(temp, self._manifest(dict(
                base,
                create_new_record={
                    "staged_record_id": "acl-gtr-some-mod-car",
                    "basis": "Identity research establishes the represented real car.",
                },
            )))
            approval = json.loads(
                (temp / "curation" / "ac-approved-porsche-911-carrera-rsr-2-8-1973.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(approval["staged_record_id"], "acl-gtr-some-mod-car")
            self.assertEqual(validate_repository(temp), [])

    def test_a_reviewers_own_source_note_does_not_erase_the_fingerprint(self) -> None:
        """The one record of which package was driven, lost to a better sentence.

        A reviewer replacing the staged source note replaced all of it, including
        the implementation fingerprint - so the preservation guarantee failed
        exactly when someone took the trouble to write good prose.

        It was first fixed by rescuing the sentence out of the old note, which
        was defeated by writing the same phrase without a digest. The fingerprint
        is a field now: prose is prose, and rewriting it cannot reach evidence.
        """
        observation = _observation()
        observation["simulator"] = "ac"
        observation["observation_id"] = "ac.acl-gtr-thing.20260822t120000000z-abcd1234"
        observation["identity"]["telemetry_name"] = "ACL GTR Some Mod Car"
        observation["implementation"] = {
            "content_id": "acl_gtr_some_mod_car",
            "fingerprint": {
                "scope": "data-acd", "algorithm": "sha256", "digest": "b" * 64,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            bundle = import_observation(observation, imported_at="2026-08-22")
            (temp / "build" / "mod.json").write_text(
                json.dumps(bundle, indent=2), encoding="utf-8"
            )
            entry = dict(
                _review_entry(),
                record_id="acl-gtr-some-mod-car",
                bundle="build/mod.json",
                live_source_notes="A carefully written note about the drive.",
            )
            self._promote(temp, self._manifest(entry))
            sources = json.loads(
                (temp / "data" / "v1" / "sources.json").read_text(encoding="utf-8")
            )["sources"]
            live = next(s for s in sources if s["source_id"].startswith("ac.local-live-"))
            self.assertIn("A carefully written note", live["notes"])
            self.assertEqual(live["implementation"]["fingerprint"]["digest"], "b" * 64)
            self.assertEqual(live["implementation"]["content_id"], "acl_gtr_some_mod_car")
            # And the prose the reviewer replaced is genuinely gone, so this is
            # not passing because the old note happened to survive.
            self.assertNotIn("b" * 64, live["notes"])

    def test_an_empty_creation_block_is_not_silently_ignored(self) -> None:
        """Writing it means something; ignoring it means the entry and the
        reviewer disagree about what this promotion does, which is the whole
        reason these refusals exist. The checks tested truthiness, and an empty
        object is falsy."""
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._creation_bundle(temp)
            for record_id, expected in (
                ("acl-gtr-some-mod-car", "already derived"),
                ("test-prototype", "already exists"),
            ):
                if record_id == "test-prototype":
                    self._promote(temp, self._manifest(_review_entry()))
                with self.assertRaises(ValueError) as caught:
                    self._promote(temp, self._manifest(dict(
                        _review_entry(),
                        record_id=record_id,
                        bundle="build/mod.json",
                        create_new_record={},
                    )))
                self.assertIn(expected, str(caught.exception))

    def test_a_destination_id_is_a_name_before_it_is_a_path(self) -> None:
        """A typo must not address a path, and must fail before anything is written."""
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._creation_bundle(temp)
            entry = dict(
                _review_entry(),
                record_id="../../escaped",
                bundle="build/mod.json",
                create_new_record={
                    "staged_record_id": "acl-gtr-some-mod-car",
                    "basis": "Identity research establishes the represented real car.",
                },
            )
            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(entry))
            self.assertIn("not a valid id", str(caught.exception))
            self.assertFalse((temp / "data" / "v1" / "escaped.json").exists())
            self.assertFalse((temp / "data" / "escaped.json").exists())

    def test_a_creation_block_is_refused_where_nothing_is_created(self) -> None:
        """Unused, it was never checked - so a stale one could say anything.

        Two paths reached the filesystem without validating it: naming the id the
        bundle already derived, and naming a record that exists, which is a merge.
        A merge also wrongly recorded a staged id, implying a rename that never
        happened.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp = self._prepare(Path(directory))
            self._creation_bundle(temp)
            creation = {"staged_record_id": "nonsense", "basis": "unchecked"}

            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(dict(
                    _review_entry(),
                    record_id="acl-gtr-some-mod-car",
                    bundle="build/mod.json",
                    create_new_record=creation,
                )))
            self.assertIn("already derived", str(caught.exception))

            self._promote(temp, self._manifest(_review_entry()))
            with self.assertRaises(ValueError) as caught:
                self._promote(temp, self._manifest(dict(
                    _review_entry(),
                    record_id="test-prototype",
                    bundle="build/mod.json",
                    create_new_record=creation,
                )))
            self.assertIn("already exists", str(caught.exception))

    def test_a_less_informed_drive_does_not_block_or_overwrite(self) -> None:
        """The second drive knowing less is not a disagreement.

        The AC EVO Huracan drive could not establish the automatic cut that AMS2
        had. Treating that as a contradiction blocked the merge over the drive
        having learned nothing, rather than over it being wrong.
        """
        merged = self._merge(
            {"transmission": {"upshift": {"automatic_cut": "yes"}}, "steering": {}},
            {"transmission": {"upshift": {"automatic_cut": "unknown"}}, "steering": {}},
        )
        self.assertEqual(
            merged["authentic_controls"]["transmission"]["upshift"]["automatic_cut"],
            "yes",
        )

    def test_prose_never_blocks_a_merge(self) -> None:
        """Two drives never word their notes the same.

        `steering.wheel_rim` is one field holding a dict, so its nested notes and
        source label were compared as part of it. That made the rim report a
        disagreement on every cross-simulator merge, whatever the values were.
        """
        merged = self._merge(
            {
                "transmission": {},
                "steering": {
                    "wheel_rim": {
                        "shape": "gt-formula",
                        "source_label": "live-cockpit-gt-closed-no-display",
                        "notes": "Seen in the AMS2 cockpit.",
                    }
                },
            },
            {
                "transmission": {},
                "steering": {
                    "wheel_rim": {
                        "shape": "gt-formula",
                        "source_label": "live-cockpit-observation",
                        "notes": "Seen in the AC EVO cockpit.",
                    }
                },
            },
        )
        self.assertEqual(
            merged["authentic_controls"]["steering"]["wheel_rim"]["notes"],
            "Seen in the AMS2 cockpit.",
        )

    def test_a_contradiction_still_stops_the_merge(self) -> None:
        """Both established and different: one of them is wrong, so a person decides."""
        with self.assertRaises(ValueError) as caught:
            self._merge(
                {"transmission": {}, "steering": {"wheel_rim": {"open_top": "yes"}}},
                {"transmission": {}, "steering": {"wheel_rim": {"open_top": "no"}}},
            )
        self.assertIn("contradicts the curated real car", str(caught.exception))

    def test_a_gap_the_drive_fills_needs_the_reviewer_to_ask_for_it(self) -> None:
        """`unknown` to a value is an improvement, but not an unattended one."""
        existing = {"transmission": {}, "steering": {"wheel_rim": {"shift_lights": "unknown"}}}
        incoming = {"transmission": {}, "steering": {"wheel_rim": {"shift_lights": "no"}}}
        with self.assertRaises(ValueError) as caught:
            self._merge(existing, incoming)
        self.assertIn("accept_from_drive", str(caught.exception))

        merged = self._merge(
            existing,
            incoming,
            accept_from_drive=["/authentic_controls/steering/wheel_rim/shift_lights"],
        )
        self.assertEqual(
            merged["authentic_controls"]["steering"]["wheel_rim"]["shift_lights"], "no"
        )

    def test_accepting_a_gap_that_does_not_exist_is_refused(self) -> None:
        """A pointer that fills nothing is a mistake, not a no-op."""
        with self.assertRaises(ValueError) as caught:
            self._merge(
                {"transmission": {"forward_gears": 6}, "steering": {}},
                {"transmission": {"forward_gears": 6}, "steering": {}},
                accept_from_drive=["/authentic_controls/transmission/forward_gears"],
            )
        self.assertIn("does not fill", str(caught.exception))

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
