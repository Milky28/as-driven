from __future__ import annotations

from pathlib import Path
import unittest

import json

from as_driven_db.importers.observation import import_observation
from as_driven_db.schema_validation import validate_instance
from as_driven_db.validate import _validate_car_approval

ROOT = Path(__file__).parents[1]


def _clean_observation() -> dict:
    """A clean LMDh-style guided drive with automation disabled."""
    return {
        "schema_version": "1.0.0",
        "observation_id": "ams2.porsche-963.2026-08-12t1200",
        "simulator": "ams2",
        "game_version": "1.6.9.91",
        "client_version": "0.15.0",
        "observed_at": "2026-08-12T12:00:00Z",
        "observer": "tester",
        "identity": {
            "telemetry_name": "Porsche 963",
            "telemetry_class": "LMDh",
            "internal_id": "porsche_963",
        },
        "assists": {
            "automatic_clutch": "disabled",
            "automatic_shifting": "disabled",
            "automatic_throttle_blip": "unavailable",
        },
        "tests": {
            "move_off_without_physical_clutch": "yes",
            "forward_gears": 7,
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
                "shift_lights": "unknown",
                "open_top": "no",
            },
        },
        "review_status": "draft",
    }


class ImportObservationTests(unittest.TestCase):
    def test_a_driven_implementation_survives_the_import(self) -> None:
        """A fingerprint is unrecoverable once a drive is over.

        Assetto Corsa reports the name a mod's author chose, and several packages
        may depict the same real car while shifting differently. Nothing consumes
        the fingerprint yet - the implementation registry does not exist - so the
        risk is that it is quietly dropped and cannot be recovered from a promoted
        record afterwards.

        It also must not be mistaken for identity. The digest says which package
        was driven; which real car that package depicts is the reviewer's
        judgement, and it is the claim that goes wrong.
        """
        observation = _clean_observation()
        observation["simulator"] = "ac"
        observation["observation_id"] = "ac.test-prototype.20260822t120000000z-abcd1234"
        observation["implementation"] = {
            "content_id": "ac_legends_gt_911rsr_73",
            "author": "AC Legends",
            "declared_version": None,
            "fingerprint": {
                "scope": "data-acd",
                "algorithm": "sha256",
                "digest": "a" * 64,
            },
        }
        schema = json.loads(
            (ROOT / "schema" / "v1" / "verification-observation.schema.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual([], validate_instance(observation, schema, "observation"))
        bundle = import_observation(observation, imported_at="2026-08-22")
        note = next(
            (n for n in bundle["review_notes"] if "Driven implementation" in n), None
        )
        self.assertIsNotNone(note, "the fingerprint reached no reviewer")
        self.assertIn("ac_legends_gt_911rsr_73", note)
        self.assertIn("data-acd", note)
        self.assertIn("no declared version", note)
        self.assertIn("not the real car", note)

    def test_maps_clean_drive_to_record_and_ids(self) -> None:
        bundle = import_observation(_clean_observation(), imported_at="2026-08-12")
        record = bundle["record"]
        transmission = record["authentic_controls"]["transmission"]

        self.assertEqual(record["record_id"], "porsche-963")
        self.assertEqual(
            bundle["source"]["source_id"],
            "ams2.local-live-porsche-963-controls.1.6.9.91",
        )
        self.assertEqual(transmission["forward_gears"], 7)
        self.assertEqual(transmission["shift_actuation"], "sequential-paddles")
        # The gate the drive genuinely saw, and no claim about how the gearbox is
        # built. Paddles used to derive `sequential`, which is a construction
        # read off an actuation: of the curated paddle cars 71 are sequential but
        # 17 are semi-automatic, 9 are dual-clutch and 2 are dog boxes. The AC EVO
        # Cayman drive asserted `sequential` over a PDK Porsche calls a six-speed
        # dual-clutch, and only the curated record refusing the merge caught it.
        self.assertEqual(transmission["gearbox_type"], "unknown")
        self.assertEqual(transmission["shift_pattern"], "sequential")
        self.assertEqual(transmission["standing_start_clutch"], "not-required")
        self.assertEqual(transmission["upshift"]["clutch"], "not-required")
        self.assertEqual(transmission["downshift"]["clutch"], "not-required")
        self.assertEqual(transmission["downshift"]["manual_blip"], "not-required")

        identities = record["simulators"][0]["identities"]
        self.assertIn(
            {"kind": "internal-id", "value": "porsche_963"},
            identities,
        )

        behavior = record["simulators"][0]["behavior"]
        self.assertEqual(behavior["shift_cut"], "yes")
        self.assertEqual(behavior["auto_blip"], "yes")
        # The fixture draft carries the retired "prototype" value, as any draft
        # saved before the rim vocabulary was merged does. The importer migrates
        # it rather than letting a value no curated record may hold back in.
        self.assertEqual(behavior["wheel_rim_type"]["normalized"], "gt-formula")
        self.assertEqual(
            record["authentic_controls"]["steering"]["wheel_rim"]["shape"], "gt-formula"
        )
        self.assertEqual(record["simulators"][0]["verified_at"], "2026-08-12")

    def test_real_world_identity_is_left_for_review(self) -> None:
        bundle = import_observation(_clean_observation())
        identity = bundle["record"]["identity"]
        self.assertEqual(identity["manufacturer"], "REVIEW-REQUIRED")
        self.assertEqual(identity["model"], "REVIEW-REQUIRED")
        self.assertEqual(identity["year"]["label"], "REVIEW-REQUIRED")
        # The exact simulator identity, however, is known from the observation.
        self.assertEqual(identity["display_name"], "Porsche 963")
        self.assertEqual(identity["class"], "LMDh")

    def test_approval_matches_record_under_real_cross_check(self) -> None:
        bundle = import_observation(_clean_observation(), imported_at="2026-08-12")
        record = bundle["record"]
        approval = bundle["approval"]

        # The emitted approval must pass validate.py's own approval<->record
        # cross-check, so a reviewer's promotion validates cleanly.
        errors: list[str] = []
        _validate_car_approval(
            approval, Path("approval.json"), {record["record_id"]: record}, errors
        )
        self.assertEqual(errors, [])
        self.assertEqual(approval["approved_controls"]["automatic_cut"], "yes")
        self.assertEqual(approval["approved_controls"]["running_shift_clutch"], "not-required")

    def test_unknown_assists_degrade_clutch_fields(self) -> None:
        observation = _clean_observation()
        observation["assists"]["automatic_clutch"] = "unknown"
        bundle = import_observation(observation)
        transmission = bundle["record"]["authentic_controls"]["transmission"]

        self.assertEqual(transmission["standing_start_clutch"], "unknown")
        self.assertEqual(transmission["upshift"]["clutch"], "unknown")
        self.assertEqual(transmission["downshift"]["clutch"], "unknown")
        self.assertTrue(
            any("assist profile" in note for note in bundle["review_notes"])
        )
        # Behavior cut/blip are independent of clutch assist and still map.
        self.assertEqual(bundle["record"]["simulators"][0]["behavior"]["shift_cut"], "yes")

    def test_unknown_actuation_does_not_infer_gearbox(self) -> None:
        observation = _clean_observation()
        observation["cockpit"]["primary_shift_actuation"] = "unknown"
        bundle = import_observation(observation)
        transmission = bundle["record"]["authentic_controls"]["transmission"]

        self.assertEqual(transmission["shift_actuation"], "unknown")
        self.assertEqual(transmission["gearbox_type"], "unknown")
        self.assertEqual(transmission["shift_pattern"], "unknown")

    def test_diverging_clutch_omits_the_unsummarizable_approval_field(self) -> None:
        observation = _clean_observation()
        # Clutchless upshifts accepted, clutchless downshifts refused.
        observation["tests"]["clutchless_downshift"] = "no"
        bundle = import_observation(observation)
        transmission = bundle["record"]["authentic_controls"]["transmission"]
        approval = bundle["approval"]

        self.assertEqual(transmission["upshift"]["clutch"], "not-required")
        self.assertEqual(transmission["downshift"]["clutch"], "required")
        # validate cannot summarize differing clutch use, so the field is omitted
        # rather than guessed; the schema allows that.
        self.assertNotIn("running_shift_clutch", approval["approved_controls"])
        self.assertTrue(
            any("running_shift_clutch" in note for note in bundle["review_notes"])
        )

        errors: list[str] = []
        _validate_car_approval(
            approval,
            Path("approval.json"),
            {bundle["record"]["record_id"]: bundle["record"]},
            errors,
        )
        self.assertEqual(errors, [])

    def test_observed_gate_pattern_beats_derivation(self) -> None:
        observation = _clean_observation()
        observation["cockpit"]["primary_shift_actuation"] = "h-pattern"
        observation["cockpit"]["shift_pattern"] = "dogleg-h"
        bundle = import_observation(observation)
        transmission = bundle["record"]["authentic_controls"]["transmission"]

        # Derivation can never produce dogleg; only the cockpit can establish it.
        self.assertEqual("dogleg-h", transmission["shift_pattern"])
        self.assertEqual("h-pattern", transmission["shift_actuation"])
        self.assertTrue(
            any("dogleg-h" in note for note in bundle["review_notes"]),
            bundle["review_notes"],
        )

    def test_unknown_gate_pattern_falls_back_to_derivation(self) -> None:
        observation = _clean_observation()
        observation["cockpit"]["shift_pattern"] = "unknown"
        bundle = import_observation(observation)
        transmission = bundle["record"]["authentic_controls"]["transmission"]
        # Paddles still derive sequential; an unknown observation adds nothing.
        self.assertEqual("sequential", transmission["shift_pattern"])

    def test_h_pattern_actuation_leaves_layout_and_construction_unknown(self) -> None:
        observation = _clean_observation()
        observation["cockpit"]["primary_shift_actuation"] = "h-pattern"
        bundle = import_observation(observation)
        transmission = bundle["record"]["authentic_controls"]["transmission"]

        self.assertEqual(transmission["shift_actuation"], "h-pattern")
        self.assertEqual(transmission["gearbox_type"], "unknown")
        self.assertEqual(transmission["shift_pattern"], "unknown")


    def test_every_retired_rim_value_is_migrated_on_import(self) -> None:
        """An old draft cannot reintroduce a retired rim value.

        gt-style, prototype and formula named a racing class rather than a rim
        and all three described the same control-panel form. A drive recorded
        before the merge still carries one, and promoting it unmigrated would
        put a value into the dataset that no curated record may hold.
        """
        for retired in ("gt-style", "prototype", "formula"):
            observation = _clean_observation()
            observation["cockpit"]["wheel_rim"]["shape"] = retired
            staged = import_observation(observation)
            record = staged["record"]
            self.assertEqual(
                "gt-formula",
                record["simulators"][0]["behavior"]["wheel_rim_type"]["normalized"],
                retired,
            )
            self.assertEqual(
                "gt-formula",
                record["authentic_controls"]["steering"]["wheel_rim"]["shape"],
                retired,
            )
        # A live value passes through untouched.
        observation = _clean_observation()
        observation["cockpit"]["wheel_rim"]["shape"] = "d-shaped"
        staged = import_observation(observation)
        self.assertEqual(
            "d-shaped",
            staged["record"]["simulators"][0]["behavior"]["wheel_rim_type"]["normalized"],
        )

if __name__ == "__main__":
    unittest.main()
