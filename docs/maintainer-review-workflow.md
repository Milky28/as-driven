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

## Hand off identity research

Generate research packets for every pending case:

```shell
python -m as_driven_db review-submissions research-brief
```

Generate or regenerate selected cases with one or more `--issue` arguments:

```shell
python -m as_driven_db review-submissions research-brief --issue 42 --issue 47
```

Each selected case gains two ignored working files:

```text
research-brief.md
research-result.template.json
```

The brief is provider-independent and can be handed to a human, Codex, Claude,
or another research system. It contains contributor hints, the exact simulator
observation, mechanically staged values, explicit source standards, unresolved
questions, and deterministic related-record leads. A related lead is either an
exact curated simulator identity or a display name that matches after removing
a four-digit year. It is labelled as a lead and never becomes an identity match.

Research must return JSON conforming to
`schema/v1/submission-research-result.schema.json`. The result separates:

- the proposed exact identity and whether to create or reuse a record;
- candidate source metadata and exact scope;
- page, section, figure, timestamp, or other precise locators;
- field-level established, conflicting, and `not-established` findings;
- source references and confidence for each claim; and
- remaining questions and researcher/model attribution.

Import the completed result:

```shell
python -m as_driven_db review-submissions import-research 42 completed-research.json
```

Import checks the schema, exact case id, source-id uniqueness, claim/source
cross-references, proposed record action, and whether a supposedly complete
result actually resolves or explicitly conflicts on identity. It refuses to
overwrite an existing local result unless the maintainer passes `--replace`.
A complete result changes only the ignored local case state to `final-review`;
partial and blocked results remain visibly routed for more work. No source is
registered and no curated file is changed.

## Final review and promotion

Generate a final-review packet after complete research has been imported:

```shell
python -m as_driven_db review-submissions prepare-review 42
```

This writes ignored `final-review.md`, proposed source and promotion manifests,
and schema-validated preview record, approval, and live-source files. It runs
the real promoter against a temporary copy of the current dataset and refuses
incomplete control research, invalid source records, stale identities, or a
promotion conflict. It does not change curated files.

Review those files, especially the real-car baseline, unknown fields, exact
simulator overrides, source wording, and identity. Then cross the explicit
maintainer gate:

```shell
python -m as_driven_db review-submissions promote 42 --approve
```

The command requires the case to remain in `manifest-review`, requires the
proposal to target the next patch after the current dataset, re-runs promotion
in a temporary copy, reuses identical registered sources, rejects source-id
drift, allocates the next numbered `curation/review-batch-N.json`, registers new
sources, promotes the record and approval, and marks the ignored local case
`promoted`. Omitting `--approve` changes nothing.

Promotion does not silently rewrite release-wide prose or machine-specific
coverage inputs. After every approved case for a release is promoted, close the
batch with:

```shell
python -m as_driven_db review-submissions finalize-release --test
```

The command regenerates the AMS2 exact-identity coverage manifest from the
maintainer machine's current audit and SimHub identity files, rebuilds the
cross-simulator disagreement audit, derives release and simulator counts from
the curated records, refreshes maintained current-status references, rebuilds
the offline site, validates the repository, and—with `--test`—runs the full
Python suite. Omitting `--test` leaves the suite visibly reported as not run.
Historical version prose is not rewritten.

## Publish the result

Commit and push the finalized release before telling a contributor that it is
available. Then preview the exact GitHub response:

```shell
python -m as_driven_db review-submissions publish-result 42
```

The preview includes the proposed comment, close reason, and every publication
blocker. It does not call GitHub. Once the text is reviewed, cross a separate
external-write gate:

```shell
python -m as_driven_db review-submissions publish-result 42 --approve
```

Approval is limited to terminal `promoted`, `released`, and byte-identical
`duplicate` cases. It refuses dirty tracked release files, an unpushed commit,
stale coverage or disagreement artifacts, a missing site build, and a second
publication attempt. A successful call comments and closes the GitHub issue,
then records a local ignored publication receipt in `case.json`. Duplicate
wording explicitly distinguishes a byte-identical resubmission from independent
corroboration.

The lower-level path remains available for records not coming through the
public-submission queue:

```shell
python -m as_driven_db promote-observation curation/review-batch.json
```

Promotion remains deliberately outside synchronization. A successful download,
valid schema, contributor identity suggestion, or AI research result can never
promote a record by itself. Only the explicit final maintainer command can cross
that boundary.
