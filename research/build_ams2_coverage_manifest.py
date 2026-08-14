"""Build a conservative AMS2 coverage queue from exact SimHub identities.

This is planning data, not runtime matching.  Formatting and inheritance
suggestions always remain explicit review categories; they never become silent
aliases in the curated dataset.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = ROOT / "build" / "ams2-simhub-identity-audit.json"
DEFAULT_CARS = Path(r"C:\Program Files (x86)\SimHub\PluginsData\Automobilista2\Cars")
DEFAULT_LIVE_LOG = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "SimHub"
    / "AsDriven"
    / "Diagnostics"
    / "unmatched-identities.jsonl"
)
OUT_JSON = ROOT / "research" / "ams2-coverage-manifest.json"
OUT_CSV = ROOT / "research" / "ams2-coverage-manifest.csv"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def live_observations(log_path: Path) -> dict[str, dict[str, Any]]:
    """Identities the plugin saw in live telemetry, newest wins.

    SimHub stores one settings file per car it has seen and does not rewrite it
    when the game renames a car, so that inventory drifts: it can name
    identities the game no longer reports and miss the ones it does. The
    plugin's unmatched-identity log is written from live telemetry on every
    uncurated load, so it carries the current model, id and class.

    It covers only uncurated cars, because a curated one stops being logged.
    That is exactly the population this queue is about, so it is used to add and
    correct identities, never to remove them.
    """
    if not log_path.exists():
        return {}
    observations: dict[str, dict[str, Any]] = {}
    for line in log_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        name = payload.get("car_model")
        if not name:
            continue
        seen = payload.get("observed_at_utc") or ""
        previous = observations.get(name)
        if previous is not None and previous["live_observed_at"] >= seen:
            continue
        observations[name] = {
            "car_id": payload.get("car_id"),
            "telemetry_class": payload.get("car_class"),
            "live_observed_at": seen,
            "live_game_version": payload.get("game_version"),
        }
    return observations


def curated_identities() -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    index = read_json(ROOT / "data" / "v1" / "index.json")
    identities: dict[str, str] = {}
    records: dict[str, dict[str, Any]] = {}
    for relative in index["records"]:
        record = read_json(ROOT / "data" / "v1" / relative)
        records[record["record_id"]] = record
        for simulator in record["simulators"]:
            if simulator["simulator"] != "ams2":
                continue
            for identity in simulator["identities"]:
                if identity["kind"] in {"telemetry-name", "internal-id", "alias"}:
                    identities[identity["value"]] = record["record_id"]
    return identities, records


def load_car_metadata(cars_dir: Path, file_name: str) -> dict[str, Any]:
    path = cars_dir / file_name
    if not path.exists():
        return {}
    payload = read_json(path)
    return {
        "simhub_max_gears": int(payload["MaxGears"]) if payload.get("MaxGears") else None,
        "identity_file_modified_at": path.stat().st_mtime,
    }


def family(name: str) -> str:
    lowered = name.casefold()
    if name.startswith("Formula") or any(
        token in lowered for token in ("brabham", "lotus 49", "lotus 98", "lola t", "reynard", "mp4/")
    ):
        return "open-wheel"
    if any(token in lowered for token in ("hybrid", "gtp", "963", "ajr", "mrx", "r89c", "962c", "787b")):
        return "prototype"
    if any(token in lowered for token in ("gt3", "gt4", "gte", "gt1", "c8.r", "570s", "cayman")):
        return "gt"
    if any(token in lowered for token in ("group", "gr5", "dtm", "procar", "stock car", "super v8")):
        return "touring-stock"
    if any(token in lowered for token in ("ginetta", "caterham", "puma", "gol", "fusca", "chevette")):
        return "club-road"
    return "other"


def reviewer_decisions() -> dict[str, dict[str, Any]]:
    """Explicit review outcomes for identities that are neither curated nor queued."""
    payload = read_json(ROOT / "research" / "ams2-identity-decisions.json")
    return {item["telemetry_name"]: item for item in payload["decisions_list"]}


def classify(
    name: str,
    curated: dict[str, str],
    observed_names: set[str],
    decisions: dict[str, dict[str, Any]],
) -> tuple[str, str, str | None]:
    if name in curated:
        return "covered-exact", "No verification needed; exact runtime identity is curated.", curated[name]

    decision = decisions.get(name)
    if decision is not None:
        if decision["disposition"] == "retired-identity":
            superseded = decision.get("superseded_by")
            action = (
                "Reviewed as a retired pre-rename identity"
                + (f"; superseded by {superseded}." if superseded else " with no identified successor.")
                + " No guided drive is scheduled."
            )
        elif decision["disposition"] == "third-party-content":
            action = (
                "Reviewed as third-party content that AMS2 never shipped; "
                "outside the curated scope of official simulator cars."
            )
        else:
            action = "Reviewed as outside product scope; no controls are curated for it."
        return decision["disposition"], action, decision.get("related_record_id")

    stripped = name.strip()
    formatting = [value for value in curated if value.strip().casefold() == stripped.casefold()]
    if formatting:
        return (
            "formatting-only-review",
            "Review the whitespace/case-only difference as an explicit alias; no guided drive is expected.",
            curated[formatting[0]],
        )

    suffix = " - Low Downforce"
    if name.endswith(suffix):
        base = name[: -len(suffix)]
        if base in curated:
            return (
                "aero-inheritance-ready",
                "Base identity is curated; review this exact aero identity as inherited and explicitly untested.",
                curated[base],
            )
        if base in observed_names:
            return (
                "aero-inheritance-after-base",
                "Verify the observed base car first, then review this exact aero identity as inherited.",
                None,
            )

    qualified = [
        value
        for value in curated
        if value.startswith(name + " - ") and ("High Downforce" in value or "Low Downforce" in value)
    ]
    if qualified:
        return (
            "configuration-inheritance-review",
            "A qualified configuration is curated; confirm this exact identity is the same controls before adding it.",
            curated[qualified[0]],
        )

    if "Safety Car" in name:
        return (
            "special-purpose-review",
            "Decide whether this non-racing/safety identity belongs in product scope before testing controls.",
            None,
        )

    return (
        "full-guided-verification",
        "Capture the current exact identity and complete the guided driving and cockpit review.",
        None,
    )


def build(audit_path: Path, cars_dir: Path, live_log_path: Path | None = None) -> dict[str, Any]:
    audit = read_json(audit_path)
    curated, records = curated_identities()
    live = live_observations(live_log_path) if live_log_path else {}

    observed = list(audit["observed_identities"])
    stored_names = {item["car_model"] for item in observed}
    # An identity the game reports but the stored inventory has never held.
    # These are the ones a queue built from car files alone silently omits.
    for name in sorted(live):
        if name in stored_names:
            continue
        observed.append({"car_model": name, "car_id": live[name]["car_id"], "file": None})
    observed.sort(key=lambda item: item["car_model"].casefold())
    observed_names = {item["car_model"] for item in observed}
    exact_candidates = {
        item["telemetry_name"]: item for item in audit.get("exact_matches", [])
    }
    entries: list[dict[str, Any]] = []

    decisions = reviewer_decisions()
    for item in observed:
        name = item["car_model"]
        disposition, action, related = classify(name, curated, observed_names, decisions)
        stored = item["file"] is not None
        seen_live = live.get(name)
        entry = {
            "telemetry_name": name,
            "car_id": item["car_id"],
            "identity_file": item["file"],
            "coverage_disposition": disposition,
            "family": family(name),
            "related_record_id": related,
            "recommended_action": action,
            "identity_source": (
                "stored-and-live" if stored and seen_live
                else "live-diagnostics" if seen_live
                else "stored-car-file"
            ),
        }
        if stored:
            entry.update(load_car_metadata(cars_dir, item["file"]))
        if seen_live:
            # Live telemetry wins on class and confirms the name is current.
            entry["telemetry_class"] = seen_live["telemetry_class"]
            entry["live_observed_at"] = seen_live["live_observed_at"]
            entry["live_game_version"] = seen_live["live_game_version"]
        candidate = exact_candidates.get(name)
        if candidate is not None:
            entry["legacy_sheet_candidate"] = {
                "source_row": candidate["source_row"],
                "display_name": candidate["display_name"],
                "class": candidate["class"],
                "year": candidate["year"],
            }
            entry["research_readiness"] = "legacy-controls-candidate-available"
        elif disposition == "full-guided-verification":
            entry["research_readiness"] = "independent-control-research-needed"
        else:
            entry["research_readiness"] = "not-applicable"
        entries.append(entry)

    dispositions = Counter(entry["coverage_disposition"] for entry in entries)
    uncovered = [entry for entry in entries if entry["coverage_disposition"] != "covered-exact"]
    verification = [entry for entry in uncovered if entry["coverage_disposition"] == "full-guided-verification"]
    family_counts = Counter(entry["family"] for entry in verification)
    readiness = Counter(entry["research_readiness"] for entry in verification)
    return {
        "manifest": "ams2-exact-identity-coverage",
        "manifest_version": "0.1.0",
        "generated_at": "2026-08-12",
        "dataset_version": read_json(ROOT / "data" / "v1" / "index.json")["dataset_version"],
        "simhub_version": audit.get("simhub_version"),
        "identity_sources": {
            "stored_car_files": str(cars_dir),
            "live_diagnostics_log": str(live_log_path) if live_log_path else None,
            "live_identities_seen": len(live),
            "live_only_identities": sorted(
                entry["telemetry_name"]
                for entry in entries
                if entry["identity_source"] == "live-diagnostics"
            ),
        },
        "rules": [
            "Every runtime match remains exact; this manifest never creates fuzzy aliases.",
            "Aero inheritance is a review suggestion and must explicitly state that the variant was not separately tested.",
            "Stored SimHub identities prove prior observation, not that the car still exists in the current selector.",
            "Stored car files are not rewritten when the game renames a car, so the live diagnostics log is preferred for the current name and class.",
            "Neither source is a roster: an identity absent here may simply never have been loaded on this PC.",
            "Full guided verification remains required when no reviewed base profile safely establishes controls.",
            "Retired and out-of-scope outcomes come from research/ams2-identity-decisions.json, not from generator heuristics.",
            "A retired identity is never aliased onto its renamed record, because it cannot be verified in the certified build.",
        ],
        "stats": {
            "observed_identities": len(entries),
            "curated_records": len(records),
            "covered_exact_identities": dispositions["covered-exact"],
            "uncovered_identities": len(uncovered),
            "full_guided_verifications": len(verification),
            "dispositions": dict(sorted(dispositions.items())),
            "full_verifications_by_family": dict(sorted(family_counts.items())),
            "full_verifications_by_research_readiness": dict(sorted(readiness.items())),
        },
        "entries": entries,
    }


def write_csv(manifest: dict[str, Any]) -> None:
    fields = [
        "telemetry_name",
        "car_id",
        "coverage_disposition",
        "family",
        "simhub_max_gears",
        "related_record_id",
        "research_readiness",
        "recommended_action",
        "identity_source",
        "telemetry_class",
        "live_observed_at",
        "identity_file",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for entry in manifest["entries"]:
            writer.writerow({field: entry.get(field) for field in fields})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--cars-dir", type=Path, default=DEFAULT_CARS)
    parser.add_argument(
        "--live-log",
        type=Path,
        default=DEFAULT_LIVE_LOG,
        help="Plugin unmatched-identity diagnostics log; corrects stale stored car files.",
    )
    args = parser.parse_args()
    manifest = build(args.audit, args.cars_dir, args.live_log)
    OUT_JSON.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(manifest)
    print(json.dumps(manifest["stats"], indent=2))


if __name__ == "__main__":
    main()
