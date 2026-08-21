import json
import re
import unittest
from pathlib import Path

from as_driven_db.site import (
    TONE_CAR,
    differences,
    TONE_DRIVER,
    TONE_OPTIONAL,
    TONE_UNKNOWN,
    build_site,
    collect,
    downshift,
    gate,
    launch,
    upshift,
    wheel_equipment,
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

    def test_wheel_display_and_shift_lights_remain_independent(self) -> None:
        self.assertEqual(wheel_equipment("yes", "yes"), "Display · Shift lights")
        self.assertEqual(wheel_equipment("yes", "no"), "Display · No shift lights")
        self.assertEqual(wheel_equipment("no", "yes"), "No display · Shift lights")
        self.assertEqual(wheel_equipment("no", "no"), "No display · No shift lights")
        self.assertEqual(
            wheel_equipment("no", "unknown"),
            "No display · Lights not established",
        )
        self.assertEqual(
            wheel_equipment("unknown", "unknown"),
            "Display not established · Lights not established",
        )

    def test_wheel_equipment_reaches_each_car_row(self) -> None:
        cars = {car["id"]: car for car in collect(ROOT)["cars"]}
        self.assertEqual(cars["roco-001"]["wheel_equipment"], "Display · No shift lights")
        self.assertEqual(cars["bmw-m6-gt3"]["wheel_equipment"], "No display · Shift lights")
        page = build_site(ROOT)
        for car in cars.values():
            rendered = car["wheel_equipment"].encode(
                "ascii", "xmlcharrefreplace"
            ).decode("ascii")
            self.assertIn(rendered, page)

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
        simulator_entries = sum(len(car["simulators"]) for car in payload["cars"])
        self.assertEqual(page.count('data-simulator-panel="'), simulator_entries)
        # A car is listed under its own name. The aero package a simulator picks
        # from the circuit is not part of it and was dropped from the records.
        for car in payload["cars"]:
            for package in (" Downforce", " - Speedway", " - Superspeedway"):
                self.assertFalse(car["name"].endswith(package), car["id"])

    def test_a_simulator_difference_is_shown_without_altering_the_car(self) -> None:
        """Both layers, and neither one overwriting the other.

        A row states the real car. Where a simulator does something else the
        record says so with an override, and the page has to show that too -
        otherwise a reader is told the Cayman needs no clutch to pull away while
        the game they are about to load demands one.
        """
        payload = collect(ROOT)
        page = build_site(ROOT)
        differing = [car for car in payload["cars"] if car["has_differences"]]
        differing_views = [
            simulator
            for car in payload["cars"]
            for simulator in car["simulators"]
            if simulator["differences"]
        ]
        self.assertEqual(page.count('class="differs-flag"'), len(differing))
        self.assertEqual(page.count('<ul class="differs">'), len(differing_views))

        by_name = {car["name"]: car for car in differing}
        # Rendered in the page's own words rather than as raw enum values, and
        # in both directions, so the reader can see which is which.
        diablo_car = by_name["Lamborghini Diablo SV-R"]
        diablo_view = next(
            simulator for simulator in diablo_car["simulators"]
            if simulator["id"] == "ams2"
        )
        diablo = diablo_view["differences"][0]
        self.assertEqual(diablo["name"], "Downshift")
        self.assertEqual(diablo["real"], "Blip optional")
        self.assertEqual(diablo["sim"], "Blip to rev-match")
        self.assertTrue(diablo["why"])

        # The table above still states the real car; the override belongs to the
        # detail panel and must not leak into the row.
        self.assertEqual(diablo_car["launch"][0], "Clutch required")

        # An override does not need an established real value underneath it. The
        # Cayman's was withdrawn when the record turned out to describe the wrong
        # generation, and the simulator's demand still has to reach the driver -
        # otherwise the page says nothing about a game that will refuse to move.
        cayman_car = by_name["Porsche Cayman GT4 Clubsport MR"]
        cayman = next(
            simulator for simulator in cayman_car["simulators"]
            if simulator["id"] == "ams2"
        )["differences"][0]
        self.assertEqual(cayman["name"], "Pulling away")
        self.assertEqual(cayman["real"], "Not established")
        self.assertEqual(cayman["sim"], "Clutch required")

    def test_a_difference_is_described_even_where_the_table_has_no_column(self) -> None:
        # The Milano's override is the clutch on a downshift, which the table
        # does not show at all. Diffing the rendered rows would have missed it,
        # so each overridden field is described on its own terms.
        milano = next(
            car for car in collect(ROOT)["cars"] if car["name"] == "Milano 55 GT1"
        )
        ams2 = next(simulator for simulator in milano["simulators"] if simulator["id"] == "ams2")
        self.assertEqual(
            ams2["differences"],
            [
                {
                    "name": "Clutch on a downshift",
                    "real": "Clutch required",
                    "sim": "No clutch needed",
                    "why": ams2["differences"][0]["why"],
                }
            ],
        )

    def test_parallel_running_clutch_gaps_are_not_rendered_twice(self) -> None:
        diablo = next(
            car for car in collect(ROOT)["cars"]
            if car["id"] == "lamborghini-diablo-sv-r"
        )
        self.assertEqual(diablo["open_fields"], ["running-shift clutch"])
        self.assertEqual(diablo["unexplained_open_fields"], [])
        self.assertEqual(len(diablo["deviations"]), 1)
        self.assertEqual(diablo["deviations"][0]["field"], "running-shift clutch")
        self.assertIn(
            "The clutch's use on running shifts is not established",
            diablo["deviations"][0]["why"],
        )

    def test_a_car_the_simulator_models_faithfully_says_nothing(self) -> None:
        self.assertEqual(differences({"forward_gears": 6}, []), [])
        quiet = [
            simulator
            for car in collect(ROOT)["cars"]
            for simulator in car["simulators"]
            if not simulator["differences"]
        ]
        self.assertGreater(len(quiet), 200)

    def test_every_reviewed_simulator_is_a_selectable_linked_view(self) -> None:
        payload = collect(ROOT)
        page = build_site(ROOT)
        audi = next(car for car in payload["cars"] if car["id"] == "audi-r8-lms-gt3-evo-ii")
        self.assertEqual(
            [(simulator["id"], simulator["label"]) for simulator in audi["simulators"]],
            [("ams2", "AMS2"), ("ac-evo", "Assetto Corsa EVO")],
        )
        self.assertIn('data-simulators=" ams2 ac-evo "', page)
        for simulator in audi["simulators"]:
            anchor = f'audi-r8-lms-gt3-evo-ii--{simulator["id"]}'
            self.assertIn(
                f'id="{anchor}" data-simulator-anchor-target="{simulator["id"]}"',
                page,
            )
            self.assertIn(f'id="{anchor}-panel" role="tabpanel"', page)
            self.assertIn(f'href="#{anchor}"', page)
        ac_evo = next(
            simulator for simulator in audi["simulators"] if simulator["id"] == "ac-evo"
        )
        self.assertEqual(ac_evo["unknown_behavior"], ["automatic shift cut"])
        self.assertIn("Simulator behavior not established", page)
        self.assertIn("window.addEventListener('hashchange'", page)

    def test_the_simulator_filter_is_derived_from_released_records(self) -> None:
        payload = collect(ROOT)
        self.assertEqual(
            payload["simulators"],
            [
                {"id": "ams2", "label": "AMS2"},
                {"id": "ac-evo", "label": "Assetto Corsa EVO"},
            ],
        )
        page = build_site(ROOT)
        self.assertIn('<option value="ac-evo">Assetto Corsa EVO</option>', page)
        self.assertIn('<option value="ams2">AMS2</option>', page)

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
        self.assertEqual(stats["simulators represented"], len(payload["simulators"]))
        self.assertEqual(
            stats["reviewed simulator views"],
            sum(len(car["simulators"]) for car in cars),
        )
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
        self.assertEqual(
            stats["differ in the simulator"],
            sum(1 for car in cars if car["has_differences"]),
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

    def test_the_table_does_not_rely_on_inheriting_colour_or_font(self) -> None:
        """The page has no doctype, so it can be rendered in quirks mode.

        It ships without one because the artifact host supplies it, but the
        documented workflow also writes the file to disk, and a local file with
        no doctype renders in quirks mode - where a table inherits neither colour
        nor font. That put the light palette's ink on the dark ground for every
        row while the surrounding page was correct, and nothing above the table
        looked wrong. The rule states both explicitly.
        """
        page = build_site(ROOT)
        rule = re.search(r"\ntable \{(.*?)\}", page, re.S).group(1)
        self.assertIn("color: var(--ink)", rule)
        self.assertIn("font: inherit", rule)

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
