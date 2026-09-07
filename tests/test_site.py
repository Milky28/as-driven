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
    shifter,
    simulator_cockpit,
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
        self.assertEqual(wheel_equipment("yes", "yes"), "Display · Lights")
        self.assertEqual(wheel_equipment("yes", "no"), "Display · No lights")
        self.assertEqual(wheel_equipment("no", "yes"), "No display · Lights")
        self.assertEqual(wheel_equipment("no", "no"), "No display · No lights")
        self.assertEqual(
            wheel_equipment("no", "unknown"),
            "No display · Lights not established",
        )
        # Both halves open collapse into one clause. Said twice this was the
        # longest string the column ever held, and it overflowed into the
        # shifter column beside it.
        self.assertEqual(
            wheel_equipment("unknown", "unknown"),
            "Display and lights not established",
        )
        # An unrecorded rim already says the wheel was not seen, on the line
        # directly above. Repeating it under that is one cell saying "unknown"
        # three times, so the equipment line is dropped.
        self.assertEqual(wheel_equipment("unknown", "unknown", "unknown"), "")
        self.assertEqual(wheel_equipment("no", "unknown", "unknown"), "")
        # A known rim keeps its equipment line whatever the fittings say.
        self.assertEqual(
            wheel_equipment("no", "no", "round"), "No display · No lights"
        )

    def test_wheel_equipment_reaches_each_car_row(self) -> None:
        cars = {car["id"]: car for car in collect(ROOT)["cars"]}
        self.assertEqual(cars["roco-001"]["wheel_equipment"], "Display · No lights")
        self.assertEqual(
            cars["bmw-m6-gt3"]["wheel_equipment"],
            "No display · Lights not established",
        )
        page = build_site(ROOT)
        for car in cars.values():
            rendered = car["wheel_equipment"].encode(
                "ascii", "xmlcharrefreplace"
            ).decode("ascii")
            self.assertIn(rendered, page)

    def test_simulator_only_wheel_facts_reach_the_simulator_tab(self) -> None:
        behavior = {
            "wheel_rim_type": {
                "normalized": "round",
                "integrated_display": "no",
                "shift_lights": "no",
                "open_top": "no",
            }
        }
        self.assertEqual(
            simulator_cockpit(behavior),
            ["Round rim", "No display", "No shift lights", "Closed top"],
        )

        viper = next(
            car for car in collect(ROOT)["cars"] if car["id"] == "dodge-viper-gts-r"
        )
        self.assertEqual(
            [view["cockpit"] for view in viper["simulators"]],
            [
                ["Round rim", "No display", "No shift lights", "Closed top"],
                ["Round rim", "No display", "No shift lights", "Closed top"],
            ],
        )
        payload = collect(ROOT)
        page = build_site(ROOT)
        cockpit_views = sum(
            bool(view["cockpit"])
            for car in payload["cars"]
            for view in car["simulators"]
        )
        self.assertEqual(page.count("Cockpit in this simulator"), cockpit_views)
        self.assertIn(
            '<h4>Cockpit in this simulator</h4><div class="chips">'
            '<span class="chip">Round rim</span><span class="chip">No display</span>'
            '<span class="chip">No shift lights</span><span class="chip">Closed top</span>',
            page,
        )

    def test_a_dogleg_states_which_side_first_sits_on_only_when_recorded(self) -> None:
        self.assertEqual(gate("h-pattern", "dogleg-h", "down-left"), "Dogleg gate, 1st down and left")
        self.assertEqual(gate("h-pattern", "dogleg-h", "down-right"), "Dogleg gate, 1st down and right")
        # A dogleg establishes only that first sits outside the racing plane.
        self.assertEqual(gate("h-pattern", "dogleg-h", None), "Dogleg gate, 1st outside the plane")

    def test_sequential_hardware_is_named_once(self) -> None:
        self.assertEqual(shifter(6, "sequential-stick"), "6-speed sequential stick")
        self.assertEqual(shifter(6, "sequential-paddles"), "6-speed paddle shift")
        self.assertEqual(gate("sequential-stick", "sequential", None), "")
        self.assertEqual(gate("sequential-paddles", "sequential", None), "")

        cars = {car["id"]: car for car in collect(ROOT)["cars"]}
        self.assertEqual(cars["dodge-viper-gts-r"]["shifter"], "6-speed sequential stick")
        self.assertEqual(cars["dodge-viper-gts-r"]["gate"], "")
        self.assertEqual(cars["dallara-sp1"]["shifter"], "6-speed paddle shift")
        self.assertEqual(cars["dallara-sp1"]["gate"], "")

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

    def test_each_car_maps_verified_fields_to_linked_sources(self) -> None:
        payload = collect(ROOT)
        page = build_site(ROOT)
        self.assertEqual(
            page.count('<details class="verification">'),
            len(payload["cars"]),
        )

        corvette = next(
            car for car in payload["cars"]
            if car["id"] == "chevrolet-corvette-c5-r"
        )
        verification = corvette["verification"]
        record = json.loads(
            (ROOT / "data" / "v1" / "cars" / "chevrolet-corvette-c5-r.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(
            verification["claim_count"],
            len(record["provenance"]["claims"]),
        )
        self.assertGreaterEqual(verification["source_count"], 2)
        self.assertTrue(
            any(
                "Transmission and shift technique" in claim["fields"]
                or "Gearbox construction" in claim["fields"]
                for claim in verification["claims"]
            )
        )
        manufacturer_claim = next(
            claim for claim in verification["claims"]
            if any(source["id"] == "gm-archive.corvette-c5r.2003"
                   for source in claim["sources"])
        )
        manufacturer_source = next(
            source for source in manufacturer_claim["sources"]
            if source["id"] == "gm-archive.corvette-c5r.2003"
        )
        self.assertEqual(manufacturer_source["title"], "2003 Corvette C5-R specifications")
        self.assertEqual(
            manufacturer_source["url"],
            "https://www.corvetteactioncenter.com/specs/c5/c5r/2003c5r.html",
        )
        self.assertIn("How this was verified", page)
        self.assertIn(
            '<a href="https://www.corvetteactioncenter.com/specs/c5/c5r/2003c5r.html" '
            'target="_blank" rel="noreferrer">2003 Corvette C5-R specifications</a>',
            page,
        )
        self.assertIn('class="confidence confidence-verified"', page)

    def test_local_observations_link_only_to_public_contribution_issues(self) -> None:
        payload = collect(ROOT)
        page = build_site(ROOT)
        sources = {
            source["id"]: source
            for car in payload["cars"]
            for claim in car["verification"]["claims"]
            for source in claim["sources"]
        }

        legacy = sources[
            "ams2.local-live-panoz-esperante-gtlm-controls.1.6.9.91"
        ]
        self.assertEqual("", legacy["url"])
        self.assertIn(f'<strong>{legacy["title"]}</strong>', page)
        self.assertNotIn(
            f'rel="noreferrer">{legacy["title"]}</a>',
            page,
        )

        public = sources[
            "ams2.local-live-toyota-corolla-stock-car-2021-controls.1.6.9.91"
        ]
        self.assertEqual(
            "https://github.com/Milky28/as-driven/issues/2",
            public["url"],
        )
        self.assertIn(
            f'href="{public["url"]}" target="_blank" '
            f'rel="noreferrer">{public["title"]}</a>',
            page,
        )

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

        # A second car, because the two differ in kind. The Diablo's override
        # softens what the driver must do; this one adds a requirement the real
        # car has no pedal for, and a reader told only the real answer would be
        # told nothing about a game that will refuse to move.
        cayman_car = by_name["Porsche Cayman GT4 Clubsport MR"]
        cayman = next(
            simulator for simulator in cayman_car["simulators"]
            if simulator["id"] == "ams2"
        )["differences"][0]
        self.assertEqual(cayman["name"], "Pulling away")
        self.assertEqual(cayman["real"], "No clutch needed")
        self.assertEqual(cayman["sim"], "Clutch required")
        self.assertEqual(cayman_car["launch"][0], "No clutch needed")

        # The BMW correction is the full boundary in one record: the row keeps
        # the works P60 V8's H-pattern technique while the AMS2 panel states
        # every observed sequential-stick departure in driver-facing language.
        bmw_car = by_name["BMW M3 E46 GTR"]
        bmw = next(
            simulator for simulator in bmw_car["simulators"]
            if simulator["id"] == "ams2"
        )
        self.assertEqual(bmw_car["shifter"], "6-speed H-pattern")
        self.assertEqual(bmw_car["gate"], "Standard gate, 1st up and left")
        self.assertEqual(
            [
                (item["name"], item["real"], item["sim"])
                for item in bmw["differences"]
            ],
            [
                ("Shifter", "6-speed H-pattern", "6-speed sequential stick"),
                (
                    "Selection pattern",
                    "Standard H-pattern",
                    "Sequential, one gear at a time",
                ),
                ("Upshift", "Lift the throttle", "Stay flat, car cuts"),
                ("Automatic shift cut", "No automatic cut", "Automatic cut"),
                # The rim rows arrived when dataset 0.5.66 returned the real
                # car's rim to unknown. AMS2 read it round, PMR and GTR2 read it
                # D-shaped, and none of the three is evidence about the works
                # car, so the page now says so instead of picking one.
                ("Wheel-rim category", "Not established", "Round rim"),
                ("Integrated wheel display", "Not established", "No"),
                ("Wheel shift lights", "Not established", "No"),
                ("Open-top wheel", "Not established", "No"),
            ],
        )
        pmr = next(
            simulator for simulator in bmw_car["simulators"]
            if simulator["id"] == "pmr"
        )
        self.assertEqual(
            [
                (item["name"], item["real"], item["sim"])
                for item in pmr["differences"]
            ],
            [
                ("Upshift", "Lift the throttle", "Stay flat"),
                ("Downshift", "Blip to rev-match", "No blip needed"),
                # PMR's rim reading is now stated against an unestablished real
                # car rather than against AMS2's, which was never evidence.
                ("Wheel-rim category", "Not established", "D-shaped rim"),
                ("Integrated wheel display", "Not established", "No"),
                ("Wheel shift lights", "Not established", "No"),
                ("Open-top wheel", "Not established", "No"),
            ],
        )
        self.assertEqual(pmr["unknown_behavior"], ["automatic shift cut"])

    def test_simulator_view_leads_with_actionable_drive_card(self) -> None:
        """A selected game answers "what do I do?" before its evidence trail.

        The card applies both an explicit simulator override and a directly
        observed game behavior. An explicit game gap cannot turn a real-car
        automation assumption into a simulator instruction.
        """
        cars = {car["id"]: car for car in collect(ROOT)["cars"]}
        cayman = cars["porsche-cayman-gt4-clubsport-mr"]
        ams2 = next(view for view in cayman["simulators"] if view["id"] == "ams2")
        self.assertEqual(ams2["drive"]["launch"], ("Clutch required", TONE_DRIVER))
        self.assertEqual(ams2["drive"]["shifter"], "6-speed paddle shift")

        audi = cars["audi-r8-lms-gt3-evo-ii"]
        ams2_audi = next(view for view in audi["simulators"] if view["id"] == "ams2")
        # AMS2 did not establish its shift-cut behavior. The drive card keeps
        # the baseline action but names the simulator gap at the field itself.
        self.assertEqual(
            ams2_audi["drive"]["upshift"],
            ("Stay flat · cut not established · No clutch needed", TONE_UNKNOWN),
        )
        self.assertIn("automatic shift cut", ams2_audi["unknown_behavior"])

        db9 = cars["aston-martin-dbr9"]
        ac_db9 = next(view for view in db9["simulators"] if view["id"] == "ac")
        self.assertEqual(
            ac_db9["drive"]["upshift"],
            ("Stay flat · cut not established · No clutch needed", TONE_UNKNOWN),
        )

        bmw = cars["bmw-2002-turbo"]
        ams2_bmw = next(view for view in bmw["simulators"] if view["id"] == "ams2")
        self.assertEqual(
            ams2_bmw["drive"]["upshift"],
            ("Lift the throttle · Clutch required", TONE_DRIVER),
        )
        self.assertEqual(
            ams2_bmw["drive"]["downshift"],
            ("Blip optional · Clutch required", TONE_OPTIONAL),
        )

        page = build_site(ROOT)
        self.assertEqual(page.count('class="drive-it"'), sum(
            len(car["simulators"]) for car in cars.values()
        ))
        self.assertIn('aria-label="How to drive Porsche Cayman GT4 Clubsport MR in AMS2"', page)
        self.assertEqual(page.count('class="copy-setup"'), sum(
            len(car["simulators"]) for car in cars.values()
        ))
        self.assertIn('data-copy-setup="Porsche Cayman GT4 Clubsport MR ', page)
        self.assertIn('data-copy-anchor="porsche-cayman-gt4-clubsport-mr--ams2"', page)
        self.assertIn("function copyText(text)", page)
        self.assertIn("navigator.clipboard.writeText(text)", page)
        self.assertIn("Copy unavailable", page)
        self.assertIn('class="understand"><summary><span>Understand this record</span>', page)
        self.assertIn('<label class="simulator-choice" for="f-simulator">', page)
        self.assertIn('data-drive-views=', page)
        self.assertNotIn('<h4>Based on</h4>', page)
        self.assertNotIn('<h4>Mechanism</h4>', page)
        self.assertNotIn('<h4>Departs from it</h4>', page)

    def test_simulator_tabs_keep_the_catalogue_and_setup_layers_in_sync(self) -> None:
        page = build_site(ROOT)
        self.assertIn('<span>Shifter</span>', page)
        self.assertIn('<span>Authentic wheel</span>', page)
        self.assertIn('<span>Simulator cockpit</span>', page)
        self.assertIn("simulatorFilter.value = simulator", page)
        self.assertIn("simulatorFilter.value !== simulator", page)
        self.assertIn("var selectedDetailRow = null", page)
        self.assertIn("var keepSelected = row === selectedDetailRow", page)
        self.assertIn("Selected car remains open even though its current simulator guidance", page)
        self.assertIn('id="results-status" role="status" aria-live="polite" aria-atomic="true"', page)
        self.assertIn(
            'href="https://github.com/Milky28/as-driven/releases/latest">Get the SimHub plugin</a>',
            page,
        )
        self.assertIn("function announceResults(text)", page)
        self.assertIn("window.setTimeout(function ()", page)
        mobile = re.search(r"@media \(max-width: 720px\) \{(.*?)\n\}\n@media", page, re.S).group(1)
        self.assertIn("thead { display: none", mobile)
        self.assertIn("tr.car {", mobile)
        self.assertIn("tr.detail > td {", mobile)
        self.assertIn(".detail-inner > div { max-width: none", mobile)

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
        self.assertEqual(diablo["unexplained_open_fields"], ["running-shift clutch"])
        self.assertEqual(len(diablo["deviations"]), 1)
        self.assertEqual(diablo["deviations"][0]["field"], "running-shift clutch")
        self.assertIn(
            "The clutch's use on running shifts is not established",
            diablo["deviations"][0]["why"],
        )
        page = build_site(ROOT)
        diablo_detail = page.split('id="details-lamborghini-diablo-sv-r"', 1)[1].split(
            '</div></div></td></tr>', 1
        )[0]
        self.assertIn('<h4>Not established</h4>', diablo_detail)
        self.assertIn('>running-shift clutch</span>', diablo_detail)

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
            [
                ("ams2", "AMS2"),
                ("ac-evo", "Assetto Corsa EVO"),
                ("acc", "Assetto Corsa Competizione"),
                ("ac", "Assetto Corsa"),
            ],
        )
        self.assertIn('data-simulators=" ams2 ac-evo acc ac "', page)
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
        acc = next(
            simulator for simulator in audi["simulators"] if simulator["id"] == "acc"
        )
        self.assertEqual(acc["unknown_behavior"], ["automatic shift cut"])
        self.assertIn("Simulator behavior not established", page)
        self.assertIn("window.addEventListener('hashchange'", page)

    def test_the_simulator_filter_is_derived_from_released_records(self) -> None:
        payload = collect(ROOT)
        self.assertEqual(
            payload["simulators"],
            [
                {"id": "ams2", "label": "AMS2"},
                {"id": "ac", "label": "Assetto Corsa"},
                {"id": "acc", "label": "Assetto Corsa Competizione"},
                {"id": "ac-evo", "label": "Assetto Corsa EVO"},
                {"id": "gtr2", "label": "GTR 2"},
                {"id": "pmr", "label": "Project Motor Racing"},
                {"id": "raceroom", "label": "RaceRoom Racing Experience"},
                {"id": "rfactor2", "label": "rFactor 2"},
            ],
        )
        page = build_site(ROOT)
        self.assertIn('<option value="ac">AC</option>', page)
        self.assertIn('<option value="acc">ACC</option>', page)
        self.assertIn('<option value="ac-evo">AC EVO</option>', page)
        self.assertIn('<option value="gtr2">GTR2</option>', page)
        self.assertIn('<option value="raceroom">RaceRoom</option>', page)
        self.assertIn('<option value="rfactor2">rF2</option>', page)
        self.assertIn('<option value="pmr">PMR</option>', page)
        self.assertIn('<option value="ams2">AMS2</option>', page)

    def test_comparison_modes_separate_coverage_from_disagreement(self) -> None:
        payload = collect(ROOT)
        page = build_site(ROOT)
        multi = [car for car in payload["cars"] if car["is_multi_sim"]]
        disagreeing = [
            car for car in payload["cars"] if car["has_simulator_disagreements"]
        ]

        self.assertGreater(len(multi), len(disagreeing))
        self.assertEqual(
            re.findall(r'data-mode="([a-z]+)" aria-pressed="(?:true|false)"', page),
            ["all", "multi", "disagreements", "benchmark"],
        )
        self.assertEqual(page.count('data-multi-sim="true"'), len(multi))
        self.assertEqual(
            page.count('data-sim-disagreement="true"'), len(disagreeing)
        )
        self.assertEqual(page.count('class="disagrees-flag"'), len(disagreeing))
        self.assertIn("row.dataset.multiSim", page)
        self.assertIn("row.dataset.simDisagreement", page)
        self.assertIn("restoreFindingLink", page)
        self.assertIn("data-open-car", page)

        header = page.split("</header>", 1)[0]
        controls = page.split('<div class="controls driver-start" id="lookup-controls">', 1)[1].split(
            '</div>\n  <details class="coverage">', 1
        )[0]
        self.assertIn('aria-label="Comparison mode"', header)
        self.assertNotIn('aria-label="Comparison mode"', controls)
        controls_rule = re.search(r"\.controls \{(.*?)\}", page, re.S).group(1)
        self.assertIn("flex-wrap: wrap", controls_rule)

    def test_only_conflicting_established_simulator_values_disagree(self) -> None:
        cars = {car["id"]: car for car in collect(ROOT)["cars"]}

        # The ACC Ginetta cockpit directly conflicts with AMS2 on two visible
        # wheel properties, so it is a benchmark disagreement.
        ginetta = cars["ginetta-g55-gt4"]
        self.assertEqual(
            [item["field"] for item in ginetta["simulator_disagreements"]],
            ["Integrated wheel display", "Wheel shift lights"],
        )

        # Both Huracan views agree everywhere they establish a value. Their
        # shared unknown automatic cut is a gap, not a disagreement.
        huracan = cars["lamborghini-huracan-gt3-evo2"]
        self.assertTrue(huracan["is_multi_sim"])
        self.assertFalse(huracan["has_simulator_disagreements"])

        # AC alone establishes a cut for the RSS Audi implementation. Three
        # unknown views cannot vote against it; only the independently observed
        # standing-start conflict qualifies.
        audi = cars["audi-r8-lms-gt3-evo-ii"]
        self.assertEqual(
            [item["field"] for item in audi["simulator_disagreements"]],
            ["Pulling away"],
        )
        self.assertNotIn(
            "Automatic shift cut",
            [item["field"] for item in audi["simulator_disagreements"]],
        )

        page = build_site(ROOT)
        self.assertIn("Only conflicting established values appear here", page)
        self.assertIn("Compare reviewed simulators", page)
        self.assertIn('class="comparison-value comparison-real"><b>Real car</b>', page)

    def test_disagreement_audit_reaches_each_conflicting_field(self) -> None:
        payload = collect(ROOT)
        findings = [
            disagreement["audit"]
            for car in payload["cars"]
            for disagreement in car["simulator_disagreements"]
        ]
        self.assertTrue(findings)
        self.assertTrue(all(findings))
        page = build_site(ROOT)
        self.assertEqual(page.count('class="audit-result audit-'), len(findings))
        self.assertIn("Provisional finding", page)
        self.assertIn("Supported departure", page)
        self.assertIn("Authentic baseline open", page)
        self.assertIn("Research it before publishing a verdict", page)

    def test_benchmark_mode_presents_every_audit_finding_as_evidence(self) -> None:
        payload = collect(ROOT)
        findings = payload["benchmark_findings"]
        page = build_site(ROOT)

        self.assertTrue(findings)
        self.assertEqual(
            page.count('class="benchmark-card benchmark-card-'), len(findings)
        )
        for finding in findings:
            self.assertIn(f'id="finding-{finding["finding_id"]}"', page)

        supported = page.index('data-benchmark-status="supported-departure"')
        open_baseline = page.index(
            'data-benchmark-status="authentic-baseline-open"'
        )
        provisional = page.index('data-benchmark-status="provisional-departure"')
        self.assertLess(supported, open_baseline)
        self.assertLess(open_baseline, provisional)
        self.assertIn("Cross-simulator authenticity benchmark", page)
        self.assertIn("Authentic baseline", page)
        self.assertIn("Evidence verdict", page)
        self.assertIn("Real-car sources", page)

    def test_benchmark_content_obeys_its_hidden_state(self) -> None:
        page = build_site(ROOT)
        self.assertIn(
            '<section class="benchmark-view" id="benchmark-view" '
            'aria-label="Benchmark findings" hidden>',
            page,
        )
        self.assertIn(".benchmark-view[hidden] { display: none; }", page)

    def test_the_page_is_self_contained_and_encoding_independent(self) -> None:
        page = build_site(ROOT)
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn('<html lang="en">', page)
        self.assertIn('<meta charset="utf-8">', page)
        self.assertIn('<meta name="viewport"', page)
        self.assertIn(
            '<link rel="canonical" href="https://milky28.github.io/as-driven/">',
            page,
        )
        page.encode("ascii")
        # Google Fonts is the one external host the artifact may fetch while
        # rendering. Benchmark evidence links may point elsewhere, but remain
        # ordinary navigation rather than runtime dependencies.
        resource_hosts = set(
            re.findall(r'(?:@import url\(|src=["\'])https?://([^/"\')\s]+)', page)
        )
        self.assertLessEqual(
            resource_hosts,
            {"fonts.googleapis.com", "fonts.gstatic.com"},
            resource_hosts,
        )
        self.assertNotIn("<script src", page)

    def test_github_pages_builds_only_the_curated_public_catalog(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python -m as_driven_db validate", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn(
            "python -m as_driven_db build-site --output dist/site/index.html",
            workflow,
        )
        self.assertIn("uses: actions/configure-pages@v6", workflow)
        self.assertIn("uses: actions/upload-pages-artifact@v5", workflow)
        self.assertIn("path: dist/site", workflow)
        self.assertIn("uses: actions/deploy-pages@v5", workflow)
        self.assertNotIn("build/review-cases", workflow)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("https://milky28.github.io/as-driven/", readme)

    def test_the_headline_counts_match_the_records(self) -> None:
        payload = collect(ROOT)
        cars = payload["cars"]
        page = build_site(ROOT)
        stats = dict(
            (label, int(value))
            for value, label in re.findall(r"<b>([\d]+)</b><span>([^<]+)</span>", page)
        )
        self.assertEqual(stats["cars"], len(cars))
        self.assertEqual(stats["simulators"], len(payload["simulators"]))
        self.assertEqual(
            stats["views"],
            sum(len(car["simulators"]) for car in cars),
        )
        self.assertEqual(
            stats["clutch starts"],
            sum(1 for car in cars if car["start"] == "required"),
        )
        self.assertEqual(
            stats["manual blip"],
            sum(1 for car in cars if car["blip"] == "required"),
        )
        self.assertEqual(
            stats["open questions"],
            sum(1 for car in cars if car["open_fields"]),
        )
        self.assertEqual(
            stats["sims disagree"],
            sum(1 for car in cars if car["has_simulator_disagreements"]),
        )

    def test_the_header_and_open_row_keep_a_compact_visual_hierarchy(self) -> None:
        page = build_site(ROOT)
        stats_rule = re.search(r"(?m)^\.stats \{(.*?)\}", page, re.S).group(1)
        stat_rule = re.search(r"\.stat \{(.*?)\}", page, re.S).group(1)
        release_rule = re.search(r"(?m)^\.release-badge \{(.*?)\}", page, re.S).group(1)
        detail_rule = re.search(r"\.detail-inner \{(.*?)\}", page, re.S).group(1)
        selected_rule = re.search(
            r'tr\.car\[aria-expanded="true"\] \{(.*?)\}', page, re.S
        ).group(1)

        self.assertIn("flex-wrap: wrap", stats_rule)
        self.assertIn("align-items: baseline", stat_rule)
        self.assertIn("white-space: nowrap", stat_rule)
        self.assertIn("background: var(--surface)", release_rule)
        self.assertIn("border-left: 3px solid var(--accent)", release_rule)
        header = page.split("</header>", 1)[0]
        self.assertLess(
            header.index('id="lookup-controls"'), header.index('<details class="coverage">')
        )
        self.assertRegex(
            header,
            r'<div class="title-block">\s*<h1>As Driven</h1>\s*'
            r'<p class="release-badge"><strong>Dataset [^<]+</strong>'
            r'<span>Released [^<]+</span></p>',
        )
        self.assertNotIn('<p class="provenance">Dataset ', header)
        self.assertIn("border-top: 2px solid var(--accent)", detail_rule)
        self.assertIn("box-shadow", detail_rule)
        self.assertIn("inset 3px 0 0 var(--accent)", selected_rule)

    def test_physical_controls_precede_driving_technique_in_the_table(self) -> None:
        page = build_site(ROOT)
        headings = re.findall(r'<th scope="col">([^<]+)</th>', page)
        self.assertEqual(
            headings,
            ["Car", "Wheel", "Shifter", "Pulling away", "Upshift", "Downshift"],
        )

        first_row = page.split('<tr class="car"', 1)[1].split("</tr>", 1)[0]
        self.assertLess(first_row.index('class="car-name"'), first_row.index('class="rim"'))
        self.assertLess(first_row.index('class="rim"'), first_row.index('class="spec"'))
        self.assertLess(first_row.index('class="spec"'), first_row.index('class="state"'))

    def test_driving_guidance_wraps_inside_the_catalogue_table(self) -> None:
        """A long simulator qualification must not force desktop sideways."""
        page = build_site(ROOT)
        table_rule = re.search(r"table \{(.*?)\}", page, re.S).group(1)
        state_rule = re.search(r"\.state \{(.*?)\}", page, re.S).group(1)
        tone_rule = re.search(r"\.tone \{(.*?)\}", page, re.S).group(1)

        self.assertIn("table-layout: fixed", table_rule)
        self.assertNotIn("min-width", table_rule)
        self.assertIn("white-space: normal", state_rule)
        self.assertIn("max-width: 100%", tone_rule)
        self.assertIn("overflow-wrap: anywhere", tone_rule)

    def test_multi_sim_cars_get_a_compact_driving_setup_comparison(self) -> None:
        page = build_site(ROOT)
        bmw = page.split('id="details-bmw-m3-e46-gtr"', 1)[1].split(
            '</div></div></td></tr>', 1
        )[0]
        single_sim = page.split('id="details-alpine-a424"', 1)[1].split(
            '</div></div></td></tr>', 1
        )[0]

        self.assertIn("Compare driving setup", bmw)
        self.assertIn("Real car", bmw)
        self.assertIn("Project Motor Racing", bmw)
        self.assertIn("Matches real car", bmw)
        self.assertIn("cut not established", bmw)
        self.assertNotIn("Compare driving setup", single_sim)
        self.assertIn("drive-compare-grid", page)

    def test_the_light_palette_separates_ground_surface_and_rules(self) -> None:
        page = build_site(ROOT)
        root = re.search(r":root \{(.*?)\}", page, re.S).group(1)
        tokens = dict(re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", root))
        self.assertNotEqual(tokens["--bg"], tokens["--surface"])
        self.assertNotEqual(tokens["--surface"], tokens["--surface-2"])
        self.assertNotEqual(tokens["--row-alt"], tokens["--surface"])
        self.assertNotEqual(tokens["--line"], tokens["--row-alt"])
        def luminance(color):
            channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                      for v in channels]
            return sum(v * weight for v, weight in zip(linear, [.2126, .7152, .0722]))
        for foreground, background in [('--faint', '--row-alt'), ('--ink', '--row-alt'),
                                       ('--optional', '--row-alt'), ('--driver', '--driver-bg'),
                                       ('--car', '--car-bg'), ('--optional', '--optional-bg')]:
            values = sorted([luminance(tokens[foreground]), luminance(tokens[background])])
            self.assertGreaterEqual((values[1] + .05) / (values[0] + .05), 4.5)

    def test_the_four_states_are_told_apart_by_more_than_hue(self) -> None:
        """Two warm fills side by side read as the same answer.

        Optional uses a saturated violet fill so it reads independently of the
        surrounding neutral surfaces. The dotted border reserves a separate
        shape for an evidence gap.
        """
        page = build_site(ROOT)
        rules = {
            tone: re.search(r"\.tone-%s \{(.*?)\}" % tone, page, re.S).group(1)
            for tone in ("you", "car", "optional", "unknown")
        }
        colors = {tone: re.search(r"color: ([^;]+);", body).group(1) for tone, body in rules.items()}
        self.assertEqual(len(set(colors.values())), 4, colors)

        filled = {tone for tone, body in rules.items() if "background: var(" in body}
        self.assertEqual(filled, {"you", "car", "optional"}, filled)
        self.assertIn("var(--optional-bg)", rules["optional"])
        # An evidence gap is hollow and dotted, unlike every settled state.
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
        self.assertIn('<html lang="en">', page)
        self.assertNotIn('<html lang="en" data-theme=', page)

    def test_the_table_does_not_rely_on_inheriting_colour_or_font(self) -> None:
        """The table remains explicit when embedded outside the public shell.

        The generated public page now owns its standards-mode document shell,
        while the catalog markup may still be embedded by another client. The
        table therefore continues to state both colour and font explicitly.
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
