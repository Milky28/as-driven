from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from .promote_observation import promote_observations
from .research_handoff import ResearchHandoffError, _read_json, _write_json
from .research_amendment import (
    merge_source_registry,
    validate_research_amendment,
)


_BATCH_RE = re.compile(r"^review-batch-(\d+)\.json$")
_AMENDMENT_RE = re.compile(r"^research-amendment-(\d+)\.json$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_patch(version: str) -> str:
    try:
        major, minor, patch = (int(token) for token in version.split("."))
    except (TypeError, ValueError) as exception:
        raise ResearchHandoffError(
            f"cannot increment current dataset version {version!r}"
        ) from exception
    return f"{major}.{minor}.{patch + 1}"


def _next_batch_path(curation_directory: Path) -> Path:
    numbers = []
    for path in curation_directory.glob("review-batch-*.json"):
        match = _BATCH_RE.fullmatch(path.name)
        if match:
            numbers.append(int(match.group(1)))
    return curation_directory / f"review-batch-{max(numbers, default=0) + 1}.json"


def _next_amendment_path(curation_directory: Path) -> Path:
    numbers = []
    for path in curation_directory.glob("research-amendment-*.json"):
        match = _AMENDMENT_RE.fullmatch(path.name)
        if match:
            numbers.append(int(match.group(1)))
    return curation_directory / f"research-amendment-{max(numbers, default=0) + 1}.json"


def _merge_candidate_sources(
    registry: dict[str, Any], proposal: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    merged = json.loads(json.dumps(registry))
    known = {source["source_id"]: source for source in merged["sources"]}
    added: list[str] = []
    for candidate in proposal["sources"]:
        source_id = candidate["source_id"]
        existing = known.get(source_id)
        if existing is not None:
            if existing != candidate:
                raise ResearchHandoffError(
                    f"candidate source {source_id!r} differs from the registered source; "
                    "resolve that source review before promotion"
                )
            continue
        merged["sources"].append(candidate)
        known[source_id] = candidate
        added.append(source_id)
    return merged, added


def _require_portable_bundles(root: Path, manifest: dict[str, Any]) -> None:
    for entry in manifest["records"]:
        bundle = Path(entry["bundle"])
        if bundle.is_absolute():
            raise ResearchHandoffError(
                f"review manifest bundle must be repository-relative, not {str(bundle)!r}"
            )
        resolved = (root / bundle).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exception:
            raise ResearchHandoffError(
                f"review manifest bundle escapes the repository: {str(bundle)!r}"
            ) from exception
        if not resolved.is_file():
            raise ResearchHandoffError(f"review manifest bundle does not exist: {bundle}")


def _dry_run(
    root: Path,
    manifest: dict[str, Any],
    merged_sources: dict[str, Any],
) -> None:
    with tempfile.TemporaryDirectory(prefix="as-driven-promote-") as directory:
        temporary = Path(directory)
        data_directory = temporary / "data" / "v1"
        curation_directory = temporary / "curation"
        shutil.copytree(root / "data" / "v1", data_directory)
        shutil.copytree(root / "curation", curation_directory)
        _write_json(data_directory / "sources.json", merged_sources)
        promote_observations(
            manifest,
            root=root,
            data_directory=data_directory,
            curation_directory=curation_directory,
        )


def _restore(path: Path, content: bytes | None) -> None:
    if content is None:
        if path.exists():
            path.unlink()
        return
    path.write_bytes(content)


def promote_review_case(
    root: Path,
    cases_directory: Path,
    issue_number: int,
    *,
    approved: bool,
) -> dict[str, Any]:
    """Promote one explicitly approved local review proposal.

    Research and proposal preparation are intentionally unable to call this
    function implicitly. The caller must supply the approval bit, and the case,
    dataset version, registered sources, and exact dry-run inputs must still
    agree at the moment of promotion.
    """
    if not approved:
        raise ResearchHandoffError(
            "promotion requires explicit maintainer approval; review final-review.md "
            "and rerun with --approve"
        )

    root = root.resolve()
    cases_directory = cases_directory.resolve()
    case_directory = cases_directory / f"issue-{issue_number}"
    case_path = case_directory / "case.json"
    case = _read_json(case_path, "review case")
    if case.get("state") != "manifest-review":
        raise ResearchHandoffError(
            f"issue #{issue_number} is {case.get('state')!r}, not 'manifest-review'"
        )
    research = case.get("research") or {}
    direct_comparison = (
        case.get("classification") == "curated-identity-comparison"
        and research.get("required") is False
        and research.get("status") == "not-required"
    )
    if research.get("status") != "complete" and not direct_comparison:
        raise ResearchHandoffError(f"issue #{issue_number} has no complete research result")
    proposal_state = case.get("review_proposal", {})
    if proposal_state.get("status") != "ready" or proposal_state.get("dry_run") != "passed":
        raise ResearchHandoffError(
            f"issue #{issue_number} has no ready proposal with a passed dry-run"
        )
    if case.get("classification") == "existing-car-research":
        return _promote_existing_car_research(
            root,
            case_directory,
            case_path,
            case,
            issue_number,
        )

    artifacts = case.get("artifacts", {})
    manifest = _read_json(
        case_directory / artifacts["review_manifest_proposal"],
        "review manifest proposal",
    )
    source_proposal = _read_json(
        case_directory / artifacts["source_proposal"],
        "source proposal",
    )
    index = _read_json(root / "data" / "v1" / "index.json", "dataset index")
    expected_version = _next_patch(index["dataset_version"])
    if manifest.get("dataset_version") != expected_version:
        raise ResearchHandoffError(
            f"proposal targets dataset {manifest.get('dataset_version')!r}, but the "
            f"current dataset {index['dataset_version']!r} requires {expected_version!r}; "
            "regenerate the proposal before approval"
        )
    if proposal_state.get("dataset_version") != manifest["dataset_version"]:
        raise ResearchHandoffError("case metadata and review manifest dataset versions differ")
    if len(manifest.get("records", [])) != 1:
        raise ResearchHandoffError("a public-submission review case must promote exactly one record")
    _require_portable_bundles(root, manifest)

    data_directory = root / "data" / "v1"
    curation_directory = root / "curation"
    registry_path = data_directory / "sources.json"
    registry = _read_json(registry_path, "source registry")
    merged_sources, added_sources = _merge_candidate_sources(registry, source_proposal)
    batch_path = _next_batch_path(curation_directory)
    if batch_path.exists():
        raise ResearchHandoffError(f"refusing to overwrite review batch {batch_path.name}")

    # The same promoter and current tree are exercised before any curated file
    # changes. This catches stale record ids, approvals, source refs, and merge
    # conflicts at the approval boundary.
    _dry_run(root, manifest, merged_sources)

    entry = manifest["records"][0]
    bundle = _read_json(root / entry["bundle"], "staged bundle")
    simulator = bundle["simulator"]
    record_path = data_directory / "cars" / f"{entry['record_id']}.json"
    approval_path = curation_directory / f"{simulator}-approved-{entry['record_id']}.json"
    index_path = data_directory / "index.json"
    snapshots = {
        path: path.read_bytes() if path.exists() else None
        for path in (registry_path, index_path, record_path, approval_path, batch_path)
    }
    try:
        _write_json(registry_path, merged_sources)
        _write_json(batch_path, manifest)
        written = promote_observations(
            manifest,
            root=root,
            data_directory=data_directory,
            curation_directory=curation_directory,
        )
    except Exception:
        for path, content in snapshots.items():
            _restore(path, content)
        raise

    promoted_at = _now()
    case["state"] = "promoted"
    case["updated_at"] = promoted_at
    case["review_proposal"].update(
        {
            "status": "promoted",
            "promoted_at": promoted_at,
            "record_id": entry["record_id"],
            "manifest": batch_path.relative_to(root).as_posix(),
        }
    )
    _write_json(case_path, case)
    return {
        "issue": issue_number,
        "state": "promoted",
        "record_id": entry["record_id"],
        "dataset_version": manifest["dataset_version"],
        "manifest": str(batch_path),
        "sources_added": added_sources,
        "written": [str(path) for path in written],
        "case": str(case_path),
    }


def _promote_existing_car_research(
    root: Path,
    case_directory: Path,
    case_path: Path,
    case: dict[str, Any],
    issue_number: int,
) -> dict[str, Any]:
    artifacts = case.get("artifacts") or {}
    manifest = _read_json(
        case_directory / artifacts["review_manifest_proposal"],
        "research amendment proposal",
    )
    source_proposal = _read_json(
        case_directory / artifacts["source_proposal"],
        "source proposal",
    )
    index_path = root / "data" / "v1" / "index.json"
    index = _read_json(index_path, "dataset index")
    expected_version = _next_patch(index["dataset_version"])
    if manifest.get("dataset_version") != expected_version:
        raise ResearchHandoffError(
            f"proposal targets dataset {manifest.get('dataset_version')!r}, but the "
            f"current dataset {index['dataset_version']!r} requires {expected_version!r}; "
            "regenerate the proposal before approval"
        )
    if (case.get("review_proposal") or {}).get("dataset_version") != expected_version:
        raise ResearchHandoffError(
            "case metadata and research amendment dataset versions differ"
        )
    candidate_sources = source_proposal.get("sources") or []
    preview_record, merged_sources = validate_research_amendment(
        root,
        manifest,
        candidate_sources,
    )
    registry_path = root / "data" / "v1" / "sources.json"
    registry = _read_json(registry_path, "source registry")
    _, added_sources = merge_source_registry(registry, candidate_sources)
    entry = manifest["records"][0]
    record_path = root / "data" / "v1" / "cars" / f"{entry['record_id']}.json"
    amendment_path = _next_amendment_path(root / "curation")
    if amendment_path.exists():
        raise ResearchHandoffError(
            f"refusing to overwrite research amendment {amendment_path.name}"
        )
    snapshots = {
        path: path.read_bytes() if path.exists() else None
        for path in (registry_path, index_path, record_path, amendment_path)
    }
    try:
        _write_json(registry_path, merged_sources)
        _write_json(record_path, preview_record)
        index["dataset_version"] = manifest["dataset_version"]
        index["released_at"] = manifest["approved_at"]
        _write_json(index_path, index)
        _write_json(amendment_path, manifest)
    except Exception:
        for path, content in snapshots.items():
            _restore(path, content)
        raise

    promoted_at = _now()
    case["state"] = "promoted"
    case["updated_at"] = promoted_at
    case["review_proposal"].update(
        {
            "status": "promoted",
            "promoted_at": promoted_at,
            "record_id": entry["record_id"],
            "manifest": amendment_path.relative_to(root).as_posix(),
        }
    )
    _write_json(case_path, case)
    return {
        "issue": issue_number,
        "state": "promoted",
        "record_id": entry["record_id"],
        "dataset_version": manifest["dataset_version"],
        "manifest": str(amendment_path),
        "sources_added": added_sources,
        "written": [
            str(registry_path),
            str(record_path),
            str(index_path),
            str(amendment_path),
        ],
        "case": str(case_path),
    }
