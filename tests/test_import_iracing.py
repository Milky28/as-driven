from pathlib import Path
import unittest

from authentic_controls_db.importers.iracing import import_iracing_html


FIXTURES = Path(__file__).parent / "fixtures"


class IRacingImporterTests(unittest.TestCase):
    def test_inherits_category_profile_and_extracts_gears(self) -> None:
        payload = import_iracing_html(
            FIXTURES / "iracing.html", source_id="test.iracing"
        )
        self.assertTrue(payload["review_required"])
        self.assertEqual(len(payload["candidates"]), 3)

        dbr9 = payload["candidates"][0]
        behavior = dbr9["simulator_candidate"]["behavior"]
        self.assertEqual(dbr9["identity"]["display_name"], "Aston Martin DBR9 GT1")
        self.assertEqual(behavior["forward_gears"], 6)
        self.assertEqual(behavior["shift_actuation"], "sequential-stick")
        self.assertEqual(behavior["shift_cut"], "yes")
        self.assertEqual(behavior["downshift_manual_blip"], "required")

    def test_preserves_legacy_status(self) -> None:
        payload = import_iracing_html(
            FIXTURES / "iracing.html", source_id="test.iracing"
        )
        legacy = payload["candidates"][1]
        self.assertEqual(
            legacy["identity"]["display_name"], "Riley MkXX Daytona Prototype - 2008"
        )
        self.assertTrue(legacy["simulator_candidate"]["legacy_content"])


if __name__ == "__main__":
    unittest.main()

