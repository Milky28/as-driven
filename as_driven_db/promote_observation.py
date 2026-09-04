"""Promote staged guided-verification bundles into curated records.

`import-observation` stages a bundle from a guided drive; it deliberately leaves
real-world identity as ``REVIEW-REQUIRED`` because a drive cannot establish it.
This module applies the reviewer's decisions from an explicit review manifest and
writes the curated record, its curation approval, the evidence sources, and the
dataset index together, so a promotion is reproducible instead of hand-made.

A second implementation in the same simulator may join an existing entry only
when a reviewer explicitly marks it compatible and its effective behavior is
identical. That covers a mod which reuses a Kunos model without pretending a
different package is a different real car; a behavioral difference still stops
for a representation decision. A later drive may replace an incorrect entry only
through an explicit correction that names the evidence it supersedes, enumerates
every behavior change, and preserves the before/after history in the approval.

It refuses to promote anything still marked ``REVIEW-REQUIRED``, refuses to
overwrite a curated record, and requires every cited source to be registered.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .importers.observation import REVIEW, derive_approved_controls
from .validate import ID_RE


OPTIONAL_TRANSMISSION_FIELDS = {"first_gear_position"}


def _required(entry: dict[str, Any], name: str, label: str) -> Any:
    value = entry.get(name)
    if value is None or value == "" or value == REVIEW:
        raise ValueError(f"{label}: {name!r} is required for promotion")
    return value


def _contains_review_marker(value: Any) -> bool:
    if isinstance(value, str):
        return REVIEW in value
    if isinstance(value, dict):
        return any(_contains_review_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_review_marker(item) for item in value)
    return False


def _source_id_token(value: str) -> str:
    """Make an exact version label safe as the final source-id component."""
    token = "".join(
        character if character.isalnum() else "-"
        for character in value.strip().casefold()
    )
    while "--" in token:
        token = token.replace("--", "-")
    return token.strip("-") or "unknown"


def _apply_game_version_correction(
    bundle: dict[str, Any], entry: dict[str, Any]
) -> dict[str, Any]:
    """Apply a reviewed exact-build correction without rewriting the draft.

    Some simulators expose no useful executable version to SimHub. The original
    observation remains immutable and says ``unknown``; the checked-in approval
    records how the reviewer tied that drive to an exact installed build. Keeping
    the correction structured makes the evidence boundary visible and prevents a
    prose edit from silently changing the version used by the curated record.
    """
    correction = entry.get("game_version_correction")
    if correction is None:
        return bundle
    label = f"review entry {entry.get('record_id') or bundle['record']['record_id']}"
    if not isinstance(correction, dict) or not correction:
        raise ValueError(f"{label}: game_version_correction must be a non-empty object")
    observed = _required(correction, "observed", f"{label} game version correction")
    verified = _required(correction, "verified", f"{label} game version correction")
    basis = _required(correction, "basis", f"{label} game version correction")
    simulator = bundle["record"]["simulators"][0]
    current = simulator["verified_game_version"]
    if observed != current:
        raise ValueError(
            f"{label}: game_version_correction.observed is {observed!r}, but the "
            f"bundle recorded {current!r}"
        )
    if str(current).strip().casefold() != "unknown":
        raise ValueError(
            f"{label}: game_version_correction is only for a bundle that recorded "
            f"'unknown'; this bundle already records {current!r}"
        )
    if str(verified).strip().casefold() in ("", "unknown", "latest"):
        raise ValueError(
            f"{label}: game_version_correction.verified must name an exact build, "
            f"not {verified!r}"
        )
    if not all(part.isdigit() for part in str(verified).split(".")):
        raise ValueError(
            f"{label}: game_version_correction.verified must use the live-source "
            f"version form (digits, optionally dot-separated), got {verified!r}. Put "
            "labels such as 'Steam build' in the correction basis."
        )

    corrected = json.loads(json.dumps(bundle))
    simulator = corrected["record"]["simulators"][0]
    source = corrected["source"]
    old_source_id = source["source_id"]
    prefix = old_source_id.rsplit(".", 1)[0]
    new_source_id = f"{prefix}.{_source_id_token(str(verified))}"

    simulator["verified_game_version"] = verified
    simulator["source_refs"] = [
        new_source_id if ref == old_source_id else ref
        for ref in simulator.get("source_refs", [])
    ]
    for note_index, note in enumerate(simulator.get("behavior", {}).get("notes", [])):
        simulator["behavior"]["notes"][note_index] = note.replace(
            f" {current} via", f" {verified} via"
        )
    for claim in corrected["record"].get("provenance", {}).get("claims", []):
        claim["source_refs"] = [
            new_source_id if ref == old_source_id else ref
            for ref in claim.get("source_refs", [])
        ]
    corrected["approval"]["observed_game_version"] = verified
    corrected["approval"]["historical_notes"] = (
        f"The draft recorded game version {observed!r}. During review it was tied "
        f"to {verified!r}: {basis}"
    )
    source["source_id"] = new_source_id
    source["notes"] = source["notes"].replace(
        f"; {corrected['simulator'].upper()} {current}.",
        f"; {corrected['simulator'].upper()} {verified}.",
    )
    source["notes"] += (
        f" The draft recorded game version {observed!r}; review established "
        f"{verified!r}: {basis}"
    )
    corrected["version_review"] = {
        "observed": observed,
        "verified": verified,
        "basis": basis,
    }
    return corrected


def _apply_entry_game_version_correction(
    entry: dict[str, Any], old_source_id: str, new_source_id: str
) -> dict[str, Any]:
    """Keep manifest-authored overrides aligned with a corrected live source."""
    correction = entry.get("game_version_correction")
    if correction is None:
        return entry
    corrected = json.loads(json.dumps(entry))
    observed = str(correction["observed"])
    verified = str(correction["verified"])
    for override in corrected.get("simulator_overrides") or []:
        override["source_refs"] = [
            new_source_id if ref == old_source_id else ref
            for ref in override.get("source_refs", [])
        ]
        condition = str(override.get("condition") or "")
        override["condition"] = condition.replace(
            f"simulator version {observed}", f"simulator version {verified}"
        )
    corrected["control_notes"] = [
        str(note).replace(f" {observed} behavior", f" {verified} behavior")
        for note in corrected.get("control_notes") or []
    ]
    corrected["live_source_notes"] = str(
        corrected.get("live_source_notes") or ""
    ).replace(f" {observed}.", f" {verified}.")
    return corrected


def build_promoted_record(
    bundle: dict[str, Any], entry: dict[str, Any], *, approved_at: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return the (record, approval, source) a reviewed bundle promotes to."""
    record = json.loads(json.dumps(bundle["record"]))
    approval = json.loads(json.dumps(bundle["approval"]))
    source = json.loads(json.dumps(bundle["source"]))
    record_id = record["record_id"]
    label = f"review entry {record_id}"

    if entry.get("record_id") != record_id:
        raise ValueError(
            f"{label}: review record_id {entry.get('record_id')!r} does not match "
            f"bundle record {record_id!r}"
        )

    simulator = record["simulators"][0]
    if simulator.get("simulator") == "other":
        # The last gate, and the one that does not depend on any interface
        # having offered the right buttons. `other` means the client did not
        # recognise the game: promoting under it would put two unrelated
        # simulators in one namespace inside records, and there is no prefix to
        # name its sources with. The drive is kept and released when the game is
        # registered; see docs/simulator-coverage.md.
        raise ValueError(
            f"{label}: this drive came from a simulator the project has not "
            f"registered, reported by the client as "
            f"{bundle.get('source_game_name') or 'a game it did not name'!r}. "
            "Register the simulator before promoting it."
        )
    live_source_id = source["source_id"]
    real_world_refs = list(_required(entry, "real_world_source_refs", label))
    if not real_world_refs:
        raise ValueError(f"{label}: at least one real-world source ref is required")
    all_refs = real_world_refs + [live_source_id]

    # Reviewer-supplied real-world identity. The drive cannot establish these.
    # The staged class is the simulator's class token. A real category is a
    # human judgement - AMS2's TC60S is called Vintage Cars Tier 1 in game, and
    # nothing in the draft says so - and the client draws it onto the overlay.
    record["identity"]["class"] = _required(entry, "class", label)
    record["identity"]["manufacturer"] = _required(entry, "manufacturer", label)
    record["identity"]["model"] = _required(entry, "model", label)
    record["identity"]["year"] = _required(entry, "year", label)
    if entry.get("display_name"):
        record["identity"]["display_name"] = entry["display_name"].strip()
    record["identity"]["real_world_identity_notes"] = _required(
        entry, "real_world_identity_notes", label
    )
    if entry.get("variant"):
        record["identity"]["variant"] = entry["variant"]

    # Optional reviewer corrections to controls the drive could not classify
    # (for example a gearbox construction supported by a real-world source).
    for name, value in (entry.get("control_overrides") or {}).items():
        if name == "wheel_rim":
            if not isinstance(value, dict) or not value:
                raise ValueError(f"{label}: wheel_rim control override must be an object")
            wheel = record["authentic_controls"]["steering"]["wheel_rim"]
            unknown = sorted(set(value) - set(wheel))
            if unknown:
                raise ValueError(f"{label}: unknown wheel_rim field(s) {unknown!r}")
            wheel.update(value)
            continue
        if (
            name not in record["authentic_controls"]["transmission"]
            and name not in OPTIONAL_TRANSMISSION_FIELDS
        ):
            raise ValueError(f"{label}: unknown transmission field {name!r}")
        record["authentic_controls"]["transmission"][name] = value
        if name == "shift_actuation":
            # Simulator behavior restates the reviewed primary mechanism. The
            # game accepts arbitrary bindings, so this field comes from cockpit
            # inspection and a reviewer may correct an accidental form choice.
            simulator["behavior"]["shift_type"] = value

    # Explicit aero or configuration aliases become exact record identities.
    aliases = entry.get("additional_telemetry_names") or []
    identities = [
        item for item in simulator["identities"] if item["kind"] != "class-id"
    ]
    class_identities = [
        item for item in simulator["identities"] if item["kind"] == "class-id"
    ]
    for alias in aliases:
        value = _required(alias, "value", f"{label} alias")
        _required(alias, "basis", f"{label} alias")
        identities.append({"kind": "telemetry-name", "value": value})
    simulator["identities"] = identities + class_identities

    # An explicit, sourced deviation where the simulator differs from the real
    # car. The record keeps the real value and the client applies the override
    # when it builds guidance, so both layers stay true.
    for override in entry.get("simulator_overrides") or []:
        for field in ("path", "value", "condition", "confidence"):
            if field not in override:
                raise ValueError(f"{label}: override is missing {field!r}")
        if not str(override["path"]).startswith("/authentic_controls/"):
            raise ValueError(
                f"{label}: override path must point into /authentic_controls/, "
                f"got {override['path']!r}"
            )
        override.setdefault("source_refs", [live_source_id])
    simulator["overrides"] = list(entry.get("simulator_overrides") or [])
    if any(
        override.get("path")
        == "/authentic_controls/transmission/shift_actuation"
        for override in simulator["overrides"]
    ):
        _synchronize_behavior_shift_type(record, simulator)

    confidence = _required(entry, "confidence", label)
    simulator["source_refs"] = all_refs
    simulator["confidence"] = {
        "level": confidence,
        "basis": _required(entry, "confidence_basis", label),
    }

    record["provenance"] = {
        "claims": [
            {
                "paths": ["/identity", "/simulators/0/identities"],
                "source_refs": all_refs,
                "confidence": confidence,
                "basis": _required(entry, "identity_basis", label),
            },
            {
                "paths": [
                    "/authentic_controls/transmission/forward_gears",
                    "/authentic_controls/transmission/gearbox_type",
                    "/authentic_controls/transmission/shift_actuation",
                    "/authentic_controls/transmission/shift_pattern",
                ],
                "source_refs": all_refs,
                "confidence": confidence,
                "basis": _required(entry, "specification_basis", label),
            },
            {
                "paths": [
                    "/authentic_controls/transmission/upshift",
                    "/authentic_controls/transmission/downshift",
                    "/authentic_controls/transmission/standing_start_clutch",
                    "/authentic_controls/steering/wheel_rim",
                    "/simulators/0/behavior",
                ],
                "source_refs": [live_source_id],
                "confidence": confidence,
                "basis": (
                    "Directly observed during the guided drive: move-off, shift "
                    "clutch use, automatic cut and blip, and the cockpit rim."
                ),
            },
        ]
    }
    # Where research established a real-car control from a source, that path
    # gets its own claim naming the source. The bundled claim above is the
    # drive's, and it covers whole objects, so without this a manufacturer
    # manual's finding was filed under "directly observed during the guided
    # drive" - which on the Radical SR3 meant the record cited a drive that had
    # observed the opposite of the value it was supporting.
    sourced_paths = [
        path for path in (entry.get("sourced_control_paths") or [])
        if str(path).startswith("/authentic_controls/")
    ]
    if sourced_paths and real_world_refs:
        record["provenance"]["claims"].append({
            "paths": sorted(sourced_paths),
            "source_refs": real_world_refs,
            "confidence": confidence,
            "basis": _required(entry, "specification_basis", label),
        })
    for claim in entry.get("additional_claims") or []:
        record["provenance"]["claims"].append(claim)

    record["authentic_controls"]["notes"] = list(
        entry.get("control_notes")
        or [
            "Simulator behavior was directly observed in a guided drive with "
            "automatic clutch and shifting disabled.",
        ]
    )
    # The one line the overlay shows the driver. Optional: a car whose Fit and
    # Use rows already say everything shows no note panel at all.
    driver_summary = entry.get("driver_summary")
    if driver_summary:
        record["driver_summary"] = driver_summary.strip()
    else:
        record.pop("driver_summary", None)

    record["notes"] = list(entry.get("record_notes") or [])
    if not record["notes"]:
        record.pop("notes")
    if entry.get("archetype"):
        record["archetype"] = entry["archetype"]
    record["updated_at"] = approved_at

    # The approval must agree with the record under validate's own mapping.
    approval["approved_controls"] = derive_approved_controls(record)
    approval["approved_at"] = approved_at
    approval["confidence_notes"] = _required(entry, "confidence_notes", label)
    if aliases:
        approval["additional_telemetry_names"] = aliases
    elif "additional_telemetry_names" in approval:
        del approval["additional_telemetry_names"]
    if entry.get("scope_notes"):
        approval["scope_notes"] = entry["scope_notes"]
    if entry.get("game_version_correction"):
        approval["game_version_correction"] = entry["game_version_correction"]

    source["url"] = _required(entry, "live_source_url", label)
    if entry.get("live_source_notes"):
        # Safe to replace outright: the implementation fingerprint is a field on
        # the source, not a sentence in this note. It used to be rescued from the
        # prose, which failed the moment a reviewer wrote the marker phrase
        # without the digest.
        source["notes"] = entry["live_source_notes"]
    correction = entry.get("game_version_correction")
    if correction:
        source["notes"] += (
            f" The draft recorded game version {correction['observed']!r}; review "
            f"established {correction['verified']!r}: {correction['basis']}"
        )

    for name, payload in (("record", record), ("approval", approval), ("source", source)):
        if _contains_review_marker(payload):
            raise ValueError(
                f"{label}: promoted {name} still contains {REVIEW}; complete the review first"
            )
    return record, approval, source


CLASS_NAMES = "simulator-class-names.json"


def resolve_class(entry: dict[str, Any], bundle: dict[str, Any], curation_directory: Path) -> str:
    """The real category for a promotion, without asking the driver for it.

    A class name is a property of the class, not of each car in it, and it is
    awkward to read from inside a running session - the driver would have to
    leave for the car-select screen, once per car, in whatever wording that
    simulator uses. So it is recorded once per class in
    ``curation/simulator-class-names.json`` and every later car in that class
    inherits it.

    A review entry may still name the class itself, which wins: an AMS2 formula
    class holds a real Grand Prix car beside Reiza's fictional ones, and the
    real car belongs to Formula One rather than to Reiza's category.
    """
    if entry.get("class"):
        return entry["class"]

    simulator_entry = bundle["record"]["simulators"][0]
    simulator = simulator_entry["simulator"]
    class_ids = [
        item["value"] for item in simulator_entry["identities"]
        if item["kind"] == "class-id"
    ]
    path = curation_directory / CLASS_NAMES
    known = {}
    if path.exists():
        for row in json.loads(path.read_text(encoding="utf-8"))["classes"]:
            known[(row["simulator"], row["class_id"])] = row["name"]
    for class_id in class_ids:
        name = known.get((simulator, class_id))
        if name:
            return name
    if not class_ids:
        # Not every simulator groups its cars. Assetto Corsa EVO reports an empty
        # class through SimHub, so there is no token to key a name on and the
        # class-names file cannot help - pointing the reviewer at it would send
        # them looking for something that does not exist.
        raise ValueError(
            f"review entry {bundle['record']['record_id']}: {simulator} reports no class "
            "for this car, so there is nothing to look up. Set 'class' on this entry to "
            "the category the car actually raced in - it is identity context for a real "
            f"car, not a simulator token, so curation/{CLASS_NAMES} does not apply."
        )
    raise ValueError(
        f"review entry {bundle['record']['record_id']}: no class name for "
        f"{simulator} {class_ids!r}. Add it once to curation/{CLASS_NAMES} - it is "
        "the name the simulator shows on its car-select screen - or set 'class' on "
        "this entry. The staged value is the simulator's own class token and must "
        "not reach a curated record."
    )


# Prose, not evidence. Two drives of the same car never word these the same, so
# comparing them made `steering.wheel_rim` report a disagreement on every merge
# regardless of the values inside it.
_PROSE_FIELDS = {"notes", "source_label"}


def _established(value: Any) -> bool:
    """Whether a value says anything. Absent, null and `unknown` do not."""
    return value is not None and value != "unknown"


def _classify_differences(
    existing: dict[str, Any], incoming: dict[str, Any]
) -> tuple[list[str], dict[str, Any]]:
    """Sort a second drive's differences into the ones that matter and the rest.

    Comparing whole sub-objects lumped three unrelated situations together and
    blocked on all of them, which mattered more than it sounds: faced with a wall
    of false alarms, the quickest way through is to "correct the record
    deliberately", and that is exactly how a second simulator ends up rewriting
    the real car. The rule survives by making the false alarms stop.

    - **Conflict**: both drives established a value and they differ. Only this
      blocks. One game is wrong, or the record is, and a person decides which.
    - **Gap filled**: the record says `unknown` and the drive established a
      value. Returned separately so the reviewer opts in per field rather than
      having a second simulator quietly write into the real car.
    - **Less informed**: the drive did not establish what the record already
      knows. Ignored - the curated value stands.
    """
    conflicts: list[str] = []
    fills: dict[str, Any] = {}
    for section in ("transmission", "steering"):
        left = existing.get(section) or {}
        right = incoming.get(section) or {}
        for field in sorted(set(left) | set(right)):
            if field in _PROSE_FIELDS:
                continue
            here, there = left.get(field), right.get(field)
            if isinstance(here, dict) or isinstance(there, dict):
                for leaf in sorted(set(here or {}) | set(there or {})):
                    if leaf in _PROSE_FIELDS:
                        continue
                    _sort_one(
                        f"/authentic_controls/{section}/{field}/{leaf}",
                        (here or {}).get(leaf),
                        (there or {}).get(leaf),
                        conflicts,
                        fills,
                    )
                continue
            _sort_one(
                f"/authentic_controls/{section}/{field}", here, there, conflicts, fills
            )
    return conflicts, fills


def _sort_one(
    pointer: str,
    here: Any,
    there: Any,
    conflicts: list[str],
    fills: dict[str, Any],
) -> None:
    if here == there:
        return
    if _established(here) and _established(there):
        conflicts.append(f"{pointer} ({here!r} vs {there!r})")
    elif _established(there):
        fills[pointer] = there


def _require_deliberate_creation(
    entry: dict[str, Any], derived_id: str, target_id: str
) -> None:
    """Allow a new record under a name the bundle did not derive, deliberately.

    A record id names the real car. A bundle derives one by slugging the name the
    simulator reports, which approximates the car for official content and does
    not for a mod: the first Assetto Corsa drive here derived
    `acl-gtr-porsche-911-rsr-1973` from a package by AC Legends, and promoting a
    real Porsche under that id would put a mod pack's initials permanently into a
    simulator-independent database.

    So a reviewer may name the real car instead - but must say that is what they
    are doing, and repeat the staged id back. Repeating it proves they saw the
    bundle this entry actually points at rather than a stale one, and it is the
    difference between a considered rename and a typo, which is the only reason
    this path is guarded at all.
    """
    has_creation = "create_new_record" in entry
    creation = entry.get("create_new_record")
    if not isinstance(creation, dict) or not creation:
        raise ValueError(
            f"review entry {target_id!r}: the bundle is for {derived_id!r} and no curated "
            f"record {target_id!r} exists to merge into. To add this drive to a car "
            "already curated, name that record's id. To promote a new car under a name "
            "the simulator did not supply - which is the ordinary case for a mod - say so "
            "with a 'create_new_record' block naming 'staged_record_id' and a 'basis'."
        )
    staged = creation.get("staged_record_id")
    if staged != derived_id:
        raise ValueError(
            f"review entry {target_id!r}: create_new_record.staged_record_id is "
            f"{staged!r} but this bundle derived {derived_id!r}. The staged id is repeated "
            "back to show which bundle is being renamed; a mismatch means the entry and "
            "the bundle have drifted apart."
        )
    if not str(creation.get("basis") or "").strip():
        raise ValueError(
            f"review entry {target_id!r}: create_new_record.basis is required. Renaming a "
            "record away from what the simulator called the car is an identity claim, and "
            "it needs a reason recorded beside it."
        )
    if not str(entry.get("display_name") or "").strip():
        raise ValueError(
            f"review entry {target_id!r}: display_name is required when creating a "
            "record under a different id. The simulator supplied a package name, and "
            "that package name must not become the real car's driver-facing name."
        )


def _redirect_to_existing_record(
    bundle: dict[str, Any], entry: dict[str, Any], data_directory: Path
) -> dict[str, Any]:
    """Point a drive at the curated record for the same real car.

    A bundle's record id is slugged from the telemetry name, so two simulators
    agree on it only when they spell the car the same way. They usually do not:
    Assetto Corsa EVO calls the Huracan one-make car "Lamborghini Huracan ST
    EVO2" where AMS2 calls it "Lamborghini Huracan Super Trofeo EVO2", which
    slug to different ids for the same real car.

    Left alone that forks a second record, which is the one outcome the
    cross-simulator design exists to prevent - and it forks silently, because
    both records are individually valid. So a review entry may name a different
    record id from the bundle's, meaning "this drive belongs to that car".

    It redirects onto a record that already exists without further ceremony. A
    name matching nothing is an error unless the entry says, in as many words,
    that a new record is meant - see `_require_deliberate_creation`. A typo must
    not quietly mint a record whose id has no relation to any real car.
    """
    derived_id = bundle["record"]["record_id"]
    target_id = entry.get("record_id")
    has_creation = "create_new_record" in entry
    creation = entry.get("create_new_record")
    if not target_id or target_id == derived_id:
        if has_creation:
            raise ValueError(
                f"review entry {derived_id!r}: create_new_record is set but the entry "
                "names the id the bundle already derived, so nothing is being renamed. "
                "Remove it, or name the real car this record should be created as."
            )
        return bundle
    # Validated before it reaches the filesystem: a record id is a name, and a
    # reviewer's typo must not be able to address a path outside the car
    # directory or leave a half-written promotion for a later check to find.
    if not ID_RE.fullmatch(str(target_id)):
        raise ValueError(
            f"review entry {target_id!r}: record_id is not a valid id. Expected lowercase "
            "words joined by '-', '_' or '.', which is what every curated record uses."
        )
    if (data_directory / "cars" / f"{target_id}.json").exists():
        if has_creation:
            raise ValueError(
                f"review entry {target_id!r}: create_new_record is set but a curated "
                f"record {target_id!r} already exists, so this drive joins it rather than "
                "creating anything. Remove the block; merging is not a rename."
            )
    else:
        _require_deliberate_creation(entry, derived_id, target_id)
    bundle = json.loads(json.dumps(bundle))
    bundle["record"]["record_id"] = target_id
    if "record_id" in bundle.get("approval", {}):
        bundle["approval"]["record_id"] = target_id
        # Keep what it was renamed from, in the approval that authorised it.
        # Only where this promotion creates the record: a merge onto an existing
        # car is not a rename, and that record's own id is already the audited one.
        if has_creation:
            bundle["approval"]["staged_record_id"] = derived_id
    return bundle


def merge_simulator_entry(
    existing: dict[str, Any],
    incoming: dict[str, Any],
    *,
    label: str,
    accept_from_drive: list[str] | None = None,
    authentic_control_corrections: list[dict[str, Any]] | None = None,
    compatible_implementation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a simulator's entry to the curated record for the same real car.

    The existing record owns the real car. A second simulator contributes its
    own entry and the claims that describe it, and never rewrites identity or
    `authentic_controls` behind the reviewer's back. If the new drive disagrees
    about the real car, that is either a correction to make deliberately or a
    deviation to record as an override, so it stops here instead.
    """
    entry = json.loads(json.dumps(incoming["simulators"][0]))
    simulator_id = entry["simulator"]
    covered = [item.get("simulator") for item in existing.get("simulators", [])]
    same_simulator = simulator_id in covered
    if same_simulator and compatible_implementation is None:
        raise FileExistsError(
            f"{label}: {simulator_id} already has an entry on this record; "
            "promoting would replace curated evidence"
        )
    if compatible_implementation is not None:
        if not same_simulator:
            raise ValueError(
                f"{label}: compatible_implementation is set but {simulator_id} has "
                "no existing entry. Remove it; an ordinary cross-simulator merge "
                "does not share an implementation."
            )
        if not isinstance(compatible_implementation, dict) or not str(
            compatible_implementation.get("basis") or ""
        ).strip():
            raise ValueError(
                f"{label}: compatible_implementation.basis is required. Two packages "
                "may share one simulator entry only after review establishes why their "
                "effective controls are the same."
            )

    corrections = list(authentic_control_corrections or [])
    if corrections and same_simulator:
        raise ValueError(
            f"{label}: top-level authentic_control_corrections are only for a "
            "different simulator whose independent real-car research corrects the "
            "shared baseline. Put a same-simulator correction under "
            "correct_existing_simulator instead."
        )
    merged = json.loads(json.dumps(existing))
    seen_corrections: set[str] = set()
    for change in corrections:
        if not isinstance(change, dict):
            raise ValueError(f"{label}: authentic control correction must be an object")
        for field in ("path", "from", "to", "basis", "source_refs", "confidence"):
            if field not in change:
                raise ValueError(
                    f"{label}: authentic control correction is missing {field!r}"
                )
        path = change["path"]
        if not str(path).startswith("/authentic_controls/"):
            raise ValueError(
                f"{label}: authentic control correction path must start with "
                f"'/authentic_controls/', got {path!r}"
            )
        if path in seen_corrections:
            raise ValueError(f"{label}: duplicate authentic control correction for {path}")
        seen_corrections.add(path)
        if change["from"] == change["to"]:
            raise ValueError(f"{label}: authentic control correction {path} changes nothing")
        if not str(change["basis"] or "").strip():
            raise ValueError(f"{label}: authentic control correction {path} has no basis")
        refs = change["source_refs"]
        if not isinstance(refs, list) or not refs or not all(
            isinstance(ref, str) and ref.strip() for ref in refs
        ):
            raise ValueError(
                f"{label}: authentic control correction {path} needs source_refs"
            )
        try:
            current = _pointer_get(merged, path)
            reviewed = _pointer_get(incoming, path)
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ValueError(
                f"{label}: authentic control correction path does not exist: {path}"
            ) from exc
        if current != change["from"]:
            raise ValueError(
                f"{label}: authentic control correction {path} expected the curated "
                f"value {change['from']!r}, but found {current!r}"
            )
        if reviewed != change["to"]:
            raise ValueError(
                f"{label}: authentic control correction {path} says the reviewed value "
                f"is {change['to']!r}, but the incoming researched record says {reviewed!r}"
            )
        supported_refs = {
            ref
            for claim in incoming.get("provenance", {}).get("claims", [])
            if path in claim.get("paths", [])
            for ref in claim.get("source_refs", [])
        }
        unsupported = sorted(set(refs) - supported_refs)
        if unsupported:
            raise ValueError(
                f"{label}: authentic control correction {path} cites source(s) that do "
                f"not support that reviewed path: {unsupported!r}"
            )
        _pointer_set(merged, path, change["to"])
        merged["provenance"]["claims"].append(
            {
                "paths": [path],
                "source_refs": list(dict.fromkeys(refs)),
                "confidence": change["confidence"],
                "basis": change["basis"].strip(),
            }
        )

    conflicts, fills = _classify_differences(
        merged["authentic_controls"], incoming["authentic_controls"]
    )
    if conflicts:
        raise ValueError(
            f"{label}: the {simulator_id} drive contradicts the curated real car at "
            + "; ".join(conflicts)
            + ". Both established a value and they differ, so one of them is wrong. "
            "Record a simulator override for a genuine deviation, or correct the record "
            "deliberately; a second simulator never rewrites the real car."
        )

    accepted = list(accept_from_drive or [])
    unclaimed = sorted(pointer for pointer in fills if pointer not in accepted)
    if unclaimed:
        raise ValueError(
            f"{label}: the {simulator_id} drive establishes "
            + "; ".join(f"{pointer} ({fills[pointer]!r})" for pointer in unclaimed)
            + ", which the record leaves unknown. This fills a gap rather than "
            "contradicting anything, but a second simulator does not write to the real "
            "car unasked: list the pointer(s) under 'accept_from_drive' on this review "
            "entry to take the value, or leave the field unknown."
        )
    stale = [pointer for pointer in accepted if pointer not in fills]
    if stale:
        raise ValueError(
            f"{label}: 'accept_from_drive' names {stale!r}, which this drive does not "
            "fill. The record may already have a value there, or the drive may not have "
            "established one; either way the acceptance would do nothing and is more "
            "likely a mistake than an intention."
        )

    for pointer, value in fills.items():
        target = merged
        parts = pointer.strip("/").split("/")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    accepted_set = set(accepted)
    for claim in incoming.get("provenance", {}).get("claims", []):
        paths = [path for path in claim.get("paths", []) if path in accepted_set]
        if paths:
            merged["provenance"]["claims"].append(dict(claim, paths=paths))
    _synchronize_behavior_shift_type(merged, entry)
    if same_simulator:
        position = covered.index(simulator_id)
        current = merged["simulators"][position]
        if _simulator_behavior_signature(current) != _simulator_behavior_signature(entry):
            raise ValueError(
                f"{label}: the second {simulator_id} implementation does not have the "
                "same effective behavior and overrides as the curated entry. It cannot "
                "be represented as a compatible identity; model the implementation "
                "difference explicitly before promoting it."
            )
        known_identities = {
            json.dumps(identity, sort_keys=True) for identity in current["identities"]
        }
        for identity in entry["identities"]:
            key = json.dumps(identity, sort_keys=True)
            if key not in known_identities:
                current["identities"].append(identity)
                known_identities.add(key)
        current["source_refs"] = list(dict.fromkeys(
            current.get("source_refs", []) + entry.get("source_refs", [])
        ))
        current_notes = current.get("behavior", {}).setdefault("notes", [])
        for note in entry.get("behavior", {}).get("notes", []):
            if note not in current_notes:
                current_notes.append(note)
        incoming_overrides = {
            (item["path"], json.dumps(item["value"], sort_keys=True)): item
            for item in entry.get("overrides", [])
        }
        for override in current.get("overrides", []):
            incoming_override = incoming_overrides.get(
                (override["path"], json.dumps(override["value"], sort_keys=True))
            )
            if incoming_override is not None:
                override["source_refs"] = list(dict.fromkeys(
                    override.get("source_refs", [])
                    + incoming_override.get("source_refs", [])
                ))
    else:
        position = len(merged["simulators"])
        merged["simulators"].append(entry)

    # Claims arrive pointing at /simulators/0 because the bundle held one entry.
    # Only the simulator-scoped ones carry over: the real car's claims already
    # stand on the existing record, and duplicating them would double-count the
    # evidence behind a value.
    for claim in incoming["provenance"]["claims"]:
        paths = [
            path.replace("/simulators/0", f"/simulators/{position}")
            for path in claim["paths"]
            if path.startswith("/simulators/0")
        ]
        if paths:
            merged["provenance"]["claims"].append(dict(claim, paths=paths))

    merged["updated_at"] = incoming["updated_at"]
    return merged


def _synchronize_behavior_shift_type(
    record: dict[str, Any], simulator: dict[str, Any]
) -> None:
    """Restate the final effective actuation in simulator behavior.

    A review can correct the incoming real-car claim, merge it into a more
    informed existing baseline, or add a simulator-specific override. Resolve
    all three before writing the deliberately redundant ``shift_type`` field.
    """
    behavior = simulator.get("behavior")
    transmission = (record.get("authentic_controls") or {}).get("transmission") or {}
    if not isinstance(behavior, dict) or "shift_actuation" not in transmission:
        return

    effective_actuation = transmission["shift_actuation"]
    for override in simulator.get("overrides") or []:
        if override.get("path") == "/authentic_controls/transmission/shift_actuation":
            effective_actuation = override.get("value")
    behavior["shift_type"] = effective_actuation


def _simulator_behavior_signature(entry: dict[str, Any]) -> dict[str, Any]:
    """The user-facing facts that compatible same-simulator packages share.

    Observation prose, confidence wording and source ids may differ because the
    drives are independent. The behavior fields and the effective override
    values may not: if either changes, one simulator entry cannot truthfully
    answer for both implementations.
    """
    behavior = json.loads(json.dumps(entry.get("behavior") or {}))
    behavior.pop("notes", None)
    wheel = behavior.get("wheel_rim_type")
    if isinstance(wheel, dict):
        wheel.pop("source_label", None)
    overrides = sorted(
        (
            item.get("path"),
            json.dumps(item.get("value"), sort_keys=True),
        )
        for item in entry.get("overrides", [])
    )
    return {"behavior": behavior, "overrides": overrides}


_ABSENT = object()


def _pointer_get(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer!r}")
    target = document
    for token in pointer.strip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(target, list):
            target = target[int(token)]
        else:
            target = target[token]
    return target


def _pointer_set(document: Any, pointer: str, value: Any) -> None:
    parts = pointer.strip("/").split("/")
    target = document
    for raw in parts[:-1]:
        token = raw.replace("~1", "/").replace("~0", "~")
        target = target[int(token)] if isinstance(target, list) else target[token]
    leaf = parts[-1].replace("~1", "/").replace("~0", "~")
    if isinstance(target, list):
        target[int(leaf)] = value
    else:
        target[leaf] = value


def _signature_leaves(entry: dict[str, Any]) -> dict[str, Any]:
    """Flatten user-facing simulator facts into stable review paths."""
    behavior = json.loads(json.dumps(entry.get("behavior") or {}))
    behavior.pop("notes", None)
    wheel = behavior.get("wheel_rim_type")
    if isinstance(wheel, dict):
        wheel.pop("source_label", None)

    leaves: dict[str, Any] = {}

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                walk(value[key], f"{path}/{key}")
            return
        leaves[path] = value

    walk(behavior, "/behavior")
    for override in entry.get("overrides", []):
        leaves[f"/overrides{override['path']}"] = override.get("value")
    return leaves


def _history_value(value: Any) -> Any:
    return {"absent": True} if value is _ABSENT else value


def _behavior_changes(
    current: dict[str, Any], replacement: dict[str, Any]
) -> list[dict[str, Any]]:
    before = _signature_leaves(current)
    after = _signature_leaves(replacement)
    changes = []
    for path in sorted(set(before) | set(after)):
        left = before.get(path, _ABSENT)
        right = after.get(path, _ABSENT)
        if left != right:
            changes.append(
                {
                    "path": path,
                    "from": _history_value(left),
                    "to": _history_value(right),
                }
            )
    return changes


def _unique_correction_source(
    bundle: dict[str, Any], entry: dict[str, Any], known_sources: set[str]
) -> dict[str, Any]:
    """Keep a repeated drive at the same game version from reusing a source id."""
    if entry.get("correct_existing_simulator"):
        source_kind = "correction"
    elif entry.get("compatible_implementation") is not None:
        source_kind = "implementation"
    else:
        return bundle
    source_id = bundle["source"]["source_id"]
    if source_id not in known_sources:
        return bundle
    observation_id = str(bundle.get("observation_id") or "")
    token = observation_id.rsplit("-", 1)[-1].lower()
    if not token or not all(char in "0123456789abcdef" for char in token):
        raise ValueError(
            f"review entry {entry.get('record_id')!r}: repeated source {source_id!r} "
            "already exists and the observation id has no hexadecimal suffix with "
            "which to distinguish the replacement drive"
        )
    replacement = f"{source_id}.{source_kind}-{token}"
    if replacement in known_sources:
        raise ValueError(
            f"review entry {entry.get('record_id')!r}: repeated source {replacement!r} "
            "is already registered"
        )
    corrected = json.loads(json.dumps(bundle))

    def replace(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace(item) for item in value]
        return replacement if value == source_id else value

    return replace(corrected)


def correct_simulator_entry(
    existing: dict[str, Any],
    incoming: dict[str, Any],
    correction: dict[str, Any],
    *,
    label: str,
    replacement_source_ref: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replace one incorrect simulator entry while retaining an audit trail."""
    if not isinstance(correction, dict) or not correction:
        raise ValueError(f"{label}: correct_existing_simulator must be a non-empty object")
    for field in (
        "basis",
        "supersedes_source_ref",
        "supersedes_observed_through",
        "corrected_behavior_paths",
    ):
        if field not in correction or correction[field] in (None, ""):
            raise ValueError(f"{label}: correction is missing {field!r}")
    basis = str(correction["basis"]).strip()
    if not basis:
        raise ValueError(f"{label}: correction basis must not be blank")

    replacement = incoming["simulators"][0]
    simulator_id = replacement["simulator"]
    positions = [
        index
        for index, candidate in enumerate(existing.get("simulators", []))
        if candidate.get("simulator") == simulator_id
    ]
    if len(positions) != 1:
        raise ValueError(
            f"{label}: correction requires exactly one existing {simulator_id} entry, "
            f"found {len(positions)}"
        )
    position = positions[0]
    current = existing["simulators"][position]
    superseded_source = correction["supersedes_source_ref"]
    if superseded_source not in current.get("source_refs", []):
        raise ValueError(
            f"{label}: correction says it supersedes {superseded_source!r}, but that "
            f"source does not support the current {simulator_id} entry"
        )
    if replacement_source_ref not in replacement.get("source_refs", []):
        raise ValueError(
            f"{label}: replacement source {replacement_source_ref!r} does not support "
            "the incoming simulator entry"
        )

    merged = json.loads(json.dumps(existing))
    authentic_changes = []
    for change in correction.get("authentic_control_corrections", []):
        for field in ("path", "from", "to", "basis"):
            if field not in change:
                raise ValueError(f"{label}: authentic correction is missing {field!r}")
        path = change["path"]
        if not str(path).startswith("/authentic_controls/"):
            raise ValueError(
                f"{label}: authentic correction path must start with "
                f"'/authentic_controls/', got {path!r}"
            )
        try:
            value = _pointer_get(merged, path)
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ValueError(f"{label}: authentic correction path does not exist: {path}") from exc
        if value != change["from"]:
            raise ValueError(
                f"{label}: authentic correction {path} expected {change['from']!r}, "
                f"but the curated record contains {value!r}"
            )
        _pointer_set(merged, path, change["to"])
        authentic_changes.append(dict(change))

    removed_overrides = []
    for removal in correction.get("remove_simulator_overrides", []):
        for field in ("simulator", "path", "value", "basis"):
            if field not in removal:
                raise ValueError(f"{label}: removed override is missing {field!r}")
        candidates = [
            item
            for item in merged.get("simulators", [])
            if item.get("simulator") == removal["simulator"]
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"{label}: cannot remove override from {removal['simulator']!r}; "
                f"found {len(candidates)} simulator entries"
            )
        overrides = candidates[0].get("overrides", [])
        matches = [
            item
            for item in overrides
            if item.get("path") == removal["path"]
            and item.get("value") == removal["value"]
        ]
        if len(matches) != 1:
            raise ValueError(
                f"{label}: expected exactly one {removal['simulator']} override "
                f"{removal['path']}={removal['value']!r}, found {len(matches)}"
            )
        overrides.remove(matches[0])
        removed_overrides.append(dict(removal))

    archetype_removal = correction.get("remove_archetype")
    if archetype_removal is not None:
        if not isinstance(archetype_removal, dict):
            raise ValueError(f"{label}: remove_archetype must be an object")
        for field in ("archetype_id", "basis"):
            if not str(archetype_removal.get(field) or "").strip():
                raise ValueError(f"{label}: remove_archetype is missing {field!r}")
        current_archetype = merged.get("archetype")
        if not isinstance(current_archetype, dict) or current_archetype.get(
            "archetype_id"
        ) != archetype_removal["archetype_id"]:
            raise ValueError(
                f"{label}: remove_archetype expected {archetype_removal['archetype_id']!r}, "
                f"but the curated record contains {current_archetype!r}"
            )
        del merged["archetype"]

    for addition in correction.get("add_simulator_overrides", []):
        for field in ("simulator", "path", "value", "condition", "confidence", "source_refs"):
            if field not in addition or addition[field] in (None, "", []):
                raise ValueError(f"{label}: added override is missing {field!r}")
        if not str(addition["path"]).startswith("/authentic_controls/"):
            raise ValueError(
                f"{label}: added override path must point into /authentic_controls/, "
                f"got {addition['path']!r}"
            )
        targets = [
            item
            for item in merged.get("simulators", [])
            if item.get("simulator") == addition["simulator"]
        ]
        if len(targets) != 1:
            raise ValueError(
                f"{label}: cannot add override to {addition['simulator']!r}; "
                f"found {len(targets)} simulator entries"
            )
        target = targets[0]
        absent_sources = [
            ref for ref in addition["source_refs"] if ref not in target.get("source_refs", [])
        ]
        if absent_sources:
            raise ValueError(
                f"{label}: added override cites source(s) absent from the target "
                f"simulator entry: {absent_sources!r}"
            )
        duplicates = [
            item
            for item in target.get("overrides", [])
            if item.get("path") == addition["path"]
            and item.get("value") == addition["value"]
        ]
        if duplicates:
            raise ValueError(
                f"{label}: added override already exists on {addition['simulator']}: "
                f"{addition['path']}={addition['value']!r}"
            )
        payload = {key: value for key, value in addition.items() if key != "simulator"}
        target.setdefault("overrides", []).append(json.loads(json.dumps(payload)))

    conflicts, fills = _classify_differences(
        merged["authentic_controls"], incoming["authentic_controls"]
    )
    if conflicts or fills:
        details = conflicts + [f"{path} (gap to {value!r})" for path, value in fills.items()]
        raise ValueError(
            f"{label}: correction leaves the incoming authentic layer out of agreement: "
            + "; ".join(details)
            + ". Correct or retract those values explicitly before replacing simulator evidence."
        )

    current_after_removals = merged["simulators"][position]
    behavior_changes = _behavior_changes(current_after_removals, replacement)
    actual_paths = {item["path"] for item in behavior_changes}
    declared_paths = set(correction["corrected_behavior_paths"])
    if actual_paths != declared_paths:
        missing = sorted(actual_paths - declared_paths)
        stale = sorted(declared_paths - actual_paths)
        raise ValueError(
            f"{label}: corrected_behavior_paths does not exactly describe the replacement; "
            f"missing {missing!r}, unchanged/stale {stale!r}"
        )

    kept_notes = correction.get("retained_behavior_notes", [])
    current_notes = current.get("behavior", {}).get("notes", [])
    absent_notes = [note for note in kept_notes if note not in current_notes]
    if absent_notes:
        raise ValueError(
            f"{label}: retained_behavior_notes includes text absent from the current entry: "
            f"{absent_notes!r}"
        )
    replacement = json.loads(json.dumps(replacement))
    replacement["identities"] = json.loads(json.dumps(current["identities"]))
    replacement["source_refs"] = list(
        dict.fromkeys(
            [ref for ref in current.get("source_refs", []) if ref != superseded_source]
            + replacement.get("source_refs", [])
        )
    )
    notes = replacement.setdefault("behavior", {}).setdefault("notes", [])
    for note in kept_notes:
        if note not in notes:
            notes.append(note)
    notes.append(f"Correction superseding {superseded_source}: {basis}")
    merged["simulators"][position] = replacement

    claims = []
    prefix = f"/simulators/{position}"
    for claim in merged.get("provenance", {}).get("claims", []):
        paths = [path for path in claim["paths"] if not path.startswith(prefix)]
        if paths:
            claims.append(dict(claim, paths=paths))
    for claim in incoming.get("provenance", {}).get("claims", []):
        paths = [
            path.replace("/simulators/0", prefix)
            for path in claim["paths"]
            if path.startswith("/simulators/0")
        ]
        if paths:
            claims.append(dict(claim, paths=paths))
    if authentic_changes:
        claims.append(
            {
                "paths": [item["path"] for item in authentic_changes],
                "source_refs": [superseded_source, replacement_source_ref],
                "confidence": "high",
                "basis": basis,
            }
        )
    merged["provenance"]["claims"] = claims
    merged["updated_at"] = incoming["updated_at"]

    history = {
        "corrected_at": incoming["updated_at"],
        "superseded_source_ref": superseded_source,
        "replacement_source_ref": replacement_source_ref,
        "basis": basis,
        "behavior_changes": [
            dict(item, path=f"/simulators/{position}{item['path']}")
            for item in behavior_changes
        ],
        "authentic_control_changes": authentic_changes,
        "removed_simulator_overrides": removed_overrides,
    }
    return merged, history


def _replace_corrected_approval(
    existing: dict[str, Any],
    incoming: dict[str, Any],
    correction: dict[str, Any],
    history: dict[str, Any],
    *,
    label: str,
    dataset_version: str,
    approved_at: str,
) -> dict[str, Any]:
    for field in ("record_id", "simulator", "telemetry_name", "observed_game_version"):
        if existing.get(field) != incoming.get(field):
            raise ValueError(
                f"{label}: corrected approval disagrees with the current approval on "
                f"{field!r} ({existing.get(field)!r} vs {incoming.get(field)!r})"
            )
    expected = correction["supersedes_observed_through"]
    if existing.get("observed_through") != expected:
        raise ValueError(
            f"{label}: correction expected approval observed_through {expected!r}, but "
            f"the current approval contains {existing.get('observed_through')!r}"
        )
    approval = json.loads(json.dumps(incoming))
    if "additional_telemetry_names" not in approval and existing.get(
        "additional_telemetry_names"
    ):
        approval["additional_telemetry_names"] = existing["additional_telemetry_names"]
    if "scope_notes" not in approval and existing.get("scope_notes"):
        approval["scope_notes"] = existing["scope_notes"]
    prior_history = list(existing.get("correction_history", []))
    approval["correction_history"] = prior_history + [history]
    old_notes = str(existing.get("historical_notes") or "").strip()
    addition = (
        f"Corrected from {expected} through {incoming['observed_through']}: "
        f"{correction['basis']}"
    )
    approval["historical_notes"] = f"{old_notes} {addition}".strip()
    approval["dataset_version"] = dataset_version
    approval["approved_at"] = approved_at
    return approval


def _merge_compatible_approval(
    existing: dict[str, Any],
    incoming: dict[str, Any],
    compatible: dict[str, Any],
    *,
    label: str,
    dataset_version: str,
    approved_at: str,
) -> dict[str, Any]:
    """Add a separately observed package name to one simulator approval."""
    for field in ("record_id", "simulator", "observed_game_version", "approved_controls"):
        if existing.get(field) != incoming.get(field):
            raise ValueError(
                f"{label}: compatible implementation approval disagrees on {field!r}; "
                "one approval cannot describe both packages."
            )
    basis = str(compatible["basis"]).strip()
    additions = [
        {"value": incoming["telemetry_name"], "basis": basis},
        *incoming.get("additional_telemetry_names", []),
    ]
    approved_names = {
        existing.get("telemetry_name"),
        *(item["value"] for item in existing.get("additional_telemetry_names", [])),
    }
    for addition in additions:
        if addition["value"] in approved_names:
            # A package may be republished without changing either its declared
            # version or telemetry name. Its distinct fingerprint and source
            # still belong in the audit trail when the effective controls match.
            continue
        existing.setdefault("additional_telemetry_names", []).append(addition)
        approved_names.add(addition["value"])
    existing["dataset_version"] = dataset_version
    existing["approved_at"] = approved_at
    existing["scope_notes"] = (
        "One simulator entry covers multiple separately fingerprinted "
        "implementations whose effective controls and overrides were reviewed "
        "as identical."
    )
    prior_confidence = str(existing.get("confidence_notes") or "").strip()
    incoming_confidence = str(incoming.get("confidence_notes") or "").strip()
    if incoming_confidence and incoming_confidence not in prior_confidence:
        existing["confidence_notes"] = (
            f"{prior_confidence} Compatible implementation: {incoming_confidence}"
        ).strip()
    history = str(existing.get("historical_notes") or "").strip()
    addition = (
        f"Compatible implementation observed through {incoming['observed_through']}: "
        f"{basis}"
    )
    existing["historical_notes"] = f"{history} {addition}".strip()
    return existing


def promote_observations(
    review: dict[str, Any],
    *,
    root: Path,
    data_directory: Path,
    curation_directory: Path,
) -> list[Path]:
    """Promote every reviewed bundle, writing records, approvals, and sources."""
    approved_at = review["approved_at"]
    dataset_version = review["dataset_version"]

    sources_path = data_directory / "sources.json"
    index_path = data_directory / "index.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    known_sources = {item["source_id"] for item in sources["sources"]}

    generated: list[tuple[Path, dict[str, Any]]] = []
    new_sources: list[dict[str, Any]] = []
    for entry in review["records"]:
        bundle_path = root / entry["bundle"]
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        old_live_source_id = bundle["source"]["source_id"]
        bundle = _apply_game_version_correction(bundle, entry)
        entry = _apply_entry_game_version_correction(
            entry, old_live_source_id, bundle["source"]["source_id"]
        )
        bundle = _unique_correction_source(bundle, entry, known_sources)
        bundle = _redirect_to_existing_record(bundle, entry, data_directory)
        entry = dict(entry, **{"class": resolve_class(entry, bundle, curation_directory)})
        record, approval, source = build_promoted_record(
            bundle, entry, approved_at=approved_at
        )
        record_id = record["record_id"]

        missing = [
            ref
            for ref in entry["real_world_source_refs"]
            if ref not in known_sources
        ]
        if missing:
            raise ValueError(
                f"{record_id}: real-world source(s) not registered in sources.json: "
                + ", ".join(sorted(missing))
            )

        simulator_id = record["simulators"][0]["simulator"]
        record_path = data_directory / "cars" / f"{record_id}.json"
        correction = entry.get("correct_existing_simulator")
        correction_history = None
        if record_path.exists():
            # The same real car, already curated from another simulator: the
            # drive adds an entry to it rather than forking a second record.
            existing = json.loads(record_path.read_text(encoding="utf-8"))
            if correction is not None:
                if entry.get("compatible_implementation") is not None:
                    raise ValueError(
                        f"review entry {record_id}: a drive cannot be both a compatible "
                        "implementation and a correction"
                    )
                record, correction_history = correct_simulator_entry(
                    existing,
                    record,
                    correction,
                    label=f"review entry {record_id}",
                    replacement_source_ref=source["source_id"],
                )
            else:
                record = merge_simulator_entry(
                    existing,
                    record,
                    label=f"review entry {record_id}",
                    accept_from_drive=entry.get("accept_from_drive"),
                    authentic_control_corrections=entry.get(
                        "authentic_control_corrections"
                    ),
                    compatible_implementation=entry.get("compatible_implementation"),
                )
        elif correction is not None:
            raise ValueError(
                f"review entry {record_id}: correct_existing_simulator is set but no "
                "curated record exists to correct"
            )

        # The approval is cross-checked against the record the entry landed in,
        # not against the proposal it was derived from. On a merge those differ:
        # the real-car baseline belongs to the record and may already hold values
        # this drive did not settle, so an approval built before the merge says
        # "unknown" where the record says "sequential-stick" and fails the gate
        # for having learned less than the first simulator did. Six fields the
        # approval schema requires cannot simply be dropped, so the summary is
        # taken again from the merged record and the entry now in it.
        approval["approved_controls"] = derive_approved_controls(
            record, simulator=simulator_id
        )
        approval["dataset_version"] = dataset_version
        approval["simulator"] = simulator_id
        approval_path = (
            curation_directory / f"{simulator_id}-approved-{record_id}.json"
        )
        if approval_path.exists():
            compatible = entry.get("compatible_implementation")
            if correction is not None:
                existing_approval = json.loads(
                    approval_path.read_text(encoding="utf-8")
                )
                approval = _replace_corrected_approval(
                    existing_approval,
                    approval,
                    correction,
                    correction_history,
                    label=f"review entry {record_id}",
                    dataset_version=dataset_version,
                    approved_at=approved_at,
                )
            elif compatible is None:
                raise FileExistsError(
                    f"refusing to overwrite curation approval: {approval_path}"
                )
            else:
                existing_approval = json.loads(
                    approval_path.read_text(encoding="utf-8")
                )
                approval = _merge_compatible_approval(
                    existing_approval,
                    approval,
                    compatible,
                    label=f"review entry {record_id}",
                    dataset_version=dataset_version,
                    approved_at=approved_at,
                )
        elif correction is not None:
            raise FileNotFoundError(
                f"review entry {record_id}: correction has no existing approval at "
                f"{approval_path}"
            )
        generated.append((record_path, record))
        generated.append((approval_path, approval))
        if source["source_id"] not in known_sources:
            new_sources.append(source)
            known_sources.add(source["source_id"])

    written: list[Path] = []
    for path, payload in generated:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        written.append(path)
        if path.parent.name == "cars":
            index["records"].append(path.relative_to(data_directory).as_posix())

    sources["sources"].extend(new_sources)
    sources_path.write_text(
        json.dumps(sources, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    index["records"] = sorted(set(index["records"]))
    index["dataset_version"] = dataset_version
    index["released_at"] = approved_at
    index_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return written
