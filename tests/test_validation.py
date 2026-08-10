import json
from pathlib import Path
import tempfile
import unittest

from authentic_controls_db.validate import _resolve_pointer, validate_repository


ROOT = Path(__file__).parents[1]


class ValidationTests(unittest.TestCase):
    def test_repository_is_valid(self) -> None:
        self.assertEqual(validate_repository(ROOT), [])

    def test_json_pointer_resolution(self) -> None:
        document = {"simulators": [{"behavior": {"shift_cut": "yes"}}]}
        self.assertTrue(_resolve_pointer(document, "/simulators/0/behavior/shift_cut"))
        self.assertFalse(_resolve_pointer(document, "/simulators/1/behavior/shift_cut"))

    def test_unknown_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            (temp_root / "schema" / "v1").mkdir(parents=True)
            (temp_root / "data" / "v1" / "cars").mkdir(parents=True)

            for schema in (ROOT / "schema" / "v1").glob("*.json"):
                (temp_root / "schema" / "v1" / schema.name).write_text(
                    schema.read_text(encoding="utf-8"), encoding="utf-8"
                )
            for name in ("index.json", "sources.json"):
                (temp_root / "data" / "v1" / name).write_text(
                    (ROOT / "data" / "v1" / name).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            for record_path in (ROOT / "data" / "v1" / "cars").glob("*.json"):
                target = temp_root / "data" / "v1" / "cars" / record_path.name
                target.write_text(record_path.read_text(encoding="utf-8"), encoding="utf-8")

            target = temp_root / "data" / "v1" / "cars" / "ams2.f301.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["simulators"][0]["source_refs"] = ["missing.source"]
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(any("unknown source_id" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
