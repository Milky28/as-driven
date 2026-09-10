"""Convention guidance: what cars of a mechanism and era were usually driven like.

A rule is evidence about a class, never a finding about a car. It is displayed
where the record leaves a field unknown, and it never becomes the record's
value. See docs/convention-guidance.md.

Two guards do the real work here. A rule only ever speaks to a field the record
leaves `unknown`, so an established value always wins and cannot be overwritten
by a class. And where a rule disagrees with a value a record has established,
that is reported rather than silently skipped: `lamborghini-miura-sv` holds
`not-required` on a synchromesh gearbox because its own reviewed research says
so, and a rule that contradicts a real car is a rule worth looking at.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

UNKNOWN = "unknown"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_conventions(root: Path) -> list[dict[str, Any]]:
    return _read(root / "data" / "v1" / "conventions.json")["conventions"]


def resolve_pointer(record: dict[str, Any], pointer: str) -> Any:
    node: Any = record
    for part in pointer.strip("/").split("/"):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _matches(record: dict[str, Any], when: dict[str, Any]) -> bool:
    transmission = record["authentic_controls"]["transmission"]
    for field, expected in (when.get("transmission") or {}).items():
        actual = transmission.get(field)
        # A rule may deliberately key on a gap, so `unknown` is a value to match
        # rather than a wildcard. Absent and unknown are the same thing here.
        if expected == UNKNOWN:
            if actual not in (None, UNKNOWN):
                return False
        elif actual != expected:
            return False
    year = (record.get("identity") or {}).get("year") or {}
    lower, upper = when.get("year_from_at_least"), when.get("year_to_at_most")
    if lower is not None and (year.get("from") is None or year["from"] < lower):
        return False
    if upper is not None and (year.get("to") is None or year["to"] > upper):
        return False
    return True


def guidance_for(record: dict[str, Any], conventions: list[dict[str, Any]]) -> dict[str, Any]:
    """What a client should show for one record, and what a reviewer should see.

    `applies` is display material: a rule matched and the field it speaks to is
    open. `conflicts` is review material: a rule matched but the record already
    answers, differently.
    """
    applies: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for rule in conventions:
        if not _matches(record, rule["when"]):
            continue
        open_paths, disagreeing = [], []
        for outcome in rule["then"]:
            current = resolve_pointer(record, outcome["path"])
            if current in (None, UNKNOWN):
                open_paths.append(outcome["path"])
            elif current != outcome["value"]:
                disagreeing.append(
                    {"path": outcome["path"], "record": current, "rule": outcome["value"]}
                )
        if open_paths:
            applies.append({
                "convention_id": rule["convention_id"],
                "paths": open_paths,
                "strength": rule["strength"],
                "guidance": rule["guidance"],
                # The same sentence at card length, for a client with one line
                # to spend. Both are carried so the client picks by the room it
                # has rather than truncating the long one mid-thought.
                "short_guidance": rule["short_guidance"],
            })
        if disagreeing:
            conflicts.append({
                "convention_id": rule["convention_id"],
                "record_id": record["record_id"],
                "fields": disagreeing,
            })
    return {"applies": applies, "conflicts": conflicts}


def report(root: Path) -> dict[str, Any]:
    """Reach and conflicts across the curated set."""
    data = root / "data" / "v1"
    index = _read(data / "index.json")
    conventions = load_conventions(root)
    records_covered, fields_covered = 0, 0
    per_rule: dict[str, int] = {rule["convention_id"]: 0 for rule in conventions}
    conflicts: list[dict[str, Any]] = []
    for relative in index["records"]:
        record = _read(data / relative)
        result = guidance_for(record, conventions)
        conflicts.extend(result["conflicts"])
        if result["applies"]:
            records_covered += 1
            for item in result["applies"]:
                fields_covered += len(item["paths"])
                per_rule[item["convention_id"]] += len(item["paths"])
    return {
        "report": "convention-guidance",
        "dataset_version": index["dataset_version"],
        "records_with_guidance": records_covered,
        "fields_covered": fields_covered,
        "fields_per_rule": per_rule,
        "conflicts": conflicts,
    }
