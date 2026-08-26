# As Driven

An open, simulator-independent authentic-controls layer for sim racing. As
Driven tells a driver which physical controls to use for a car and how to shift
it authentically, while keeping simulator-specific behavior separate from the
real car.

The versioned JSON database is the source of truth. The working SimHub
integration is the reference client: it turns the data into pre-flight cards,
exact live-car matching, and a guided contribution workflow, but it does not own
the format. Websites, hardware selectors, voice assistants, and other telemetry
clients can consume the same releases without SimHub.

The project separates three questions:

1. **What controls did the real car have?** (`authentic_controls`)
2. **How does a simulator represent them?** (`simulators[].behavior`)
3. **What evidence supports each claim?** (`provenance.claims` and
   `data/v1/sources.json`)

An explicit `unknown` is different from `no`. A blank source cell is converted
to `no` only when that source documents that convention.

## What ships today

- Dataset 0.5.1 contains 263 reviewed car records under the open v1 JSON
  contract.
- The SimHub reference client is at 0.19.0, with exact matching, three pre-flight
  card sizes, offline preview, local diagnostics, and guided verification.
- The certified early-access target is Windows, SimHub 9.11.22, and AMS2
  1.6.9.91. Assetto Corsa EVO and the original Assetto Corsa are development
  tracks with reviewed observations. Assetto Corsa Competizione now has 18
  reviewed entries and remains a development track. None is part of that
  certified release target.

Dataset coverage, client recognition, and certified release support are
deliberately different claims. See [EARLY_ACCESS.md](EARLY_ACCESS.md) for the
supported release boundary.

## Project scope

The database answers a narrow pre-session question: **which physical controls
should I use, and how should I operate them authentically?** Core data covers:

- wheel-rim category;
- shifter actuation, gear count, and unusual patterns such as dogleg;
- clutch use for starting, upshifts, and downshifts;
- throttle lift, automatic shift cut, and manual/automatic blipping.

Steering DOR is optional reference metadata because most simulators and modern
wheelbases apply it automatically. General specifications, driver aids and
electronics, and handbrake construction are intentionally outside the MVP.
Importers select only relevant source columns rather than mirroring a general
car spreadsheet.

The format is simulator-independent, but a released dataset only covers the
simulators for which it carries reviewed entries. That list is derived from the
records themselves rather than declared, so a client can report an uncovered
game plainly instead of reporting every car in it as unmatched. AMS2 has broad
curated coverage; Assetto Corsa EVO and Assetto Corsa Competizione carry
reviewed cross-simulator entries and remain development targets.

## Repository layout

```text
schema/v1/                   JSON Schemas for records, sources, and the index
data/v1/index.json           Dataset release manifest
data/v1/sources.json         Reusable provenance/source records
data/v1/archetypes.json      Named control mechanisms records classify against
data/v1/cars/*.json          One curated car record per file
curation/                    Explicit, reviewable promotion approvals
as_driven_db/                Dependency-free validator and staging importers
as_driven_db/site.py         Renders the database as one browsable page
research/simulator-disagreement-audit.json  Field-level benchmark queue
tests/                       Unit tests and small source-layout fixtures
docs/data-model.md           Field semantics and confidence policy
docs/evidence-boundaries.md  Real, simulated, and effective guidance layers
docs/verification-observations.md  Guided in-game verification contract
docs/contribution-intake.md  Public submission, privacy, and intake states
docs/importers.md            AMS2 and iRacing import/review design
docs/ams2-import-audit.md    Live import coverage and SimHub identity findings
docs/ams2-post-sheet-research.md  Post-1.5.5.2 car/source backlog and test order
docs/ac-evo-coverage-plan.md  AC EVO overlap order and identity traps
docs/acc-coverage-plan.md     ACC overlap order and identity traps
docs/simulator-disagreement-audit.md  Cross-sim adjudication policy
docs/simhub-roadmap.md       Reference-client design and remaining roadmap
docs/releasing.md            Early-access build, QA, and publishing process
docs/plugin-distribution.md  Single-DLL drop-in question and what it would cost
simhub/                      .NET lookup library, plugin adapter, and diagnostics
release/                     Independent database-release packaging
```

## Quick start

Python 3.11 or newer is the only requirement.

```shell
python -m as_driven_db validate
python -m unittest discover -s tests -v
```

Audit private-beta records that still need their real-world and simulator
evidence separated:

```shell
python -m as_driven_db audit-boundaries --output build/evidence-boundaries.json
```

Validate a draft exported by SimHub's guided verification form:

```shell
python -m as_driven_db validate-observation observation.json
```

Receive an untrusted public draft into the ignored local intake directory. The
command validates the strict schema, records a SHA-256 receipt, and distinguishes
an exact resubmission from corroboration, contradiction, another implementation,
or a new exact identity:

```shell
python -m as_driven_db intake-observation observation.json
```

For maintainer batches, synchronize every open GitHub issue labeled
`observation-received`. This downloads the one attached JSON through the
authenticated GitHub CLI, runs intake and staging together, and creates an
idempotent case under ignored `build/review-cases/`:

```shell
python -m as_driven_db review-submissions sync
python -m as_driven_db review-submissions queue
```

Run the same workflow through the localhost-only maintainer workbench:

```shell
python -m as_driven_db review-submissions workbench
```

The workbench opens the queue in a browser, exposes the durable case artifacts,
accepts completed research JSON, and calls the same tested preparation,
promotion, finalization, and publication functions as the CLI. Promotion and
GitHub publication retain separate explicit approval controls.

Use `sync --issue 42` to process one issue. The commands require an authenticated
GitHub CLI (`gh auth login`) but never change issue labels or comments. See
`docs/maintainer-review-workflow.md` for the case contract and review states.

Generate provider-independent research packets for every pending case, then
validate and attach a completed structured result for final maintainer review:

```shell
python -m as_driven_db review-submissions research-brief
python -m as_driven_db review-submissions import-research 42 completed-research.json
```

Research can propose identity, sources, and field-level findings, but these
commands cannot register a source, edit curated data, or promote a record.

Generate a schema-validated preview and dry-run, review its `final-review.md`,
then cross the separate explicit maintainer gate:

```shell
python -m as_driven_db review-submissions prepare-review 42
python -m as_driven_db review-submissions promote 42 --approve
python -m as_driven_db review-submissions finalize-release --test
python -m as_driven_db review-submissions publish-result 42
```

The approval command refuses release-version drift, source-id drift, duplicate
promotion, and any case that has not reached `manifest-review`. It registers
approved candidate sources, allocates the next numbered review batch, promotes
the record and approval, and marks the local case promoted. Release-wide
coverage, prose references, validation, tests, and site generation remain one
finalization step after the chosen contribution batch.

`finalize-release` regenerates the AMS2 coverage manifest and cross-simulator
disagreement audit, refreshes maintained current release facts from the actual
records, rebuilds the offline site, and validates the repository. Pass `--test`
to include the full Python test suite.

After the release commit is pushed, `publish-result` previews the exact
contributor-facing comment and close reason. It makes no GitHub change unless
rerun with `--approve`; approval is refused while tracked release files are
dirty, the branch is ahead of its upstream, or finalization artifacts are stale.

Stage a curated-record candidate from that draft, then promote the reviewed
bundle once its real-world identity and sources are resolved:

```shell
python -m as_driven_db import-observation observation.json --output build/staged.json
```

```shell
python -m as_driven_db promote-observation curation/review-batch.json
```

Read the whole database in a browser, with no install and no JSON. One
self-contained page, filterable by simulator, shifter, clutch and blip, written
to the ignored `dist/` directory. Its comparison modes show all cars, multi-sim
coverage, or only conflicting established simulator values; an unknown in one
simulator never counts as disagreement. A car stays one row while reviewed
simulators appear as separate views inside it, each with a stable shareable link:

```shell
python -m research.build_simulator_disagreement_audit
python -m as_driven_db build-site
```

Dataset 0.5.1 contains 263 reviewed records. Of the 365 exact AMS2 identities
observed on the development machine, 349 are covered by the 255 AMS2-backed
curated records and 15 are closed by written decisions. One current Chevrolet
Cruze Stock Car 2021 identity remains queued for guided verification. New content still fails closed until it is observed and reviewed.
4 records carry Assetto Corsa EVO entries, 3 of them shared with AMS2. ACC has 18
reviewed cross-simulator entries. Original Assetto Corsa has 7 AC-only records and 14
records shared with AMS2.

The SimHub reference client has its own build and test command on Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

Build a standalone database package without SimHub binaries:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-database.ps1
```

Install that database snapshot into an existing SimHub installation without
replacing the As Driven plugin, dashboards, overlays, or settings:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\install-database.ps1
```

Database and plugin versions advance independently. A plugin package may carry
a known-good data snapshot for first installation, while database-only releases
can update compatible data without changing the client.

Build the complete early-access release candidates on the supported Windows
release machine:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-early-access.ps1
```

See [EARLY_ACCESS.md](EARLY_ACCESS.md) for supported versions, installation,
known limitations, and rollback. The plugin is offline and stores optional
diagnostics and verification drafts locally as described in
[PRIVACY.md](PRIVACY.md).

See [simhub/README.md](simhub/README.md) for its properties, diagnostic command,
packaging layout, and installation boundary.

Stage a local export of the AMS2 sheet for review:

```shell
python -m as_driven_db import-ams2 ams2.csv --output build/ams2-candidates.json
```

Stage a saved copy of the official iRacing transmission article:

```shell
python -m as_driven_db import-iracing iracing.html --output build/iracing-candidates.json
```

Compare AMS2 candidates with car identities already observed by SimHub:

```shell
python -m as_driven_db audit-simhub-ams2 --candidates build/ams2-candidates.json --cars-dir "C:\Program Files (x86)\SimHub\PluginsData\Automobilista2\Cars" --output build/ams2-simhub-identity-audit.json --review-csv build/ams2-alias-review.csv
```

Promote only the aliases recorded in the reviewed approval manifest:

```shell
python -m as_driven_db promote-ams2 --candidates build/ams2-candidates.json --audit build/ams2-simhub-identity-audit.json --approvals curation/ams2-approved-records.json --data-dir data/v1
```

Importers and audits do not modify `data/`. They produce candidates containing
normalized values alongside raw source values. The promotion command requires
an explicit approval manifest and accepts only aliases present in the audit's
conservative suggestion set. A person must still resolve identity, review
source metadata and reuse rights, and approve each promoted record.

## Data versioning

- `schema_version` follows semantic versioning and describes structure.
- `dataset_version` follows semantic versioning and describes a curated data
  release.
- `verified_game_version` belongs to every simulator entry. It says when that
  implementation was last checked; it does not claim newer game versions are
  equivalent.
- Breaking schema changes create a new directory such as `schema/v2` and
  `data/v2`. Existing releases remain readable.

## Contributing a correction or car

1. Create or edit one file in `data/v1/cars/`.
2. Add each new source once to `data/v1/sources.json`.
3. Cite every material claim with JSON Pointer paths in `provenance.claims`.
4. Record a confidence level and a short, falsifiable basis.
5. For simulator behavior, include the exact `verified_game_version` and check
   date. Do not write `latest`.
6. Run the validator and tests.

Primary sources (manufacturer manuals, homologation documents, simulator
documentation) are preferred. High-quality community research is welcome when
identified as such. Search snippets, unattributed reposts, and AI-generated
claims are not acceptable sources. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the full review policy.

## Dataset status

Dataset 0.5.1 contains 263 curated car records promoted through the reviewed
identity workflow. Of those, 255 carry AMS2 entries; 1 is AC EVO-only and 7 are
original-AC-only. 3 AMS2 records also carry separately reviewed Assetto Corsa
EVO entries, 14 also carry original Assetto Corsa entries, and 18 also carry
Assetto Corsa Competizione entries. They demonstrate useful
coverage, not a claim of complete vehicle or simulator coverage. Older records retain selected values
from Coanda's Extended Car Info sheet as published for AMS2 1.5.5.2, while
post-sheet cars use independent primary-source research and exact AMS2
1.6.9.91 tests. Raw wheel-rim codes are retained, unsupported driving
technique stays `unknown`, and only explicitly reviewed exact identities are
matched.

Per-version dataset history is in [CHANGELOG.md](CHANGELOG.md).

## Licensing

Software is MIT licensed. The original database selection and arrangement is
CC BY 4.0; third-party sources retain their own rights. See
[DATA_LICENSE.md](DATA_LICENSE.md).
