import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = REPOSITORY_ROOT / "simhub" / "dash" / "generate.py"
OVERLAY_LAYOUT_PATH = (
    REPOSITORY_ROOT / "simhub" / "overlay" / "As Driven.olayout"
)
ULTRAWIDE_LAYOUT_PATH = (
    REPOSITORY_ROOT
    / "simhub"
    / "overlay"
    / "As Driven 5120x1440.olayout"
)
RASTER_ASSET_PATH = REPOSITORY_ROOT / "simhub" / "dash" / "assets"


def load_generator():
    sys.path.insert(0, str(GENERATOR_PATH.parent))
    spec = importlib.util.spec_from_file_location("simhub_dash_generator", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


# Exactly one preflight size ships placed, alongside the verification surface.
PLACED_BY_DEFAULT = frozenset(
    {"As Driven Preflight Compact", "As Driven Verification Drive"}
)


class SimHubDashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = load_generator()

    def test_overlay_variants_and_display_have_distinct_visibility_contracts(self):
        overlay = self.generator.build_dashboard(overlay=True, variant="detailed")
        display = self.generator.build_dashboard(overlay=False)

        self.assertTrue(overlay["IsOverlay"])
        self.assertFalse(display["IsOverlay"])
        overlay_card = overlay["Screens"][0]["Items"][0]
        display_card = display["Screens"][0]["Items"][0]
        self.assertEqual(
            "[AsDriven.PopupDetailedVisible]",
            overlay_card["Bindings"]["Visible"]["Formula"]["Expression"],
        )
        self.assertNotIn("Bindings", display_card)

        expected_sizes = {
            "detailed": (840, 360),
            "compact": (520, 300),
            "glance": (320, 120),
            "verification": (700, 220),
        }
        for variant, expected_size in expected_sizes.items():
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            self.assertEqual(expected_size, (dashboard["BaseWidth"], dashboard["BaseHeight"]))
            expression = dashboard["Screens"][0]["Items"][0]["Bindings"]["Visible"]["Formula"]["Expression"]
            expected_expression = (
                "[AsDriven.VerificationDriveVisible]"
                if variant == "verification"
                else "[AsDriven.Popup" + variant.title() + "Visible]"
            )
            self.assertEqual(expected_expression, expression)

    def test_guided_verification_surface_exposes_live_prompt_and_results(self):
        dashboard = self.generator.build_dashboard(overlay=True, variant="verification")
        serialized = json.dumps(dashboard)
        named = {
            value["Name"]: value
            for value in walk(dashboard)
            if isinstance(value, dict) and "Name" in value
        }
        self.assertEqual("GUIDED VERIFICATION", named["Eyebrow"]["Text"])
        self.assertIn("AsDriven.VerificationDriveStepNumber", serialized)
        self.assertIn("AsDriven.VerificationDriveStepCount", serialized)
        self.assertIn("AsDriven.VerificationDriveTitle", serialized)
        self.assertIn("AsDriven.VerificationDrivePrompt", serialized)
        self.assertIn("AsDriven.VerificationDrivePromptLine1", serialized)
        self.assertIn("AsDriven.VerificationDrivePromptLine2", serialized)
        self.assertIn("AsDriven.VerificationDriveResultReady", serialized)
        self.assertIn("AsDriven.VerificationDriveResultSuccessful", serialized)
        self.assertIn("AsDriven.VerificationDriveResult", serialized)
        self.assertIn("AsDriven.VerificationDriveStatus", serialized)
        self.assertIn("AsDriven.VerificationDriveLiveValues", serialized)
        self.assertEqual("✓ CAPTURED", named["SuccessBadge"]["Text"])
        self.assertEqual(self.generator.GREEN, named["SuccessBadge"]["TextColor"])

        # A negative outcome is still a captured result, so both status states say
        # CAPTURED and only the colour differs. Badging one REVIEW read as a fault.
        self.assertEqual("✓ CAPTURED", named["ReviewBadge"]["Text"])
        self.assertEqual(self.generator.ORANGE, named["ReviewBadge"]["TextColor"])

        # The action row tells the driver what to do only once a result exists.
        # Before that the verbs are reference, so they stay muted beside telemetry.
        self.assertIn("NEXT / ACCEPT", named["ControlsIdleText"]["Text"])
        self.assertEqual(self.generator.MUTED, named["ControlsIdleText"]["TextColor"])

        # Once captured the row is one full-width sentence: each verb states what
        # it does, rather than an abbreviation squeezed into the corner.
        ready = named["ControlsReadyText"]["Text"]
        self.assertIn("NEXT to accept this result", ready)
        self.assertIn("RETRY to drive this test again", ready)
        self.assertIn("SKIP to answer it in the form", ready)
        self.assertEqual(self.generator.ACCENT, named["ControlsReadyText"]["TextColor"])
        self.assertEqual(648, named["ControlsReadyText"]["Width"])
        self.assertLessEqual(named["SuccessSummary"]["Height"], 28)
        self.assertEqual(14, named["PromptLine1"]["FontSize"])
        self.assertEqual(22, named["PromptLine1"]["Height"])
        self.assertEqual(91, named["PromptLine1"]["Top"])
        self.assertEqual(14, named["PromptLine2"]["FontSize"])
        self.assertEqual(22, named["PromptLine2"]["Height"])
        self.assertEqual(115, named["PromptLine2"]["Top"])

    def test_cards_reference_only_explicit_plugin_values(self):
        dashboard = self.generator.build_dashboard(overlay=True)
        serialized = json.dumps(dashboard)
        for property_name in (
            "AsDriven.HasMatch",
            "AsDriven.MatchStatus",
            "AsDriven.RawCarIdentifier",
            "AsDriven.OverlayCarNameDetailed",
            "AsDriven.ShiftActuation",
            "AsDriven.ShiftPattern",
            "AsDriven.AutoBlip",
            "AsDriven.ShiftCut",
            "AsDriven.TechniqueSummaryLine1",
            "AsDriven.TechniqueSummaryLine2",
            "AsDriven.VerifiedGameVersion",
            "AsDriven.Confidence",
            "AsDriven.PopupDetailedVisible",
        ):
            self.assertIn(property_name, serialized)
        self.assertIn("No hardware or technique values have been assumed.", serialized)
        self.assertIn("Unknown", serialized)
        for display_label in (
            "Round",
            "D-shaped",
            "H-pattern",
            "Sequential stick",
            "Lift throttle",
            "Automatic throttle cut",
            "Manual blip",
            "Automatic throttle blip",
            "Display name match",
            "Telemetry name match",
            "Preview",
        ):
            self.assertIn(display_label, serialized)
        self.assertNotIn("MANUAL CUT", serialized)
        self.assertNotIn("MANUAL BLIP", serialized)

    def test_unmatched_card_offers_a_contribution_handoff_without_assuming_values(self):
        for variant in ("detailed", "compact", "glance"):
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            serialized = json.dumps(dashboard)
            if variant == "glance":
                self.assertIn("Contribution available", serialized)
            else:
                self.assertIn("No hardware or technique values have been assumed.", serialized)
                self.assertIn("CONTRIBUTE IN AS DRIVEN", serialized)
                self.assertIn("choose Contribute this car", serialized)
                self.assertNotIn("AsDriven.BeginCarContribution", serialized)
                self.assertNotIn("AsDriven.ContributionRequestPending", serialized)

    def test_bitmap_icons_cover_supported_control_categories_and_unknowns(self):
        dashboards = [
            self.generator.build_dashboard(overlay=True, variant=variant)
            for variant in ("detailed", "compact", "glance")
        ]
        serialized = json.dumps(dashboards)
        for value in (
            "round",
            "d-shaped",
            "gt-style",
            "prototype",
            "formula",
            "yoke",
            "h-pattern",
            "sequential-stick",
            "sequential-paddles",
            "automatic-lever",
            "direct-selection",
            "dogleg-h",
        ):
            self.assertIn(value, serialized)
        for asset in (
            "wheel-round",
            "wheel-gt-formula",
            "shift-dogleg-h",
            "shift-sequential-stick",
            "shift-sequential-paddles",
            "cut-auto",
            "blip-auto",
            "blip-manual",
            "lift-required",
        ):
            self.assertIn(asset, serialized)
        self.assertIn("GraphicalDash.Models.ImageItem", serialized)
        self.assertNotIn("cut-manual", serialized)
        self.assertEqual(19, len(dashboards[0]["Images"]))
        self.assertTrue(all(image["Extension"] == ".png" for image in dashboards[0]["Images"]))
        self.assertTrue(all(image["Width"] == 128 for image in dashboards[0]["Images"]))
        for dashboard in dashboards:
            sids = [
                value["Sid"]
                for value in walk(dashboard)
                if isinstance(value, dict) and "Sid" in value
            ]
            self.assertEqual(len(sids), len(set(sids)))

    def test_approved_raster_assets_are_packaged_without_falling_back(self):
        expected = {
            "brand-mark",
            "blip-auto",
            "blip-manual",
            "blip-unknown",
            "cut-auto",
            "cut-unknown",
            "lift-required",
            "shift-automatic-lever",
            "shift-direct-selection",
            "shift-dogleg-h",
            "shift-h-pattern",
            "shift-sequential-paddles",
            "shift-sequential-stick",
            "shift-unknown",
            "wheel-d-shaped",
            "wheel-gt-formula",
            "wheel-round",
            "wheel-yoke",
            "wheel-unknown",
        }
        self.assertEqual(expected, {path.stem for path in RASTER_ASSET_PATH.glob("*.png")})
        packaged = self.generator._icon_assets()
        for name in expected:
            self.assertEqual((RASTER_ASSET_PATH / f"{name}.png").read_bytes(), packaged[name])

    def test_detailed_adds_actionable_driving_technique_summary(self):
        dashboard = self.generator.build_dashboard(overlay=True, variant="detailed")
        serialized = json.dumps(dashboard)
        named = {
            value["Name"]: value
            for value in walk(dashboard)
            if isinstance(value, dict) and "Name" in value
        }
        self.assertIn("TechniqueSummaryLine1", named)
        self.assertIn("TechniqueSummaryLine2", named)
        self.assertEqual("DRIVING TECHNIQUE", named["DrivingTechniqueHeading"]["Text"])
        self.assertIn("AsDriven.TechniqueSummaryLine1", serialized)
        self.assertIn("AsDriven.TechniqueSummaryLine2", serialized)
        self.assertNotIn("AsDriven.UpshiftGuidance", serialized)
        self.assertNotIn("AsDriven.DownshiftGuidance", serialized)
        self.assertEqual(333, named["Evidence"]["Top"])
        self.assertEqual(21.5, named["Title"]["FontSize"])
        self.assertIn(
            "AsDriven.OverlayCarNameDetailed",
            named["Title"]["Bindings"]["Text"]["Formula"]["Expression"],
        )
        self.assertIn(
            "AsDriven.OverlayCarClassDetailed",
            named["CarClass"]["Bindings"]["Text"]["Formula"]["Expression"],
        )

    def test_compact_adds_smaller_technique_summary_but_glance_stays_icon_only(self):
        compact = self.generator.build_dashboard(overlay=True, variant="compact")
        compact_named = {
            value["Name"]: value
            for value in walk(compact)
            if isinstance(value, dict) and "Name" in value
        }
        self.assertEqual("DRIVING TECHNIQUE", compact_named["DrivingTechniqueHeading"]["Text"])
        self.assertEqual(9.5, compact_named["TechniqueSummaryLine1"]["FontSize"])
        self.assertIn(
            "AsDriven.TechniqueSummaryCompactLine2",
            compact_named["TechniqueSummaryLine2"]["Bindings"]["Text"]["Formula"]["Expression"],
        )
        self.assertIn(
            "AsDriven.OverlayCarNameCompact",
            compact_named["Title"]["Bindings"]["Text"]["Formula"]["Expression"],
        )
        self.assertIn(
            "AsDriven.OverlayCarClassCompact",
            compact_named["CarClass"]["Bindings"]["Text"]["Formula"]["Expression"],
        )

        glance = self.generator.build_dashboard(overlay=True, variant="glance")
        glance_names = {
            value["Name"]
            for value in walk(glance)
            if isinstance(value, dict) and "Name" in value
        }
        self.assertNotIn("DrivingTechniqueHeading", glance_names)
        self.assertNotIn("TechniqueSummaryLine1", glance_names)
        self.assertNotIn("TechniqueSummaryLine2", glance_names)
        self.assertIn(
            "AsDriven.OverlayCarNameGlance",
            glance["Screens"][0]["Items"][0]["Childrens"][3]["Childrens"][1]["Bindings"]["Text"]["Formula"]["Expression"],
        )

    def test_preview_badge_explicitly_says_preview_is_not_live(self):
        for variant in ("detailed", "compact", "glance"):
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            named = {
                value["Name"]: value
                for value in walk(dashboard)
                if isinstance(value, dict) and "Name" in value
            }
            self.assertIn("PreviewBadge", named)
            self.assertEqual(
                "[AsDriven.MatchKind] == 'preview'",
                named["PreviewBadge"]["Bindings"]["Visible"]["Formula"]["Expression"],
            )
            badge_text = " ".join(
                value.get("Text", "")
                for value in walk(named["PreviewBadge"])
                if isinstance(value, dict)
            )
            self.assertIn("PREVIEW", badge_text)
            self.assertIn("NOT LIVE", badge_text)

    def test_blue_open_rail_layout_uses_brand_mark_and_group_headings(self):
        expected_icon_widths = {
            "detailed": 84.0,
            "compact": 62.0,
            "glance": 38.0,
        }
        for variant, expected_icon_width in expected_icon_widths.items():
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            named = {
                value["Name"]: value
                for value in walk(dashboard)
                if isinstance(value, dict) and "Name" in value
            }
            self.assertEqual("brand-mark", named["Mark"]["Image"])
            self.assertNotIn("MarkText", named)
            self.assertEqual("PHYSICAL CONTROLS", named["PhysicalControlsHeading"]["Text"])
            self.assertEqual("SHIFTING TECHNIQUE", named["ShiftingTechniqueHeading"]["Text"])
            self.assertEqual(self.generator.GROUP_PANEL, named["PhysicalControlsGroup"]["BackgroundColor"])
            self.assertEqual(self.generator.GROUP_PANEL, named["ShiftingTechniqueGroup"]["BackgroundColor"])
            self.assertEqual(self.generator.SLATE, named["PhysicalControlsGroup"]["BorderStyle"]["BorderColor"])
            self.assertEqual(self.generator.SLATE, named["ShiftingTechniqueGroup"]["BorderStyle"]["BorderColor"])
            self.assertNotIn("ControlTechniqueSeparator", named)
            self.assertNotIn("WheelTile", named)
            self.assertNotIn("ShiftTile", named)
            self.assertNotIn("CutTile", named)
            self.assertNotIn("BlipTile", named)
            self.assertEqual(expected_icon_width, named["WheelIconRoundBitmap"]["Width"])
            self.assertEqual(self.generator.ACCENT, named["Accent"]["BackgroundColor"])
            self.assertEqual(20, named["Accent"]["Left"])
            self.assertEqual(dashboard["BaseWidth"] - 20, named["Accent"]["Left"] + named["Accent"]["Width"])
            self.assertEqual(4, named["Card"]["Left"])
            self.assertEqual(dashboard["BaseWidth"] - 4, named["Card"]["Left"] + named["Card"]["Width"])
            self.assertEqual(dashboard["BaseHeight"] - 4, named["Card"]["Top"] + named["Card"]["Height"])

    def test_compact_uses_clear_match_mark_and_consistent_confidence_case(self):
        dashboard = self.generator.build_dashboard(overlay=True, variant="compact")
        named = {
            value["Name"]: value
            for value in walk(dashboard)
            if isinstance(value, dict) and "Name" in value
        }
        self.assertEqual("✓", named["Match"]["Text"])
        self.assertIn("Bindings", named["Match"])
        self.assertIn("MatchKind", named["Match"]["Bindings"]["Text"]["Formula"]["Expression"])
        self.assertEqual("PREVIEW", named["PreviewBadgeTitle"]["Text"])
        self.assertEqual("NOT LIVE", named["PreviewBadgeLive"]["Text"])
        evidence = named["Evidence"]["Bindings"]["Text"]["Formula"]["Expression"]
        self.assertIn("Confidence: ", evidence)
        self.assertIn("'Verified'", evidence)
        self.assertIn("'Medium'", evidence)

    def test_generator_writes_parseable_native_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = self.generator.write_dashboards(Path(temporary_directory))
            self.assertEqual(15, len(paths))
            for path in paths:
                self.assertTrue(path.is_file())
                self.assertEqual(path.parent.name, path.name.split(".djson", 1)[0])
                if path.name.endswith(".ressources"):
                    with zipfile.ZipFile(path) as archive:
                        names = archive.namelist()
                        self.assertEqual(19, len(names))
                        self.assertIn("brand-mark.png", names)
                        self.assertNotIn("cut-manual.png", names)
                        self.assertIn("lift-required.png", names)
                        for name in names:
                            self.assertTrue(archive.read(name).startswith(b"\x89PNG\r\n\x1a\n"))
                else:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(2.0, payload["MetadataVersion"] if path.suffix == ".metadata" else payload["Metadata"]["MetadataVersion"])

    def test_ready_made_overlay_layout_contains_all_native_sizes(self):
        layout = json.loads(OVERLAY_LAYOUT_PATH.read_text(encoding="utf-8"))
        self.assertEqual("As Driven", layout["Name"])
        self.assertTrue(layout["ShowWhenPausedOrInMenu"])
        parts = layout["OverlayLayoutParts"]
        self.assertEqual(4, len(parts))
        expected = {
            "As Driven Preflight Overlay": ((840.0, 360.0), (540.0, 60.0)),
            "As Driven Preflight Compact": ((520.0, 300.0), (700.0, 60.0)),
            "As Driven Preflight Glance": ((320.0, 120.0), (800.0, 60.0)),
            "As Driven Verification Drive": ((700.0, 220.0), (610.0, 430.0)),
        }
        part_ids = set()
        for part in parts:
            stem = Path(part["DashboardName"]).stem
            self.assertIn(stem, expected)
            expected_size, expected_position = expected[stem]
            self.assertEqual(expected_size, (part["Width"], part["Height"]))
            self.assertEqual(expected_position, (part["Left"], part["Top"]))
            # Only one preflight size is placed. The three sizes are
            # alternatives, and SimHub renders every placed overlay in its own
            # window, so placing all three would show the same card three times
            # and put three entries in the alt-tab list. Compact is the one the
            # plugin's own default popup size selects.
            self.assertEqual(stem in PLACED_BY_DEFAULT, part["Placed"], stem)
            self.assertTrue(part["Transparent"])
            part_ids.add(part["PartId"])
        self.assertEqual(4, len(part_ids))
        # The unplaced sizes still ship, so they remain one drag away.
        self.assertEqual(4, len(expected))

    def test_5120_layout_centers_all_sizes_near_the_top(self):
        standard = json.loads(OVERLAY_LAYOUT_PATH.read_text(encoding="utf-8"))
        layout = json.loads(ULTRAWIDE_LAYOUT_PATH.read_text(encoding="utf-8"))
        self.assertEqual("As Driven 5120x1440", layout["Name"])
        self.assertNotEqual(standard["UniqueId"], layout["UniqueId"])
        part_ids = set()
        for part in layout["OverlayLayoutParts"]:
            expected_top = (
                430.0
                if Path(part["DashboardName"]).stem == "As Driven Verification Drive"
                else 60.0
            )
            self.assertEqual(expected_top, part["Top"])
            self.assertEqual(2560.0, part["Left"] + part["Width"] / 2)
            self.assertEqual(
                Path(part["DashboardName"]).stem in PLACED_BY_DEFAULT, part["Placed"]
            )
            self.assertTrue(part["Transparent"])
            part_ids.add(part["PartId"])
        self.assertEqual(4, len(part_ids))


if __name__ == "__main__":
    unittest.main()
