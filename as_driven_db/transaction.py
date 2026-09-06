"""Small recoverable transactions for curated-dataset promotions."""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4


JOURNAL_NAME = ".as-driven-promotion-transaction.json"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def recover_promotion(root: Path) -> None:
    """Roll back an incomplete promotion, or finish cleaning a committed one."""
    journal = root / JOURNAL_NAME
    if not journal.exists():
        return
    state = json.loads(journal.read_text(encoding="utf-8"))
    entries = state["entries"]
    if state.get("state") != "committed":
        for entry in entries:
            target = Path(entry["target"])
            temporary = Path(entry["temporary"])
            backup = Path(entry["backup"])
            if backup.exists():
                os.replace(backup, target)
            elif not entry["existed"] and target.exists():
                target.unlink()
            if temporary.exists():
                temporary.unlink()
    for entry in entries:
        backup = Path(entry["backup"])
        temporary = Path(entry["temporary"])
        if backup.exists():
            backup.unlink()
        if temporary.exists():
            temporary.unlink()
    journal.unlink()


def write_promotion_transaction(root: Path, outputs: list[tuple[Path, str]]) -> None:
    """Replace every output or leave the tree exactly as it was.

    All content is staged before an original is moved. If replacement fails,
    rollback runs immediately; a process interruption leaves the durable journal
    for the next promotion to recover.
    """
    root.mkdir(parents=True, exist_ok=True)
    recover_promotion(root)
    token = uuid4().hex
    entries = []
    for number, (target, content) in enumerate(outputs):
        temporary = target.with_name(f".{target.name}.promotion-{token}-{number}.new")
        backup = target.with_name(f".{target.name}.promotion-{token}-{number}.bak")
        temporary.write_text(content, encoding="utf-8")
        entries.append({
            "target": str(target), "temporary": str(temporary),
            "backup": str(backup), "existed": target.exists(),
        })

    journal = root / JOURNAL_NAME
    _write_json(journal, {"state": "prepared", "entries": entries})
    try:
        for entry in entries:
            target, backup = Path(entry["target"]), Path(entry["backup"])
            temporary = Path(entry["temporary"])
            if entry["existed"]:
                os.replace(target, backup)
            os.replace(temporary, target)
        _write_json(journal, {"state": "committed", "entries": entries})
    except Exception:
        recover_promotion(root)
        raise
    recover_promotion(root)
