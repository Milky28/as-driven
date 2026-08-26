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
PREFLIGHT_ASSET_PATH = REPOSITORY_ROOT / "simhub" / "dash" / "preflight-assets"
BRAND_MARK_GENERATOR_PATH = REPOSITORY_ROOT / "simhub" / "dash" / "brand_mark.py"


def load_generator():
    sys.path.insert(0, str(GENERATOR_PATH.parent))
    spec = importlib.util.spec_from_file_location("simhub_dash_generator", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_brand_mark_generator():
    sys.path.insert(0, str(BRAND_MARK_GENERATOR_PATH.parent))
    spec = importlib.util.spec_from_file_location(
        "simhub_brand_mark_generator", BRAND_MARK_GENERATOR_PATH
    )
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

    def test_brand_mark_has_a_deterministic_svg_master(self):
        brand_mark = load_brand_mark_generator()
        svg_path = RASTER_ASSET_PATH / "brand-mark.svg"
        self.assertEqual(brand_mark.build_svg(), svg_path.read_bytes())
        svg = svg_path.read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 128 128"', svg)
        self.assertIn('stroke="#fff"', svg)
        self.assertNotIn("<rect", svg)

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
            "detailed": (720, 428),
            "compact": (520, 360),
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
        # The card binds to properties; the wording itself lives in
        # AsDriven.Core.PreflightLabels so every surface says the same thing and
        # the phrasing is asserted in the .NET suite rather than in a formula.
        for property_name in (
            "AsDriven.HasMatch",
            "AsDriven.MatchStatus",
            "AsDriven.RawCarIdentifier",
            "AsDriven.OverlayCarNameDetailed",
            "AsDriven.WheelRimLabel",
            "AsDriven.WheelFeatureLabel",
            "AsDriven.ShifterLabel",
            "AsDriven.ShifterGateLabel",
            "AsDriven.LaunchLabel",
            "AsDriven.UpshiftLabel",
            "AsDriven.DownshiftLabel",
            "AsDriven.LaunchTone",
            "AsDriven.UpshiftTone",
            "AsDriven.DownshiftTone",
            "AsDriven.UseBandTone",
            "AsDriven.SimulatorLabel",
            "AsDriven.VerifiedGameVersion",
            "AsDriven.Confidence",
            "AsDriven.PopupDetailedVisible",
        ):
            self.assertIn(property_name, serialized)
        self.assertIn("No hardware or technique values have been assumed.", serialized)
        self.assertIn("Unknown", serialized)
        # The four-tile vocabulary is gone with the tiles that carried it.
        for retired in (
            "AsDriven.TechniqueSummaryLine1",
            "AsDriven.TechniqueSummaryLine2",
            "Automatic throttle cut",
            "Automatic throttle blip",
            "PHYSICAL CONTROLS",
            "SHIFTING TECHNIQUE",
            "DRIVING TECHNIQUE",
        ):
            self.assertNotIn(retired, serialized)
        self.assertNotIn("MANUAL CUT", serialized)
        self.assertNotIn("MANUAL BLIP", serialized)

    def test_unmatched_card_offers_a_contribution_handoff_without_assuming_values(self):
        for variant in ("detailed", "compact"):
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            serialized = json.dumps(dashboard)
            self.assertIn("No hardware or technique values have been assumed.", serialized)
            self.assertIn("CONTRIBUTE IN AS DRIVEN", serialized)
            self.assertIn("choose Contribute this car", serialized)
            self.assertNotIn("AsDriven.BeginCarContribution", serialized)
            self.assertNotIn("AsDriven.ContributionRequestPending", serialized)

    def test_bitmap_icons_cover_supported_control_categories_and_unknowns(self):
        dashboards = [
            self.generator.build_dashboard(overlay=True, variant=variant)
            for variant in ("detailed", "compact")
        ]
        serialized = json.dumps(dashboards)
        # Every rim and shifter value the schema allows still selects an icon,
        # including the three retired rim values, so an older installed dataset
        # never falls through to the unknown mark.
        for value in (
            "round",
            "d-shaped",
            "gt-formula",
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
            "wheel-d-shaped",
            "wheel-gt-formula",
            "wheel-yoke",
            "shift-dogleg-h",
            "shift-h-pattern",
            "shift-sequential-stick",
            "shift-sequential-paddles",
            "brand-mark",
        ):
            self.assertIn(asset, serialized)
        self.assertIn("GraphicalDash.Models.ImageItem", serialized)
        # The cut, blip and lift tiles were replaced by the Use band's text.
        for retired in ("cut-auto", "cut-manual", "blip-auto", "blip-manual", "lift-required"):
            self.assertNotIn(retired, serialized)
        self.assertEqual(18, len(dashboards[0]["Images"]))
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
        # The card draws the flat preflight family; the only reviewed raster it
        # still takes from the popup asset directory is the brand mark, which is
        # generated geometry rather than an icon and must ship byte for byte.
        packaged = self.generator._icon_assets()
        self.assertEqual(
            (RASTER_ASSET_PATH / "brand-mark.png").read_bytes(), packaged["brand-mark"]
        )
        family = self.generator.generate_preflight_icons(size=128)
        self.assertEqual(set(packaged), set(family) | {"brand-mark"})
        for name, data in family.items():
            self.assertEqual(data, packaged[name])
            self.assertEqual(
                (PREFLIGHT_ASSET_PATH / f"{name}.png").read_bytes(),
                data,
                f"{name} on disk differs from the generated master",
            )

    def test_flat_preflight_icon_family_is_complete_and_deterministic(self):
        expected = {
            "control-clutch",
            "control-throttle",
            "note-info",
            "shift-automatic-lever",
            "shift-direct-selection",
            "shift-dogleg-h",
            "shift-dogleg-h-mirrored",
            "shift-h-pattern",
            "shift-sequential-paddles",
            "shift-sequential-stick",
            "shift-unknown",
            "wheel-d-shaped",
            "wheel-gt-formula",
            "wheel-other",
            "wheel-round",
            "wheel-unknown",
            "wheel-yoke",
        }
        paths = {
            path.stem: path
            for path in PREFLIGHT_ASSET_PATH.glob("*.png")
        }
        self.assertEqual(expected, set(paths))

        icon_module = sys.modules["icons"]
        generated = icon_module.generate_preflight_icons()
        self.assertEqual(expected, set(generated))
        for name, path in paths.items():
            data = path.read_bytes()
            self.assertEqual(b"\x89PNG\r\n\x1a\n", data[:8])
            self.assertEqual((128, 128), tuple(int.from_bytes(data[offset:offset + 4], "big") for offset in (16, 20)))
            self.assertEqual(data, generated[name])

    def test_detailed_separates_what_to_fit_from_what_to_do(self):
        dashboard = self.generator.build_dashboard(overlay=True, variant="detailed")
        named = {
            value["Name"]: value
            for value in walk(dashboard)
            if isinstance(value, dict) and "Name" in value
        }
        # Two bands, each with its own spine, and the Use band below the Fit
        # band because hardware is settled before the car moves.
        self.assertEqual("FIT", named["FitRailLabel"]["Text"])
        self.assertEqual(270, named["FitRailLabel"]["Rotation"])
        self.assertLess(named["FitBand"]["Top"], named["UseBand"]["Top"])
        self.assertEqual(
            "AsDriven.WheelRimLabel",
            named["FitWheelHead"]["Bindings"]["Text"]["Formula"]["Expression"].strip("[]"),
        )
        self.assertEqual(
            "AsDriven.ShifterLabel",
            named["FitShiftHead"]["Bindings"]["Text"]["Formula"]["Expression"].strip("[]"),
        )
        # Three moments, in the order they happen.
        for moment in ("Launch", "Upshift", "Downshift"):
            self.assertIn(f"UseValue{moment}", named)
        # Both running shifts state their clutch outright. Leaving it unsaid
        # would be indistinguishable from never having checked it.
        self.assertEqual(
            "[AsDriven.UpshiftClutchLabel]",
            named["UseClutchUpshift"]["Bindings"]["Text"]["Formula"]["Expression"],
        )
        self.assertEqual(
            "[AsDriven.DownshiftClutchLabel]",
            named["UseClutchDownshift"]["Bindings"]["Text"]["Formula"]["Expression"],
        )
        self.assertLess(named["UseValueUpshift"]["Top"], named["UseClutchUpshift"]["Top"])
        self.assertLess(named["UseValueLaunch"]["Left"], named["UseValueUpshift"]["Left"])
        self.assertLess(named["UseValueUpshift"]["Left"], named["UseValueDownshift"]["Left"])
        # The rail and every cell carry their own tone, so a cell that
        # disagrees with the band is never overpainted by it.
        for suffix in ("You", "Car", "Rest"):
            self.assertIn(f"UseRail{suffix}", named)
            self.assertIn(f"UseCellUpshift{suffix}", named)
        # The heading has a fourth state: optional is settled and reads in
        # ordinary text, so grey is left to mean "not established".
        for suffix in ("You", "Car", "Optional", "Unknown"):
            self.assertIn(f"UseHeadUpshift{suffix}", named)
        self.assertEqual(
            self.generator.CELL_CAR, named["UseCellUpshiftCarFill"]["BackgroundColor"]
        )
        self.assertEqual(
            self.generator.CELL_YOU, named["UseCellUpshiftYouFill"]["BackgroundColor"]
        )

    def test_compact_keeps_both_bands(self):
        compact = self.generator.build_dashboard(overlay=True, variant="compact")
        compact_named = {
            value["Name"]: value
            for value in walk(compact)
            if isinstance(value, dict) and "Name" in value
        }
        self.assertEqual("FIT", compact_named["FitRailLabel"]["Text"])
        for moment in ("Launch", "Upshift", "Downshift"):
            self.assertIn(f"UseValue{moment}", compact_named)
        self.assertIn(
            "AsDriven.OverlayCarNameDetailed",
            compact_named["Title"]["Bindings"]["Text"]["Formula"]["Expression"],
        )

    def test_every_size_binds_its_own_fitted_name_and_class(self):
        """Each size measures the name for its own width.

        The aero package now rides on the class line, so the name binding must
        be the fitted one for that surface rather than the raw display name,
        which is 45 characters at its longest and was being cut off.
        """
        for variant, name_property in (
            ("detailed", "OverlayCarNameDetailed"),
            ("compact", "OverlayCarNameDetailed"),
        ):
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            named = {
                value["Name"]: value
                for value in walk(dashboard)
                if isinstance(value, dict) and "Name" in value
            }
            self.assertIn(
                f"AsDriven.{name_property}",
                named["Title"]["Bindings"]["Text"]["Formula"]["Expression"],
                variant,
            )
            self.assertIn(
                "AsDriven.OverlayCarClassDetailed",
                named["CarClass"]["Bindings"]["Text"]["Formula"]["Expression"],
                variant,
            )

    def test_card_content_stays_inside_the_box_that_holds_it(self):
        """Nothing overlaps its neighbour or escapes its container.

        The simulator-difference marker was 150px wide and anchored near a
        cell's right edge, so it ran across the divider and printed over the
        next moment's heading. Screenshots caught that; this catches the next
        one.
        """
        for variant in ("detailed", "compact"):
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            named = {
                value["Name"]: value
                for value in walk(dashboard)
                if isinstance(value, dict) and "Name" in value
            }

            def box(name):
                item = named[name]
                return (item["Left"], item["Top"],
                        item["Left"] + item["Width"], item["Top"] + item["Height"])

            band = named["UseBand"]
            cell_width = (band["Width"] - 30) / 3
            # Every text item in a moment stays within that moment's column.
            for index, moment in enumerate(("Launch", "Upshift", "Downshift")):
                left_edge = band["Left"] + 30 + cell_width * index
                for part in ("UseValue", "UseClutch", "UseDiffers"):
                    key = part + moment + ("Text" if part == "UseDiffers" else "")
                    x1, _, x2, _ = box(key)
                    self.assertGreaterEqual(x1, left_edge - 1, f"{variant} {key} starts left of its cell")
                    self.assertLessEqual(
                        x2, left_edge + cell_width + 1,
                        f"{variant} {key} runs into the next moment",
                    )

            # The vertical stack never collides, and the last row stays on the card.
            order = ["HeaderRule", "FitBand", "UseBand", "NotePanel", "FooterRule"]
            for upper, lower in zip(order, order[1:]):
                self.assertLessEqual(
                    box(upper)[3], box(lower)[1],
                    f"{variant}: {upper} overlaps {lower}",
                )
            self.assertLessEqual(box("UseDiffersDownshiftText")[3], box("UseBand")[3], variant)
            self.assertLessEqual(box("NoteLine3")[3], box("NotePanel")[3], variant)
            self.assertLessEqual(box("Dataset")[3], dashboard["BaseHeight"], variant)

    def test_static_text_fits_the_box_that_draws_it(self):
        """Geometry is not enough: the glyphs have to fit too.

        The box-containment test above passes when an item is exactly as wide as
        its container, which is what a full-width line always is. The waiting
        card said "...to see authentic controls gui" for exactly that reason -
        every rectangle was in the right place and the sentence was longer than
        the space for it.

        Dashboard text items do not wrap, so a string wider than its box is
        clipped rather than reflowed. This measures at half the font size per
        character, which is narrower than any bold sans actually renders, so a
        string that fails here is certainly too long rather than arguably so.
        """
        # Both empty states are always built into the card and shown by
        # expression, so every variant already carries all of this text.
        for variant in ("detailed", "compact"):
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            for item in walk(dashboard):
                if not isinstance(item, dict) or "Name" not in item:
                    continue
                text = item.get("Text")
                size = item.get("FontSize")
                if not isinstance(text, str) or not text or not size:
                    continue
                if item.get("Expression"):
                    # Driven by a formula at runtime; the literal is a
                    # placeholder and says nothing about what is drawn.
                    continue
                estimated = len(text) * size * 0.5
                self.assertLessEqual(
                    estimated, item["Width"],
                    "%s %s: %r needs about %dpx and has %d"
                    % (variant, item["Name"], text, estimated, item["Width"]),
                )

    def test_note_panel_only_appears_when_the_record_carries_a_summary(self):
        for variant in ("detailed", "compact"):
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            named = {
                value["Name"]: value
                for value in walk(dashboard)
                if isinstance(value, dict) and "Name" in value
            }
            prefix = "DriverSummary" if variant == "detailed" else "DriverSummaryCompact"
            # Dashboard text items do not wrap, so the summary is drawn as three
            # pre-broken lines rather than one item that would clip.
            for index in (1, 2, 3):
                self.assertEqual(
                    f"[AsDriven.{prefix}Line{index}]",
                    named[f"NoteLine{index}"]["Bindings"]["Text"]["Formula"]["Expression"],
                    variant,
                )
            # The whole group hides when there is nothing to say, so a record
            # without a summary ends after the Use band instead of reserving an
            # empty panel.
            self.assertEqual(
                "[AsDriven.DriverSummary] != ''",
                named["DriverNote"]["Bindings"]["Visible"]["Formula"]["Expression"],
                variant,
            )
            self.assertEqual("note-info", named["NoteIcon"]["Image"], variant)

    def test_rows_mark_where_the_simulator_departs_from_the_real_car(self):
        dashboard = self.generator.build_dashboard(overlay=True, variant="detailed")
        named = {
            value["Name"]: value
            for value in walk(dashboard)
            if isinstance(value, dict) and "Name" in value
        }
        # The card renders effective behaviour. Each row distinguishes a real
        # departure from simulator evidence filling an unknown authentic value.
        for name, flag in (
            ("FitShiftDiffers", "ShifterDiffers"),
            ("FitWheelDiffers", "WheelDiffers"),
            ("UseDiffersLaunch", "LaunchDiffers"),
            ("UseDiffersUpshift", "UpshiftDiffers"),
            ("UseDiffersDownshift", "DownshiftDiffers"),
        ):
            self.assertEqual(
                f"[AsDriven.{flag}]",
                named[name + "Departure"]["Bindings"]["Visible"]["Formula"]["Expression"],
                name,
            )
            self.assertEqual("* not as the real car", named[name + "Text"]["Text"])
            unestablished_flag = flag.replace("Differs", "Unestablished")
            self.assertEqual(
                f"[AsDriven.{unestablished_flag}] && ![AsDriven.{flag}]",
                named[name + "Unestablished"]["Bindings"]["Visible"]["Formula"]["Expression"],
                name,
            )
            self.assertEqual(
                "* real car not established",
                named[name + "UnestablishedText"]["Text"],
            )

    def test_evidence_footer_uses_the_matched_simulator(self):
        dashboard = self.generator.build_dashboard(overlay=True, variant="detailed")
        named = {
            value["Name"]: value
            for value in walk(dashboard)
            if isinstance(value, dict) and "Name" in value
        }
        expression = named["Evidence"]["Bindings"]["Text"]["Formula"]["Expression"]
        self.assertIn("[AsDriven.SimulatorLabel]", expression)
        self.assertNotIn("'AMS2 '", expression)


    def test_preview_badge_explicitly_says_preview_is_not_live(self):
        for variant in ("detailed", "compact"):
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

    def test_every_size_titles_the_card_with_the_brand_mark(self):
        for variant in ("detailed", "compact"):
            dashboard = self.generator.build_dashboard(overlay=True, variant=variant)
            named = {
                value["Name"]: value
                for value in walk(dashboard)
                if isinstance(value, dict) and "Name" in value
            }
            self.assertEqual("brand-mark", named["Mark"]["Image"], variant)
            self.assertNotIn("MarkText", named)
            # The retired four-tile furniture is gone from every size.
            for retired in (
                "PhysicalControlsHeading",
                "ShiftingTechniqueHeading",
                "PhysicalControlsGroup",
                "ShiftingTechniqueGroup",
                "WheelTile",
                "ShiftTile",
                "CutTile",
                "BlipTile",
                "DrivingTechniqueHeading",
            ):
                self.assertNotIn(retired, named, f"{retired} still in {variant}")
            self.assertEqual(self.generator.ACCENT, named["Accent"]["BackgroundColor"])
            self.assertEqual(4, named["Card"]["Left"])

    def test_compact_states_the_match_in_words_and_keeps_confidence_case(self):
        dashboard = self.generator.build_dashboard(overlay=True, variant="compact")
        named = {
            value["Name"]: value
            for value in walk(dashboard)
            if isinstance(value, dict) and "Name" in value
        }
        # A tick alone did not say what had matched. The header now states it,
        # with a dot carrying the colour so the words stay readable.
        self.assertEqual("Telemetry matched", named["Match"]["Text"])
        self.assertEqual(self.generator.GREEN, named["MatchDot"]["FillColor"])
        self.assertIn("MatchKind", named["Match"]["Bindings"]["Text"]["Formula"]["Expression"])
        self.assertEqual("PREVIEW", named["PreviewBadgeTitle"]["Text"])
        self.assertEqual("NOT LIVE", named["PreviewBadgeLive"]["Text"])
        evidence = named["Evidence"]["Bindings"]["Text"]["Formula"]["Expression"]
        self.assertIn("'Verified'", evidence)
        self.assertIn("'Medium'", evidence)

    def test_generator_writes_parseable_native_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = self.generator.write_dashboards(Path(temporary_directory))
            self.assertEqual(12, len(paths))
            for path in paths:
                self.assertTrue(path.is_file())
                self.assertEqual(path.parent.name, path.name.split(".djson", 1)[0])
                if path.name.endswith(".ressources"):
                    with zipfile.ZipFile(path) as archive:
                        names = archive.namelist()
                        self.assertEqual(18, len(names))
                        self.assertIn("brand-mark.png", names)
                        self.assertIn("wheel-gt-formula.png", names)
                        self.assertNotIn("cut-auto.png", names)
                        self.assertNotIn("lift-required.png", names)
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
        self.assertEqual(3, len(parts))
        expected = {
            "As Driven Preflight Overlay": ((720.0, 428.0), (600.0, 60.0)),
            "As Driven Preflight Compact": ((520.0, 360.0), (700.0, 60.0)),
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
        self.assertEqual(3, len(part_ids))
        # The unplaced sizes still ship, so they remain one drag away.
        self.assertEqual(3, len(expected))

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
        self.assertEqual(3, len(part_ids))


if __name__ == "__main__":
    unittest.main()
