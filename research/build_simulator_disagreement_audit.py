"""Build the cross-simulator disagreement audit from reviewed records.

The audit is a research view, not a second source of control truth.  It keeps
the authentic baseline, simulator observations, and evidence strength visible
beside every conflict so a disagreement can become a falsifiable benchmark
finding instead of a badge with no adjudication path.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from as_driven_db.site import _comparison_value, simulator_disagreements


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "simulator-disagreement-audit.json"

PRIMARY_SOURCE_TYPES = {"manufacturer", "homologation"}

HARDWARE_PATHS = {
    "/authentic_controls/transmission/forward_gears",
    "/authentic_controls/transmission/gearbox_type",
    "/authentic_controls/transmission/shift_actuation",
    "/authentic_controls/transmission/shift_pattern",
    "/authentic_controls/transmission/first_gear_position",
    "/authentic_controls/steering/wheel_rim/shape",
    "/authentic_controls/steering/wheel_rim/open_top",
}
LAUNCH_PATHS = {
    "/authentic_controls/transmission/standing_start_clutch",
}
RUNNING_SHIFT_PATHS = {
    "/authentic_controls/transmission/upshift/clutch",
    "/authentic_controls/transmission/upshift/throttle_lift",
    "/authentic_controls/transmission/upshift/automatic_cut",
    "/authentic_controls/transmission/downshift/clutch",
    "/authentic_controls/transmission/downshift/manual_blip",
    "/authentic_controls/transmission/downshift/automatic_blip",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_pointer(document: dict[str, Any], pointer: str) -> Any:
    node: Any = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            return None
        node = node[token]
    return node


def claim_for_path(record: dict[str, Any], path: str) -> dict[str, Any] | None:
    candidates: list[tuple[int, dict[str, Any]]] = []
    for claim in record.get("provenance", {}).get("claims", []):
        for claim_path in claim.get("paths", []):
            if path == claim_path or path.startswith(claim_path.rstrip("/") + "/"):
                candidates.append((len(claim_path), claim))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def driver_impact(path: str) -> tuple[str, str]:
    if path in HARDWARE_PATHS:
        return "hardware-choice", "high"
    if path in LAUNCH_PATHS:
        return "launch-technique", "high"
    if path in RUNNING_SHIFT_PATHS:
        return "running-shift-technique", "high"
    return "cockpit-equipment", "medium"


def finding_id(record_id: str, path: str) -> str:
    suffix = path.removeprefix("/authentic_controls/").replace("/", "-")
    return f"{record_id}--{suffix.replace('_', '-')}"


def build_audit(root: Path = ROOT) -> dict[str, Any]:
    data = root / "data" / "v1"
    index = read_json(data / "index.json")
    source_registry = read_json(data / "sources.json")["sources"]
    sources = {source["source_id"]: source for source in source_registry}

    findings: list[dict[str, Any]] = []
    for relative in index["records"]:
        record = read_json(data / relative)
        entries = record.get("simulators") or []
        if len(entries) < 2:
            continue
        entries_by_id = {entry["simulator"]: entry for entry in entries}
        for disagreement in simulator_disagreements(
            record["authentic_controls"], entries
        ):
            path = disagreement["path"]
            baseline_value = resolve_pointer(record, path)
            claim = claim_for_path(record, path) or {}
            source_refs = list(claim.get("source_refs") or [])
            primary_refs = [
                source_ref
                for source_ref in source_refs
                if sources.get(source_ref, {}).get("source_type")
                in PRIMARY_SOURCE_TYPES
            ]
            confidence = claim.get("confidence", "unknown")
            impact, priority = driver_impact(path)

            simulator_views = []
            matching: list[str] = []
            departing: list[str] = []
            for value in disagreement["values"]:
                simulator_id = value["simulator_id"]
                raw_value = value["raw_value"]
                entry = entries_by_id[simulator_id]
                if raw_value in {None, "unknown"}:
                    relationship = "not-established"
                elif baseline_value in {None, "unknown"}:
                    relationship = "baseline-open"
                elif raw_value == baseline_value:
                    relationship = "matches-baseline"
                    matching.append(simulator_id)
                else:
                    relationship = "departs-from-baseline"
                    departing.append(simulator_id)
                simulator_views.append(
                    {
                        "simulator": simulator_id,
                        "label": value["simulator"],
                        "value": raw_value,
                        "display_value": value["value"],
                        "relationship_to_authentic": relationship,
                        "verified_game_version": entry.get(
                            "verified_game_version", ""
                        ),
                        "verified_at": entry.get("verified_at", ""),
                        "confidence": (entry.get("confidence") or {}).get(
                            "level", "unknown"
                        ),
                        "source_refs": entry.get("source_refs") or [],
                    }
                )

            if baseline_value in {None, "unknown"}:
                status = "authentic-baseline-open"
                basis = (
                    "The reviewed simulators establish conflicting values, but "
                    "the authentic real-car value is not established. Research "
                    "the real car before treating either simulator as the benchmark."
                )
                next_action = (
                    f"Find real-car evidence for {disagreement['field'].lower()}."
                )
            elif confidence in {"verified", "high"} and primary_refs:
                status = "supported-departure"
                basis = (
                    "The curated authentic baseline has high-confidence manufacturer "
                    "or homologation support. Simulator values that differ are recorded "
                    "departures from that baseline."
                )
                next_action = (
                    "Publish the finding with the cited real-car evidence and exact "
                    "simulator versions."
                )
            else:
                status = "provisional-departure"
                basis = (
                    "The curated baseline supplies a comparison answer, but this field "
                    "does not yet have both high confidence and a registered manufacturer "
                    "or homologation source. Treat the apparent departure as provisional."
                )
                next_action = (
                    f"Strengthen the real-car evidence for {disagreement['field'].lower()} "
                    "before publishing a benchmark verdict."
                )

            findings.append(
                {
                    "finding_id": finding_id(record["record_id"], path),
                    "record_id": record["record_id"],
                    "display_name": record["identity"]["display_name"],
                    "class": record["identity"].get("class", ""),
                    "path": path,
                    "field": disagreement["field"],
                    "driver_impact": impact,
                    "priority": priority,
                    "authentic_baseline": {
                        "value": baseline_value,
                        "display_value": _comparison_value(path, baseline_value),
                        "confidence": confidence,
                        "source_refs": source_refs,
                        "primary_source_refs": primary_refs,
                        "basis": claim.get("basis", ""),
                    },
                    "simulator_views": simulator_views,
                    "adjudication": {
                        "status": status,
                        "matching_simulators": matching,
                        "departing_simulators": departing,
                        "basis": basis,
                        "next_action": next_action,
                    },
                }
            )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(
        key=lambda item: (
            priority_order[item["priority"]],
            item["display_name"].casefold(),
            item["field"].casefold(),
        )
    )
    status_counts = Counter(
        item["adjudication"]["status"] for item in findings
    )
    impact_counts = Counter(item["driver_impact"] for item in findings)
    return {
        "audit": "simulator-disagreement-audit",
        "schema_version": "1.0.0",
        "dataset_version": index["dataset_version"],
        "generated_at": index["released_at"],
        "policy": [
            "Only conflicting established simulator values are findings; an unknown beside a value is an evidence gap, not a disagreement.",
            "The authentic baseline remains separate from every simulator observation and is never rewritten by majority vote.",
            "Supported departure means the curated baseline has high-confidence manufacturer or homologation evidence; it does not infer why a simulator differs.",
            "Provisional departure means the simulator conflict is real but the authentic baseline needs stronger independent evidence before publication as a benchmark verdict.",
        ],
        "summary": {
            "cars_with_disagreements": len(
                {item["record_id"] for item in findings}
            ),
            "findings": len(findings),
            "by_status": dict(sorted(status_counts.items())),
            "by_driver_impact": dict(sorted(impact_counts.items())),
        },
        "findings": findings,
    }


def main() -> int:
    payload = build_audit()
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
