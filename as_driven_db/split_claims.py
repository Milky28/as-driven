"""Separate a provenance claim that spans the authentic and simulator layers.

A claim is the authoritative unit of evidence, and its confidence describes the
strength of that evidence. Promotions before `sourced_control_paths` wrote one
claim covering both `/authentic_controls/...` and `/simulators/N/behavior`, so a
single confidence had to serve both halves. A reviewed guided drive really is
verified evidence - about the simulator. It is no evidence about the real car,
and 110 real-car claims carry `verified` on that basis alone.

Splitting is mechanical: no control value changes, no confidence changes, no
judgment about any car. Each half keeps the sources, confidence and basis it
already had, and the authentic half can then be re-sourced or lowered on its own
without disturbing the simulator observation. Deciding what the authentic half
deserves is the review task `docs/evidence-boundaries.md` describes, and this
tool does not do it; it reports which halves now stand alone on a drive so that
review has a queue.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

AUTHENTIC_PREFIX = "/authentic_controls"
IN_GAME_SOURCE_TYPE = "in-game-observation"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_record(path: Path, record: dict[str, Any]) -> None:
    """Canonical JSON with LF endings.

    `.gitattributes` says the index is uniformly LF and exists because CRLF on
    disk kept showing up as a modification with an empty diff. Writing LF means
    an untouched line hashes the same as the one in the index.
    """
    text = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    path.write_bytes(text.encode("utf-8"))


def split_claims(claims: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Rewritten claims, and a report entry for each claim that was split."""
    rewritten: list[dict[str, Any]] = []
    splits: list[dict[str, Any]] = []
    for index, claim in enumerate(claims):
        paths = list(claim.get("paths") or [])
        authentic = [path for path in paths if path.startswith(AUTHENTIC_PREFIX)]
        other = [path for path in paths if not path.startswith(AUTHENTIC_PREFIX)]
        if not authentic or not other:
            rewritten.append(claim)
            continue
        # The authentic half keeps the original position, so a record's claims
        # stay in the order a reviewer already knows.
        authentic_claim = copy.deepcopy(claim)
        authentic_claim["paths"] = authentic
        other_claim = copy.deepcopy(claim)
        other_claim["paths"] = other
        rewritten.extend((authentic_claim, other_claim))
        splits.append(
            {
                "claim_index": index,
                "confidence": claim.get("confidence"),
                "source_refs": list(claim.get("source_refs") or []),
                "authentic_paths": authentic,
                "other_paths": other,
            }
        )
    return rewritten, splits


def split_record(record: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    claims = record.get("provenance", {}).get("claims") or []
    rewritten, splits = split_claims(claims)
    if not splits:
        return record, []
    updated = copy.deepcopy(record)
    updated["provenance"]["claims"] = rewritten
    return updated, splits


def plan(root: Path, record_ids: Iterable[str] | None = None) -> dict[str, Any]:
    """What splitting would do, without writing anything."""
    data = root / "data" / "v1"
    index = _read_json(data / "index.json")
    sources = _read_json(data / "sources.json")
    registry = {entry["source_id"]: entry for entry in sources["sources"]}
    wanted = set(record_ids) if record_ids else None

    records: list[dict[str, Any]] = []
    split_count = 0
    drive_only = 0
    by_confidence: dict[str, int] = {}
    for relative in index["records"]:
        path = data / relative
        record = _read_json(path)
        if wanted is not None and record["record_id"] not in wanted:
            continue
        _, splits = split_record(record)
        if not splits:
            continue
        for split in splits:
            types = {
                registry.get(ref, {}).get("source_type") for ref in split["source_refs"]
            }
            # The authentic half stands on a drive alone: nothing else cites it.
            split["authentic_half_is_drive_only"] = types == {IN_GAME_SOURCE_TYPE}
            drive_only += split["authentic_half_is_drive_only"]
            level = str(split["confidence"])
            by_confidence[level] = by_confidence.get(level, 0) + 1
        split_count += len(splits)
        records.append(
            {
                "record_id": record["record_id"],
                "path": relative,
                "splits": splits,
            }
        )
    return {
        "report": "split-layer-claims",
        "records_affected": len(records),
        "claims_split": split_count,
        "drive_only_authentic_halves": drive_only,
        "by_confidence": by_confidence,
        "records": records,
    }


def apply(root: Path, record_ids: Iterable[str] | None = None) -> list[str]:
    """Write the split records. Returns the record ids that changed."""
    data = root / "data" / "v1"
    index = _read_json(data / "index.json")
    wanted = set(record_ids) if record_ids else None
    changed: list[str] = []
    for relative in index["records"]:
        path = data / relative
        record = _read_json(path)
        if wanted is not None and record["record_id"] not in wanted:
            continue
        updated, splits = split_record(record)
        if not splits:
            continue
        write_record(path, updated)
        changed.append(record["record_id"])
    return changed
