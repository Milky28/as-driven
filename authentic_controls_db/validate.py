from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
STATES = {"yes", "no", "unknown", "not-applicable"}
CONFIDENCE = {"verified", "high", "medium", "low", "unknown"}
SIMULATORS = {"ams2", "iracing", "ac-evo", "ac-rally", "other"}
CLUTCH_USE = {"required", "not-required", "optional", "unknown", "not-applicable"}
THROTTLE_LIFT = {"required", "not-required", "partial", "unknown", "not-applicable"}
BLIP_USE = {"required", "not-required", "optional", "unknown", "not-applicable"}
START_CLUTCH = {"required", "not-required", "anti-stall-available", "unknown", "not-applicable"}


def _load(path: Path, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: cannot read valid JSON: {exc}")
        return None


def _required(obj: Any, fields: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{label}: expected an object")
        return False
    missing = sorted(fields - obj.keys())
    if missing:
        errors.append(f"{label}: missing required field(s): {', '.join(missing)}")
        return False
    return True


def _valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _resolve_pointer(document: Any, pointer: str) -> bool:
    if pointer == "":
        return True
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return False
    current = document
    for encoded in pointer[1:].split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return False
    return True


def _source_refs(
    refs: object, source_ids: set[str], label: str, errors: list[str]
) -> None:
    if not isinstance(refs, list) or not refs:
        errors.append(f"{label}: source_refs must be a non-empty array")
        return
    if len(refs) != len(set(refs)):
        errors.append(f"{label}: duplicate source reference")
    for ref in refs:
        if ref not in source_ids:
            errors.append(f"{label}: unknown source_id {ref!r}")


def _validate_sources(payload: Any, label: str, errors: list[str]) -> set[str]:
    if not _required(payload, {"schema_version", "sources"}, label, errors):
        return set()
    if payload["schema_version"] != "1.0.0":
        errors.append(f"{label}: schema_version must be 1.0.0")
    sources = payload["sources"]
    if not isinstance(sources, list):
        errors.append(f"{label}: sources must be an array")
        return set()
    ids: set[str] = set()
    required = {
        "source_id",
        "title",
        "publisher",
        "url",
        "source_type",
        "retrieved_at",
        "reuse_status",
        "notes",
    }
    for index, source in enumerate(sources):
        item = f"{label}.sources[{index}]"
        if not _required(source, required, item, errors):
            continue
        source_id = source["source_id"]
        if not isinstance(source_id, str) or not ID_RE.fullmatch(source_id):
            errors.append(f"{item}: invalid source_id")
        elif source_id in ids:
            errors.append(f"{item}: duplicate source_id {source_id}")
        else:
            ids.add(source_id)
        if not _valid_date(source["retrieved_at"]):
            errors.append(f"{item}: retrieved_at must be an ISO date")
        if source.get("published_or_updated_at") is not None and not _valid_date(
            source.get("published_or_updated_at")
        ):
            errors.append(f"{item}: published_or_updated_at must be an ISO date or null")
    return ids


def _validate_behavior(behavior: Any, label: str, errors: list[str]) -> None:
    required = {
        "shift_type",
        "auto_blip",
        "shift_cut",
        "wheel_rim_type",
    }
    if not _required(behavior, required, label, errors):
        return
    for name in ("auto_blip", "shift_cut"):
        if behavior[name] not in STATES:
            errors.append(f"{label}.{name}: invalid state {behavior[name]!r}")
    dor = behavior.get("steering_dor")
    if dor is not None and (not isinstance(dor, int) or not 90 <= dor <= 1800):
        errors.append(f"{label}.steering_dor: expected 90..1800 when present")
    rim = behavior["wheel_rim_type"]
    if not _required(rim, {"normalized", "source_label"}, f"{label}.wheel_rim_type", errors):
        return


def _validate_transmission(transmission: Any, label: str, errors: list[str]) -> None:
    required = {
        "forward_gears",
        "gearbox_type",
        "shift_actuation",
        "shift_pattern",
        "upshift",
        "downshift",
        "standing_start_clutch",
    }
    if not _required(transmission, required, label, errors):
        return
    gears = transmission["forward_gears"]
    if gears is not None and (not isinstance(gears, int) or not 1 <= gears <= 20):
        errors.append(f"{label}.forward_gears: expected null or 1..20")
    if transmission["standing_start_clutch"] not in START_CLUTCH:
        errors.append(f"{label}.standing_start_clutch: invalid value")
    action_required = {
        "clutch",
        "throttle_lift",
        "automatic_cut",
        "manual_blip",
        "automatic_blip",
    }
    for direction in ("upshift", "downshift"):
        action = transmission[direction]
        action_label = f"{label}.{direction}"
        if not _required(action, action_required, action_label, errors):
            continue
        if action["clutch"] not in CLUTCH_USE:
            errors.append(f"{action_label}.clutch: invalid value")
        if action["throttle_lift"] not in THROTTLE_LIFT:
            errors.append(f"{action_label}.throttle_lift: invalid value")
        if action["manual_blip"] not in BLIP_USE:
            errors.append(f"{action_label}.manual_blip: invalid value")
        for name in ("automatic_cut", "automatic_blip"):
            if action[name] not in STATES:
                errors.append(f"{action_label}.{name}: invalid state")


def _validate_record(
    record: Any, path: Path, source_ids: set[str], errors: list[str]
) -> str | None:
    label = str(path)
    required = {
        "$schema",
        "schema_version",
        "record_id",
        "identity",
        "authentic_controls",
        "simulators",
        "provenance",
        "updated_at",
    }
    if not _required(record, required, label, errors):
        return None
    record_id = record["record_id"]
    if not isinstance(record_id, str) or not ID_RE.fullmatch(record_id):
        errors.append(f"{label}: invalid record_id")
        return None
    if path.stem != record_id:
        errors.append(f"{label}: filename must match record_id {record_id!r}")
    if record["schema_version"] != "1.0.0":
        errors.append(f"{label}: schema_version must be 1.0.0")
    if not _valid_date(record["updated_at"]):
        errors.append(f"{label}: updated_at must be an ISO date")

    identity = record["identity"]
    _required(identity, {"display_name", "manufacturer", "model", "year", "class"}, f"{label}.identity", errors)
    controls = record["authentic_controls"]
    if _required(controls, {"transmission", "steering"}, f"{label}.authentic_controls", errors):
        _validate_transmission(
            controls["transmission"],
            f"{label}.authentic_controls.transmission",
            errors,
        )
        steering = controls["steering"]
        if _required(steering, {"wheel_rim"}, f"{label}.authentic_controls.steering", errors):
            dor = steering.get("degrees_of_rotation")
            if dor is not None and (not isinstance(dor, int) or not 90 <= dor <= 1800):
                errors.append(
                    f"{label}.authentic_controls.steering.degrees_of_rotation: "
                    "expected 90..1800 when present"
                )

    simulators = record["simulators"]
    if not isinstance(simulators, list) or not simulators:
        errors.append(f"{label}.simulators: expected a non-empty array")
    else:
        seen_simulators: set[str] = set()
        sim_required = {
            "simulator",
            "identities",
            "behavior",
            "overrides",
            "verified_game_version",
            "verified_at",
            "source_refs",
            "confidence",
        }
        for index, simulator in enumerate(simulators):
            sim_label = f"{label}.simulators[{index}]"
            if not _required(simulator, sim_required, sim_label, errors):
                continue
            sim_name = simulator["simulator"]
            if sim_name not in SIMULATORS:
                errors.append(f"{sim_label}: invalid simulator {sim_name!r}")
            elif sim_name in seen_simulators:
                errors.append(f"{sim_label}: duplicate simulator {sim_name!r}")
            seen_simulators.add(sim_name)
            if simulator["verified_game_version"].lower() == "latest":
                errors.append(f"{sim_label}: verified_game_version cannot be 'latest'")
            if not _valid_date(simulator["verified_at"]):
                errors.append(f"{sim_label}: verified_at must be an ISO date")
            _source_refs(simulator["source_refs"], source_ids, sim_label, errors)
            confidence = simulator["confidence"]
            if _required(confidence, {"level", "basis"}, f"{sim_label}.confidence", errors):
                if confidence["level"] not in CONFIDENCE:
                    errors.append(f"{sim_label}.confidence: invalid level")
            _validate_behavior(simulator["behavior"], f"{sim_label}.behavior", errors)

    provenance = record["provenance"]
    if _required(provenance, {"claims"}, f"{label}.provenance", errors):
        claims = provenance["claims"]
        if not isinstance(claims, list) or not claims:
            errors.append(f"{label}.provenance.claims: expected a non-empty array")
        else:
            for index, claim in enumerate(claims):
                claim_label = f"{label}.provenance.claims[{index}]"
                if not _required(claim, {"paths", "source_refs", "confidence", "basis"}, claim_label, errors):
                    continue
                if claim["confidence"] not in CONFIDENCE:
                    errors.append(f"{claim_label}: invalid confidence")
                _source_refs(claim["source_refs"], source_ids, claim_label, errors)
                paths = claim["paths"]
                if not isinstance(paths, list) or not paths:
                    errors.append(f"{claim_label}: paths must be a non-empty array")
                else:
                    for pointer in paths:
                        if not _resolve_pointer(record, pointer):
                            errors.append(f"{claim_label}: unresolved JSON Pointer {pointer!r}")
    return record_id


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    schema_dir = root / "schema" / "v1"
    for name in ("car-record.schema.json", "source-record.schema.json", "dataset-index.schema.json"):
        _load(schema_dir / name, errors)

    data_dir = root / "data" / "v1"
    sources = _load(data_dir / "sources.json", errors)
    source_ids = _validate_sources(sources, str(data_dir / "sources.json"), errors) if sources else set()

    index = _load(data_dir / "index.json", errors)
    indexed: list[str] = []
    if index and _required(index, {"schema_version", "dataset_version", "released_at", "records"}, str(data_dir / "index.json"), errors):
        if index["schema_version"] != "1.0.0":
            errors.append("index.json: schema_version must be 1.0.0")
        if not isinstance(index["dataset_version"], str) or not SEMVER_RE.fullmatch(index["dataset_version"]):
            errors.append("index.json: dataset_version must be semantic version x.y.z")
        if not _valid_date(index["released_at"]):
            errors.append("index.json: released_at must be an ISO date")
        if not isinstance(index["records"], list):
            errors.append("index.json: records must be an array")
        else:
            indexed = index["records"]
            if len(indexed) != len(set(indexed)):
                errors.append("index.json: duplicate record path")

    actual_paths = sorted((data_dir / "cars").glob("*.json"))
    actual_relative = [path.relative_to(data_dir).as_posix() for path in actual_paths]
    if sorted(indexed) != actual_relative:
        errors.append("index.json: records must exactly match data/v1/cars/*.json")

    record_ids: set[str] = set()
    for path in actual_paths:
        record = _load(path, errors)
        if record is None:
            continue
        record_id = _validate_record(record, path, source_ids, errors)
        if record_id in record_ids:
            errors.append(f"{path}: duplicate record_id {record_id}")
        elif record_id:
            record_ids.add(record_id)
    return errors
