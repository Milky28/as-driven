# Maintainer submission workflow

The maintainer queue removes manual downloading and command chaining without
weakening the review boundary. GitHub issues remain the public submission
inbox; versioned JSON remains the evidence format; the existing intake and
observation importer remain the only code that classifies and stages a draft.

## Prerequisites

Install and authenticate the GitHub CLI for an account that can read the
repository:

```shell
gh auth login
```

Run maintainer commands from the repository root.

## Synchronize submissions

Fetch every open issue carrying `observation-received`, download its single
JSON attachment, validate and intake it, and stage its candidate bundle:

```shell
python -m as_driven_db review-submissions sync
```

Process one or several named issues when desired:

```shell
python -m as_driven_db review-submissions sync --issue 42 --issue 47
```

Synchronization is idempotent. An unchanged successful issue is not downloaded
or processed again. A failed case is retried on the next synchronization. The
command validates that the issue's attachment section contains exactly one safe
`.json` basename and accepts downloads only from GitHub attachment hosts. It
limits the payload before intake, then applies the observation schema and draft
status checks. It does not execute attachments, perform fuzzy identity matching,
update GitHub labels, comment on issues, or promote records.

The defaults can be overridden for a fork or alternate local workspace:

```shell
python -m as_driven_db review-submissions sync \
  --repo owner/repository \
  --label observation-received \
  --cases-dir build/review-cases \
  --inbox build/observation-intake
```

## Local case contract

Every issue has a stable ignored directory named `issue-<number>`:

```text
build/review-cases/issue-42/
  case.json
  issue.json
  submission.json
  receipt.json
  staged.json
```

- `issue.json` preserves the exact GitHub issue response used for the sync.
- `submission.json` preserves the exact downloaded bytes.
- `receipt.json` is the result of the normal intake classifier.
- `staged.json` is the normal observation-import bundle.
- `case.json` is the versioned local orchestration record. It points to the
  other artifacts, preserves separately entered contributor hints, summarizes
  the observation, and records queue and research state.

`case.json` schema version `1.0.0` has these stable top-level concepts:

- `case_id`, `state`, and `classification` identify the workflow decision;
- `issue` contains repository metadata and parsed Issue Form answers;
- `attachment` records filename, URL, exact SHA-256, and redaction status;
- `observation` summarizes the simulator identity and implementation;
- `artifacts` names files relative to the case directory;
- `research` records whether identity research is needed and its local status;
- `error` contains a retryable intake failure and is otherwise null; and
- `created_at` and `updated_at` record local case processing time.

The case directory is working state and remains ignored. Only reviewed research,
curation manifests, approvals, registered sources, and promoted records enter
version control.

## Inspect the queue

```shell
python -m as_driven_db review-submissions queue
```

Use `--json` on either command for later tooling or a local workbench UI.
Current automatic case states are:

| State | Meaning |
| --- | --- |
| `identity-research` | A new, related, changed, or additional implementation needs real-car identity research. |
| `review-needed` | Intake found comparable evidence that needs a maintainer decision but not automatic identity research. |
| `needs-clarification` | Established facts contradict another observation of the same implementation and version. |
| `duplicate` | The exact attachment bytes already exist in the intake inbox. |
| `released` | This exact observation already appears in curated provenance. |
| `intake-error` | Download, attachment, schema, or staging failed; the next sync retries it. |

These are local routing decisions, not authenticity verdicts. In particular,
`identity-research` does not assert that the contributor's proposed identity is
correct.

## Continue review

Open `staged.json` for the mechanical simulator-observation candidate and use
the Issue Form answers in `case.json` only as research leads. Resolve identity
and real-car controls from registered sources, create the checked-in review
manifest, and retain explicit human review before running:

```shell
python -m as_driven_db promote-observation curation/review-batch.json
```

Promotion remains deliberately outside synchronization. A successful download,
valid schema, contributor identity suggestion, or future AI research result can
never promote a record by itself.
