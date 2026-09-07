"""Format curated JSON without making whitespace a data-validation rule."""

from __future__ import annotations

import json
from pathlib import Path


def format_records(root: Path) -> list[Path]:
    changes = []
    # Parse every file before writing, so malformed JSON does not leave a
    # partially formatted collection. Preserve values and key order.
    for path in sorted((root / "data" / "v1" / "cars").glob("*.json")):
        original = path.read_text(encoding="utf-8-sig")
        formatted = json.dumps(json.loads(original), indent=2, ensure_ascii=False) + "\n"
        if original != formatted:
            changes.append((path, formatted))
    for path, formatted in changes:
        path.write_text(formatted, encoding="utf-8")
    return [path for path, _ in changes]
