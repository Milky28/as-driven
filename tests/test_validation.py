import json
from pathlib import Path
import shutil
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
            temp_root = self._copy_repository_data(Path(directory))

            target = temp_root / "data" / "v1" / "cars" / "ams2.f301.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["simulators"][0]["source_refs"] = ["missing.source"]
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(any("unknown source_id" in error for error in errors))

    def test_schema_rejects_invalid_shift_actuation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            target = temp_root / "data" / "v1" / "cars" / "ams2.f301.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["authentic_controls"]["transmission"]["shift_actuation"] = "magic"
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(
                any("shift_actuation: invalid value 'magic'" in error for error in errors)
            )

    def test_schema_rejects_unexpected_record_property(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            target = temp_root / "data" / "v1" / "cars" / "ams2.f301.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["unreviewed_guess"] = True
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(any("unreviewed_guess: unexpected property" in error for error in errors))

    def test_schema_rejects_invalid_source_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory))
            target = temp_root / "data" / "v1" / "sources.json"
            sources = json.loads(target.read_text(encoding="utf-8"))
            sources["sources"][0]["source_type"] = "rumor"
            target.write_text(json.dumps(sources), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(any("source_type: invalid value 'rumor'" in error for error in errors))

    def test_approval_must_match_curated_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory), include_curation=True)
            target = temp_root / "curation" / "ams2-approved-audi-r8-lmp1.json"
            approval = json.loads(target.read_text(encoding="utf-8"))
            approval["approved_controls"]["forward_gears"] = 7
            target.write_text(json.dumps(approval), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertTrue(
                any("forward_gears: approved 7 does not match curated value 6" in error for error in errors)
            )

    def test_simulator_approval_checks_simulator_cut_not_authentic_cut(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = self._copy_repository_data(Path(directory), include_curation=True)
            target = temp_root / "data" / "v1" / "cars" / "ams2.audi-r8-lmp1.json"
            record = json.loads(target.read_text(encoding="utf-8"))
            record["authentic_controls"]["transmission"]["upshift"]["automatic_cut"] = "no"
            target.write_text(json.dumps(record), encoding="utf-8")

            errors = validate_repository(temp_root)
            self.assertFalse(
                any("approved_controls.automatic_cut" in error for error in errors),
                errors,
            )

    @staticmethod
    def _copy_repository_data(directory: Path, include_curation: bool = False) -> Path:
        shutil.copytree(ROOT / "schema", directory / "schema")
        shutil.copytree(ROOT / "data", directory / "data")
        if include_curation:
            shutil.copytree(ROOT / "curation", directory / "curation")
        return directory


if __name__ == "__main__":
    unittest.main()
