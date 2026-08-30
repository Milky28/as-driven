# Development and maintenance

Everything needed to work on the database, the tooling, and the SimHub client.
For using As Driven, see the [README](../README.md) and
[docs/install.md](install.md). For what makes a claim acceptable evidence, see
[CONTRIBUTING.md](../CONTRIBUTING.md).

Python 3.11 or newer is the only requirement for the database side. The SimHub
client additionally needs Windows and a local SimHub installation.

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
research/                    Checked-in research manifests and generators
tests/                       Unit tests and small source-layout fixtures
simhub/AsDriven.Core/        Exact-match JSON reader and guidance logic
simhub/AsDriven.Plugin/      SimHub adapter and settings UI
simhub/dash/                 Generated Dash Studio source and raster assets
release/                     Independent database and client release packaging
docs/                        Data model, evidence, coverage, and process docs
```

Generated `build/`, `dist/`, `bin/`, `obj/`, Python caches, and local telemetry
artifacts are ignored and must never be committed.

## Required validation

After data, schema, Python tooling, research-manifest, or importer changes:

```powershell
python -m as_driven_db validate
python -m unittest discover -s tests -v
```

After C#, SimHub adapter, settings, XAML, dashboard, overlay, or plugin asset
changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

The SimHub build expects SimHub at `C:\Program Files (x86)\SimHub` unless
`-SimHubInstallPath` is supplied. It compiles, runs the .NET assertions,
generates dashboards, and packages only under `simhub/dist`. It never installs
into SimHub - installation is always a separate, explicit act.

Before committing:

```powershell
git diff --check
```

## Key documents

| Document | What it covers |
| --- | --- |
| [data-model.md](data-model.md) | Field semantics, confidence policy, identity rules |
| [evidence-boundaries.md](evidence-boundaries.md) | Real, simulated, and effective guidance layers |
| [verification-observations.md](verification-observations.md) | The guided in-game verification contract |
| [contribution-intake.md](contribution-intake.md) | Public submission, privacy, and intake states |
| [maintainer-review-workflow.md](maintainer-review-workflow.md) | Case contract and review states |
| [registering-a-simulator.md](registering-a-simulator.md) | The nine places a new simulator touches |
| [archetypes.md](archetypes.md) | Named control mechanisms and classification |
| [importers.md](importers.md) | AMS2 and iRacing import/review design |
| [releasing.md](releasing.md) | Build, QA, and publishing process |
| [architecture.md](architecture.md) | How the pieces fit together |
| [simhub-roadmap.md](simhub-roadmap.md) | Reference-client design and remaining work |

## Contribution review workflow

The maintainer workbench is the preferred interface and calls the same tested
functions as the CLI:

```shell
python -m as_driven_db review-submissions workbench
```

It opens the queue on localhost, exposes the durable case artifacts, accepts
completed research JSON, and keeps promotion and GitHub publication behind
separate explicit approval controls.

### The same workflow from the CLI

Synchronize every open GitHub issue labeled `observation-received`. This
downloads the one attached JSON through the authenticated GitHub CLI, runs
intake and staging together, and creates an idempotent case under ignored
`build/review-cases/`:

```shell
python -m as_driven_db review-submissions sync
python -m as_driven_db review-submissions queue
```

Use `sync --issue 42` for one issue. These commands require an authenticated
GitHub CLI (`gh auth login`) and never change issue labels or comments.

Generate provider-independent research packets, then validate and attach a
completed structured result:

```shell
python -m as_driven_db review-submissions research-brief
python -m as_driven_db review-submissions import-research 42 completed-research.json
```

Research can propose identity, sources, and field-level findings, but these
commands cannot register a source, edit curated data, or promote a record.

Generate a schema-validated preview and dry run, review its `final-review.md`,
then cross the separate explicit maintainer gate:

```shell
python -m as_driven_db review-submissions prepare-review 42
python -m as_driven_db review-submissions promote 42 --approve
python -m as_driven_db review-submissions finalize-release --test
python -m as_driven_db review-submissions publish-result 42
```

Approval refuses release-version drift, source-id drift, duplicate promotion,
and any case that has not reached `manifest-review`. It registers approved
candidate sources, allocates the next numbered review batch, promotes the record
and approval, and marks the local case promoted.

`finalize-release` regenerates the AMS2 coverage manifest and cross-simulator
disagreement audit, refreshes maintained release facts from the actual records,
rebuilds the offline site, and validates the repository. Pass `--test` to
include the full Python test suite.

After the release commit is pushed, `publish-result` previews the exact
contributor-facing comment and close reason. It makes no GitHub change unless
rerun with `--approve`, and refuses while tracked release files are dirty, the
branch is ahead of its upstream, or finalization artifacts are stale.

## Working with individual observations

Validate a draft exported by the plugin's guided verification form:

```shell
python -m as_driven_db validate-observation observation.json
```

Receive an untrusted public draft into the ignored local intake directory. This
validates the strict schema, records a SHA-256 receipt, and distinguishes an
exact resubmission from corroboration, contradiction, another implementation, or
a new exact identity:

```shell
python -m as_driven_db intake-observation observation.json
```

Stage a curated-record candidate, then promote the reviewed bundle once identity
and sources are resolved:

```shell
python -m as_driven_db import-observation observation.json --output build/staged.json
python -m as_driven_db promote-observation curation/review-batch.json
```

Audit records that still need real-world and simulator evidence separated:

```shell
python -m as_driven_db audit-boundaries --output build/evidence-boundaries.json
```

## Browsing the database offline

One self-contained page, filterable by simulator, shifter, clutch, and blip,
written to the ignored `dist/` directory:

```shell
python -m research.build_simulator_disagreement_audit
python -m as_driven_db build-site
```

Comparison modes show all cars, multi-simulator coverage, or only conflicting
established values; an `unknown` in one simulator never counts as disagreement.
A car stays one row while reviewed simulators appear as separate views inside
it, each with a stable shareable link.

## Bulk importers

These stage candidates only. They never modify `data/`, and they produce
normalized values alongside the raw source values.

```shell
python -m as_driven_db import-ams2 ams2.csv --output build/ams2-candidates.json
python -m as_driven_db import-iracing iracing.html --output build/iracing-candidates.json
```

Compare AMS2 candidates with identities already observed by SimHub:

```shell
python -m as_driven_db audit-simhub-ams2 --candidates build/ams2-candidates.json --cars-dir "C:\Program Files (x86)\SimHub\PluginsData\Automobilista2\Cars" --output build/ams2-simhub-identity-audit.json --review-csv build/ams2-alias-review.csv
```

Promote only the aliases recorded in a reviewed approval manifest:

```shell
python -m as_driven_db promote-ams2 --candidates build/ams2-candidates.json --audit build/ams2-simhub-identity-audit.json --approvals curation/ams2-approved-records.json --data-dir data/v1
```

A person must still resolve identity, review source metadata and reuse rights,
and approve each promoted record.

## Release commands

Build a database-only package:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-database.ps1
```

Build the complete release candidates on Windows with the SimHub SDK installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-release.ps1
```

This runs database validation, the Python tests, the complete SimHub build,
temporary install and uninstall tests, database rollback tests, final-ZIP
checksum and per-file hash verification, and an install from the extracted
artifact. Outputs go under ignored `dist/release`.

Plugin and database versions describe different things, but ship together:

- plugin and core DLL versions are aligned for an easily audited client build;
- `data/v1/index.json` owns the dataset version;
- every published release ships the full client package carrying the current
  dataset, so a release that exists only because the data changed still bumps
  the plugin version.

Users have exactly one update procedure: install the newest release over the old
one. `build-database.ps1` still produces a portable dataset package for clients
that are not SimHub, and `install-database.ps1` remains a maintainer tool - it
resolves paths from a repository checkout and is not shipped to users.

See [releasing.md](releasing.md) and [release/README.md](../release/README.md)
before publishing.

## Data versioning

- `schema_version` follows semantic versioning and describes structure.
- `dataset_version` follows semantic versioning and describes a curated data
  release.
- `verified_game_version` belongs to every simulator entry. It says when that
  implementation was last checked; it does not claim newer game versions are
  equivalent.
- Breaking schema changes create a new directory such as `schema/v2` and
  `data/v2`. Existing releases remain readable.

## README screenshots

The README shows five captures under `docs/images/`: `preflight-card.png`,
`preflight-card-compact.png`, `settings-garage.png`, `settings-browser.png`, and
`guided-drive.png`. They are from AMS2 1.6.9.91 with dataset 0.5.34 and plugin
0.21.0.

If you replace one, keep it PNG, keep it under a few hundred kilobytes, and
prefer a car whose technique is worth showing: the current pair use the Audi V8
quattro DTM because a synchromesh H-pattern exercises every field at once, and
the browser capture uses the BMW 2002 Turbo for the same reason.

A photographic capture - anything showing the cockpit rather than the plugin's
own flat UI - compresses badly as PNG. `guided-drive.png` is 1.4 MB for that
reason, against a repository whose whole pack is about 5 MB. That was judged
worth it once, for the one image that shows the contribution flow in the car;
save any further cockpit captures as JPEG or crop them to the panel that matters,
because the history was rewritten once to remove bulk imagery and should stay
small.
