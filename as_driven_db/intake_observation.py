from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from .schema_validation import validate_instance


MAX_OBSERVATION_BYTES = 256 * 1024
UNKNOWN_VALUES = {None, "", "unknown", "not-tested"}


class IntakeError(ValueError):
    pass


def _read_observation(path: Path, root: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exception:
        raise IntakeError(f"could not read observation: {exception}") from exception
    if len(raw) > MAX_OBSERVATION_BYTES:
        raise IntakeError(
            f"observation is {len(raw):,} bytes; maximum is {MAX_OBSERVATION_BYTES:,}"
        )
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        schema = json.loads(
            (root / "schema" / "v1" / "verification-observation.schema.json")
            .read_text(encoding="utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exception:
        raise IntakeError(f"could not parse observation or schema: {exception}") from exception
    errors = validate_instance(payload, schema, str(path))
    if errors:
        raise IntakeError("schema validation failed:\n" + "\n".join(errors))
    if payload.get("review_status") != "draft":
        raise IntakeError("public intake accepts review_status 'draft' only")
    return payload, raw


def _stored_observations(inbox: Path) -> list[tuple[Path, dict[str, Any], bytes]]:
    stored: list[tuple[Path, dict[str, Any], bytes]] = []
    if not inbox.exists():
        return stored
    for path in sorted(inbox.glob("*.json")):
        if path.name.endswith(".receipt.json"):
            continue
        try:
            raw = path.read_bytes()
            payload = json.loads(raw.decode("utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and payload.get("observation_id"):
            stored.append((path, payload, raw))
    return stored


def _identity_key(observation: dict[str, Any]) -> tuple[str, str, str]:
    identity = observation["identity"]
    return (
        observation["simulator"],
        str(identity.get("internal_id") or ""),
        identity["telemetry_name"],
    )


def _same_reported_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_sim, left_internal, left_name = _identity_key(left)
    right_sim, right_internal, right_name = _identity_key(right)
    if left_sim != right_sim:
        return False
    if left_internal and right_internal:
        return left_internal == right_internal
    return left_name == right_name


def _fingerprint(observation: dict[str, Any]) -> tuple[str, str, str, str] | None:
    implementation = observation.get("implementation")
    if not isinstance(implementation, dict):
        return None
    fingerprint = implementation.get("fingerprint")
    if not isinstance(fingerprint, dict):
        return None
    return (
        str(implementation.get("content_id") or ""),
        str(fingerprint.get("scope") or ""),
        str(fingerprint.get("algorithm") or ""),
        str(fingerprint.get("digest") or ""),
    )


def _flatten_facts(observation: dict[str, Any]) -> dict[str, Any]:
    facts: dict[str, Any] = {}

    def visit(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                if key == "notes" or key.endswith("_method") or key == "actuation_basis":
                    continue
                visit(f"{prefix}/{key}", value[key])
        elif isinstance(value, list):
            established = sorted(item for item in value if item not in UNKNOWN_VALUES)
            if established:
                facts[prefix] = established
        elif value not in UNKNOWN_VALUES:
            facts[prefix] = value

    visit("/assists", observation.get("assists", {}))
    visit("/tests", observation.get("tests", {}))
    visit("/cockpit", observation.get("cockpit", {}))
    return facts


def _conflicts(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    left_facts = _flatten_facts(left)
    right_facts = _flatten_facts(right)
    return sorted(
        path
        for path in left_facts.keys() & right_facts.keys()
        if left_facts[path] != right_facts[path]
    )


def _relationship(
    observation: dict[str, Any],
    stored: list[tuple[Path, dict[str, Any], bytes]],
) -> tuple[str | None, list[dict[str, Any]]]:
    related: list[dict[str, Any]] = []
    strongest: str | None = None
    priority = {
        "alternate-representation": 7,
        "contradiction": 6,
        "changed-implementation": 5,
        "additional-implementation": 4,
        "versioned-observation": 3,
        "corroboration": 2,
        "related-identity": 1,
    }
    incoming_fp = _fingerprint(observation)
    for path, previous, _ in stored:
        if previous.get("observation_id") == observation.get("observation_id"):
            relation = "alternate-representation"
            conflicts = _conflicts(observation, previous)
        elif not _same_reported_identity(observation, previous):
            continue
        else:
            previous_fp = _fingerprint(previous)
            conflicts = _conflicts(observation, previous)
            if incoming_fp and previous_fp and incoming_fp[0] == previous_fp[0] and incoming_fp != previous_fp:
                relation = "changed-implementation"
            elif incoming_fp and previous_fp and incoming_fp[0] != previous_fp[0]:
                relation = "additional-implementation"
            elif incoming_fp != previous_fp and (incoming_fp is None or previous_fp is None):
                relation = "related-identity"
            elif observation["game_version"] != previous["game_version"]:
                relation = "versioned-observation"
            elif conflicts:
                relation = "contradiction"
            else:
                relation = "corroboration"
        related.append(
            {
                "stored_file": path.name,
                "observation_id": previous.get("observation_id"),
                "relationship": relation,
                "conflicting_paths": conflicts,
            }
        )
        if strongest is None or priority[relation] > priority[strongest]:
            strongest = relation
    return strongest, related


def _curated_matches(root: Path, observation: dict[str, Any]) -> list[dict[str, str]]:
    data_dir = root / "data" / "v1"
    index = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    simulator = observation["simulator"]
    identity = observation["identity"]
    submitted = {("telemetry-name", identity["telemetry_name"])}
    if identity.get("internal_id"):
        submitted.add(("internal-id", identity["internal_id"]))
    matches: list[dict[str, str]] = []
    for relative in index["records"]:
        record = json.loads((data_dir / relative).read_text(encoding="utf-8"))
        for simulator_entry in record["simulators"]:
            if simulator_entry["simulator"] != simulator:
                continue
            identities = {
                (item["kind"], item["value"])
                for item in simulator_entry["identities"]
                if item["kind"] in {"telemetry-name", "internal-id"}
            }
            for kind, value in sorted(submitted & identities):
                matches.append(
                    {
                        "record_id": record["record_id"],
                        "kind": kind,
                        "value": value,
                    }
                )
    return matches


def _already_reviewed(root: Path, observation_id: str) -> bool:
    sources = json.loads(
        (root / "data" / "v1" / "sources.json").read_text(encoding="utf-8")
    )
    return any(observation_id in json.dumps(source) for source in sources["sources"])


def intake_observation(root: Path, input_path: Path, inbox: Path) -> dict[str, Any]:
    root = root.resolve()
    input_path = input_path.resolve()
    inbox = inbox.resolve()
    observation, raw = _read_observation(input_path, root)
    digest = hashlib.sha256(raw).hexdigest()
    stored = _stored_observations(inbox)
    for path, previous, previous_raw in stored:
        if hashlib.sha256(previous_raw).hexdigest() == digest:
            return {
                "status": "exact-resubmission",
                "sha256": digest,
                "observation_id": observation["observation_id"],
                "existing_file": path.name,
                "stored": False,
            }

    relationship, related = _relationship(observation, stored)
    curated_matches = _curated_matches(root, observation)
    already_reviewed = _already_reviewed(root, observation["observation_id"])
    if already_reviewed:
        classification = "already-reviewed-observation"
    elif relationship:
        classification = relationship
    elif curated_matches:
        classification = "curated-identity-comparison"
    else:
        classification = "new-identity"

    inbox.mkdir(parents=True, exist_ok=True)
    stem = f"{observation['observation_id']}--{digest[:12]}"
    stored_path = inbox / f"{stem}.json"
    receipt_path = inbox / f"{stem}.receipt.json"
    shutil.copyfile(input_path, stored_path)
    receipt = {
        "status": classification,
        "sha256": digest,
        "observation_id": observation["observation_id"],
        "received_at": datetime.now(timezone.utc).isoformat(),
        "stored": True,
        "stored_file": stored_path.name,
        "dataset_version": observation.get("dataset_version"),
        "identity": observation["identity"],
        "implementation": observation.get("implementation"),
        "related_submissions": related,
        "curated_matches": curated_matches,
    }
    receipt_path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return receipt
