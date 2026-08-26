from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any

from .schema_validation import validate_instance
from .validate import canonical_simulator


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
    # The schema states this as a conditional requirement, which the repository's
    # dependency-free validator does not implement, so it is enforced here as
    # well. Without the game's own name an `other` observation is anonymous: it
    # can never be grouped, and registering the simulator it came from could
    # never release it.
    if payload.get("simulator") == "other" and not str(
        payload.get("source_game_name") or ""
    ).strip():
        raise IntakeError(
            "an observation from an unregistered simulator must carry "
            "source_game_name, naming the game the telemetry client reported"
        )
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


def _normalise_tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.casefold()) if token}


def _curated_candidates(root: Path, observation: dict[str, Any]) -> list[dict[str, str]]:
    """Curated records this submission may be a second simulator's view of.

    A contributor cannot be expected to know a car is already curated from
    another simulator, and exact matching will never tell them: Assetto Corsa
    calls the Miura "Lamborghini Miura P400 SV" where the curated record's AMS2
    name is "Lamborghini Miura SV". Nothing matched, so the case was routed as a
    new identity and the existing record went unmentioned.

    This suggests, it does not decide. A candidate needs the record's
    manufacturer and every token of its model to appear in the submitted name,
    which is deliberately loose enough to propose a GT3 record for a GT3 Evo -
    the reviewer is expected to reject that. Nothing here is a match, and the
    client's exact matching is untouched: a shared name is not a shared car.
    """

    data_dir = root / "data" / "v1"
    index = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    simulator = observation["simulator"]
    submitted = _normalise_tokens(observation["identity"]["telemetry_name"])
    if not submitted:
        return []
    candidates: list[dict[str, str]] = []
    for relative in index["records"]:
        record = json.loads((data_dir / relative).read_text(encoding="utf-8"))
        covered = {entry["simulator"] for entry in record["simulators"]}
        if simulator in covered:
            # Already covered for this simulator: an exact match would have
            # found it, and its absence is a real answer rather than a gap.
            continue
        identity = record["identity"]
        manufacturer = _normalise_tokens(str(identity.get("manufacturer") or ""))
        model = _normalise_tokens(str(identity.get("model") or ""))
        if not manufacturer or not model:
            continue
        if manufacturer <= submitted and model <= submitted:
            candidates.append(
                {
                    "record_id": record["record_id"],
                    "display_name": identity.get("display_name"),
                    "covered_simulators": ",".join(sorted(covered)),
                    "basis": (
                        "The record's manufacturer and model both appear in the "
                        "submitted name. This is a suggestion for the reviewer, "
                        "not a match."
                    ),
                }
            )
    return candidates


def _release_registered_simulator(observation: dict[str, Any]) -> str | None:
    """Adopt the registered id for a drive the client filed as `other`.

    This is the half of the promise that was missing. `source_game_name` was
    kept so registering a game later would rename the drives waiting on it, and
    nothing performed the rename: the draft's `simulator` field is written by
    whichever client version took the drive and never changes afterwards, so
    re-running intake on a held observation held it again.

    The rename happens here instead, on the way in, from the name the client
    reported. The observation on disk is untouched; what changes is the id the
    case is filed under, which is what was blocking it.
    """
    if observation.get("simulator") != "other":
        return None
    return canonical_simulator(str(observation.get("source_game_name") or ""))


def _unregistered_simulator(observation: dict[str, Any]) -> dict[str, str] | None:
    """The game this drive came from, when the client did not recognise it.

    An observation whose simulator is `other` is real evidence about a real car,
    and there is nothing wrong with the drive. What is missing is the project's
    decision about the game: an id, whether its telemetry can settle a cut, what
    its source refs are called. Until that decision is made the observation is
    held rather than promoted, because `other` is a bucket and not an identity -
    two unrelated games promoted under it would be indistinguishable inside a
    record, and no source-naming prefix exists for either.

    The drive is not wasted. `source_game_name` preserves what the game called
    itself, so registering that simulator later renames these observations
    instead of asking a contributor to drive every car again.
    """
    if observation.get("simulator") != "other":
        return None
    return {
        "source_game_name": observation.get("source_game_name") or "unknown",
        "reason": (
            "This simulator is not registered, so the observation is held. "
            "Register it in the simulator enums and re-run intake to release "
            "the drives it is holding."
        ),
    }


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
    released = _release_registered_simulator(observation)

    stored = _stored_observations(inbox)
    for path, previous, previous_raw in stored:
        if hashlib.sha256(previous_raw).hexdigest() != digest:
            continue
        if released is not None:
            # The same bytes, and normally nothing to say about them. But this
            # copy was taken in when its simulator was unregistered, so the
            # receipt beside it holds a verdict the project has since overturned.
            # Resubmitting is exactly how a maintainer asks for that verdict
            # again, so it is answered rather than deflected as a duplicate.
            #
            # The stored copy is dropped rather than merely stepped over. It is
            # this submission, byte for byte, and leaving it in place made the
            # drive an "alternate representation" of itself: same observation id,
            # so the relationship check reported a second version of a drive
            # nobody had submitted twice.
            stored = [item for item in stored if item[0] != path]
            break
        return {
            "status": "exact-resubmission",
            "sha256": digest,
            "observation_id": observation["observation_id"],
            "existing_file": path.name,
            "stored": False,
        }

    if released is not None:
        # From here the observation is treated as the simulator it came from,
        # so it classifies against that simulator's curated records rather than
        # being held for a game the project now knows.
        observation = dict(observation, simulator=released)

    relationship, related = _relationship(observation, stored)
    curated_matches = _curated_matches(root, observation)
    curated_candidates = _curated_candidates(root, observation)
    already_reviewed = _already_reviewed(root, observation["observation_id"])
    unregistered = _unregistered_simulator(observation)
    if already_reviewed:
        classification = "already-reviewed-observation"
    elif unregistered:
        # Ahead of every identity classification. Which car this is stays an
        # open and interesting question, but it cannot be acted on until the
        # game it was driven in has an id.
        classification = "unregistered-simulator"
    elif relationship:
        classification = relationship
    elif curated_matches:
        classification = "curated-identity-comparison"
    elif curated_candidates:
        # Still research, and still the reviewer's decision - but the case now
        # carries the record it may belong to instead of starting from nothing.
        classification = "curated-identity-candidate"
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
        "curated_candidates": curated_candidates,
        "unregistered_simulator": unregistered,
        "released_simulator": released,
    }
    receipt_path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return receipt
