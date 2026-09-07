from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from as_driven_db.release_finalize import (
    ReleaseFinalizeError,
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
        "# As Driven\n\n"
        "<!-- release-facts:start -->\n"
        "Dataset 0.9.9 contains 1 reviewed car records.\n"
        "<!-- release-facts:end -->\n\n"
        "Matching is exact.\n",
        encoding="utf-8",
    )
    for name in ("AGENTS.md", "CLAUDE.md"):
        (root / name).write_text(
            "- Dataset: 0.9.9 with 1 curated records.\n", encoding="utf-8"
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
            )

            self.assertIn("README.md", changed)
            readme = (root / "README.md").read_text()
            self.assertIn("Dataset 1.2.3 contains 2 reviewed", readme)
            # The block is regenerated whole, so the table arrives with it and
            # the prose on either side is left alone.
            self.assertIn("| Automobilista 2 | 1 | not applicable |", readme)
            self.assertIn("| Assetto Corsa Competizione | 1 | 0 |", readme)
            self.assertIn("Matching is exact.", readme)
            self.assertEqual(["README.md"], changed)
            # Release preparation must not rewrite policy or research prose.
            self.assertEqual(
                "- Dataset: 0.9.9 with 1 curated records.\n",
                (root / "AGENTS.md").read_text(),
            )
            self.assertEqual(
                [],
                update_release_references(
                    root,
                    stats,
                ),
            )

    def test_a_missing_readme_block_is_refused_rather_than_ignored(self) -> None:
        # The release facts used to be patched into prose by eight regexes, and
        # re.sub leaves the text alone when a pattern stops matching. Rewording
        # the README therefore published stale counts silently. The generated
        # block has to fail loudly instead.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seed_release(root)
            (root / "README.md").write_text(
                "# As Driven\n\nDataset 0.9.9 contains 1 reviewed car records.\n",
                encoding="utf-8",
            )
            with self.assertRaises(ReleaseFinalizeError) as raised:
                update_release_references(
                    root,
                    release_stats(root),
                )
            self.assertIn("release-facts", str(raised.exception))

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

    def test_a_release_retains_coverage_when_local_inputs_are_incomplete(self) -> None:
        """A release does not require local diagnostics to retain coverage.

        The manifest is checked in, but it is generated from a developer audit
        under the ignored `build/` and from the plugin's live diagnostics log
        under `%LOCALAPPDATA%`, neither of which travels with the repository. A
        release that touched nothing about coverage once rewrote the manifest
        with 145 of 370 identities missing, because the live log was not read on
        that machine, and the prose kept claiming the larger number. The
        inventory only grows, so a smaller manifest is a missing input rather
        than a vanished car.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seed_release(root)
            manifest = root / "research" / "ams2-coverage-manifest.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(
                json.dumps(
                    {
                        "entries": [{"telemetry_name": f"car {index}"} for index in range(370)],
                        "identity_sources": {"live_identities_seen": 206},
                        "stats": {},
                    }
                ),
                encoding="utf-8",
            )

            finalize_release(
                root,
                coverage_builder=lambda *_args: {
                    "stats": {},
                    "identity_sources": {"live_identities_seen": 0},
                    "entries": [
                        {"telemetry_name": f"car {index}"} for index in range(225)
                    ],
                },
                disagreement_builder=lambda _root: {
                    "dataset_version": "1.2.3",
                    "summary": {"findings": 0, "cars_with_disagreements": 0},
                },
                site_builder=lambda _root: "<!doctype html><title>test</title>",
                validator=lambda _root: [],
            )

            retained = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(370, len(retained["entries"]))
            self.assertEqual("1.2.3", retained["dataset_version"])

    def test_a_growing_coverage_manifest_is_written(self) -> None:
        """The guard stops a loss, not an ordinary refresh."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _seed_release(root)
            manifest = root / "research" / "ams2-coverage-manifest.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(
                json.dumps(
                    {
                        "entries": [{"telemetry_name": "car 0"}],
                        "identity_sources": {"live_identities_seen": 1},
                        "stats": {},
                    }
                ),
                encoding="utf-8",
            )

            finalize_release(
                root,
                coverage_builder=lambda *_args: {
                    "stats": {},
                    "identity_sources": {"live_identities_seen": 2},
                    "entries": [{"telemetry_name": "car 0"}, {"telemetry_name": "car 1"}],
                },
                disagreement_builder=lambda _root: {
                    "dataset_version": "1.2.3",
                    "summary": {"findings": 0, "cars_with_disagreements": 0},
                },
                site_builder=lambda _root: "<!doctype html><title>test</title>",
                validator=lambda _root: [],
            )

            self.assertEqual(
                2, len(json.loads(manifest.read_text(encoding="utf-8"))["entries"])
            )


if __name__ == "__main__":
    unittest.main()
