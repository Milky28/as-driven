from pathlib import Path
import unittest

from as_driven_db.importers.ams2 import _shift, _wheel, import_ams2_csv


FIXTURES = Path(__file__).parent / "fixtures"


class AMS2ImporterTests(unittest.TestCase):
    def test_maps_source_fields_and_source_specific_blanks(self) -> None:
        payload = import_ams2_csv(
            FIXTURES / "ams2.csv",
            source_id="test.ams2",
            verified_game_version="1.5.5.2",
        )
        self.assertTrue(payload["review_required"])
        self.assertEqual(len(payload["candidates"]), 3)

        f301 = payload["candidates"][0]
        behavior = f301["simulator_candidate"]["behavior"]
        self.assertEqual(f301["identity"]["display_name"], "F301")
        self.assertEqual(behavior["auto_blip"], "yes")
        self.assertEqual(behavior["shift_cut"], "yes")
        self.assertEqual(behavior["steering_dor"], 450)
        self.assertEqual(behavior["wheel_rim_type"]["source_label"], "RSF1")

    def test_steering_dor_column_is_optional(self) -> None:
        payload = import_ams2_csv(
            FIXTURES / "ams2-no-dor.csv",
            source_id="test.ams2",
            verified_game_version="1.5.5.2",
        )
        candidate = payload["candidates"][0]
        self.assertNotIn(
            "degrees_of_rotation",
            candidate["authentic_controls_candidate"]["steering"],
        )
        self.assertNotIn("steering_dor", candidate["simulator_candidate"]["behavior"])

    def test_dogleg_does_not_infer_gearbox_construction(self) -> None:
        payload = import_ams2_csv(
            FIXTURES / "ams2.csv",
            source_id="test.ams2",
            verified_game_version="1.5.5.2",
        )
        c9 = payload["candidates"][1]["authentic_controls_candidate"]["transmission"]
        self.assertEqual(c9["shift_actuation"], "h-pattern")
        self.assertEqual(c9["shift_pattern"], "dogleg-h")
        self.assertEqual(c9["gearbox_type"], "unknown")

    def test_known_source_shift_variants_are_normalized(self) -> None:
        self.assertEqual(_shift("Automatic")["shift_actuation"], "automatic-lever")
        self.assertEqual(_shift("Seq")["gearbox_type"], "sequential")
        self.assertEqual(_shift("Seq")["shift_actuation"], "unknown")

    def test_documented_gt_wheel_family_is_normalized(self) -> None:
        self.assertEqual(_wheel("GTF1")["normalized"], "gt-style")
        self.assertEqual(_wheel("GTF1FL2")["normalized"], "gt-style")
        self.assertEqual(_wheel("F1")["normalized"], "formula")
        self.assertEqual(_wheel("F1M")["normalized"], "formula")
        self.assertEqual(_wheel("RSF1")["normalized"], "round")
        self.assertEqual(_wheel("unmapped")["normalized"], "unknown")


if __name__ == "__main__":
    unittest.main()
