from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any, Callable


class ReviewFeedbackError(ValueError):
    pass


FeedbackPublisher = Callable[[str, int, str, str], None]
ReadinessChecker = Callable[[Path, dict[str, Any]], list[str]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exception:
        raise ReviewFeedbackError(f"could not read {label} {path}: {exception}") from exception
    if not isinstance(payload, dict):
        raise ReviewFeedbackError(f"{label} {path} is not a JSON object")
    return payload


def _run_git(root: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exception:
        raise ReviewFeedbackError("could not run git to verify publication readiness") from exception


def _dataset_version_key(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdecimal() for part in parts):
        return None
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def publication_blockers(root: Path, case: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    index = _read_json(root / "data" / "v1" / "index.json", "dataset index")
    current_version = index.get("dataset_version")
    proposal = case.get("review_proposal") or {}
    if case.get("state") == "promoted":
        promoted_version = proposal.get("dataset_version")
        promoted_key = _dataset_version_key(promoted_version)
        current_key = _dataset_version_key(current_version)
        if promoted_key is None or current_key is None:
            blockers.append(
                "the promoted or current dataset version cannot be compared"
            )
        elif promoted_key > current_key:
            blockers.append(
                "the promoted case targets future dataset "
                f"{promoted_version!r}, but the current dataset is {current_version!r}"
            )
        record_id = proposal.get("record_id")
        if not isinstance(record_id, str) or f"cars/{record_id}.json" not in index.get(
            "records", []
        ):
            blockers.append(
                f"the promoted record {record_id!r} is absent from the current dataset"
            )

    for relative, label in (
        (Path("research/ams2-coverage-manifest.json"), "AMS2 coverage manifest"),
        (Path("research/simulator-disagreement-audit.json"), "disagreement audit"),
    ):
        path = root / relative
        if not path.exists():
            blockers.append(f"{label} is missing; run finalize-release")
            continue
        payload = _read_json(path, label)
        if payload.get("dataset_version") != current_version:
            blockers.append(f"{label} is not finalized for dataset {current_version}")
    if not (root / "dist" / "site" / "index.html").exists():
        blockers.append("the offline site has not been built; run finalize-release")

    status = _run_git(root, ["status", "--porcelain", "--untracked-files=no"])
    if status.returncode != 0:
        blockers.append("git could not verify whether tracked release files are clean")
    elif status.stdout.strip():
        blockers.append("tracked release files are not committed")

    ahead = _run_git(root, ["rev-list", "--count", "@{upstream}..HEAD"])
    if ahead.returncode != 0:
        blockers.append("the current branch has no readable upstream publication state")
    else:
        try:
            ahead_count = int(ahead.stdout.strip())
        except ValueError:
            blockers.append("git returned an invalid upstream commit count")
        else:
            if ahead_count:
                blockers.append(
                    f"the current branch is {ahead_count} commit(s) ahead of its upstream; push first"
                )
    return blockers


def publication_next_step(blockers: list[str]) -> str:
    """The one action that actually moves publication forward.

    The workbench used to print "use Finalize release + run tests, then commit
    and push" whatever the blockers said, so a maintainer who had just run
    finalize was told to run it again. The blockers are ordered work: nothing
    can be committed until the release is finalized, and nothing pushed until it
    is committed, so the next step is the first stage still outstanding.
    """

    if not blockers:
        return ""
    finalize = (
        "is not finalized",
        "is missing; run finalize-release",
        "has not been built; run finalize-release",
    )
    if any(any(token in blocker for token in finalize) for blocker in blockers):
        return "Next: use Finalize release + run tests above."
    if any("not committed" in blocker for blocker in blockers):
        return "Next: commit the release, then push it."
    if any("push first" in blocker for blocker in blockers):
        return "Next: push the branch."
    if any(
        "dataset" in blocker or "absent from the current dataset" in blocker
        for blocker in blockers
    ):
        return (
            "Next: this case cannot publish against the current dataset. Promote "
            "it again, or advance the release it targets."
        )
    return "Next: resolve the blockers above; publication stays closed until they clear."


def _feedback(case: dict[str, Any]) -> tuple[str, str]:
    state = case.get("state")
    if state == "promoted":
        proposal = case.get("review_proposal") or {}
        record_id = proposal.get("record_id")
        version = proposal.get("dataset_version")
        if not isinstance(record_id, str) or not isinstance(version, str):
            raise ReviewFeedbackError("promoted case is missing its record id or dataset version")
        return (
            "completed",
            "Thanks for the contribution. This observation was reviewed and included "
            f"in As Driven dataset {version} as `{record_id}`.\n\n"
            "The submitted drive is retained as simulator evidence. The real-car identity "
            "and authentic controls were reviewed separately from cited sources before "
            "promotion.",
        )
    if state == "duplicate":
        return (
            "not planned",
            "Thanks for the contribution. This attachment is byte-for-byte identical to "
            "a draft already received, so it does not create a separate corroborating "
            "observation and no additional review is needed.",
        )
    if state == "released":
        return (
            "completed",
            "Thanks for the contribution. This exact observation is already represented "
            "in the curated dataset provenance, so no additional data change is needed.",
        )
    raise ReviewFeedbackError(
        f"case state {state!r} is not ready for final GitHub feedback"
    )


def publish_github_feedback(
    repository: str,
    issue_number: int,
    reason: str,
    body: str,
) -> None:
    try:
        completed = subprocess.run(
            [
                "gh",
                "issue",
                "close",
                str(issue_number),
                "--repo",
                repository,
                "--reason",
                reason,
                "--comment",
                body,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exception:
        raise ReviewFeedbackError(
            "could not run GitHub CLI; install `gh` and authenticate with `gh auth login`"
        ) from exception
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise ReviewFeedbackError(f"GitHub feedback failed: {detail}")


def publish_review_result(
    root: Path,
    cases_directory: Path,
    issue_number: int,
    *,
    approved: bool = False,
    publisher: FeedbackPublisher = publish_github_feedback,
    readiness_checker: ReadinessChecker = publication_blockers,
) -> dict[str, Any]:
    root = root.resolve()
    case_path = cases_directory / f"issue-{issue_number}" / "case.json"
    case = _read_json(case_path, "review case")
    repository = case.get("issue", {}).get("repository")
    actual_issue = case.get("issue", {}).get("number")
    if not isinstance(repository, str) or actual_issue != issue_number:
        raise ReviewFeedbackError("review case does not contain the requested GitHub issue")
    existing = case.get("github_feedback") or {}
    if existing.get("status") == "published":
        raise ReviewFeedbackError(
            f"GitHub feedback for issue #{issue_number} was already published"
        )

    reason, body = _feedback(case)
    blockers = readiness_checker(root, case)
    result = {
        "issue": issue_number,
        "repository": repository,
        "case_state": case.get("state"),
        "close_reason": reason,
        "comment": body,
        "blockers": blockers,
        "status": "preview",
    }
    if not approved:
        return result
    if blockers:
        raise ReviewFeedbackError(
            "GitHub feedback is blocked:\n" + "\n".join(f"- {item}" for item in blockers)
        )

    publisher(repository, issue_number, reason, body)
    published_at = _now()
    case["github_feedback"] = {
        "status": "published",
        "published_at": published_at,
        "close_reason": reason,
    }
    case["updated_at"] = published_at
    case_path.write_text(
        json.dumps(case, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    result.update({"status": "published", "published_at": published_at})
    return result
