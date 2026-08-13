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


def review_unmatched_ams2_observations(
    candidate_payload: dict[str, Any],
    log_path: Path,
    *,
    curated_data_directory: Path | None = None,
) -> dict[str, Any]:
    """Correlate plugin JSONL observations with staged AMS2 candidates.

    This is deliberately a review-only workflow. It never creates records or
    treats a normalized suggestion as a telemetry alias.
    """

    candidates = candidate_payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidate payload must contain a candidates array")
    if not log_path.is_file():
        raise ValueError(f"unmatched identity log does not exist: {log_path}")

    parsed: list[dict[str, str]] = []
    parse_errors: list[dict[str, Any]] = []
    unsupported_games: list[dict[str, Any]] = []
    exact_line_keys: set[tuple[str, ...]] = set()
    duplicate_lines = 0
    for line_number, line in enumerate(
        log_path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("entry must be a JSON object")
            required = ("observed_at_utc", "game_name", "car_model", "car_id", "car_class")
            for field in required:
                if not isinstance(value.get(field), str) or not value[field]:
                    raise ValueError(f"{field} must be a non-empty string")
            observation = {
                "observed_at_utc": value["observed_at_utc"],
                "game_name": value["game_name"],
                "game_version": _diagnostic_string(value.get("game_version")),
                "car_model": value["car_model"],
                "car_id": value["car_id"],
                "car_class": value["car_class"],
                "dataset_version": _diagnostic_string(value.get("dataset_version")),
                "simhub_version": _diagnostic_string(value.get("simhub_version")),
                "line_number": str(line_number),
            }
            if _normalized_name(observation["game_name"]) not in {
                "ams2",
                "automobilista2",
            }:
                unsupported_games.append({**observation, "reason": "not an AMS2 observation"})
                continue
            exact_key = tuple(observation[field] for field in (
                "observed_at_utc",
                "game_name",
                "game_version",
                "car_model",
                "car_id",
                "car_class",
                "dataset_version",
                "simhub_version",
            ))
            if exact_key in exact_line_keys:
                duplicate_lines += 1
                continue
            exact_line_keys.add(exact_key)
            parsed.append(observation)
        except (json.JSONDecodeError, ValueError) as exc:
            parse_errors.append({"line_number": line_number, "error": str(exc)})

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for observation in parsed:
        key = (
            observation["car_model"],
            observation["car_id"],
            observation["car_class"],
        )
        grouped.setdefault(key, []).append(observation)

    candidate_rows = []
    for candidate in candidates:
        identity = candidate.get("identity", {})
        candidate_rows.append(
            {
                "candidate": candidate,
                "source_row": candidate.get("source_row"),
                "display_name": identity.get("display_name"),
                "chassis_manufacturer": identity.get("chassis_manufacturer"),
                "class": identity.get("class"),
                "year": identity.get("year", {}).get("label"),
            }
        )
    curated = _load_curated_ams2_identities(curated_data_directory)

    review_items: list[dict[str, Any]] = []
    for (car_model, car_id, car_class), observations in sorted(grouped.items()):
        observations = sorted(observations, key=lambda item: item["observed_at_utc"])
        versions = _preferred_versions(item["game_version"] for item in observations)
        exact_candidates = [
            row for row in candidate_rows if row["display_name"] == car_model
        ]
        suggestion_candidates: list[tuple[dict[str, Any], str, str]] = []
        for row in candidate_rows:
            display_name = row["display_name"]
            if not isinstance(display_name, str):
                continue
            if _normalized_name(display_name) == _normalized_name(car_model):
                suggestion_candidates.append(
                    (
                        row,
                        "normalized-exact",
                        "Names differ only by case, accents, spaces, or punctuation.",
                    )
                )
                continue
            manufacturer = row["chassis_manufacturer"]
            if (
                isinstance(manufacturer, str)
                and manufacturer != "unknown"
                and _normalized_name(f"{manufacturer} {display_name}")
                == _normalized_name(car_model)
            ):
                suggestion_candidates.append(
                    (
                        row,
                        "chassis-manufacturer-prefix",
                        "Logged name equals the sheet chassis manufacturer plus display name.",
                    )
                )

        item: dict[str, Any] = {
            "status": "no-candidate",
            "confidence": "unknown",
            "rule": "",
            "rationale": "No conservative source-candidate rule matched.",
            "car_model": car_model,
            "car_id": car_id,
            "car_class": car_class,
            "preferred_game_version": _latest_known(observations, "game_version"),
            "game_versions": versions,
            "preferred_simhub_version": _latest_known(observations, "simhub_version"),
            "simhub_versions": _preferred_versions(
                observation["simhub_version"] for observation in observations
            ),
            "preferred_dataset_version": _latest_known(observations, "dataset_version"),
            "dataset_versions": _preferred_versions(
                observation["dataset_version"] for observation in observations
            ),
            "first_observed_at_utc": observations[0]["observed_at_utc"],
            "last_observed_at_utc": observations[-1]["observed_at_utc"],
            "observation_count": len(observations),
            "source_row": None,
            "candidate_name": None,
            "candidate_class": None,
            "candidate_year": None,
            "curated_record_id": curated.get(car_model),
        }
        if car_model in curated:
            item.update(
                status="already-curated",
                confidence="verified",
                rule="exact-curated-identity",
                rationale="The exact logged telemetry name already exists in the curated dataset.",
            )
        elif len(exact_candidates) == 1:
            _apply_candidate(
                item,
                exact_candidates[0],
                status="exact-candidate",
                confidence="verified",
                rule="exact-source-name",
                rationale="Logged CarModel exactly equals one staged source display name.",
            )
        elif len(exact_candidates) > 1:
            item.update(
                status="ambiguous-candidate",
                rationale="Multiple staged source rows have the exact logged name.",
            )
        elif len(suggestion_candidates) == 1:
            candidate, rule, rationale = suggestion_candidates[0]
            _apply_candidate(
                item,
                candidate,
                status="suggested-candidate",
                confidence="high",
                rule=rule,
                rationale=rationale,
            )
        elif len(suggestion_candidates) > 1:
            item.update(
                status="ambiguous-candidate",
                rationale="Multiple staged rows satisfy a conservative formatting rule.",
            )
        review_items.append(item)

    status_counts = Counter(item["status"] for item in review_items)
    return {
        "review": "ams2-unmatched-observations",
        "review_version": "0.1.0",
        "reviewed_at": date.today().isoformat(),
        "source_log": str(log_path),
        "candidate_source_id": candidate_payload.get("source_id"),
        "curated_data_directory": (
            str(curated_data_directory) if curated_data_directory is not None else None
        ),
        "stats": {
            "parsed_ams2_observations": len(parsed),
            "unique_raw_identities": len(review_items),
            "duplicate_lines": duplicate_lines,
            "unsupported_game_observations": len(unsupported_games),
            "parse_errors": len(parse_errors),
            "statuses": dict(sorted(status_counts.items())),
        },
        "review_items": review_items,
        "unsupported_game_observations": unsupported_games,
        "parse_errors": parse_errors,
        "review_notes": [
            "This queue never promotes records or adds telemetry aliases.",
            "Exact candidate correlation establishes a review target, not control-data validity for the logged game version.",
            "Suggested candidates use formatting-only or chassis-manufacturer-prefix rules; all require explicit approval.",
            "No-candidate observations require a new source or direct research before curation.",
        ],
    }


def write_unmatched_review_csv(review: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "status",
        "confidence",
        "car_model",
        "car_id",
        "car_class",
        "preferred_game_version",
        "game_versions",
        "preferred_simhub_version",
        "simhub_versions",
        "preferred_dataset_version",
        "dataset_versions",
        "first_observed_at_utc",
        "last_observed_at_utc",
        "observation_count",
        "source_row",
        "candidate_name",
        "candidate_class",
        "candidate_year",
        "curated_record_id",
        "rule",
        "rationale",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in review.get("review_items", []):
            row = dict(item)
            for field in ("game_versions", "simhub_versions", "dataset_versions"):
                row[field] = " | ".join(row.get(field, []))
            writer.writerow({field: row.get(field) for field in fields})


def _diagnostic_string(value: Any) -> str:
    return value if isinstance(value, str) and value else "unknown"


def _preferred_versions(values: Any) -> list[str]:
    unique = sorted(set(values))
    known = [value for value in unique if value != "unknown"]
    return known + (["unknown"] if "unknown" in unique else [])


def _latest_known(observations: list[dict[str, str]], field: str) -> str:
    for observation in reversed(observations):
        value = observation[field]
        if value != "unknown":
            return value
    return "unknown"


def _apply_candidate(
    item: dict[str, Any],
    candidate: dict[str, Any],
    *,
    status: str,
    confidence: str,
    rule: str,
    rationale: str,
) -> None:
    item.update(
        status=status,
        confidence=confidence,
        rule=rule,
        rationale=rationale,
        source_row=candidate["source_row"],
        candidate_name=candidate["display_name"],
        candidate_class=candidate["class"],
        candidate_year=candidate["year"],
    )


def _load_curated_ams2_identities(data_directory: Path | None) -> dict[str, str]:
    if data_directory is None:
        return {}
    index_path = data_directory / "index.json"
    if not index_path.is_file():
        raise ValueError(f"curated dataset index does not exist: {index_path}")
    index = _load_json(index_path)
    identities: dict[str, str] = {}
    for relative_path in index.get("records", []):
        record = _load_json(data_directory / relative_path)
        record_id = record.get("record_id")
        for simulator in record.get("simulators", []):
            if simulator.get("simulator") != "ams2":
                continue
            for identity in simulator.get("identities", []):
                value = identity.get("value")
                if isinstance(value, str) and isinstance(record_id, str):
                    identities[value] = record_id
    return identities
