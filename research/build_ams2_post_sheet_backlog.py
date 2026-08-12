"""Merge the staged AMS2 release, source, and identity research.

The inputs live in ``build`` because they are independently reproducible web
and local-audit staging artifacts. The outputs in this directory are checked
in for review, but remain deliberately separate from ``data/v1``.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
OUT_JSON = ROOT / "research" / "ams2-post-1.5.5.2-backlog.json"
OUT_CSV = ROOT / "research" / "ams2-post-1.5.5.2-backlog.csv"
EVENT_MAP = ROOT / "curation" / "ams2-post-sheet-event-map.json"

# These release events are class/rename/configuration bookkeeping. Their model
# members or predecessor records carry the actual control-source research.
NON_STANDALONE_SOURCE_ITEMS = {
    (2024, "Stock Car Pro Series 2024 season"),
    (2025, "Aston Martin Vantage GT3 Evo — second configuration not named by Reiza"),
    (2025, "Ligier European Series"),
    (2025, "Vintage Cars Tier 1"),
    (2025, "Vintage Cars Tier 2"),
    (2025, "2005 LMP1"),
    (2025, "2005 LMP2"),
    (2025, "2005 GT1"),
    (2025, "2005 GT2"),
    (2025, "2004 GTR"),
    (2025, "F-V8 Gen3"),
    (2025, "F-Hybrid Gen2"),
    (2025, "F-Hybrid Gen3"),
    (2026, "Formula Edge class"),
    (2026, "Formula V10 Gen3 class"),
    (2026, "Formula V8 Gen1 class"),
    (2026, "Formula V8 Gen2 class"),
    (2026, "GT2 2005 class"),
    (2026, "High-downforce formula configurations"),
}

# Promotion state is resolved from EVENT_MAP and per-car approval manifests.
def read_json(path: Path) -> Any:
    # PowerShell-authored staging files may include a UTF-8 BOM.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def extract_items(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, list):
        return document
    for key in ("items", "inventory"):
        value = document.get(key)
        if isinstance(value, list):
            return value
    raise ValueError("Expected an array or an object with an items array")


def index_by_name(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        name = canonical_item_name(item["item_name"])
        if name in result:
            raise ValueError(f"Duplicate item_name in one staging file: {name}")
        result[name] = item
    return result


def canonical_item_name(name: str) -> str:
    """Repair the one known PowerShell UTF-8 em-dash transcription artifact."""
    return name.replace("ā€”", "—").replace("â€”", "—")


def text_list(value: Any) -> str:
    if isinstance(value, list):
        return " | ".join(str(item) for item in value)
    return "" if value is None else str(value)


def load_promoted_records() -> dict[tuple[int, str], dict[str, str]]:
    """Resolve explicit release-event mappings through checked-in car approvals."""
    approvals: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "curation").glob("ams2-approved-*.json")):
        payload = read_json(path)
        if "approved_controls" in payload:
            record_id = payload["record_id"]
            if record_id in approvals:
                raise ValueError(f"Duplicate per-car approval for {record_id}")
            approvals[record_id] = payload

    promoted: dict[tuple[int, str], dict[str, str]] = {}
    for mapping in read_json(EVENT_MAP)["event_mappings"]:
        key = (mapping["calendar_year"], mapping["item_name"])
        if key in promoted:
            raise ValueError(f"Duplicate post-sheet event mapping: {key}")
        record_id = mapping["record_id"]
        approval = approvals.get(record_id)
        if approval is None:
            continue
        promoted[key] = {
            "record_id": record_id,
            "dataset_version": approval["dataset_version"],
            "scope": approval.get("scope_notes", approval["confidence_notes"]),
        }
    return promoted


def build_backlog() -> dict[str, Any]:
    promoted_records = load_promoted_records()
    merged: list[dict[str, Any]] = []
    missing_source_research: list[str] = []
    missing_comparisons: list[str] = []
    non_standalone_source_events: list[str] = []

    for year in (2024, 2025, 2026):
        inventory_path = BUILD / f"reiza-{year}-inventory.json"
        source_path = BUILD / f"reiza-{year}-control-sources.json"
        comparison_path = BUILD / f"reiza-{year}-comparison.json"

        inventory = extract_items(read_json(inventory_path))
        sources = (
            index_by_name(extract_items(read_json(source_path)))
            if source_path.exists()
            else {}
        )
        comparisons = (
            index_by_name(extract_items(read_json(comparison_path)))
            if comparison_path.exists()
            else {}
        )

        for event in inventory:
            name = event["item_name"]
            promotion = promoted_records.get((year, name))
            source_research = sources.get(name)
            comparison = comparisons.get(name)
            source_disposition = "researched"
            if source_research is None and (year, name) in NON_STANDALONE_SOURCE_ITEMS:
                source_disposition = "covered-by-model-member-or-predecessor"
                non_standalone_source_events.append(f"{year}: {name}")
            elif source_research is None:
                source_disposition = "research-gap"
                missing_source_research.append(f"{year}: {name}")
            if comparison is None:
                missing_comparisons.append(f"{year}: {name}")

            merged.append(
                {
                    "calendar_year": year,
                    **event,
                    "comparison": comparison,
                    "control_source_research": source_research,
                    "control_source_research_disposition": source_disposition,
                    "promotion_status": (
                        "approved" if promotion is not None else "research-only-not-approved"
                    ),
                    "promotion": promotion,
                }
            )

    merged.sort(
        key=lambda item: (
            item["release_date"],
            item["release_version"],
            item["item_name"].casefold(),
        )
    )
    event_types = Counter(item["event_type"] for item in merged)
    year_counts = Counter(str(item["calendar_year"]) for item in merged)
    researched = sum(item["control_source_research"] is not None for item in merged)
    sourced = sum(
        bool((item["control_source_research"] or {}).get("sources"))
        for item in merged
    )
    compared = sum(item["comparison"] is not None for item in merged)
    promoted = sum(item["promotion_status"] == "approved" for item in merged)

    return {
        "research": "ams2-post-1.5.5.2-car-content-and-controls",
        "research_version": "0.1.0",
        "status": "research-only-not-approved",
        "compiled_at": "2026-08-10",
        "baseline": {
            "simulator_version": "1.5.5.2",
            "source_id": "ams2.coanda-sheet.v1.0.34",
            "source_updated_at": "2024-01-17",
        },
        "target": {
            "simulator_version": "1.6.9.91",
            "as_of": "2026-08-10",
        },
        "rules": [
            "Official Reiza sources establish release events, not authentic controls.",
            "Class, rename, replacement, aero, and tyre events remain distinct from model additions.",
            "Identity comparisons separate exact or formatting-only evidence from reviewer suggestions.",
            "Control sources state both supported evidence and remaining unknowns.",
            "Nothing in this backlog may be used for runtime matching without explicit approval and promotion.",
        ],
        "stats": {
            "inventory_events": len(merged),
            "events_by_year": dict(sorted(year_counts.items())),
            "events_by_type": dict(sorted(event_types.items())),
            "events_with_control_source_research": researched,
            "model_events_with_verified_source_urls": sourced,
            "model_events_with_explicit_source_gap": researched - sourced,
            "events_with_identity_comparison": compared,
            "promoted_events": promoted,
            "non_standalone_source_events": len(non_standalone_source_events),
            "unresearched_model_events": len(missing_source_research),
            "events_without_identity_comparison": len(merged) - compared,
        },
        "known_gaps": {
            "control_source_research": missing_source_research,
            "identity_comparison": missing_comparisons,
        },
        "non_standalone_source_events": non_standalone_source_events,
        "events": merged,
    }


def write_csv(backlog: dict[str, Any]) -> None:
    fields = [
        "calendar_year",
        "release_date",
        "release_version",
        "event_type",
        "item_name",
        "class",
        "dlc_or_free",
        "baseline_sheet_status",
        "curated_status",
        "observed_simhub_status",
        "control_research_status",
        "remaining_unknowns",
        "recommended_action",
        "promotion_status",
        "promoted_record_id",
        "official_source_url",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in backlog["events"]:
            comparison = item.get("comparison") or {}
            control = item.get("control_source_research") or {}
            writer.writerow(
                {
                    "calendar_year": item["calendar_year"],
                    "release_date": item["release_date"],
                    "release_version": item["release_version"],
                    "event_type": item["event_type"],
                    "item_name": item["item_name"],
                    "class": item["class"],
                    "dlc_or_free": item["dlc_or_free"],
                    "baseline_sheet_status": comparison.get("baseline_sheet", {}).get("status", ""),
                    "curated_status": comparison.get("curated", {}).get("status", ""),
                    "observed_simhub_status": comparison.get("observed_simhub", {}).get("status", ""),
                    "control_research_status": control.get("research_status", ""),
                    "remaining_unknowns": text_list(control.get("remaining_unknowns")),
                    "recommended_action": comparison.get("recommended_action", ""),
                    "promotion_status": item["promotion_status"],
                    "promoted_record_id": (item.get("promotion") or {}).get("record_id", ""),
                    "official_source_url": item["official_source_url"],
                }
            )


def main() -> None:
    backlog = build_backlog()
    OUT_JSON.write_text(
        json.dumps(backlog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_csv(backlog)
    print(json.dumps(backlog["stats"], indent=2))


if __name__ == "__main__":
    main()
