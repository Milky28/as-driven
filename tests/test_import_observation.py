from __future__ import annotations

from pathlib import Path
import unittest

from as_driven_db.importers.observation import import_observation
from as_driven_db.validate import _validate_car_approval


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
        "identity": {"telemetry_name": "Porsche 963", "telemetry_class": "LMDh"},
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
    def test_maps_clean_drive_to_record_and_ids(self) -> None:
        bundle = import_observation(_clean_observation(), imported_at="2026-08-12")
        record = bundle["record"]
        transmission = record["authentic_controls"]["transmission"]

        self.assertEqual(record["record_id"], "ams2.porsche-963")
        self.assertEqual(
            bundle["source"]["source_id"],
            "ams2.local-live-porsche-963-controls.1.6.9.91",
        )
        self.assertEqual(transmission["forward_gears"], 7)
        self.assertEqual(transmission["shift_actuation"], "sequential-paddles")
        self.assertEqual(transmission["gearbox_type"], "sequential")
        self.assertEqual(transmission["shift_pattern"], "sequential")
        self.assertEqual(transmission["standing_start_clutch"], "not-required")
        self.assertEqual(transmission["upshift"]["clutch"], "not-required")
        self.assertEqual(transmission["downshift"]["clutch"], "not-required")
        self.assertEqual(transmission["downshift"]["manual_blip"], "not-required")

        behavior = record["simulators"][0]["behavior"]
        self.assertEqual(behavior["shift_cut"], "yes")
        self.assertEqual(behavior["auto_blip"], "yes")
        self.assertEqual(behavior["wheel_rim_type"]["normalized"], "prototype")
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

    def test_h_pattern_actuation_leaves_layout_and_construction_unknown(self) -> None:
        observation = _clean_observation()
        observation["cockpit"]["primary_shift_actuation"] = "h-pattern"
        bundle = import_observation(observation)
        transmission = bundle["record"]["authentic_controls"]["transmission"]

        self.assertEqual(transmission["shift_actuation"], "h-pattern")
        self.assertEqual(transmission["gearbox_type"], "unknown")
        self.assertEqual(transmission["shift_pattern"], "unknown")


if __name__ == "__main__":
    unittest.main()
