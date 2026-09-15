import copy
import unittest
from pathlib import Path
from as_driven_db.intake_observation import _curated_matches
from as_driven_db.validate import _collect_identities

ROOT = Path(__file__).parents[1]

class ClassMatchingTests(unittest.TestCase):
    def test_camaro_intake_uses_exact_class(self):
        for car_class, record in [("Historic USV8", "chevrolet-camaro-z28-1969"),
                                  ("USV8", "chevrolet-camaro-usv8-2022"),
                                  (None, None), ("usv8", None)]:
            matches = _curated_matches(ROOT, {"simulator": "pmr", "identity": {
                "telemetry_name": "Camaro", "internal_id": "Camaro", "telemetry_class": car_class}})
            self.assertEqual({m["record_id"] for m in matches}, {record} if record else set())

    def test_collisions_require_nonoverlapping_classes(self):
        first = {"record_id": "old", "simulators": [{"simulator": "pmr", "identities": [
            {"kind": "telemetry-name", "value": "Camaro"},
            {"kind": "class-id", "value": "Historic USV8"}]}]}
        for car_class, collision in [("USV8", False), ("Historic USV8", True), (None, True)]:
            second = copy.deepcopy(first)
            second["record_id"] = "new"
            identities = second["simulators"][0]["identities"]
            if car_class is None:
                identities.pop()
            else:
                identities[1]["value"] = car_class
            claimed, errors = {}, []
            _collect_identities(first, "old", claimed, errors)
            _collect_identities(second, "new", claimed, errors)
            self.assertEqual(bool(errors), collision, errors)
