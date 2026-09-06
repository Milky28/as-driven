"""Deterministic, evidence-linked control changes between two dataset releases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTROL_FIELDS = (
    ("wheel", "wheel rim", ("steering", "wheel_rim", "shape")),
    ("shifter", "forward gears", ("transmission", "forward_gears")),
    ("shifter", "shift actuation", ("transmission", "shift_actuation")),
    ("shifter", "shift pattern", ("transmission", "shift_pattern")),
    ("clutch", "start clutch", ("transmission", "standing_start_clutch")),
    ("clutch", "upshift clutch", ("transmission", "upshift", "clutch")),
    ("clutch", "downshift clutch", ("transmission", "downshift", "clutch")),
    ("blip", "upshift manual blip", ("transmission", "upshift", "manual_blip")),
    ("blip", "upshift automatic blip", ("transmission", "upshift", "automatic_blip")),
    ("blip", "downshift manual blip", ("transmission", "downshift", "manual_blip")),
    ("blip", "downshift automatic blip", ("transmission", "downshift", "automatic_blip")),
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _data_directory(path: Path) -> Path:
    """Accept either a release root or its data/v1 directory."""
    path = path.resolve()
    return path if (path / "index.json").is_file() else path / "data" / "v1"


def _value_at(value: Any, path: tuple[str, ...]) -> Any:
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _records(data: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    index = _read_json(data / "index.json")
    records = {
        record["record_id"]: record
        for relative in index["records"]
        for record in [_read_json(data / relative)]
    }
    return index, records


def _source_catalog(data: Path) -> dict[str, dict[str, Any]]:
    sources_path = data / "sources.json"
    if not sources_path.exists():
        return {}
    return {
        source["source_id"]: source
        for source in _read_json(sources_path).get("sources", [])
    }


def _evidence(record: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    # Provenance is path-specific in curated records. Listing all registered
    # sources for a changed record is deliberately conservative: it never
    # fabricates a narrower claim-to-source connection in a release summary.
    refs = {
        source_id
        for claim in record.get("provenance", {}).get("claims", [])
        for source_id in claim.get("source_refs", [])
    }
    for simulator in record.get("simulators", []):
        refs.update(simulator.get("source_refs", []))
    evidence = []
    for source_id in sorted(refs):
        source = sources.get(source_id)
        if not source:
            continue
        url = source.get("url") or source.get("archive_url")
        if url:
            evidence.append({"source_id": source_id, "title": source["title"], "url": url})
    return evidence


def release_control_changes(
    previous: Path,
    current: Path,
    *,
    priority_record_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Report material controls changes for records present in both releases."""
    previous_data = _data_directory(previous)
    current_data = _data_directory(current)
    previous_index, previous_records = _records(previous_data)
    current_index, current_records = _records(current_data)
    sources = _source_catalog(current_data)
    changes: list[dict[str, Any]] = []
    priority_record_ids = priority_record_ids or set()

    for record_id in sorted(previous_records.keys() & current_records.keys()):
        before = previous_records[record_id]
        after = current_records[record_id]
        before_controls = before.get("authentic_controls", {})
        after_controls = after.get("authentic_controls", {})
        for category, label, path in CONTROL_FIELDS:
            old_value = _value_at(before_controls, path)
            new_value = _value_at(after_controls, path)
            if old_value == new_value:
                continue
            changes.append(
                {
                    "record_id": record_id,
                    "display_name": after.get("identity", {}).get("display_name", record_id),
                    "category": category,
                    "control": label,
                    "path": "/authentic_controls/" + "/".join(path),
                    "before": old_value,
                    "after": new_value,
                    "priority_recent": record_id in priority_record_ids,
                    "evidence": _evidence(after, sources),
                }
            )

    changes.sort(key=lambda item: (not item["priority_recent"], item["display_name"], item["control"]))
    by_category = {category: sum(1 for item in changes if item["category"] == category)
                   for category in ("wheel", "shifter", "clutch", "blip")}
    return {
        "previous": {"dataset_version": previous_index["dataset_version"], "released_at": previous_index.get("released_at")},
        "current": {"dataset_version": current_index["dataset_version"], "released_at": current_index.get("released_at")},
        "summary": {
            "changed_controls": len(changes),
            "changed_cars": len({item["record_id"] for item in changes}),
            "new_records": sorted(current_records.keys() - previous_records.keys()),
            "retired_records": sorted(previous_records.keys() - current_records.keys()),
            "by_category": by_category,
        },
        "changes": changes,
    }


def render_release_control_changes(report: dict[str, Any]) -> str:
    """Render a compact, human-reviewable summary with evidence links."""
    previous = report["previous"]["dataset_version"]
    current = report["current"]["dataset_version"]
    summary = report["summary"]
    lines = [
        f"# Control-guidance changes: {previous} to {current}",
        "",
        f"{summary['changed_controls']} changed control field(s) across {summary['changed_cars']} car(s).",
        "",
    ]
    if not report["changes"]:
        lines.append("No wheel, shifter, clutch, or blip guidance changed for records present in both releases.")
    for change in report["changes"]:
        recent = " (recent car)" if change["priority_recent"] else ""
        lines.extend([
            f"## {change['display_name']} - {change['control']}{recent}",
            "",
            f"`{change['before']}` → `{change['after']}`",
            "",
        ])
        if change["evidence"]:
            lines.append("Evidence: " + "; ".join(
                f"[{item['source_id']}]({item['url']})" for item in change["evidence"]
            ))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
