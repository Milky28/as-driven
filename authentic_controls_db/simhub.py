from __future__ import annotations

import json
import csv
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
import unicodedata


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _normalized_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    return "".join(character for character in decomposed if character.isalnum())


def audit_ams2_identities(
    candidate_payload: dict[str, Any],
    cars_directory: Path,
    *,
    simhub_version: str = "unknown",
) -> dict[str, Any]:
    """Compare staged AMS2 sheet names with identities observed by SimHub.

    SimHub writes one .shcarsettings file for each car it has observed. This is
    useful evidence for telemetry aliases, but the audit intentionally makes
    only exact matches. Similar-looking names remain review work.
    """

    candidates = candidate_payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidate payload must contain a candidates array")
    if not cars_directory.is_dir():
        raise ValueError(f"SimHub cars directory does not exist: {cars_directory}")

    observed: list[dict[str, str]] = []
    parse_errors: list[dict[str, str]] = []
    for path in sorted(cars_directory.glob("*.shcarsettings")):
        try:
            payload = _load_json(path)
            car_id = payload.get("CarId")
            car_model = payload.get("CarModel")
            if not isinstance(car_id, str) or not isinstance(car_model, str):
                raise ValueError("CarId and CarModel must both be strings")
            observed.append(
                {"car_id": car_id, "car_model": car_model, "file": path.name}
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            parse_errors.append({"file": path.name, "error": str(exc)})

    candidate_rows = [
        {
            "source_row": candidate.get("source_row"),
            "display_name": candidate.get("identity", {}).get("display_name"),
            "class": candidate.get("identity", {}).get("class"),
            "year": candidate.get("identity", {}).get("year", {}).get("label"),
        }
        for candidate in candidates
    ]
    candidate_names = [
        row["display_name"] for row in candidate_rows if isinstance(row["display_name"], str)
    ]
    observed_models = [row["car_model"] for row in observed]
    observed_set = set(observed_models)
    candidate_set = set(candidate_names)
    candidate_name_counts = Counter(candidate_names)
    observed_by_normalized: dict[str, list[dict[str, str]]] = {}
    for row in observed:
        observed_by_normalized.setdefault(_normalized_name(row["car_model"]), []).append(row)

    exact_matches = [
        {**row, "telemetry_name": row["display_name"]}
        for row in candidate_rows
        if row["display_name"] in observed_set
    ]
    unmatched_candidates = [
        row for row in candidate_rows if row["display_name"] not in observed_set
    ]
    observed_without_exact_candidate = [
        row for row in observed if row["car_model"] not in candidate_set
    ]
    duplicate_candidate_names = [
        {"display_name": name, "count": count}
        for name, count in sorted(Counter(candidate_names).items())
        if count > 1
    ]
    id_model_mismatches = [
        row for row in observed if row["car_id"] != row["car_model"]
    ]
    alias_suggestions: list[dict[str, Any]] = []
    for candidate, row in zip(candidates, candidate_rows, strict=True):
        display_name = row["display_name"]
        if not isinstance(display_name, str):
            continue
        if display_name in observed_set or candidate_name_counts[display_name] != 1:
            continue
        chassis_manufacturer = candidate.get("identity", {}).get("chassis_manufacturer")
        rules: list[tuple[str, str, str]] = [
            (
                "normalized-exact",
                _normalized_name(display_name),
                "Names differ only by case, accents, spaces, or punctuation.",
            )
        ]
        if (
            isinstance(chassis_manufacturer, str)
            and chassis_manufacturer != "unknown"
        ):
            rules.append(
                (
                    "chassis-manufacturer-prefix",
                    _normalized_name(f"{chassis_manufacturer} {display_name}"),
                    "SimHub name equals the sheet chassis manufacturer plus display name.",
                )
            )
        for rule, normalized, rationale in rules:
            matches = observed_by_normalized.get(normalized, [])
            if len(matches) != 1:
                continue
            telemetry_name = matches[0]["car_model"]
            # Do not redirect an alias to a telemetry name already claimed by
            # a different exact sheet name.
            if telemetry_name in candidate_set:
                continue
            alias_suggestions.append(
                {
                    **row,
                    "telemetry_name": telemetry_name,
                    "rule": rule,
                    "confidence": "high",
                    "rationale": rationale,
                }
            )
            break

    return {
        "audit": "ams2-simhub-identity",
        "audit_version": "0.1.0",
        "audited_at": date.today().isoformat(),
        "simhub_version": simhub_version,
        "source_directory": str(cars_directory),
        "identity_contract": {
            "sdk_game": "GameData.GameName",
            "sdk_car_model": "GameData.NewData.CarModel",
            "sdk_car_id": "GameData.NewData.CarId",
            "dash_car_model": "DataCorePlugin.GameData.NewData.CarModel",
            "dash_car_id": "DataCorePlugin.GameData.NewData.CarId",
            "recommended_match_key": "exact CarModel/CarId telemetry-name alias",
        },
        "stats": {
            "candidate_rows": len(candidate_rows),
            "observed_simhub_identities": len(observed),
            "observed_car_id_equals_car_model": len(observed) - len(id_model_mismatches),
            "candidate_rows_with_exact_match": len(exact_matches),
            "unique_candidate_names_with_exact_match": len(
                set(row["display_name"] for row in exact_matches)
            ),
            "duplicate_candidate_name_groups": len(duplicate_candidate_names),
            "unmatched_candidate_rows": len(unmatched_candidates),
            "observed_without_exact_candidate": len(observed_without_exact_candidate),
            "alias_suggestions": len(alias_suggestions),
            "parse_errors": len(parse_errors),
        },
        "exact_matches": exact_matches,
        "alias_suggestions": alias_suggestions,
        "duplicate_candidate_names": duplicate_candidate_names,
        "unmatched_candidates": unmatched_candidates,
        "observed_without_exact_candidate": observed_without_exact_candidate,
        "id_model_mismatches": id_model_mismatches,
        "observed_identities": observed,
        "parse_errors": parse_errors,
        "review_notes": [
            "Exact matches are safe alias proposals, not automatically promoted records.",
            "Do not fuzzy-match unmatched names; review season, class, variant, and low-downforce suffixes.",
            "Duplicate sheet display names require variant-specific record IDs before promotion.",
        ],
    }


def write_alias_review_csv(audit: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "status",
        "rule",
        "confidence",
        "source_row",
        "sheet_name",
        "telemetry_name",
        "class",
        "year",
        "rationale",
    ]
    rows = []
    for suggestion in audit.get("alias_suggestions", []):
        rows.append(
            {
                "status": "suggested",
                "rule": suggestion["rule"],
                "confidence": suggestion["confidence"],
                "source_row": suggestion["source_row"],
                "sheet_name": suggestion["display_name"],
                "telemetry_name": suggestion["telemetry_name"],
                "class": suggestion["class"],
                "year": suggestion["year"],
                "rationale": suggestion["rationale"],
            }
        )
    for candidate in audit.get("unmatched_candidates", []):
        if any(
            suggestion["source_row"] == candidate["source_row"]
            for suggestion in audit.get("alias_suggestions", [])
        ):
            continue
        rows.append(
            {
                "status": "manual-review",
                "rule": "",
                "confidence": "unknown",
                "source_row": candidate["source_row"],
                "sheet_name": candidate["display_name"],
                "telemetry_name": "",
                "class": candidate["class"],
                "year": candidate["year"],
                "rationale": "No conservative one-to-one identity rule matched.",
            }
        )
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
