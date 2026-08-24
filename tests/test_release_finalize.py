from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from as_driven_db.release_finalize import (
    finalize_release,
    release_stats,
    update_release_references,
)


def _record(record_id: str, simulators: list[str], classification: str | None) -> dict:
    record = {
        "record_id": record_id,
        "authentic_controls": {
            "transmission": {
                "forward_gears": 6 if record_id == "one" else 5,
                "shift_actuation": "sequential-paddles",
            }
        },
        "simulators": [{"simulator": simulator} for simulator in simulators],
    }
    if classification:
        record["archetype"] = {"classification": classification}
    return record


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_release(root: Path) -> None:
    _write_json(
        root / "data" / "v1" / "index.json",
        {
            "dataset_version": "1.2.3",
            "released_at": "2026-08-24",
            "records": ["cars/one.json", "cars/two.json"],
        },
    )
    _write_json(
        root / "data" / "v1" / "cars" / "one.json",
        _record("one", ["ams2", "ac"], "matches"),
    )
    _write_json(
        root / "data" / "v1" / "cars" / "two.json",
        _record("two", ["acc"], None),
    )
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(
        "Dataset 0.9.9 contains 1 reviewed car record.\n"
        "The database currently contains 1 curated car records.\n"
        "Of those, 1 carry AMS2 entries; one is AC EVO-only and two are original-AC-only.\n",
        encoding="utf-8",
    )
    for name in ("AGENTS.md", "CLAUDE.md"):
        (root / name).write_text(
            "- Dataset: 0.9.9 with 1 curated records.\n", encoding="utf-8"
        )
    (root / "EARLY_ACCESS.md").write_text(
        "- As Driven dataset 0.9.9 and schema v1.\n"
        "The database currently contains 1 curated car records. Of those, 1 carry\n"
        "AMS2 entries; one is currently AC EVO-only and two original-AC records are AC-only.\n",
        encoding="utf-8",
    )
    (root / "docs" / "ams2-coverage-plan.md").write_text(
        "Dataset 0.9.9 contains 1 curated records, 1 of which carry AMS2 entries.\n",
        encoding="utf-8",
    )
    (root / "docs" / "archetypes.md").write_text(
        "**Status: complete. All 1 records are classified** - 1 compatible matches, 0\n"
        "deviations, 0 undetermined and 0 with no archetype.\n"
        "Across the 1 curated records there are **1 distinct transmission blocks**.\n"
        "Only 1 records are one of a kind.\n",
        encoding="utf-8",
    )
    (root / "docs" / "simulator-disagreement-audit.md").write_text(
        "Dataset 0.9.9 contains 1 field-level findings across 1 cars:\n",
        encoding="utf-8",
    )


class ReleaseFinalizeTests(unittest.TestCase):
    def test_release_stats_are_derived_from_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seed_release(root)
            stats = release_stats(root)

            self.assertEqual("1.2.3", stats["dataset_version"])
            self.assertEqual(2, stats["records"])
            self.assertEqual(3, stats["simulator_views"])
            self.assertEqual({"ac": 1, "acc": 1, "ams2": 1}, stats["simulator_records"])
            self.assertEqual({"ac": 1}, stats["ams2_overlaps"])
            self.assertEqual(1, stats["classified_records"])
            self.assertEqual(2, stats["transmission_signatures"])
            self.assertEqual(2, stats["unique_transmission_signatures"])

    def test_release_references_use_computed_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seed_release(root)
            stats = release_stats(root)
            changed = update_release_references(
                root,
                stats,
                {"summary": {"findings": 4, "cars_with_disagreements": 3}},
            )

            self.assertIn("README.md", changed)
            self.assertIn("Dataset 1.2.3 contains 2 reviewed", (root / "README.md").read_text())
            self.assertIn(
                "As Driven dataset 1.2.3 and schema v1",
                (root / "EARLY_ACCESS.md").read_text(),
            )
            archetypes = (root / "docs" / "archetypes.md").read_text()
            self.assertIn("1 of 2 records are classified", archetypes)
            self.assertIn("1 awaiting classification", archetypes)
            disagreement = (root / "docs" / "simulator-disagreement-audit.md").read_text()
            self.assertIn("Dataset 1.2.3 contains 4 field-level findings across 3 cars", disagreement)
            self.assertEqual(
                [],
                update_release_references(
                    root,
                    stats,
                    {"summary": {"findings": 4, "cars_with_disagreements": 3}},
                ),
            )

    def test_finalize_writes_outputs_and_runs_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seed_release(root)
            validated: list[Path] = []

            result = finalize_release(
                root,
                coverage_builder=lambda *_args: {"stats": {}, "entries": []},
                disagreement_builder=lambda _root: {
                    "dataset_version": "1.2.3",
                    "summary": {"findings": 0, "cars_with_disagreements": 0},
                },
                site_builder=lambda _root: "<!doctype html><title>test</title>",
                validator=lambda value: validated.append(value) or [],
            )

            self.assertEqual([root.resolve()], validated)
            self.assertEqual("passed", result["validation"])
            self.assertEqual("not-run", result["tests"])
            self.assertTrue((root / "research" / "ams2-coverage-manifest.json").exists())
            self.assertTrue((root / "research" / "simulator-disagreement-audit.json").exists())
            self.assertTrue((root / "dist" / "site" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
