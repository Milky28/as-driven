from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .research_handoff import ResearchHandoffError, _read_json, _write_json
from .schema_validation import validate_instance
from .validate import validate_repository


def record_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pointer_value(document: dict[str, Any], pointer: str) -> tuple[bool, Any]:
    current: Any = document
    for token in (part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]):
        if not isinstance(current, dict) or token not in current:
            return False, None
        current = current[token]
    return True, copy.deepcopy(current)


def set_pointer(document: dict[str, Any], pointer: str, value: Any) -> None:
    tokens = [
        part.replace("~1", "/").replace("~0", "~")
        for part in pointer.split("/")[1:]
    ]
    current: Any = document
    for token in tokens[:-1]:
        if not isinstance(current, dict) or token not in current:
            raise ResearchHandoffError(
                f"research amendment points to unknown parent field {pointer!r}"
            )
        current = current[token]
    if not tokens or not isinstance(current, dict):
        raise ResearchHandoffError(f"research amendment points to invalid field {pointer!r}")
    current[tokens[-1]] = copy.deepcopy(value)


def merge_source_registry(
    registry: dict[str, Any], candidates: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    merged = copy.deepcopy(registry)
    known = {source["source_id"]: source for source in merged.get("sources", [])}
    added: list[str] = []
    for candidate in candidates:
        source_id = candidate["source_id"]
        existing = known.get(source_id)
        if existing is not None:
            if existing != candidate:
                raise ResearchHandoffError(
                    f"candidate source {source_id!r} differs from the registered source"
                )
            continue
        merged["sources"].append(copy.deepcopy(candidate))
        known[source_id] = candidate
        added.append(source_id)
    return merged, added


def _friendly_path(path: str) -> str:
    return path.removeprefix("/authentic_controls/").replace("/", " ").replace("_", " ")


def _refresh_control_notes(
    record: dict[str, Any], changed_paths: list[str], issue_url: str
) -> None:
    if not changed_paths:
        return
    controls = record["authentic_controls"]
    prior = controls.get("notes") or []
    gap_words = ("not establish", "remain unknown", "unknown field", "still open")
    preserved = [
        note
        for note in prior
        if not any(word in str(note).casefold() for word in gap_words)
    ]
    material: list[str] = []

    def visit(value: Any, prefix: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key not in {"notes", "source_label"}:
                    visit(child, f"{prefix}/{key}")
        elif value in {None, "unknown"}:
            material.append(prefix)

    visit(controls, "/authentic_controls")
    amended = ", ".join(_friendly_path(path) for path in sorted(changed_paths))
    preserved.append(
        f"Reviewed existing-car research at {issue_url} updated: {amended}."
    )
    if material:
        preserved.append(
            "The reviewed real-car evidence still does not establish: "
            + ", ".join(_friendly_path(path) for path in sorted(material))
            + "."
        )
    controls["notes"] = preserved


def apply_research_amendment(
    existing_record: dict[str, Any], entry: dict[str, Any], approved_at: str
) -> dict[str, Any]:
    record = copy.deepcopy(existing_record)
    changed_control_paths: list[str] = []
    changed_transmission = False
    for claim in entry["claims"]:
        path = claim["path"]
        present, current = pointer_value(record, path)
        if present != claim["previously_present"] or current != claim["from"]:
            raise ResearchHandoffError(
                f"curated record drifted at {path!r}; regenerate the research proposal"
            )
        changed = current != claim["to"] or not present
        if changed != claim["changed"]:
            raise ResearchHandoffError(
                f"research amendment changed flag is stale for {path!r}"
            )
        if changed:
            set_pointer(record, path, claim["to"])
            if path.startswith("/authentic_controls/"):
                changed_control_paths.append(path)
                changed_transmission = changed_transmission or path.startswith(
                    "/authentic_controls/transmission/"
                )
        record.setdefault("provenance", {}).setdefault("claims", []).append(
            {
                "paths": [path],
                "source_refs": list(claim["source_refs"]),
                "confidence": claim["confidence"],
                "basis": claim["basis"],
            }
        )

    changed_by_path = {
        claim["path"]: claim for claim in entry["claims"] if claim["changed"]
    }
    for simulator in record.get("simulators", []):
        retained: list[dict[str, Any]] = []
        for override in simulator.get("overrides", []):
            claim = changed_by_path.get(override.get("path"))
            if claim is None:
                retained.append(override)
                continue
            if override.get("value") == claim["to"]:
                continue
            revised = copy.deepcopy(override)
            revised["condition"] = (
                f"Reviewed real-car research at {entry['issue_url']} establishes "
                f"{claim['to']!r}, while this exact simulator implementation retained "
                f"the observed value {override.get('value')!r}."
            )
            revised["source_refs"] = sorted(
                set(revised.get("source_refs", [])) | set(claim["source_refs"])
            )
            retained.append(revised)
        simulator["overrides"] = retained

    if any(path.startswith("/authentic_controls/steering/wheel_rim/") for path in changed_control_paths):
        wheel = record["authentic_controls"]["steering"]["wheel_rim"]
        wheel["source_label"] = "real-car-research"
        wheel["notes"] = "Wheel details reflect the reviewed exact-car sources in provenance."
    _refresh_control_notes(record, changed_control_paths, entry["issue_url"])
    if changed_transmission and "archetype" in record:
        if entry.get("removed_archetype") != record["archetype"]:
            raise ResearchHandoffError(
                "transmission research changed a classified record without preserving its prior archetype"
            )
        record.pop("archetype", None)
    elif entry.get("removed_archetype") is not None:
        raise ResearchHandoffError("research amendment removes an archetype without a transmission change")
    if entry.get("driver_summary"):
        record["driver_summary"] = entry["driver_summary"]
    record["updated_at"] = approved_at
    return record


def validate_research_amendment(
    root: Path,
    manifest: dict[str, Any],
    candidate_sources: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = _read_json(
        root / "schema" / "v1" / "research-amendment.schema.json",
        "research amendment schema",
    )
    errors = validate_instance(manifest, schema, "research amendment")
    if errors:
        raise ResearchHandoffError("; ".join(errors))
    if len(manifest["records"]) != 1:
        raise ResearchHandoffError(
            "research amendment must contain exactly one curated record"
        )
    entry = manifest["records"][0]
    paths = [claim["path"] for claim in entry["claims"]]
    if len(paths) != len(set(paths)):
        raise ResearchHandoffError("research amendment claim paths must be unique")
    claim_sources = {
        source_id
        for claim in entry["claims"]
        for source_id in claim["source_refs"]
    }
    if set(entry["source_refs"]) != claim_sources:
        raise ResearchHandoffError(
            "research amendment source_refs must exactly match its claim sources"
        )
    record_path = root / "data" / "v1" / "cars" / f"{entry['record_id']}.json"
    if not record_path.is_file():
        raise ResearchHandoffError(
            f"research amendment target {entry['record_id']!r} is not curated"
        )
    if record_sha256(record_path) != entry["previous_record_sha256"]:
        raise ResearchHandoffError(
            "the curated record changed after this proposal was prepared; regenerate it"
        )
    registry = _read_json(root / "data" / "v1" / "sources.json", "source registry")
    merged_sources, _ = merge_source_registry(registry, candidate_sources)
    known_sources = {source["source_id"] for source in merged_sources["sources"]}
    missing_sources = sorted(set(entry["source_refs"]) - known_sources)
    if missing_sources:
        raise ResearchHandoffError(
            f"research amendment cites unregistered source(s) {missing_sources!r}"
        )
    preview = apply_research_amendment(
        _read_json(record_path, "curated record"), entry, manifest["approved_at"]
    )
    car_schema = _read_json(
        root / "schema" / "v1" / "car-record.schema.json", "car record schema"
    )
    errors = validate_instance(preview, car_schema, "research amendment preview")
    if errors:
        raise ResearchHandoffError("; ".join(errors))

    with tempfile.TemporaryDirectory(prefix="as-driven-research-amendment-") as directory:
        temporary = Path(directory)
        shutil.copytree(root / "data", temporary / "data")
        shutil.copytree(root / "curation", temporary / "curation")
        shutil.copytree(root / "schema", temporary / "schema")
        _write_json(temporary / "data" / "v1" / "sources.json", merged_sources)
        _write_json(
            temporary / "data" / "v1" / "cars" / f"{entry['record_id']}.json",
            preview,
        )
        index = _read_json(temporary / "data" / "v1" / "index.json", "dataset index")
        index["dataset_version"] = manifest["dataset_version"]
        index["released_at"] = manifest["approved_at"]
        _write_json(temporary / "data" / "v1" / "index.json", index)
        _write_json(temporary / "curation" / "research-amendment-preview.json", manifest)
        errors = validate_repository(temporary)
        if errors:
            raise ResearchHandoffError(
                "research amendment dry-run validation failed:\n"
                + "\n".join(errors)
            )
    return preview, merged_sources
