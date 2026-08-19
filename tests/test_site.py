import json
import re
import unittest
from pathlib import Path

from as_driven_db.site import (
    TONE_CAR,
    TONE_DRIVER,
    TONE_OPTIONAL,
    TONE_UNKNOWN,
    build_site,
    collect,
    downshift,
    gate,
    launch,
    upshift,
)


ROOT = Path(__file__).parents[1]


class SiteTests(unittest.TestCase):
    def test_a_gap_never_renders_as_a_car_that_handles_it(self) -> None:
        """The rule the whole dataset rests on, carried onto the page.

        An unrecorded value must read as unrecorded. Rendering it as "no clutch
        needed" or "no blip needed" would turn a gap in the evidence into an
        instruction, which is the one failure this project exists to avoid.
        """
        self.assertEqual(launch("unknown"), ("Not established", TONE_UNKNOWN))
        self.assertEqual(
            upshift("unknown", "unknown", "not-required"),
            ("Not established", TONE_UNKNOWN),
        )
        self.assertEqual(
            downshift("unknown", "no", "not-required"),
            ("Not established", TONE_UNKNOWN),
        )
        # And the established negatives stay distinct from it.
        self.assertEqual(launch("not-required"), ("No clutch needed", TONE_CAR))
        self.assertEqual(
            downshift("not-required", "no", "not-required"),
            ("No blip needed", TONE_CAR),
        )

    def test_an_optional_blip_is_neither_required_nor_absent(self) -> None:
        # Rounding it up invents an instruction; rounding it down loses
        # authentic technique the record deliberately keeps.
        self.assertEqual(
            downshift("optional", "no", "not-required"), ("Blip optional", TONE_OPTIONAL)
        )
        self.assertEqual(
            downshift("required", "no", "not-required"), ("Blip to rev-match", TONE_DRIVER)
        )

    def test_a_dogleg_states_which_side_first_sits_on_only_when_recorded(self) -> None:
        self.assertEqual(gate("h-pattern", "dogleg-h", "down-left"), "Dogleg gate, 1st down and left")
        self.assertEqual(gate("h-pattern", "dogleg-h", "down-right"), "Dogleg gate, 1st down and right")
        # A dogleg establishes only that first sits outside the racing plane.
        self.assertEqual(gate("h-pattern", "dogleg-h", None), "Dogleg gate, 1st outside the plane")

    def test_every_curated_car_reaches_the_page(self) -> None:
        payload = collect(ROOT)
        index = json.loads((ROOT / "data" / "v1" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["cars"]), len(index["records"]))
        self.assertEqual(payload["version"], index["dataset_version"])

        page = build_site(ROOT)
        self.assertEqual(page.count('<tr class="car"'), len(index["records"]))
        # A car is listed under its own name. The aero package a simulator picks
        # from the circuit is not part of it and was dropped from the records.
        for car in payload["cars"]:
            for package in (" Downforce", " - Speedway", " - Superspeedway"):
                self.assertFalse(car["name"].endswith(package), car["id"])

    def test_the_page_is_self_contained_and_encoding_independent(self) -> None:
        page = build_site(ROOT)
        # It owns no <head>, so it cannot declare a charset.
        page.encode("ascii")
        # Google Fonts is the one external host an artifact may reach; nothing
        # else may be fetched, or the page breaks wherever it is opened.
        hosts = set(re.findall(r'https?://([^/"\s]+)', page))
        self.assertLessEqual(hosts, {"fonts.googleapis.com", "fonts.gstatic.com"}, hosts)
        self.assertNotIn("<script src", page)

    def test_the_headline_counts_match_the_records(self) -> None:
        payload = collect(ROOT)
        cars = payload["cars"]
        page = build_site(ROOT)
        stats = dict(
            (label, int(value))
            for value, label in re.findall(r"<b>([\d]+)</b><span>([^<]+)</span>", page)
        )
        self.assertEqual(stats["cars"], len(cars))
        self.assertEqual(
            stats["need the clutch to pull away"],
            sum(1 for car in cars if car["start"] == "required"),
        )
        self.assertEqual(
            stats["need you to blip"],
            sum(1 for car in cars if car["blip"] == "required"),
        )
        self.assertEqual(
            stats["have something unestablished"],
            sum(1 for car in cars if car["open_fields"]),
        )

    def test_the_four_states_are_told_apart_by_more_than_hue(self) -> None:
        """Two warm fills side by side read as the same answer.

        Optional used to be a second amber fill next to the driver's, and at a
        glance the pair was indistinguishable. Each state now differs from the
        others in form as well as colour: the fill says something is being asked
        of somebody, and the border style separates a decided option from a gap.
        """
        page = build_site(ROOT)
        rules = {
            tone: re.search(r"\.tone-%s \{(.*?)\}" % tone, page, re.S).group(1)
            for tone in ("you", "car", "optional", "unknown")
        }
        colors = {tone: re.search(r"color: ([^;]+);", body).group(1) for tone, body in rules.items()}
        self.assertEqual(len(set(colors.values())), 4, colors)

        filled = {tone for tone, body in rules.items() if "background: var(" in body}
        self.assertEqual(filled, {"you", "car"}, filled)
        # The two hollow states are separated by their border, not their hue alone.
        self.assertIn("1px solid", rules["optional"])
        self.assertIn("1px dotted", rules["unknown"])

    def test_the_theme_control_offers_the_three_states_the_page_has(self) -> None:
        """Following the system is a state, not the absence of one.

        An explicit choice stamps the root element and following the system
        stamps nothing, so a control with only Light and Dark would let a reader
        leave the default and never hand the decision back to their machine.
        """
        page = build_site(ROOT)
        offered = re.findall(r'data-theme-set="([a-z]+)"', page)
        self.assertEqual(offered, ["system", "light", "dark"])
        # Nothing is stamped until someone chooses, so the default follows the
        # viewer and the un-stamped palette stays the one that renders.
        self.assertIn('data-theme-set="system" aria-pressed="true"', page)
        self.assertNotIn("<html", page)

    def test_a_theme_token_is_never_defined_only_behind_a_media_query(self) -> None:
        """The viewer's theme has three states, not two.

        The default setting stamps no attribute, so a color whose only
        definition sits inside a media or [data-theme] block never applies
        there, and the page renders one theme's text on the other's ground.
        """
        page = build_site(ROOT)
        root_block = re.search(r":root \{(.*?)\}", page, re.S).group(1)
        base = set(re.findall(r"(--[a-z0-9-]+):", root_block))
        for guarded in re.findall(
            r":root(?:\:not\(\[data-theme=\"light\"\]\)|\[data-theme=\"dark\"\]) \{(.*?)\}",
            page,
            re.S,
        ):
            self.assertLessEqual(set(re.findall(r"(--[a-z0-9-]+):", guarded)), base)


if __name__ == "__main__":
    unittest.main()
