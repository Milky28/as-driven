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
DOC_STATUS_FILES = ("README.md", "CLAUDE.md", "AGENTS.md", "EARLY_ACCESS.md")
DOC_STATUS_RE = re.compile(
    r"[Dd]ataset:? (\d+\.\d+\.\d+) (?:contains|with) (\d+) (?:curated|reviewed)"
)
DOC_RECORD_COUNT_RE = re.compile(r"currently contains (\d+) curated records")
STATES = {"yes", "no", "unknown", "not-applicable"}
CONFIDENCE = {"verified", "high", "medium", "low", "unknown"}
SIMULATORS = {"ams2", "iracing", "ac", "ac-evo", "ac-rally", "other"}
# Every simulator that can publish a drive. `other` is a placeholder for a
# simulator the enum does not name yet, so it owns no source prefix and its
# observations are not held to the convention below.
OBSERVING_SIMULATORS = tuple(sorted(SIMULATORS - {"other"}))
# One naming convention for live-observation evidence, so a car's drive source is
# predictable from its name whichever simulator recorded it. Tooling for other
# publishers (SimHub's own identity inventories, for example) uses its own prefix
# and is not checked.
LIVE_OBSERVATION_ID_RE = re.compile(
    r"^(?:"
    + "|".join(re.escape(simulator) for simulator in OBSERVING_SIMULATORS)
    + r")\.local-live-[a-z0-9]+(?:-[a-z0-9]+)*-controls\.\d+(?:\.\d+)*$"
)
CLUTCH_USE = {"required", "not-required", "optional", "unknown", "not-applicable"}
THROTTLE_LIFT = {"required", "not-required", "partial", "unknown", "not-applicable"}
BLIP_USE = {"required", "not-required", "optional", "unknown", "not-applicable"}
START_CLUTCH = {"required", "not-required", "anti-stall-available", "unknown", "not-applicable"}
FIRST_GEAR_POSITION = {"up-left", "up-right", "down-left", "down-right", "unknown"}
# The one vocabulary for how a driver changes gear. The schema pins it on
# authentic_controls; `behavior.shift_type` restates it and must not invent a
# second spelling of the same mechanism.
SHIFT_ACTUATION = {
    "h-pattern",
    "sequential-stick",
    "sequential-paddles",
    "automatic-lever",
    "direct-selection",
    "unknown",
}


# How each simulator spells an aero package, and the only kinds a match is ever
# looked up by. AsDrivenDatabase.MatchPriority in the client is the same list;
# class-id is deliberately absent from both, which is why dozens of records
# share a class key without colliding.
MATCHED_IDENTITY_KINDS = {
    "telemetry-name",
    "display-name",
    "alias",
    "internal-id",
    "car-path",
}
AERO_SUFFIXES = {
    "ams2": {
        "base": "",
        "high-downforce": " - High Downforce",
        "low-downforce": " - Low Downforce",
        "speedway": " - Speedway",
        "superspeedway": " - Superspeedway",
    }
}


def expand_identity(simulator: str, value: str, packages: list[str] | None) -> list[str]:
    """The exact strings an identity stands for.

    Without a package list an identity is one literal string, which is what every
    record wrote by hand before this existed and what a simulator that names its
    variants unsystematically still writes. With one, the base name grows a
    suffix per declared package. Nothing here is applied to an incoming name at
    match time: the expansion happens once, when the database is read, and
    produces keys that are still compared byte for byte.

    Two failure modes are answered the same way AsDrivenDatabase.ExpandIdentity
    answers them, because a client and a validator that disagree about what a
    record means are worse than either being wrong alone. A simulator this table
    does not know falls back to the literal name, so its records match on exactly
    what they spell out. A package the table does not know is a fault in the data
    rather than a name to guess at, and raises: dropping it would expand the
    identity to nothing and leave the car quietly unmatched at one kind of
    circuit.
    """
    if not packages:
        return [value]
    suffixes = AERO_SUFFIXES.get(simulator)
    if not suffixes:
        return [value]
    unknown = [package for package in packages if package not in suffixes]
    if unknown:
        raise ValueError(
            f"unknown aero package(s) {unknown!r} for {simulator}"
        )
    return [value + suffixes[package] for package in packages]


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
            prefix = source_id.split(".", 1)[0]
            if (
                source.get("source_type") == "in-game-observation"
                and prefix in OBSERVING_SIMULATORS
                and not LIVE_OBSERVATION_ID_RE.fullmatch(source_id)
            ):
                errors.append(
                    f"{item}: in-game observation source_id must be "
                    f"{prefix}.local-live-<car>-controls.<game-version>, got {source_id!r}"
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
    # `shift_type` was an unconstrained string, and nine spellings of three
    # mechanisms accumulated: H-pattern beside h-pattern and H-Dogleg, Paddles
    # beside Seq-Paddle and sequential-paddles. None of them ever disagreed with
    # the record's own actuation, which is the invariant worth stating rather
    # than a list of accepted spellings - the client does not read this field at
    # all, deriving what it shows from authentic_controls, so anything else here
    # is a second copy free to rot.
    if behavior["shift_type"] not in SHIFT_ACTUATION:
        errors.append(
            f"{label}.shift_type: {behavior['shift_type']!r} is not one of "
            f"{sorted(SHIFT_ACTUATION)}; it restates the effective shift_actuation "
            "and must use the same vocabulary"
        )
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
    position = transmission.get("first_gear_position")
    if position is not None and position not in FIRST_GEAR_POSITION:
        errors.append(f"{label}.first_gear_position: invalid value")
    # A dogleg only says first is outside the racing plane. Which side is a
    # separate fact, and the McLaren MP4/4 mirrors it, so it is never assumed.
    if position in {"up-left", "up-right"} and transmission["shift_pattern"] == "dogleg-h":
        errors.append(f"{label}.first_gear_position: a dogleg puts first down, not up")
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


def _validate_identities(
    simulator: dict[str, Any], sim_name: str, label: str, errors: list[str]
) -> None:
    """Checks the identities of one simulator entry.

    A declared aero package is only a shorthand for strings the record could have
    written out, so the rules here are the ones that keep the shorthand honest:
    the name it grows from must be a base name, and the simulator must actually
    spell its packages as a suffix. Where either fails, the record writes its
    identities out literally instead and nothing is lost.
    """
    identities = simulator.get("identities")
    if not isinstance(identities, list):
        return
    suffixes = AERO_SUFFIXES.get(sim_name, {})
    for index, identity in enumerate(identities):
        if not isinstance(identity, dict):
            continue
        item = f"{label}.identities[{index}]"
        packages = identity.get("aero_packages")
        value = identity.get("value")
        if packages is None or not isinstance(value, str):
            continue
        if identity.get("kind") != "telemetry-name":
            errors.append(
                f"{item}: aero_packages is only valid on a telemetry-name, "
                f"not {identity.get('kind')!r}"
            )
            continue
        if not suffixes:
            errors.append(
                f"{item}: {sim_name} has no declared aero package spelling, so this "
                "identity must be written out literally"
            )
            continue
        unknown = [
            package
            for package in packages
            if isinstance(packages, list) and package not in suffixes
        ]
        if unknown:
            # The schema's enum and AERO_SUFFIXES are two lists that have to say
            # the same thing. If they ever drift, this is where it surfaces, and
            # it surfaces as an error rather than as a name quietly not expanded.
            errors.append(
                f"{item}: {sim_name} has no spelling for aero package(s) "
                f"{unknown!r}; the suffix table and the schema enum disagree"
            )
            continue
        if value != value.strip():
            errors.append(
                f"{item}: a base name carries no leading or trailing whitespace; "
                f"{value!r} does"
            )
        for suffix in suffixes.values():
            if suffix and value.endswith(suffix):
                errors.append(
                    f"{item}: value {value!r} already carries the {suffix.strip(' -')!r} "
                    "package; aero_packages expands a base name"
                )
                break


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
            # ...and it must restate this record's actuation, not some other
            # mechanism. An override moves it, so compare against the effective
            # value rather than the authentic one.
            effective_actuation = (record.get("authentic_controls", {})
                                   .get("transmission", {})
                                   .get("shift_actuation"))
            for override in simulator.get("overrides") or []:
                if str(override.get("path", "")).endswith("/shift_actuation"):
                    effective_actuation = override.get("value")
            if (simulator.get("behavior", {}).get("shift_type") is not None
                    and simulator["behavior"]["shift_type"] != effective_actuation):
                errors.append(
                    f"{sim_label}.behavior.shift_type: "
                    f"{simulator['behavior']['shift_type']!r} does not match the "
                    f"effective shift_actuation {effective_actuation!r}"
                )
            # "latest" moves under the record; "unknown" is what the plugin
            # writes when it cannot read a version off a running process, and at
            # least one simulator - Assetto Corsa EVO - exposes none anywhere on
            # disk. A draft may carry that honestly, but a curated record may
            # not: an observation is only reproducible against an exact build,
            # so the reviewer has to supply the version the game itself shows.
            game_version = simulator["verified_game_version"].strip().lower()
            if game_version in ("latest", "unknown", ""):
                errors.append(
                    f"{sim_label}: verified_game_version cannot be "
                    f"{simulator['verified_game_version']!r}; record the exact build the "
                    "simulator reports, which for a game that exposes no version to the "
                    "plugin is the one shown on its own settings screen"
                )
            if not _valid_date(simulator["verified_at"]):
                errors.append(f"{sim_label}: verified_at must be an ISO date")
            _source_refs(simulator["source_refs"], source_ids, sim_label, errors)
            confidence = simulator["confidence"]
            if _required(confidence, {"level", "basis"}, f"{sim_label}.confidence", errors):
                if confidence["level"] not in CONFIDENCE:
                    errors.append(f"{sim_label}.confidence: invalid level")
            _validate_behavior(simulator["behavior"], f"{sim_label}.behavior", errors)
            _validate_identities(simulator, sim_name, sim_label, errors)

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
    """Every exact name of one kind, declared packages expanded.

    An approval names the strings the simulator reports, not the shorthand a
    record stores them as, so this has to answer in the simulator's terms or a
    reviewed name would stop being found the moment its record declared packages
    instead of spelling them out.
    """
    simulator_id = simulator.get("simulator")
    values: set[str] = set()
    for identity in simulator.get("identities", []):
        if not isinstance(identity, dict) or identity.get("kind") != kind:
            continue
        value = identity.get("value")
        if not isinstance(value, str):
            continue
        try:
            values.update(
                expand_identity(simulator_id, value, identity.get("aero_packages"))
            )
        except ValueError:
            # _validate_identities reports the drift itself, with the record and
            # the offending package named. Skipping here keeps the approval check
            # running so the rest of its findings still reach the reviewer.
            continue
    return values


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

    # An approval accepts one simulator's evidence for a car, and a car may be
    # covered by several, so the approval says which rather than assuming AMS2.
    approved_simulator = approval.get("simulator")
    simulator = next(
        (
            item
            for item in record.get("simulators", [])
            if item.get("simulator") == approved_simulator
        ),
        None,
    )
    if simulator is None:
        errors.append(
            f"{label}.simulator: curated record has no {approved_simulator!r} entry"
        )
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

    # A simulator that does not group its cars has no class to approve, so an
    # absent telemetry_class is checked against nothing rather than failing. The
    # record carries no class-id identity in that case either, which is what
    # keeps this from silently skipping a class the record does declare.
    approved_classes = []
    if approval.get("telemetry_class") is not None:
        approved_classes.append(approval["telemetry_class"])
    approved_classes.extend(approval.get("additional_telemetry_classes", []))
    record_classes = _simulator_identity_values(simulator, "class-id")
    for class_id in approved_classes:
        if class_id not in record_classes:
            errors.append(
                f"{label}: approved telemetry class {class_id!r} is not an exact record identity"
            )

    if approval.get("observed_game_version") != simulator.get("verified_game_version"):
        errors.append(
            f"{label}.observed_game_version: does not match the curated "
            f"{approved_simulator} verification version"
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

    # A truncated status file has nothing to disagree with, so the checks below
    # would pass it silently. Dataset 0.3.65 shipped four of these emptied by a
    # bad version bump and validation stayed green, so require the content.
    for name in DOC_STATUS_FILES:
        path = root / name
        if not path.exists():
            # Test fixtures build a repository from schema and data alone.
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exception:
            errors.append(f"{name}: could not read documentation ({exception})")
            continue
        if not text.strip():
            errors.append(f"{name}: status document is empty")
        elif version not in text:
            errors.append(f"{name}: does not state the current dataset version {version}")

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


TRANSMISSION_POINTER = "/authentic_controls/transmission"


def _flatten_transmission(transmission: Any) -> dict[str, Any]:
    """The transmission block as JSON Pointer paths into the record."""
    flat: dict[str, Any] = {}

    def walk(node: Any, prefix: str) -> None:
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            path = f"{prefix}/{key}"
            if isinstance(value, dict):
                walk(value, path)
            else:
                flat[path] = value

    walk(transmission, TRANSMISSION_POINTER)
    return flat


def _archetype_consistent(record: dict[str, Any], archetype: dict[str, Any]) -> bool:
    """Whether an archetype could still describe a record that has gaps in it.

    An `unknown` is a wildcard here and nothing else is. This is the only place
    an archetype is allowed to look past a gap, and it still never fills one:
    the answer decides whether a reviewer can classify the record at all.
    """
    for path in set(record) | set(archetype):
        if record.get(path) == "unknown":
            continue
        if record.get(path) != archetype.get(path):
            return False
    return True


def _validate_archetype_registry(
    payload: Any,
    label: str,
    transmission_schema: dict[str, Any] | None,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    """Checks the archetype registry and returns each flattened block by id."""
    if not _required(payload, {"schema_version", "archetypes"}, label, errors):
        return {}
    if payload["schema_version"] != "1.0.0":
        errors.append(f"{label}: schema_version must be 1.0.0")
    archetypes = payload["archetypes"]
    if not isinstance(archetypes, list):
        errors.append(f"{label}: archetypes must be an array")
        return {}

    flattened: dict[str, dict[str, Any]] = {}
    blocks: dict[str, str] = {}
    for index, archetype in enumerate(archetypes):
        item = f"{label}.archetypes[{index}]"
        if not _required(
            archetype, {"archetype_id", "label", "transmission", "basis"}, item, errors
        ):
            continue
        archetype_id = archetype["archetype_id"]
        if not isinstance(archetype_id, str) or not ID_RE.fullmatch(archetype_id):
            errors.append(f"{item}: invalid archetype_id")
            continue
        if archetype_id in flattened:
            errors.append(f"{item}: duplicate archetype_id {archetype_id}")
            continue

        transmission = archetype["transmission"]
        # The shape is enforced against the car record's own definition rather
        # than restated in the archetype schema, so the two cannot drift apart.
        if transmission_schema is not None:
            errors.extend(
                validate_instance(
                    transmission, transmission_schema, f"{item}.transmission"
                )
            )
        flat = _flatten_transmission(transmission)
        gaps = sorted(path for path, value in flat.items() if value == "unknown")
        if gaps:
            errors.append(
                f"{item}: archetype {archetype_id} must be fully specified; "
                f"unknown at {', '.join(gaps)}"
            )

        signature = json.dumps(transmission, sort_keys=True)
        if signature in blocks:
            errors.append(
                f"{item}: archetype {archetype_id} has the same transmission block "
                f"as {blocks[signature]}"
            )
        else:
            blocks[signature] = archetype_id
        flattened[archetype_id] = flat
    return flattened


def _validate_record_archetype(
    record: dict[str, Any],
    label: str,
    archetypes: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    """Checks a record's declared archetype against the registry.

    Nothing here changes a record. The archetype describes the transmission the
    record already states, so every rule is a comparison: a departure the record
    does not declare is an error, and so is a declared departure that turns out
    to agree. That is what keeps an unintended change loud.
    """
    block = record.get("archetype")
    if block is None:
        return
    if not isinstance(block, dict) or "classification" not in block:
        errors.append(f"{label}: archetype must declare a classification")
        return

    classification = block["classification"]
    archetype_id = block.get("archetype_id")
    deviations = block.get("deviations", [])
    basis = block.get("basis")
    if not isinstance(deviations, list):
        errors.append(f"{label}: archetype.deviations must be an array")
        return

    classified = classification in {"matches", "deviates"}
    if classified and not archetype_id:
        errors.append(
            f"{label}: archetype.archetype_id is required when classification "
            f"is {classification}"
        )
    if not classified and archetype_id:
        errors.append(
            f"{label}: archetype.archetype_id must be absent when classification "
            f"is {classification}"
        )
    if not classified and not basis:
        errors.append(
            f"{label}: archetype.basis is required when classification "
            f"is {classification}"
        )
    if classification == "deviates" and not deviations:
        errors.append(
            f"{label}: archetype.deviations must list at least one departure "
            "when classification is deviates"
        )
    if classification != "deviates" and deviations:
        errors.append(
            f"{label}: archetype.deviations must be empty when classification "
            f"is {classification}"
        )

    controls = record.get("authentic_controls")
    if not isinstance(controls, dict):
        return
    record_flat = _flatten_transmission(controls.get("transmission"))

    declared: set[str] = set()
    for index, deviation in enumerate(deviations):
        item = f"{label}: archetype.deviations[{index}]"
        if not isinstance(deviation, dict) or "path" not in deviation:
            errors.append(f"{item}: must declare a path")
            continue
        path = deviation["path"]
        if path not in record_flat:
            errors.append(
                f"{item}: {path} is not a field of this record's transmission"
            )
            continue
        if path in declared:
            errors.append(f"{item}: duplicate deviation path {path}")
            continue
        declared.add(path)

    if archetype_id and archetype_id not in archetypes:
        if classified:
            errors.append(f"{label}: unknown archetype_id {archetype_id}")
        return

    if classified and archetype_id:
        archetype_flat = archetypes[archetype_id]
        differing = {
            path
            for path in set(record_flat) | set(archetype_flat)
            if record_flat.get(path) != archetype_flat.get(path)
        }
        if classification == "matches" and differing:
            errors.append(
                f"{label}: archetype {archetype_id} is declared as matched but the "
                f"record differs at {', '.join(sorted(differing))}"
            )
        if classification == "deviates":
            undeclared = sorted(differing - declared)
            if undeclared:
                errors.append(
                    f"{label}: undeclared departure from archetype {archetype_id} "
                    f"at {', '.join(undeclared)}"
                )
            agreeing = sorted(declared - differing)
            if agreeing:
                errors.append(
                    f"{label}: archetype.deviations names {', '.join(agreeing)}, "
                    f"where the record agrees with archetype {archetype_id}"
                )

    if classification == "undetermined":
        # Undetermined is a gap, not a verdict. It has to be caused by a gap in
        # this record, and the gap has to actually leave the choice open: with
        # one candidate left there is nothing further for a drive to settle.
        if not any(value == "unknown" for value in record_flat.values()):
            errors.append(
                f"{label}: archetype classification undetermined requires an "
                "unknown in the transmission block"
            )
        candidates = sorted(
            identifier
            for identifier, archetype_flat in archetypes.items()
            if _archetype_consistent(record_flat, archetype_flat)
        )
        if len(candidates) < 2:
            errors.append(
                f"{label}: archetype classification undetermined requires at least "
                f"two candidate archetypes; found "
                f"{len(candidates) if candidates else 'none'}"
                + (f" ({candidates[0]})" if candidates else "")
            )


def _collect_identities(
    record: dict[str, Any],
    label: str,
    claimed: dict[tuple[str, str, str], str],
    errors: list[str],
) -> None:
    """Records every exact key this record claims, and reports a second claimant."""
    record_id = record.get("record_id")
    own: set[tuple[str, str, str]] = set()
    for simulator in record.get("simulators", []) or []:
        if not isinstance(simulator, dict):
            continue
        sim_name = simulator.get("simulator")
        for identity in simulator.get("identities", []) or []:
            if not isinstance(identity, dict):
                continue
            kind = identity.get("kind")
            value = identity.get("value")
            if kind not in MATCHED_IDENTITY_KINDS or not isinstance(value, str):
                continue
            packages = identity.get("aero_packages")
            try:
                expansion = expand_identity(sim_name, value, packages)
            except ValueError:
                # Reported against the record by _validate_identities. Collision
                # detection skips it rather than crashing the whole run.
                continue
            for expanded in expansion:
                key = (sim_name, kind, expanded)
                owner = claimed.get(key)
                if owner is not None and owner != record_id:
                    errors.append(
                        f"{label}: exact identity {expanded!r} ({sim_name}, {kind}) "
                        f"is already claimed by {owner}"
                    )
                    continue
                # A record claiming its own key twice is redundant rather than
                # ambiguous, and the client tolerates it - which is precisely how
                # a half-finished migration would go unnoticed, with a declared
                # package and the hand-written spelling it replaced side by side.
                if key in own:
                    errors.append(
                        f"{label}: exact identity {expanded!r} ({sim_name}, {kind}) "
                        "is claimed twice by this record"
                    )
                    continue
                own.add(key)
                claimed[key] = record_id


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
            "control-archetype.schema.json",
        )
    }
    car_schema = schemas["car-record.schema.json"]
    transmission_schema = (
        {"$defs": car_schema["$defs"], "$ref": "#/$defs/transmission"}
        if isinstance(car_schema, dict) and "$defs" in car_schema
        else None
    )

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

    archetypes_path = data_dir / "archetypes.json"
    archetype_payload = _load(archetypes_path, errors)
    if archetype_payload is not None and schemas["control-archetype.schema.json"] is not None:
        errors.extend(
            validate_instance(
                archetype_payload,
                schemas["control-archetype.schema.json"],
                str(archetypes_path),
            )
        )
    archetypes = (
        _validate_archetype_registry(
            archetype_payload, str(archetypes_path), transmission_schema, errors
        )
        if archetype_payload is not None
        else {}
    )

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
    # Every exact key a match can resolve to, expansions included. The client
    # throws on a duplicate while loading the database, so a collision that only
    # surfaced there would be a validated dataset that will not open.
    claimed_identities: dict[tuple[str, str, str], str] = {}
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
        _validate_record_archetype(record, str(path), archetypes, errors)
        _collect_identities(record, str(path), claimed_identities, errors)
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
