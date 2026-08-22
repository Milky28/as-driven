"""Promote staged guided-verification bundles into curated records.

`import-observation` stages a bundle from a guided drive; it deliberately leaves
real-world identity as ``REVIEW-REQUIRED`` because a drive cannot establish it.
This module applies the reviewer's decisions from an explicit review manifest and
writes the curated record, its curation approval, the evidence sources, and the
dataset index together, so a promotion is reproducible instead of hand-made.

It refuses to promote anything still marked ``REVIEW-REQUIRED``, refuses to
overwrite a curated record, and requires every cited source to be registered.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .importers.observation import REVIEW, derive_approved_controls
from .validate import ID_RE


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
    record["identity"]["real_world_identity_notes"] = _required(
        entry, "real_world_identity_notes", label
    )
    if entry.get("variant"):
        record["identity"]["variant"] = entry["variant"]

    # Optional reviewer corrections to controls the drive could not classify
    # (for example a gearbox construction supported by a real-world source).
    for name, value in (entry.get("control_overrides") or {}).items():
        if name not in record["authentic_controls"]["transmission"]:
            raise ValueError(f"{label}: unknown transmission field {name!r}")
        record["authentic_controls"]["transmission"][name] = value

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

    source["url"] = _required(entry, "live_source_url", label)
    if entry.get("live_source_notes"):
        # Safe to replace outright: the implementation fingerprint is a field on
        # the source, not a sentence in this note. It used to be rescued from the
        # prose, which failed the moment a reviewer wrote the marker phrase
        # without the digest.
        source["notes"] = entry["live_source_notes"]

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
) -> dict[str, Any]:
    """Add a simulator's entry to the curated record for the same real car.

    The existing record owns the real car. A second simulator contributes its
    own entry and the claims that describe it, and never rewrites identity or
    `authentic_controls` behind the reviewer's back. If the new drive disagrees
    about the real car, that is either a correction to make deliberately or a
    deviation to record as an override, so it stops here instead.
    """
    entry = incoming["simulators"][0]
    simulator_id = entry["simulator"]
    covered = [item.get("simulator") for item in existing.get("simulators", [])]
    if simulator_id in covered:
        raise FileExistsError(
            f"{label}: {simulator_id} already has an entry on this record; "
            "promoting would replace curated evidence"
        )

    conflicts, fills = _classify_differences(
        existing["authentic_controls"], incoming["authentic_controls"]
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

    merged = json.loads(json.dumps(existing))
    for pointer, value in fills.items():
        target = merged
        parts = pointer.strip("/").split("/")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
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
        if record_path.exists():
            # The same real car, already curated from another simulator: the
            # drive adds an entry to it rather than forking a second record.
            existing = json.loads(record_path.read_text(encoding="utf-8"))
            record = merge_simulator_entry(
                existing,
                record,
                label=f"review entry {record_id}",
                accept_from_drive=entry.get("accept_from_drive"),
            )

        approval["dataset_version"] = dataset_version
        approval["simulator"] = simulator_id
        approval_path = (
            curation_directory / f"{simulator_id}-approved-{record_id}.json"
        )
        if approval_path.exists():
            raise FileExistsError(
                f"refusing to overwrite curation approval: {approval_path}"
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
