import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from as_driven_db.conventions import (  # noqa: E402
    guidance_for,
    load_conventions,
    report,
)
from as_driven_db.schema_validation import validate_instance  # noqa: E402


def _read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


class ConventionRegistryTests(unittest.TestCase):
    def test_the_registry_matches_its_schema(self) -> None:
        self.assertEqual(
            [],
            validate_instance(
                _read(ROOT / "data" / "v1" / "conventions.json"),
                _read(ROOT / "schema" / "v1" / "convention-rule.schema.json"),
                "data/v1/conventions.json",
            ),
        )

    def test_every_rule_tells_the_driver_the_real_value_is_unknown(self) -> None:
        """The sentence has to distinguish itself from an evidenced answer.

        A driver reading the card must be able to tell convention from a finding
        about their car, and the wording is the only thing that does it.
        """
        for rule in load_conventions(ROOT):
            with self.subTest(rule=rule["convention_id"]):
                self.assertRegex(
                    rule["guidance"], r"not established", rule["convention_id"]
                )

    def test_no_rule_contradicts_a_curated_record(self) -> None:
        """A rule describes a class; a record can still know better.

        lamborghini-miura-sv is the standing case: it holds not-required on a
        synchromesh gearbox because its own reviewed research says clutchless
        running shifts are ordinary there. A rule that disagreed with an
        established value would be asserting something false about a real car,
        so a conflict is a defect in the rule rather than an exception to it.
        """
        conflicts = report(ROOT)["conflicts"]
        self.assertEqual([], conflicts)


class ConventionResolverTests(unittest.TestCase):
    @staticmethod
    def _record(gearbox, upshift_clutch):
        return {
            "record_id": "example",
            "identity": {"year": {"from": 1965, "to": 1965}},
            "authentic_controls": {
                "transmission": {
                    "shift_actuation": "h-pattern",
                    "gearbox_type": gearbox,
                    "upshift": {"clutch": upshift_clutch},
                    "downshift": {"clutch": "unknown"},
                }
            },
        }

    def test_guidance_is_offered_only_where_the_record_is_silent(self) -> None:
        rules = load_conventions(ROOT)
        open_record = self._record("unknown", "unknown")
        result = guidance_for(open_record, rules)
        self.assertTrue(result["applies"])
        self.assertIn(
            "/authentic_controls/transmission/upshift/clutch",
            result["applies"][0]["paths"],
        )

    def test_an_established_value_is_never_described_by_a_rule(self) -> None:
        rules = load_conventions(ROOT)
        answered = self._record("unknown", "required")
        paths = [p for item in guidance_for(answered, rules)["applies"] for p in item["paths"]]
        self.assertNotIn("/authentic_controls/transmission/upshift/clutch", paths)

    def test_a_rule_disagreeing_with_the_record_is_reported_not_hidden(self) -> None:
        rules = load_conventions(ROOT)
        miura_like = self._record("unknown", "not-required")
        result = guidance_for(miura_like, rules)
        self.assertTrue(result["conflicts"])
        self.assertEqual(
            "not-required", result["conflicts"][0]["fields"][0]["record"]
        )
        paths = [p for item in result["applies"] for p in item["paths"]]
        self.assertNotIn("/authentic_controls/transmission/upshift/clutch", paths)

    def test_a_rule_does_not_reach_a_car_whose_mechanism_differs(self) -> None:
        rules = load_conventions(ROOT)
        established = self._record("synchromesh", "unknown")
        self.assertEqual([], guidance_for(established, rules)["applies"])


if __name__ == "__main__":
    unittest.main()
