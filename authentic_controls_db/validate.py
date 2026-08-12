from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from .schema_validation import validate_instance

ID_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
# Documentation repeats the current release in prose. These patterns match only
# present-tense status claims; historical release notes use verbs such as
# "adds", "promotes", and "revalidates", so they are never checked.
DOC_STATUS_FILES = ("README.md", "CLAUDE.md", "EARLY_ACCESS.md")
DOC_STATUS_RE = re.compile(
    r"[Dd]ataset:? (\d+\.\d+\.\d+) (?:contains|with) (\d+) (?:curated|reviewed)"
)
DOC_RECORD_COUNT_RE = re.compile(r"currently contains (\d+) curated records")
# One naming convention for AMS2 live-observation evidence, so a car's drive
# source is predictable from its name. Tooling for other publishers (SimHub's
# own identity inventories, for example) uses its own prefix and is not checked.
LIVE_OBSERVATION_ID_RE = re.compile(
    r"^ams2\.local-live-[a-z0-9]+(?:-[a-z0-9]+)*-controls\.\d+(?:\.\d+)*$"
)
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
            if (
                source.get("source_type") == "in-game-observation"
                and source_id.startswith("ams2.")
                and not LIVE_OBSERVATION_ID_RE.fullmatch(source_id)
            ):
                errors.append(
                    f"{item}: in-game observation source_id must be "
                    f"ams2.local-live-<car>-controls.<game-version>, got {source_id!r}"
                )
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


def _simulator_identity_values(simulator: dict[str, Any], kind: str) -> set[str]:
    return {
        identity["value"]
        for identity in simulator.get("identities", [])
        if isinstance(identity, dict)
        and identity.get("kind") == kind
        and isinstance(identity.get("value"), str)
    }


def _validate_car_approval(
    approval: dict[str, Any],
    path: Path,
    records: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    label = str(path)
    record_id = approval.get("record_id")
    record = records.get(record_id)
    if record is None:
        errors.append(f"{label}.record_id: no curated record {record_id!r}")
        return

    simulator = next(
        (item for item in record.get("simulators", []) if item.get("simulator") == "ams2"),
        None,
    )
    if simulator is None:
        errors.append(f"{label}.record_id: curated record has no AMS2 simulator entry")
        return

    approved_names = [approval.get("telemetry_name")]
    approved_names.extend(
        item.get("value") if isinstance(item, dict) else item
        for item in approval.get("additional_telemetry_names", [])
    )
    record_names = _simulator_identity_values(simulator, "telemetry-name")
    for name in approved_names:
        if name not in record_names:
            errors.append(
                f"{label}: approved telemetry name {name!r} is not an exact record identity"
            )

    approved_classes = [approval.get("telemetry_class")]
    approved_classes.extend(approval.get("additional_telemetry_classes", []))
    record_classes = _simulator_identity_values(simulator, "class-id")
    for class_id in approved_classes:
        if class_id not in record_classes:
            errors.append(
                f"{label}: approved telemetry class {class_id!r} is not an exact record identity"
            )

    if approval.get("observed_game_version") != simulator.get("verified_game_version"):
        errors.append(
            f"{label}.observed_game_version: does not match the curated AMS2 verification version"
        )

    controls = approval.get("approved_controls", {})
    transmission = record["authentic_controls"]["transmission"]
    expected = {
        "forward_gears": transmission["forward_gears"],
        "shift_actuation": transmission["shift_actuation"],
        "shift_pattern": transmission["shift_pattern"],
        "standing_start_clutch": transmission["standing_start_clutch"],
        "throttle_lift": transmission["upshift"]["throttle_lift"],
        "automatic_cut": simulator["behavior"]["shift_cut"],
        "automatic_blip": simulator["behavior"]["auto_blip"],
        "manual_blip": transmission["downshift"]["manual_blip"],
        "wheel_rim_shape": simulator["behavior"]["wheel_rim_type"]["normalized"],
    }
    simulator_wheel = simulator["behavior"]["wheel_rim_type"]
    for approval_name, behavior_name in (
        ("wheel_integrated_display", "integrated_display"),
        ("wheel_shift_lights", "shift_lights"),
        ("wheel_open_top", "open_top"),
    ):
        if behavior_name in simulator_wheel:
            expected[approval_name] = simulator_wheel[behavior_name]
    if transmission["upshift"]["clutch"] == transmission["downshift"]["clutch"]:
        expected["running_shift_clutch"] = transmission["upshift"]["clutch"]
    elif "running_shift_clutch" in controls:
        errors.append(
            f"{label}.approved_controls.running_shift_clutch: cannot summarize different "
            "upshift and downshift clutch requirements"
        )

    for name, value in controls.items():
        if name in expected and value != expected[name]:
            errors.append(
                f"{label}.approved_controls.{name}: approved {value!r} does not match "
                f"curated value {expected[name]!r}"
            )


def _validate_approval_record_references(
    payload: dict[str, Any], path: Path, record_ids: set[str], errors: list[str]
) -> None:
    for collection_name in ("records", "identities"):
        collection = payload.get(collection_name)
        if not isinstance(collection, list):
            continue
        for index, item in enumerate(collection):
            if not isinstance(item, dict) or "record_id" not in item:
                continue
            record_id = item["record_id"]
            if record_id not in record_ids:
                errors.append(
                    f"{path}.{collection_name}[{index}].record_id: "
                    f"no curated record {record_id!r}"
                )
    event_mappings = payload.get("event_mappings")
    if isinstance(event_mappings, list):
        seen: set[tuple[Any, Any]] = set()
        for index, item in enumerate(event_mappings):
            if not isinstance(item, dict):
                continue
            key = (item.get("calendar_year"), item.get("item_name"))
            if key in seen:
                errors.append(f"{path}.event_mappings[{index}]: duplicate release event {key!r}")
            seen.add(key)
            record_id = item.get("record_id")
            if record_id not in record_ids:
                errors.append(
                    f"{path}.event_mappings[{index}].record_id: no curated record {record_id!r}"
                )


def _validate_documentation_claims(
    root: Path, index: Any, errors: list[str]
) -> None:
    """Keep prose statements of the current release in step with index.json.

    Only present-tense status claims are compared. Historical release notes are
    left alone so the dataset narrative in README.md stays readable.
    """
    if not isinstance(index, dict):
        return
    version = index.get("dataset_version")
    records = index.get("records")
    if not isinstance(version, str) or not isinstance(records, list):
        return
    count = len(records)

    paths = [root / name for name in DOC_STATUS_FILES]
    paths.extend(sorted((root / "docs").glob("*.md")))
    for path in paths:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exception:
            errors.append(f"{path}: could not read documentation ({exception})")
            continue
        label = path.relative_to(root).as_posix()
        for number, line in enumerate(text.splitlines(), start=1):
            status = DOC_STATUS_RE.search(line)
            if status:
                if status.group(1) != version:
                    errors.append(
                        f"{label}:{number}: documented dataset version "
                        f"{status.group(1)!r} does not match index.json {version!r}"
                    )
                if int(status.group(2)) != count:
                    errors.append(
                        f"{label}:{number}: documented record count "
                        f"{status.group(2)} does not match index.json {count}"
                    )
            only_count = DOC_RECORD_COUNT_RE.search(line)
            if only_count and int(only_count.group(1)) != count:
                errors.append(
                    f"{label}:{number}: documented record count "
                    f"{only_count.group(1)} does not match index.json {count}"
                )


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    schema_dir = root / "schema" / "v1"
    schemas = {
        name: _load(schema_dir / name, errors)
        for name in (
            "car-record.schema.json",
            "source-record.schema.json",
            "dataset-index.schema.json",
            "curation-approval.schema.json",
            "post-sheet-event-map.schema.json",
            "verification-observation.schema.json",
        )
    }

    data_dir = root / "data" / "v1"
    sources = _load(data_dir / "sources.json", errors)
    if sources is not None and schemas["source-record.schema.json"] is not None:
        errors.extend(
            validate_instance(
                sources,
                schemas["source-record.schema.json"],
                str(data_dir / "sources.json"),
            )
        )
    source_ids = _validate_sources(sources, str(data_dir / "sources.json"), errors) if sources else set()

    index = _load(data_dir / "index.json", errors)
    if index is not None and schemas["dataset-index.schema.json"] is not None:
        errors.extend(
            validate_instance(
                index,
                schemas["dataset-index.schema.json"],
                str(data_dir / "index.json"),
            )
        )
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

    records: dict[str, dict[str, Any]] = {}
    for path in actual_paths:
        record = _load(path, errors)
        if record is None:
            continue
        if schemas["car-record.schema.json"] is not None:
            errors.extend(
                validate_instance(
                    record,
                    schemas["car-record.schema.json"],
                    str(path),
                )
            )
        record_id = _validate_record(record, path, source_ids, errors)
        if record_id in records:
            errors.append(f"{path}: duplicate record_id {record_id}")
        elif record_id:
            records[record_id] = record

    curation_dir = root / "curation"
    for path in sorted(curation_dir.glob("*.json")):
        approval = _load(path, errors)
        if not isinstance(approval, dict):
            continue
        if "approved_controls" in approval:
            approval_schema = schemas["curation-approval.schema.json"]
            if approval_schema is not None:
                errors.extend(validate_instance(approval, approval_schema, str(path)))
            _validate_car_approval(approval, path, records, errors)
        else:
            if path.name == "ams2-post-sheet-event-map.json":
                event_map_schema = schemas["post-sheet-event-map.schema.json"]
                if event_map_schema is not None:
                    errors.extend(validate_instance(approval, event_map_schema, str(path)))
            _validate_approval_record_references(approval, path, set(records), errors)

    _validate_documentation_claims(root, index, errors)
    return errors
