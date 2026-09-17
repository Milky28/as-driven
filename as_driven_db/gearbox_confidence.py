"""Derive gearbox_type's confidence from the provenance claims that cover it.

`transmission.gearbox_type` is established or left `unknown` by a claim like
any other field, but nothing surfaces how strongly - a synchromesh or dog-box
value inferred from a family of homologated variants and one stated outright
by a specification are shown identically today. `gearbox_type_confidence` is
a derived field that closes that gap for the SimHub client, which marks the
FIT card's construction term when it is below `high`
(docs/simhub-roadmap.md, Phase 5).

It is derived, never hand-authored: the source of truth stays the claim, and
this module - not a reviewer - computes the field from it. `validate.py`
checks the two stay in step.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

from .split_claims import write_record

TARGET_PATH = "/authentic_controls/transmission/gearbox_type"

# The order every doc already lists them in (docs/data-model.md: "Confidence
# levels are verified, high, medium, low, and unknown"). No other module
# ranks confidence levels by strength; this is the first that needs to.
CONFIDENCE_RANK = {"verified": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}


def _pointer_parts(pointer: str) -> list[str]:
    return [part for part in pointer.strip("/").split("/") if part]


_TARGET_PARTS = _pointer_parts(TARGET_PATH)


def resolve_confidence(record: dict[str, Any]) -> str:
    """The strongest confidence among every claim covering gearbox_type.

    A claim covers the field when one of its paths is the field itself or an
    ancestor of it - `/authentic_controls/transmission` covers every field
    under it the way a handful of records claim the whole transmission block
    at once. The deepest (most specific) covering path wins over a shallower
    one, because a review that narrows a broader claim's confidence for just
    this field does so by removing the field from the broader claim's own
    paths, never by leaving both in place - confirmed against every record
    a prior construction review touched.

    Two or more claims can validly cover the field at the same depth,
    independently corroborating the same value from different evidence; the
    result is the strongest of them, never the weakest, since corroborating
    evidence is never a reason to report lower confidence than the best
    single piece of it would justify alone.

    Returns "unknown" when no claim covers the field at all - the same
    answer the field's own value takes when nothing establishes it.
    """
    best_depth = -1
    best_confidence = "unknown"
    for claim in record.get("provenance", {}).get("claims", []):
        confidence = claim.get("confidence", "unknown")
        for path in claim.get("paths", []):
            parts = _pointer_parts(path)
            if len(parts) > len(_TARGET_PARTS) or parts != _TARGET_PARTS[: len(parts)]:
                continue
            depth = len(parts)
            if depth > best_depth or (
                depth == best_depth
                and CONFIDENCE_RANK.get(confidence, 0) > CONFIDENCE_RANK.get(best_confidence, 0)
            ):
                best_depth = depth
                best_confidence = confidence
    return best_confidence


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _current_value(record: dict[str, Any]) -> str | None:
    return record.get("authentic_controls", {}).get("transmission", {}).get(
        "gearbox_type_confidence"
    )


def _with_confidence(record: dict[str, Any], confidence: str) -> dict[str, Any]:
    updated = copy.deepcopy(record)
    updated["authentic_controls"]["transmission"]["gearbox_type_confidence"] = confidence
    return updated


def plan(root: Path, record_ids: Iterable[str] | None = None) -> dict[str, Any]:
    """What writing the derived field would do, without writing anything."""
    data = root / "data" / "v1"
    index = _load_json(data / "index.json")
    wanted = set(record_ids) if record_ids else None

    changes: list[dict[str, Any]] = []
    unchanged = 0
    by_confidence: dict[str, int] = {}
    for relative in index["records"]:
        record = _load_json(data / relative)
        if wanted is not None and record["record_id"] not in wanted:
            continue
        resolved = resolve_confidence(record)
        by_confidence[resolved] = by_confidence.get(resolved, 0) + 1
        current = _current_value(record)
        if current == resolved:
            unchanged += 1
            continue
        changes.append(
            {
                "record_id": record["record_id"],
                "path": relative,
                "current": current,
                "resolved": resolved,
            }
        )
    return {
        "report": "gearbox-type-confidence",
        "records_considered": unchanged + len(changes),
        "records_unchanged": unchanged,
        "records_to_update": len(changes),
        "by_resolved_confidence": dict(sorted(by_confidence.items())),
        "changes": changes,
    }


def apply(root: Path, record_ids: Iterable[str] | None = None) -> list[str]:
    """Write the derived field. Returns the record ids that changed."""
    data = root / "data" / "v1"
    index = _load_json(data / "index.json")
    wanted = set(record_ids) if record_ids else None
    changed: list[str] = []
    for relative in index["records"]:
        path = data / relative
        record = _load_json(path)
        if wanted is not None and record["record_id"] not in wanted:
            continue
        resolved = resolve_confidence(record)
        if _current_value(record) == resolved:
            continue
        write_record(path, _with_confidence(record, resolved))
        changed.append(record["record_id"])
    return changed
