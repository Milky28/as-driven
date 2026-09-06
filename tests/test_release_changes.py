from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from as_driven_db.release_changes import release_control_changes, render_release_control_changes


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed(root: Path, version: str, *, actuation: str, blip: str) -> None:
    data = root / "data" / "v1"
    _write(data / "index.json", {"dataset_version": version, "released_at": "2026-09-05", "records": ["cars/test.json"]})
    _write(data / "sources.json", {"sources": [{"source_id": "test.source", "title": "Test evidence", "url": "https://example.test/evidence"}]})
    _write(data / "cars" / "test.json", {
        "record_id": "test", "identity": {"display_name": "Test car"},
        "authentic_controls": {"steering": {"wheel_rim": {"shape": "round"}}, "transmission": {
            "forward_gears": 6, "shift_actuation": actuation, "shift_pattern": "sequential",
            "standing_start_clutch": "required", "upshift": {"clutch": "not-required", "manual_blip": "not-applicable", "automatic_blip": "not-applicable"},
            "downshift": {"clutch": "not-required", "manual_blip": "not-required", "automatic_blip": blip},
        }},
        "simulators": [{"source_refs": ["test.source"]}],
        "provenance": {"claims": [{"source_refs": ["test.source"]}]},
    })


class ReleaseControlChangesTests(unittest.TestCase):
    def test_reports_material_guidance_changes_with_current_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seed(root / "previous", "0.5.45", actuation="sequential-stick", blip="not-required")
            _seed(root / "current", "0.5.46", actuation="sequential-paddles", blip="yes")
            report = release_control_changes(
                root / "previous",
                root / "current" / "data" / "v1",
                priority_record_ids={"test"},
            )

            self.assertEqual(2, report["summary"]["changed_controls"])
            self.assertEqual({"shifter": 1, "blip": 1, "wheel": 0, "clutch": 0}, report["summary"]["by_category"])
            shifter = next(item for item in report["changes"] if item["control"] == "shift actuation")
            self.assertEqual("sequential-paddles", shifter["after"])
            self.assertTrue(shifter["priority_recent"])
            self.assertEqual("https://example.test/evidence", shifter["evidence"][0]["url"])
            self.assertIn("(recent car)", render_release_control_changes(report))
            self.assertIn("[test.source](https://example.test/evidence)", render_release_control_changes(report))


if __name__ == "__main__":
    unittest.main()
