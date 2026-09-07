import json
from pathlib import Path
import tempfile
import unittest

from as_driven_db.format_records import format_records


class FormatRecordsTests(unittest.TestCase):
    def test_formatting_preserves_values_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cars = root / "data/v1/cars"
            cars.mkdir(parents=True)
            path = cars / "example.json"
            payload = {"notes": "Citroën", "unknown": None, "flags": [False, 6]}
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual([path], format_records(root))
            self.assertEqual(payload, json.loads(path.read_text(encoding="utf-8")))
            self.assertEqual([], format_records(root))

    def test_invalid_json_does_not_partially_format_the_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cars = root / "data/v1/cars"
            cars.mkdir(parents=True)
            first = cars / "a.json"
            first.write_text('{"value":null}', encoding="utf-8")
            (cars / "b.json").write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                format_records(root)
            self.assertEqual('{"value":null}', first.read_text(encoding="utf-8"))
