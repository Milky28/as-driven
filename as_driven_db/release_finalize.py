from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable

from research.build_ams2_coverage_manifest import (
    DEFAULT_CARS,
    DEFAULT_LIVE_LOG,
    build as build_ams2_coverage,
    write_csv as write_ams2_coverage_csv,
)
from research.build_simulator_disagreement_audit import build_audit

from .site import build_site
from .validate import validate_repository


class ReleaseFinalizeError(ValueError):
    """The promoted dataset is not ready to be closed as a release."""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def release_stats(root: Path) -> dict[str, Any]:
    data = root / "data" / "v1"
    index = _read_json(data / "index.json")
    records = [_read_json(data / relative) for relative in index["records"]]
    simulator_records: Counter[str] = Counter()
    ams2_overlaps: Counter[str] = Counter()
    classifications: Counter[str] = Counter()
    transmission_signatures: Counter[str] = Counter()

    for record in records:
        simulators = {entry["simulator"] for entry in record["simulators"]}
        simulator_records.update(simulators)
        if "ams2" in simulators:
            ams2_overlaps.update(simulators - {"ams2"})
        archetype = record.get("archetype")
        classifications[
            archetype.get("classification", "awaiting") if archetype else "awaiting"
        ] += 1
        transmission_signatures[
            json.dumps(
                record["authentic_controls"]["transmission"],
                sort_keys=True,
                separators=(",", ":"),
            )
        ] += 1

    return {
        "dataset_version": index["dataset_version"],
        "released_at": index["released_at"],
        "records": len(records),
        "simulator_views": sum(len(record["simulators"]) for record in records),
        "simulator_records": dict(sorted(simulator_records.items())),
        "ams2_overlaps": dict(sorted(ams2_overlaps.items())),
        "exclusive_records": {
            simulator: count - ams2_overlaps.get(simulator, 0)
            for simulator, count in sorted(simulator_records.items())
            if simulator != "ams2"
        },
        "archetype_classifications": dict(sorted(classifications.items())),
        "classified_records": len(records) - classifications["awaiting"],
        "transmission_signatures": len(transmission_signatures),
        "unique_transmission_signatures": sum(
            1 for count in transmission_signatures.values() if count == 1
        ),
    }


# Display names for the simulators a release can cover. The README table below
# is generated, so a simulator missing here would appear under its bare id.
SIMULATOR_NAMES = {
    "ams2": "Automobilista 2",
    "ac": "Assetto Corsa",
    "acc": "Assetto Corsa Competizione",
    "ac-evo": "Assetto Corsa EVO",
    "ac-rally": "Assetto Corsa Rally",
    "iracing": "iRacing",
    "raceroom": "RaceRoom Racing Experience",
    "rfactor2": "rFactor 2",
    "pmr": "Project Motor Racing",
    "gtr2": "GTR 2",
}


def _release_facts(stats: dict[str, Any]) -> str:
    """The generated README block stating what the current dataset covers.

    Written whole rather than patched sentence by sentence. The prose version
    needed eight overlapping regexes over one paragraph, and `re.sub` leaves the
    text alone when a pattern stops matching, so an edit to the wording failed
    silently and left a stale number in the file most readers see first.
    """
    version = stats["dataset_version"]
    records = stats["records"]
    simulators = stats["simulator_records"]
    overlaps = stats["ams2_overlaps"]
    lines = [
        f"Dataset {version} contains {records} reviewed car records.",
        "",
        "| Simulator | Records | Also curated for AMS2 |",
        "| --- | --- | --- |",
    ]
    for simulator, count in sorted(
        simulators.items(), key=lambda item: (-item[1], item[0])
    ):
        shared = (
            "not applicable"
            if simulator == "ams2"
            else str(overlaps.get(simulator, 0))
        )
        lines.append(
            f"| {SIMULATOR_NAMES.get(simulator, simulator)} | {count} | {shared} |"
        )
    return "\n".join(lines)


def _replace_block(text: str, name: str, body: str) -> str:
    """Replace one delimited generated block, refusing to no-op silently."""
    start = f"<!-- {name}:start -->"
    end = f"<!-- {name}:end -->"
    pattern = re.compile(re.escape(start) + r"[\s\S]*?" + re.escape(end))
    if not pattern.search(text):
        raise ReleaseFinalizeError(
            f"the generated {name!r} block is missing; release facts cannot be refreshed"
        )
    return pattern.sub(lambda _match: f"{start}\n{body}\n{end}", text)


def _replace(text: str, pattern: str, replacement: str) -> str:
    return re.sub(pattern, lambda _match: replacement, text, flags=re.MULTILINE)


def _verb(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def update_release_references(
    root: Path,
    stats: dict[str, Any],
    disagreement: dict[str, Any],
) -> list[str]:
    version = stats["dataset_version"]
    records = stats["records"]
    simulators = stats["simulator_records"]
    overlaps = stats["ams2_overlaps"]
    exclusive = stats["exclusive_records"]
    classes = stats["archetype_classifications"]

    paths = [
        root / "README.md",
        root / "AGENTS.md",
        root / "CLAUDE.md",
        root / "docs" / "ams2-coverage-plan.md",
        root / "docs" / "archetypes.md",
        root / "docs" / "simulator-disagreement-audit.md",
    ]
    changed: list[str] = []
    for path in paths:
        if not path.exists():
            raise ReleaseFinalizeError(f"required release reference is missing: {path}")
        original = path.read_text(encoding="utf-8")
        text = original

        if path.name in {"AGENTS.md", "CLAUDE.md"}:
            text = _replace(
                text,
                r"- Dataset: \d+\.\d+\.\d+ with \d+ curated records\.",
                f"- Dataset: {version} with {records} curated records.",
            )
        if path.name == "README.md":
            text = _replace_block(text, "release-facts", _release_facts(stats))

        if path.name == "ams2-coverage-plan.md":
            text = re.sub(
                r"Dataset \d+\.\d+\.\d+ contains \d+ curated records, \d+ of which carry AMS2 entries\.",
                f"Dataset {version} contains {records} curated records, "
                f"{simulators.get('ams2', 0)} of which carry AMS2 entries.",
                text,
            )

        if path.name == "archetypes.md":
            awaiting = classes.get("awaiting", 0)
            status = (
                f"All {records} records are classified"
                if awaiting == 0
                else f"{stats['classified_records']} of {records} records are classified"
            )
            text = re.sub(
                r"\*\*Status: [^*]+\*\* - [^.]+\.",
                f"**Status: {status}** - {classes.get('matches', 0)} matches, "
                f"{classes.get('deviates', 0)} deviations, "
                f"{classes.get('undetermined', 0)} undetermined, "
                f"{classes.get('no-archetype', 0)} with no archetype, and "
                f"{awaiting} awaiting classification.",
                text,
            )
            text = _replace(
                text,
                r"Across the \d+ curated records there are \*\*\d+ distinct transmission blocks\*\*\.",
                f"Across the {records} curated records there are "
                f"**{stats['transmission_signatures']} distinct transmission blocks**.",
            )
            text = _replace(
                text,
                r"Only \d+ records are one of a kind\.",
                f"Only {stats['unique_transmission_signatures']} records are one of a kind.",
            )

        if path.name == "simulator-disagreement-audit.md":
            summary = disagreement["summary"]
            text = re.sub(
                r"Dataset \d+\.\d+\.\d+ contains \d+ field-level findings across \d+ cars:",
                f"Dataset {version} contains {summary['findings']} field-level findings "
                f"across {summary['cars_with_disagreements']} cars:",
                text,
            )

        if text != original:
            path.write_text(text, encoding="utf-8")
            changed.append(str(path.relative_to(root)))

    return changed


def _run_tests(root: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stdout + "\n" + result.stderr).strip()
        raise ReleaseFinalizeError(f"test suite failed:\n{detail}")


def finalize_release(
    root: Path,
    *,
    run_tests: bool = False,
    coverage_builder: Callable[..., dict[str, Any]] = build_ams2_coverage,
    disagreement_builder: Callable[[Path], dict[str, Any]] = build_audit,
    site_builder: Callable[[Path], str] = build_site,
    validator: Callable[[Path], list[str]] = validate_repository,
) -> dict[str, Any]:
    root = root.resolve()
    stats = release_stats(root)

    coverage = coverage_builder(
        root / "build" / "ams2-simhub-identity-audit.json",
        DEFAULT_CARS,
        DEFAULT_LIVE_LOG,
        root,
    )
    coverage_json = root / "research" / "ams2-coverage-manifest.json"
    coverage_csv = root / "research" / "ams2-coverage-manifest.csv"
    coverage_json.parent.mkdir(parents=True, exist_ok=True)
    coverage_json.write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_ams2_coverage_csv(coverage, coverage_csv)

    disagreement = disagreement_builder(root)
    disagreement_path = root / "research" / "simulator-disagreement-audit.json"
    disagreement_path.write_text(
        json.dumps(disagreement, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    changed_docs = update_release_references(root, stats, disagreement)
    site_path = root / "dist" / "site" / "index.html"
    site_path.parent.mkdir(parents=True, exist_ok=True)
    site_path.write_text(site_builder(root), encoding="utf-8")

    errors = validator(root)
    if errors:
        raise ReleaseFinalizeError(
            "release validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        )
    if run_tests:
        _run_tests(root)

    return {
        **stats,
        "changed_documentation": changed_docs,
        "generated": [
            str(coverage_json.relative_to(root)),
            str(coverage_csv.relative_to(root)),
            str(disagreement_path.relative_to(root)),
            str(site_path.relative_to(root)),
        ],
        "validation": "passed",
        "tests": "passed" if run_tests else "not-run",
    }
