from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SIMULATOR_EVIDENCE_TYPES = {"official-simulator", "in-game-observation"}


def audit_evidence_boundaries(root: Path) -> dict[str, Any]:
    """Find authentic-control claims supported only by simulator evidence."""
    data_dir = root / "data" / "v1"
    source_payload = json.loads((data_dir / "sources.json").read_text(encoding="utf-8"))
    source_types = {
        source["source_id"]: source["source_type"] for source in source_payload["sources"]
    }

    findings: list[dict[str, Any]] = []
    record_count = 0
    authentic_claim_count = 0
    for path in sorted((data_dir / "cars").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        record_count += 1
        for claim_index, claim in enumerate(record["provenance"]["claims"]):
            authentic_paths = [
                pointer
                for pointer in claim["paths"]
                if pointer == "/authentic_controls"
                or pointer.startswith("/authentic_controls/")
            ]
            if not authentic_paths:
                continue
            authentic_claim_count += 1
            types = sorted({source_types.get(ref, "missing") for ref in claim["source_refs"]})
            if types and set(types).issubset(SIMULATOR_EVIDENCE_TYPES):
                findings.append(
                    {
                        "code": "authentic-claim-simulator-only",
                        "record_id": record["record_id"],
                        "claim_index": claim_index,
                        "paths": authentic_paths,
                        "source_refs": claim["source_refs"],
                        "source_types": types,
                        "basis": claim["basis"],
                    }
                )

    affected_records = sorted({finding["record_id"] for finding in findings})
    return {
        "audit": "evidence-boundaries",
        "schema_version": "1.0.0",
        "rules": [
            "Authentic-control claims require non-simulator evidence.",
            "Simulator-only evidence belongs in simulators[].behavior or a staged verification observation.",
            "Findings are migration work, not permission to replace unknown with an assumption.",
        ],
        "stats": {
            "records": record_count,
            "authentic_claims": authentic_claim_count,
            "simulator_only_authentic_claims": len(findings),
            "affected_records": len(affected_records),
        },
        "affected_record_ids": affected_records,
        "findings": findings,
    }
