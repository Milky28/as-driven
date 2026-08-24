from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable
from urllib.parse import urlsplit

from .importers.observation import import_observation
from .intake_observation import MAX_OBSERVATION_BYTES, IntakeError, intake_observation


DEFAULT_REPOSITORY = "Milky28/as-driven"
DEFAULT_LABEL = "observation-received"
CASE_SCHEMA_VERSION = "1.0.0"

IssueLoader = Callable[[str, str], list[dict[str, Any]]]
AttachmentFetcher = Callable[[str], bytes]


class SubmissionSyncError(ValueError):
    pass


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_under(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def load_github_issues(repository: str, label: str) -> list[dict[str, Any]]:
    command = [
        "gh",
        "issue",
        "list",
        "--repo",
        repository,
        "--state",
        "open",
        "--label",
        label,
        "--limit",
        "1000",
        "--json",
        "number,title,body,url,labels,createdAt,updatedAt",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exception:
        raise SubmissionSyncError(
            "could not run GitHub CLI; install `gh` and authenticate with `gh auth login`"
        ) from exception
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise SubmissionSyncError(f"GitHub issue query failed: {detail}")
    try:
        issues = json.loads(completed.stdout)
    except json.JSONDecodeError as exception:
        raise SubmissionSyncError("GitHub CLI returned invalid JSON") from exception
    if not isinstance(issues, list):
        raise SubmissionSyncError("GitHub CLI issue response was not a list")
    return issues


def _allowed_attachment_url(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if host == "github.com":
        return parsed.path.startswith(
            ("/user-attachments/files/", "/user-attachments/assets/")
        )
    return host == "user-images.githubusercontent.com"


def fetch_github_attachment(url: str) -> bytes:
    if not _allowed_attachment_url(url):
        raise SubmissionSyncError(f"refusing non-GitHub attachment URL: {url}")
    try:
        completed = subprocess.run(
            ["gh", "api", url, "-H", "Accept: application/octet-stream"],
            check=False,
            capture_output=True,
        )
    except OSError as exception:
        raise SubmissionSyncError(
            "could not run GitHub CLI; install `gh` and authenticate with `gh auth login`"
        ) from exception
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SubmissionSyncError(
            f"authenticated GitHub attachment download failed: {detail or 'unknown error'}"
        )
    payload = completed.stdout
    if len(payload) > MAX_OBSERVATION_BYTES:
        raise SubmissionSyncError(
            f"attachment exceeds the {MAX_OBSERVATION_BYTES:,}-byte observation limit"
        )
    return payload


def _sections(body: str) -> dict[str, str]:
    matches = list(re.finditer(r"^###\s+(.+?)\s*$", body, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[match.group(1).strip()] = body[match.end() : end].strip()
    return sections


def extract_observation_attachment(body: str) -> dict[str, str]:
    section = _sections(body).get("Guided-drive draft JSON", "")
    links = re.findall(r"\[([^\]\r\n]+\.json)\]\((https://[^)\s]+)\)", section)
    if len(links) != 1:
        raise SubmissionSyncError(
            "expected exactly one .json link under 'Guided-drive draft JSON'"
        )
    filename, url = links[0]
    if Path(filename).name != filename or not filename.lower().endswith(".json"):
        raise SubmissionSyncError("attachment filename is not a safe .json basename")
    if not _allowed_attachment_url(url):
        raise SubmissionSyncError(f"refusing non-GitHub attachment URL: {url}")
    return {"filename": filename, "url": url}


def extract_issue_answers(body: str) -> dict[str, str | None]:
    sections = _sections(body)

    def answer(heading: str) -> str | None:
        value = sections.get(heading, "").strip()
        return None if not value or value == "_No response_" else value

    return {
        "intent": answer("What prompted this observation?"),
        "proposed_identity": answer("What exact real car do you believe this depicts?"),
        "identity_evidence": answer("Identity or real-car evidence"),
        "uncertainty": answer("Uncertainty or reviewer notes"),
    }


def _research_required(classification: str) -> bool:
    return classification in {
        "new-identity",
        "changed-implementation",
        "additional-implementation",
        "related-identity",
    }


def _case_state(classification: str) -> str:
    if classification == "exact-resubmission":
        return "duplicate"
    if classification == "already-reviewed-observation":
        return "released"
    if classification == "contradiction":
        return "needs-clarification"
    if _research_required(classification):
        return "identity-research"
    return "review-needed"


def _case_id(repository: str, issue_number: int) -> str:
    repository_token = re.sub(r"[^a-z0-9]+", "-", repository.lower()).strip("-")
    return f"github-{repository_token}-{issue_number}"


def _case_is_current(case_dir: Path, issue: dict[str, Any], attachment_url: str) -> bool:
    case_path = case_dir / "case.json"
    if not case_path.exists():
        return False
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if case.get("schema_version") != CASE_SCHEMA_VERSION:
        return False
    if case.get("state") == "intake-error":
        return False
    if case.get("issue", {}).get("updated_at") != issue.get("updatedAt"):
        return False
    if case.get("attachment", {}).get("url") != attachment_url:
        return False
    artifacts = case.get("artifacts", {})
    required = ["issue", "submission", "receipt", "staged_bundle"]
    return all(
        isinstance(artifacts.get(key), str)
        and (case_dir / artifacts[key]).is_file()
        for key in required
    )


def _same_attachment_case(
    case_dir: Path,
    attachment_url: str,
    digest: str,
) -> dict[str, Any] | None:
    """Return a usable prior case for the same issue attachment.

    Editing an issue changes its GitHub timestamp but does not make its attached
    observation a new submission. Reuse the prior routing decision rather than
    feeding the same bytes through the global duplicate detector again.
    """

    case_path = case_dir / "case.json"
    if not case_path.is_file():
        return None
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    attachment = case.get("attachment") or {}
    if attachment.get("url") != attachment_url or attachment.get("sha256") != digest:
        return None
    if case.get("state") == "intake-error":
        return None
    artifacts = case.get("artifacts") or {}
    required = ["issue", "submission", "receipt", "staged_bundle"]
    if not all(
        isinstance(artifacts.get(key), str)
        and (case_dir / artifacts[key]).is_file()
        for key in required
    ):
        return None
    return case


def _issue_summary(issue: dict[str, Any], repository: str) -> dict[str, Any]:
    labels = issue.get("labels", [])
    return {
        "repository": repository,
        "number": issue.get("number"),
        "title": issue.get("title"),
        "url": issue.get("url"),
        "created_at": issue.get("createdAt"),
        "updated_at": issue.get("updatedAt"),
        "labels": [
            label.get("name") for label in labels if isinstance(label, dict) and label.get("name")
        ],
        "answers": extract_issue_answers(str(issue.get("body") or "")),
    }


def _error_case(
    case_dir: Path,
    repository: str,
    issue: dict[str, Any],
    message: str,
    attachment: dict[str, str] | None = None,
) -> dict[str, Any]:
    existing_created_at: str | None = None
    try:
        existing_created_at = json.loads(
            (case_dir / "case.json").read_text(encoding="utf-8")
        ).get("created_at")
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    case = {
        "schema_version": CASE_SCHEMA_VERSION,
        "case_id": _case_id(repository, int(issue["number"])),
        "state": "intake-error",
        "classification": None,
        "issue": _issue_summary(issue, repository),
        "attachment": attachment,
        "artifacts": {"issue": "issue.json"},
        "research": {"required": False, "status": "blocked"},
        "error": message,
        "created_at": existing_created_at or _now(),
        "updated_at": _now(),
    }
    _write_json(case_dir / "issue.json", issue)
    _write_json(case_dir / "case.json", case)
    return case


def _sync_issue(
    root: Path,
    repository: str,
    issue: dict[str, Any],
    cases_dir: Path,
    inbox: Path,
    attachment_fetcher: AttachmentFetcher,
) -> tuple[str, dict[str, Any]]:
    try:
        number = int(issue["number"])
    except (KeyError, TypeError, ValueError) as exception:
        raise SubmissionSyncError("GitHub issue is missing an integer number") from exception
    case_dir = cases_dir / f"issue-{number}"
    case_dir.mkdir(parents=True, exist_ok=True)
    _write_json(case_dir / "issue.json", issue)
    attachment: dict[str, str] | None = None
    try:
        attachment = extract_observation_attachment(str(issue.get("body") or ""))
        if _case_is_current(case_dir, issue, attachment["url"]):
            case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
            return "skipped", case

        raw = attachment_fetcher(attachment["url"])
        if len(raw) > MAX_OBSERVATION_BYTES:
            raise SubmissionSyncError(
                f"attachment exceeds the {MAX_OBSERVATION_BYTES:,}-byte observation limit"
            )
        digest = hashlib.sha256(raw).hexdigest()
        prior_case = _same_attachment_case(case_dir, attachment["url"], digest)
        if prior_case is not None:
            prior_case["issue"] = _issue_summary(issue, repository)
            prior_case["updated_at"] = _now()
            _write_json(case_dir / "case.json", prior_case)
            return "processed", prior_case
        submission_path = case_dir / "submission.json"
        submission_path.write_bytes(raw)
        receipt = intake_observation(root, submission_path, inbox)
        _write_json(case_dir / "receipt.json", receipt)

        try:
            observation = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exception:
            raise SubmissionSyncError(f"could not parse validated observation: {exception}") from exception
        staged = import_observation(observation)
        _write_json(case_dir / "staged.json", staged)

        existing_created_at: str | None = None
        try:
            existing_created_at = json.loads(
                (case_dir / "case.json").read_text(encoding="utf-8")
            ).get("created_at")
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
        classification = str(receipt["status"])
        case = {
            "schema_version": CASE_SCHEMA_VERSION,
            "case_id": _case_id(repository, number),
            "state": _case_state(classification),
            "classification": classification,
            "issue": _issue_summary(issue, repository),
            "attachment": {
                **attachment,
                "sha256": digest,
                "redacted": attachment["filename"].lower().endswith(".redacted.json"),
            },
            "observation": {
                "observation_id": observation.get("observation_id"),
                "simulator": observation.get("simulator"),
                "game_version": observation.get("game_version"),
                "dataset_version": observation.get("dataset_version"),
                "identity": observation.get("identity"),
                "implementation": observation.get("implementation"),
            },
            "artifacts": {
                "issue": "issue.json",
                "submission": "submission.json",
                "receipt": "receipt.json",
                "staged_bundle": "staged.json",
            },
            "research": {
                "required": _research_required(classification),
                "status": "not-started" if _research_required(classification) else "not-required",
            },
            "error": None,
            "created_at": existing_created_at or _now(),
            "updated_at": _now(),
        }
        _write_json(case_dir / "case.json", case)
        return "processed", case
    except (IntakeError, SubmissionSyncError, OSError, KeyError, ValueError) as exception:
        case = _error_case(case_dir, repository, issue, str(exception), attachment)
        return "error", case


def sync_submissions(
    root: Path,
    repository: str = DEFAULT_REPOSITORY,
    label: str = DEFAULT_LABEL,
    cases_directory: Path = Path("build") / "review-cases",
    inbox: Path = Path("build") / "observation-intake",
    issue_numbers: set[int] | None = None,
    issue_loader: IssueLoader = load_github_issues,
    attachment_fetcher: AttachmentFetcher = fetch_github_attachment,
) -> dict[str, Any]:
    root = root.resolve()
    cases_dir = _resolve_under(root, cases_directory)
    intake_dir = _resolve_under(root, inbox)
    cases_dir.mkdir(parents=True, exist_ok=True)
    issues = issue_loader(repository, label)
    if issue_numbers is not None:
        issues = [issue for issue in issues if issue.get("number") in issue_numbers]
    issues.sort(key=lambda issue: int(issue.get("number", 0)))

    results: list[dict[str, Any]] = []
    counts = {"processed": 0, "skipped": 0, "error": 0}
    for issue in issues:
        outcome, case = _sync_issue(
            root,
            repository,
            issue,
            cases_dir,
            intake_dir,
            attachment_fetcher,
        )
        counts[outcome] += 1
        results.append(
            {
                "issue": issue.get("number"),
                "outcome": outcome,
                "state": case.get("state"),
                "classification": case.get("classification"),
                "case_directory": f"issue-{issue.get('number')}",
                "error": case.get("error"),
            }
        )
    return {
        "repository": repository,
        "label": label,
        "cases_directory": str(cases_dir),
        "issues_found": len(issues),
        **counts,
        "results": results,
    }


def list_review_cases(cases_directory: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    if not cases_directory.exists():
        return cases
    for path in cases_directory.glob("issue-*/case.json"):
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        issue = case.get("issue", {})
        observation = case.get("observation", {})
        identity = observation.get("identity") or {}
        publication = case.get("github_feedback") or {}
        publication_status = publication.get("status") or "not-published"
        cases.append(
            {
                "issue": issue.get("number"),
                "state": case.get("state"),
                "display_state": (
                    "published" if publication_status == "published" else case.get("state")
                ),
                "classification": case.get("classification"),
                "simulator": observation.get("simulator"),
                "telemetry_name": identity.get("telemetry_name"),
                "research": case.get("research", {}).get("status"),
                "publication_status": publication_status,
                "allowed_actions": allowed_case_actions(case),
                "title": issue.get("title"),
                "url": issue.get("url"),
                "case_directory": str(path.parent),
                "error": case.get("error"),
            }
        )
    return sorted(cases, key=lambda case: int(case.get("issue") or 0))


def allowed_case_actions(case: dict[str, Any]) -> list[str]:
    """Return the actions a workbench may offer without inferring the state machine."""

    if (case.get("github_feedback") or {}).get("status") == "published":
        return []
    state = case.get("state")
    research_status = (case.get("research") or {}).get("status")
    if state == "intake-error":
        return ["sync"]
    if state == "identity-research":
        actions = ["generate-research-brief"]
        if research_status in {"not-started", "brief-ready", "partial", "blocked"}:
            actions.append("import-research")
        return actions
    if state == "final-review":
        return ["prepare-review"]
    if state == "manifest-review":
        return ["promote"]
    if state in {"promoted", "released", "duplicate"}:
        return ["preview-publication", "publish-result"]
    return []
