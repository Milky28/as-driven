# Maintainer submission workflow

The maintainer queue removes manual downloading and command chaining without
weakening the review boundary. GitHub issues remain the public submission
inbox; versioned JSON remains the evidence format; guided drives still pass
through the existing intake and observation importer, while research-only
issues target an exact curated record without fabricating a drive.

## Prerequisites

Install and authenticate the GitHub CLI for an account that can read the
repository:

```shell
gh auth login
```

Run maintainer commands from the repository root.

## Synchronize submissions

Fetch every open issue carrying the shared `contribution` label. Simulator
observations have their single JSON attachment validated, intaken, and staged.
**Improve an existing car** issues are parsed without an attachment and must
resolve exactly to one curated record:

```shell
python -m as_driven_db review-submissions sync
```

Process one or several named issues when desired:

```shell
python -m as_driven_db review-submissions sync --issue 42 --issue 47
```

Synchronization is idempotent. An unchanged successful issue is not downloaded
or processed again. Editing an issue without replacing its attachment preserves
the existing classification; editing research notes preserves the exact target
and existing local research state. The local workbench serializes synchronization
requests from multiple browser tabs. A failed case is retried on the next
synchronization. For observation issues, the command validates that the issue's
attachment section contains exactly one safe
`.json` basename and accepts downloads only from GitHub attachment hosts. It
limits the payload before intake, then applies the observation schema and draft
status checks. It does not execute attachments, perform fuzzy identity matching,
update GitHub labels, comment on issues, or promote records.

The defaults can be overridden for a fork or alternate local workspace:

```shell
python -m as_driven_db review-submissions sync \
  --repo owner/repository \
  --label contribution \
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

Research-only cases contain `case.json` and `issue.json`, then gain the same
research brief, result, proposal, preview, and final-review artifacts as they
advance. They deliberately have no `submission.json`, intake receipt, staged
bundle, simulator approval, or live-observation source.

- `issue.json` preserves the exact GitHub issue response used for the sync.
- `submission.json` preserves the exact downloaded bytes.
- `receipt.json` is the result of the normal intake classifier.
- `staged.json` is the normal observation-import bundle.
- `case.json` is the versioned local orchestration record. It points to the
  other artifacts, preserves separately entered contributor hints, summarizes
  the observation, and records queue and research state.

`case.json` schema version `1.0.0` has these stable top-level concepts:

- `case_id`, `state`, and `classification` identify the workflow decision;
- `submission_type` distinguishes a guided drive from existing-car research;
- `issue` contains repository metadata and parsed Issue Form answers;
- `attachment` records filename, URL, exact SHA-256, and redaction status;
- `observation` summarizes the simulator identity and implementation;
- `target_record` names the exact curated record for research-only cases;
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

Use `--json` on either command for other tooling. Queue entries include the
durable routing `state`, a contributor-facing `display_state`, separate
`publication_status`, and `allowed_actions`. A client must use those actions
rather than reconstructing the workflow state machine itself.
Current automatic case states are:

| State | Meaning |
| --- | --- |
| `identity-research` | A new, related, changed, or additional implementation needs identity research, or an existing-car issue needs scoped source research. |
| `review-needed` | Intake matched an existing curated identity and offers a direct comparison review without repeating identity research. |
| `needs-clarification` | Established facts contradict another observation of the same implementation and version. |
| `duplicate` | The exact attachment bytes already exist in the intake inbox. |
| `released` | This exact observation already appears in curated provenance. |
| `intake-error` | Download, attachment, schema, or staging failed; the next sync retries it. |
| `final-review` | Complete research is imported and can be converted into a promotion proposal. |
| `manifest-review` | A proposal passed its dry run and awaits explicit maintainer approval. |
| `promoted` | Curated files were written; release finalization, commit, push, and contributor feedback remain. |

`published` is a display state layered over a terminal routing state after the
GitHub response has been sent. The underlying routing state is preserved for
auditability.

These are local routing decisions, not authenticity verdicts. In particular,
`identity-research` does not assert that the contributor's proposed identity is
correct.

## Local maintainer workbench

Start the dependency-free local interface from the repository root:

```shell
python -m as_driven_db review-submissions workbench
```

It binds only to `127.0.0.1`, opens the default browser, and remains available
until its terminal is closed or interrupted. Use `--no-open` to print the URL
without opening it, or `--port 0` to choose an available ephemeral port.

The workbench is a thin adapter over this document's commands. It can:

- synchronize the GitHub inbox and show the resulting queue;
- display the submitted observation, intake receipt, research packet, source
  proposal, preview record, and final-review packet;
- present completed research as a formatted review with raw JSON available;
- filter and prioritize the queue from the four summary cards, with distinct
  colors for each workflow state;
- generate and copy a provider-independent research brief;
- import a completed structured research-result JSON file;
- discover and validate `research-result.json` files written into case folders
  when the local queue is refreshed;
- prepare and dry-run the final review proposal;
- generate or regenerate conservative driver-summary prose from the reviewed
  record-wide controls, then dry-run the updated proposal again;
- promote only after the maintainer checks the explicit approval statement;
- finalize the release only with the complete test gate; and
- preview or publish GitHub feedback, with the same clean-tree and pushed-commit
  checks as the CLI.

The browser receives a per-process request token, mutating requests without it
are refused, uploaded JSON is size-limited, artifact paths cannot escape their
case directory, and the server refuses non-loopback binding. The ignored local
case directory remains the workbench's state; it does not introduce a second
database or state machine.

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

The researcher should save the completed object beside those files as
`research-result.json`. **Refresh local queue** discovers it, validates it, and
advances complete research to final review. The workbench also keeps a manual
file picker available after a brief is generated when the result was saved
somewhere else.

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
cross-references, canonical claim paths, proposed control value types, proposed
record action, and whether a supposedly complete result actually resolves or
explicitly conflicts on identity. It refuses to
overwrite an existing local result unless the maintainer passes `--replace`.
A complete result changes only the ignored local case state to `final-review`;
partial and blocked results remain visibly routed for more work. No source is
registered and no curated file is changed.

For existing-car research, the result keeps `record_action: use-existing` and
the exact target record id. It may address only the submitted scope; unlike a
new-car observation, it need not repeat a finding for every control field.
Complete research must contain at least one established real-car claim backed
by a non-simulator source. That claim may fill an unknown, deliberately correct
an established value, or strengthen provenance without changing the value.

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

An exact `curated-identity-comparison` in `review-needed` offers the same
**Prepare final review** action immediately. That path retains the curated
real-car identity, authentic-control baseline, sources, and driver summary,
then compares the new guided drive with the existing entry for that simulator.
The proposal must classify the drive as compatible repeat evidence or as an
audited correction that names the superseded observation and every changed
behavior path. It still runs the full temporary promotion dry run, and it never
treats the drive as proof of real-car identity.

An `existing-car-research` case instead produces a versioned research-amendment
manifest. It locks the current record by SHA-256, lists every `from` and `to`
value, distinguishes value changes from source-only strengthening, previews the
complete resulting record, and validates it against all existing simulator
approvals in a temporary repository. Matching simulator overrides become
redundant and are removed; differing ones remain explicit simulator departures.
No fake observation, live source, or simulator approval is created.

Review those files, especially the real-car baseline, unknown fields, exact
simulator overrides, source wording, and identity. Then cross the explicit
maintainer gate:

At `manifest-review`, the workbench also offers **Generate driver summary**.
It writes the draft into the proposed manifest, creates `driver-summary.md`,
updates `final-review.md` and `preview-record.json`, and reruns the same temporary
promotion validation. The draft uses only reviewed control values, keeps
unknowns explicit, and points any cross-simulator technique disagreement back
to the selected game's USE row. It never promotes automatically. Existing
record-wide summary prose is preserved unless the maintainer explicitly asks to
regenerate it.

Then cross the explicit maintainer gate:

```shell
python -m as_driven_db review-submissions promote 42 --approve
```

The command requires the case to remain in `manifest-review`, requires the
proposal to target the next patch after the current dataset, re-runs promotion
in a temporary copy, reuses identical registered sources, rejects source-id
drift, allocates the next numbered `curation/review-batch-N.json`, registers new
sources, promotes the record and approval, and marks the ignored local case
`promoted`. Omitting `--approve` changes nothing.

The proposal does not invent an archetype classification. That optional
classification is a separate reviewer decision and remains absent unless a
maintainer deliberately adds a valid classification to the manifest.

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
the offline site, validates the repository, and - with `--test` - runs the full
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
