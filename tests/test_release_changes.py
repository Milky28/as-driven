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
        "provenance": {"claims": [{
            "paths": ["/authentic_controls/transmission", "/authentic_controls/steering"],
            "source_refs": ["test.source"],
        }]},
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

    def test_evidence_names_only_sources_whose_claim_covers_the_changed_field(
        self,
    ) -> None:
        """A release note must not credit a source for a field it never mentions.

        This listed every source registered anywhere on a changed record, which
        was called conservative because it invented no narrower connection.
        Printed under a heading reading "Evidence" it did the reverse: the 0.21.4
        note put seven links beneath nine derived standing-start values, none of
        which mentions the standing start. Provenance is path-specific, so the
        narrower answer was available all along.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seed(root / "previous", "0.5.45", actuation="sequential-stick", blip="not-required")
            _seed(root / "current", "0.5.46", actuation="sequential-paddles", blip="yes")

            # A source cited only for the wheel must not appear under a shifter
            # change, and a drive is reported apart from a real-car source.
            record_path = root / "current" / "data" / "v1" / "cars" / "test.json"
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["provenance"]["claims"] = [
                {
                    "paths": ["/authentic_controls/transmission/shift_actuation"],
                    "source_refs": ["test.source"],
                },
                {
                    "paths": ["/authentic_controls/steering/wheel_rim"],
                    "source_refs": ["wheel.only"],
                },
                {
                    "paths": ["/authentic_controls/transmission/downshift"],
                    "source_refs": ["ams2.local-live-test-controls.1.0"],
                },
            ]
            record_path.write_text(json.dumps(record), encoding="utf-8")
            sources_path = root / "current" / "data" / "v1" / "sources.json"
            sources = json.loads(sources_path.read_text(encoding="utf-8"))
            sources["sources"].extend([
                {"source_id": "wheel.only", "title": "Wheel", "url": "https://example.test/wheel"},
                {"source_id": "ams2.local-live-test-controls.1.0", "title": "Drive",
                 "url": "https://example.test/drive"},
            ])
            sources_path.write_text(json.dumps(sources), encoding="utf-8")

            report = release_control_changes(
                root / "previous", root / "current" / "data" / "v1"
            )
            shifter = next(c for c in report["changes"] if c["control"] == "shift actuation")
            blip = next(c for c in report["changes"] if c["category"] == "blip")

            self.assertEqual(["test.source"], [i["source_id"] for i in shifter["evidence"]])
            self.assertEqual([], shifter["observed_in"])

            # The blip's only covering source is a drive, so it is not evidence.
            self.assertEqual([], blip["evidence"])
            self.assertEqual(
                ["ams2.local-live-test-controls.1.0"],
                [i["source_id"] for i in blip["observed_in"]],
            )

            rendered = render_release_control_changes(report)
            self.assertNotIn("https://example.test/wheel", rendered)
            self.assertIn("No real-car source is cited for this field", rendered)


if __name__ == "__main__":
    unittest.main()
