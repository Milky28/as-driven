from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable
from urllib.parse import unquote, urlsplit

from .importers.observation import import_observation
from .intake_observation import MAX_OBSERVATION_BYTES, IntakeError, intake_observation
from .validate import canonical_simulator


DEFAULT_REPOSITORY = "Milky28/as-driven"
DEFAULT_LABEL = "contribution"
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
        "record": answer("Existing car record"),
        "research_intent": answer("What should this research improve?"),
        "applicability": answer("Exact car and source applicability"),
        "fields": answer("Fields or claims affected"),
        "evidence": answer("Sources and precise locators"),
        "conflicts": answer("Conflicts, limitations, or uncertainty"),
    }


def _issue_kind(body: str) -> str:
    headings = _sections(body)
    if "Guided-drive draft JSON" in headings:
        return "simulator-observation"
    if "Existing car record" in headings:
        return "existing-car-research"
    raise SubmissionSyncError(
        "contribution issue is neither a simulator observation nor existing-car research"
    )


def _record_reference_candidates(value: str) -> set[str]:
    candidates = {value.strip().strip("`\"")}

    def add_url_candidates(url: str) -> None:
        parsed = urlsplit(url)
        if parsed.fragment:
            fragment = (
                unquote(parsed.fragment)
                .removeprefix("car-")
                .removeprefix("record-")
            )
            candidates.add(fragment)
            # Simulator tabs are shareable as #<record-id>--<simulator>. A
            # double hyphen cannot occur in a valid record id, so this remains
            # exact identity resolution rather than fuzzy matching.
            if "--" in fragment:
                candidates.add(fragment.split("--", 1)[0])
        if parsed.path:
            candidates.add(unquote(parsed.path.rstrip("/").rsplit("/", 1)[-1]))

    for label, url in re.findall(r"\[([^\]\r\n]+)\]\((https://[^)\s]+)\)", value):
        candidates.add(label.strip().strip("`\""))
        add_url_candidates(url)
    parsed = urlsplit(value.strip())
    if parsed.scheme == "https":
        add_url_candidates(value.strip())
    return {candidate for candidate in candidates if candidate}


def _resolve_existing_record(root: Path, reference: str | None) -> dict[str, Any]:
    if not reference:
        raise SubmissionSyncError("existing-car research is missing its car record")
    index_path = root / "data" / "v1" / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exception:
        raise SubmissionSyncError(f"could not read the curated index: {exception}") from exception
    candidates = {value.casefold() for value in _record_reference_candidates(reference)}
    matches: list[dict[str, Any]] = []
    for relative in index.get("records", []):
        path = root / "data" / "v1" / str(relative)
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exception:
            raise SubmissionSyncError(f"could not read curated record {path}: {exception}") from exception
        names = {
            str(record.get("record_id") or "").casefold(),
            str((record.get("identity") or {}).get("display_name") or "").casefold(),
        }
        if candidates.intersection(names):
            matches.append(record)
    if not matches:
        raise SubmissionSyncError(
            f"existing-car research does not name an exact curated record: {reference!r}"
        )
    unique = {str(record["record_id"]): record for record in matches}
    if len(unique) != 1:
        raise SubmissionSyncError(
            f"existing-car research record reference is ambiguous: {reference!r}"
        )
    return next(iter(unique.values()))


def _research_required(classification: str) -> bool:
    return classification in {
        "new-identity",
        # Carries a candidate curated record, which the research has to confirm
        # or reject. It is not a match and must not skip the research gate.
        "curated-identity-candidate",
        "changed-implementation",
        "additional-implementation",
        "related-identity",
    }


def _case_state(classification: str) -> str:
    if classification == "exact-resubmission":
        return "duplicate"
    if classification == "unregistered-simulator":
        # Deliberately not identity research. No amount of research into the
        # car unblocks this one; the maintainer has to register the game. It is
        # held rather than rejected, and registering the simulator releases
        # every case waiting behind it at once.
        return "blocked-on-simulator"
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


def _held_case_is_now_releasable(case_dir: Path, case: dict[str, Any]) -> bool:
    """Whether a case held for an unregistered simulator can move again.

    Registering a simulator changes nothing about the issue - same body, same
    attachment, same timestamp, same bytes - so every shortcut on the sync path
    reported such a case unchanged and returned before intake could look at it
    again. There were three of them, and the drive stayed blocked behind a
    decision that had already been taken. They now share this one question.

    The reported game name is read from the case summary, or from the submitted
    observation on disk for cases written before the summary carried it, so
    registering a simulator releases the drives already waiting rather than only
    the ones submitted afterwards.
    """
    if case.get("state") != "blocked-on-simulator":
        return False
    reported = (case.get("observation") or {}).get("source_game_name")
    if not reported:
        submission = case_dir / str((case.get("artifacts") or {}).get("submission") or "")
        try:
            reported = json.loads(submission.read_text(encoding="utf-8")).get(
                "source_game_name"
            )
        except (OSError, json.JSONDecodeError, ValueError):
            reported = None
    return bool(reported) and canonical_simulator(str(reported)) is not None


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
    if _held_case_is_now_releasable(case_dir, case):
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
    if _held_case_is_now_releasable(case_dir, case):
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


def _sync_existing_car_research_issue(
    root: Path,
    repository: str,
    issue: dict[str, Any],
    case_dir: Path,
) -> tuple[str, dict[str, Any]]:
    number = int(issue["number"])
    summary = _issue_summary(issue, repository)
    existing: dict[str, Any] | None = None
    try:
        existing = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    if (
        existing
        and existing.get("schema_version") == CASE_SCHEMA_VERSION
        and existing.get("submission_type") == "existing-car-research"
        and existing.get("state") != "intake-error"
        and (existing.get("issue") or {}).get("updated_at") == issue.get("updatedAt")
        and (case_dir / "issue.json").is_file()
    ):
        return "skipped", existing

    target = _resolve_existing_record(root, summary["answers"].get("record"))
    target_id = str(target["record_id"])
    if (
        existing
        and existing.get("submission_type") == "existing-car-research"
        and existing.get("state") != "intake-error"
        and (existing.get("target_record") or {}).get("record_id") == target_id
    ):
        existing["issue"] = summary
        existing["updated_at"] = _now()
        _write_json(case_dir / "case.json", existing)
        return "processed", existing

    case = {
        "schema_version": CASE_SCHEMA_VERSION,
        "case_id": _case_id(repository, number),
        "submission_type": "existing-car-research",
        "state": "identity-research",
        "classification": "existing-car-research",
        "issue": summary,
        "attachment": None,
        "observation": {},
        "target_record": {
            "record_id": target_id,
            "display_name": (target.get("identity") or {}).get("display_name"),
            "identity": target.get("identity"),
        },
        "artifacts": {"issue": "issue.json"},
        "research": {"required": True, "status": "not-started"},
        "error": None,
        "created_at": (existing or {}).get("created_at") or _now(),
        "updated_at": _now(),
    }
    _write_json(case_dir / "case.json", case)
    return "processed", case


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
        if _issue_kind(str(issue.get("body") or "")) == "existing-car-research":
            return _sync_existing_car_research_issue(
                root,
                repository,
                issue,
                case_dir,
            )
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
        if receipt.get("released_simulator"):
            # Releasing a held drive changed which id the case is filed under.
            # The staged bundle is built here, separately, from the observation
            # as submitted - which still says "other", because the file on disk
            # records what the client knew and is never rewritten. Without this
            # the record, its source id and its approval are all staged under
            # "other" and promotion refuses a drive whose game is registered.
            observation = dict(observation, simulator=receipt["released_simulator"])
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
            "submission_type": "simulator-observation",
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
                # The id the case is filed under, which is the released one where
                # the drive came from a game registered after it was taken. The
                # observation on disk keeps saying "other" - it is a record of
                # what the client knew at the time and is never rewritten - but
                # showing that here would label a released case with the state it
                # was released from.
                "simulator": receipt.get("released_simulator")
                or observation.get("simulator"),
                "source_game_name": observation.get("source_game_name"),
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


def github_issue_absent(repository: str, number: int) -> bool:
    """Whether GitHub cannot resolve this issue at all.

    Closed is not absent. A closed issue answers this query normally, which is
    the whole point of asking: the issue list is filtered to open issues, so
    absence from it says nothing about whether an issue still exists.

    A failure to reach GitHub answers False. Retiring a case because the network
    was down would be the same mistake in a different costume.
    """
    try:
        completed = subprocess.run(
            ["gh", "issue", "view", str(number), "--repo", repository, "--json", "number"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return False
    if completed.returncode == 0:
        return False
    detail = (completed.stderr or "") + (completed.stdout or "")
    return "could not resolve" in detail.lower() or "not found" in detail.lower()


def _mark_withdrawn_cases(
    cases_dir: Path,
    issues: list[dict[str, Any]],
    issue_numbers: set[int] | None,
    issue_absent: Callable[[int], bool],
) -> list[int]:
    """Retire local cases whose issue is no longer on GitHub.

    Sync only ever added and updated, so an issue deleted upstream left its case
    on disk forever and the workbench kept offering it. Deleting the case would
    be the tidier answer and is the wrong one: the load can come back short for
    reasons that are nothing to do with the contributor withdrawing anything -
    a label removed, a rate limit, a filtered sync - and a deleted case takes the
    staged observation with it.

    So the case is marked and kept. It leaves the active queue, offers no
    actions, and says why. If the issue comes back the next sync overwrites the
    state and the case resumes.

    Only a full sync may do this. A sync narrowed to specific issues has no
    opinion about the ones it did not ask for, and treating its silence as
    absence would retire the entire queue.
    """
    if issue_numbers is not None:
        return []
    live = {int(issue["number"]) for issue in issues if issue.get("number") is not None}
    withdrawn: list[int] = []
    for case_path in sorted(cases_dir.glob("issue-*/case.json")):
        try:
            case = json.loads(case_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        number = (case.get("issue") or {}).get("number")
        if number is None or int(number) in live:
            continue
        # Finished work is never retired. A case that has been promoted, or
        # answered as a duplicate, has already produced whatever it was going to
        # produce, and deleting the issue afterwards does not un-curate a record.
        # Skipping these first is also what keeps the check cheap: it is the
        # completed cases that dominate the queue, and each one costs a call.
        if case.get("state") in {"promoted", "released", "duplicate", "withdrawn"} or (
            (case.get("github_feedback") or {}).get("status") == "published"
        ):
            if case.get("state") == "withdrawn":
                withdrawn.append(int(number))
            continue
        # Absence from the list is not deletion, and this is the trap. The query
        # asks for open issues carrying the label, so every issue that was
        # closed - which is what happens to every case that completes - is
        # missing from it too. Inferring deletion from absence retired twelve
        # finished contributions along with the two deleted drives.
        #
        # So each remaining candidate is asked about directly, and only an issue
        # GitHub cannot resolve at all is treated as gone. Anything else,
        # including a failure to reach GitHub, leaves the case alone.
        if not issue_absent(int(number)):
            continue
        if case.get("state") == "withdrawn":
            withdrawn.append(int(number))
            continue
        case["state"] = "withdrawn"
        case["withdrawn_reason"] = (
            "The GitHub issue for this case no longer exists. The local drive is "
            "kept, but the case offers no actions until the issue returns."
        )
        case_path.write_text(
            json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        withdrawn.append(int(number))
    return withdrawn


def sync_submissions(
    root: Path,
    repository: str = DEFAULT_REPOSITORY,
    label: str = DEFAULT_LABEL,
    cases_directory: Path = Path("build") / "review-cases",
    inbox: Path = Path("build") / "observation-intake",
    issue_numbers: set[int] | None = None,
    issue_loader: IssueLoader = load_github_issues,
    attachment_fetcher: AttachmentFetcher = fetch_github_attachment,
    absence_checker: Callable[[int], bool] | None = None,
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
    withdrawn = _mark_withdrawn_cases(
        cases_dir,
        issues,
        issue_numbers,
        absence_checker or (lambda number: github_issue_absent(repository, number)),
    )
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
        "withdrawn": withdrawn,
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
        observation = case.get("observation") or {}
        identity = observation.get("identity") or {}
        target = case.get("target_record") or {}
        publication = case.get("github_feedback") or {}
        publication_status = publication.get("status") or "not-published"
        cases.append(
            {
                "issue": issue.get("number"),
                "state": case.get("state"),
                "display_state": (
                    "published" if publication_status == "published" else case.get("state")
                ),
                "withdrawn_reason": case.get("withdrawn_reason"),
                "classification": case.get("classification"),
                "submission_type": case.get("submission_type") or "simulator-observation",
                "simulator": observation.get("simulator"),
                # What the game called itself. Only an unregistered simulator
                # carries one, and it is the whole reason such a case can be
                # grouped and acted on rather than sitting in an "other" heap.
                "source_game_name": observation.get("source_game_name"),
                "telemetry_name": identity.get("telemetry_name") or target.get("display_name"),
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


def unregistered_simulators(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Held cases grouped by the game they came from, commonest first.

    A contributor who drives forty cars in a simulator this project has never
    seen produces forty held cases, and read one at a time that is forty
    identical disappointments. Grouped, it is one decision: register the game,
    and every case behind it moves at once.

    The name is reported exactly as the telemetry client supplied it, because
    that is the string a maintainer has to recognise and the one the client will
    have to canonicalise.
    """
    held: dict[str, dict[str, Any]] = {}
    for case in cases:
        if case.get("classification") != "unregistered-simulator":
            continue
        name = case.get("source_game_name") or "unknown"
        entry = held.setdefault(name, {"source_game_name": name, "cases": 0, "cars": set()})
        entry["cases"] += 1
        if case.get("telemetry_name"):
            entry["cars"].add(case["telemetry_name"])
    return sorted(
        (
            {
                "source_game_name": entry["source_game_name"],
                "cases": entry["cases"],
                "distinct_cars": len(entry["cars"]),
            }
            for entry in held.values()
        ),
        key=lambda entry: (-entry["cases"], entry["source_game_name"]),
    )


def allowed_case_actions(case: dict[str, Any]) -> list[str]:
    """Return the actions a workbench may offer without inferring the state machine."""

    if (case.get("github_feedback") or {}).get("status") == "published":
        return []
    state = case.get("state")
    research_status = (case.get("research") or {}).get("status")
    if state == "intake-error":
        return ["sync"]
    if state == "withdrawn":
        # The issue it belonged to is gone. Nothing here can be published back
        # to a thread that no longer exists, and promoting from it would curate
        # a contribution nobody can now be credited or queried about.
        return []
    if state == "blocked-on-simulator":
        # Nothing here is the reviewer's to do. The case waits on the project
        # registering the game, not on research, a brief or a promotion, and
        # offering any of those would invite a promotion that must not happen.
        return []
    if state in {"identity-research", "research-blocked"}:
        actions = ["generate-research-brief"]
        if research_status in {"not-started", "brief-ready", "partial", "blocked"}:
            actions.append("import-research")
        return actions
    if (
        state == "review-needed"
        and case.get("classification") == "curated-identity-comparison"
    ):
        # The curated identity and authentic baseline already have reviewed
        # evidence. Prepare a proposal that compares this repeat drive with the
        # existing simulator entry and makes any correction explicit.
        return ["prepare-review"]
    # Research can be revisited after it is complete. The brief is regenerated
    # from the staged bundle and the current generator, so a case researched
    # before the brief asked a question - cockpit photographs, say - can be sent
    # back through with the question included, without discarding what is
    # already there. Generating writes only the brief and template, and leaves a
    # completed research status alone; importing is what replaces the result.
    if state == "final-review":
        return ["prepare-review", "generate-research-brief", "import-research"]
    if state == "manifest-review":
        return [
            "promote",
            "prepare-review",
            "generate-driver-summary",
            "save-driver-summary",
            "generate-research-brief",
            "import-research",
        ]
    if state in {"promoted", "released", "duplicate"}:
        return ["preview-publication", "publish-result"]
    return []
