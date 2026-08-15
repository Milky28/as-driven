# As Driven development guide

## Project purpose

As Driven is a simulator-independent, open-source database that tells
sim racers which physical controls and shifting technique to use for an
authentic experience. SimHub is the first client; it does not own the data
format.

Keep the core dataset focused on choices that affect pre-session hardware or
driving technique:

- wheel-rim category;
- shifter actuation, pattern, and forward gear count;
- clutch use for starts, upshifts, and downshifts;
- throttle lift, shift cut, and manual or automatic blipping;
- optional steering DOR as reference metadata.

Do not expand this into a general vehicle database. TC, ABS, unrelated driver
aids, performance specifications, and handbrake construction are outside the
current scope.

## Implementation style

Act as an expert C# game-telemetry developer. The SimHub client uses the
standard SimHub SDK and must retain its required `IPlugin`, `IDataPlugin`,
`IWPFSettings`, and `PluginManager` integration. Prefer small, direct changes.
Do not add service layers, framework migrations, speculative wrappers, or heavy
abstractions.

The SimHub projects target .NET Framework 4.0 and intentionally use the SDK
assemblies from the locally installed SimHub. Do not introduce NuGet or copy
SimHub SDK binaries into the repository or release package.

## Repository map

- `schema/v1/`: versioned JSON Schema contracts.
- `data/v1/`: curated index, sources, and one JSON record per car.
- `curation/`: explicit reviewer approvals required for promotion.
- `as_driven_db/`: dependency-free Python validation, import, audit,
  and promotion tools.
- `research/`: checked-in research manifests and deterministic generators.
- `simhub/AsDriven.Core/`: exact-match JSON reader and guidance logic.
- `simhub/AsDriven.Plugin/`: direct SimHub adapter and settings UI.
- `simhub/dash/`: generated Dash Studio source and approved raster assets.
- `tests/`: Python regression tests and legally safe fixtures.
- `release/`: separate database and early-access release tooling.
- `docs/`: data model, evidence, coverage, integration, and release guidance.

Generated `build/`, `dist/`, `bin/`, `obj/`, Python caches, and local telemetry
artifacts are ignored. Never commit them.

## Required validation

Run after data, schema, Python tooling, research-manifest, or importer changes:

```powershell
python -m as_driven_db validate
python -m unittest discover -s tests -v
```

Run after C#, SimHub adapter, settings, XAML, dashboard, overlay, or plugin asset
changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

The SimHub build requires the supported SimHub installation at
`C:\Program Files (x86)\SimHub` unless `-SimHubInstallPath` is supplied. It
compiles, runs the .NET assertions, generates dashboards, and packages only
under `simhub/dist`. It must never install into SimHub.

Before committing, also run:

```powershell
git diff --check
```

## Installation and removal

Installation is a separate, explicit user action. Never install merely because
the project was built.

With SimHub closed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\install.ps1
```

The installer creates a timestamped rollback backup, updates plugin binaries,
Dash Studio templates, and the bundled database, and preserves customized
`As Driven*.olayout` files by default.

Remove packaged plugin components while preserving the database, settings,
diagnostics, contribution drafts, and customized layouts:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\uninstall.ps1
```

Use `-RemovePackagedLayouts` only when the user explicitly wants those layouts
backed up and removed.

## Release commands

Build and test a database-only package:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-database.ps1
```

Build the complete early-access candidates on Windows with the supported SimHub
SDK installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-early-access.ps1
```

The early-access command runs database validation, Python tests, the complete
SimHub build, temporary install and uninstall tests, database rollback tests,
final-ZIP checksum and per-file hash verification, and an install from the
extracted artifact. Outputs go under ignored `dist/early-access`.

Plugin and database versions are independent:

- plugin and core DLL versions are aligned for an easily audited client build;
- `data/v1/index.json` owns the dataset version;
- a database-only release must not change the plugin version;
- a plugin package may bundle a known-good dataset for first installation.

See `EARLY_ACCESS.md`, `docs/releasing.md`, and `release/README.md` before
publishing. Automatic update checks remain out of scope until the public GitHub
repository and release endpoint are stable.

## Data and evidence rules

- Preserve `unknown` when evidence does not establish a value. Never convert it
  to `no` by assumption.
- Match simulator identities exactly. Do not add silent fuzzy matching.
- Every material claim needs source references, confidence, and a falsifiable
  basis.
- Simulator observations require the exact game version and verification date.
- Keep real-car hardware under `authentic_controls` and simulator behavior under
  `simulators[].behavior`; use an override for explicit differences.
- Imported candidates stay outside `data/v1` until reviewed.
- Every promoted record requires a checked-in approval under `curation/`.
- Chassis manufacturer is identity context, not automatically the marque.
- Do not silently inherit controls across aero, tyre, generation, or suffix
  variants. Record and review each intended relationship explicitly.

For a new or corrected record, update the record, source registry, index,
approval, relevant research/backlog documentation, and tests together. Follow
`CONTRIBUTING.md`, `docs/data-model.md`, and `docs/evidence-boundaries.md`.

## Contribution and privacy boundary

The plugin is offline. It has no analytics, account, background update check, or
automatic telemetry upload. Unmatched diagnostics and guided-verification
drafts stay under `%LOCALAPPDATA%\SimHub\AsDriven`. A draft never edits
the curated database or uploads itself. Maintainer validation and explicit
approval are required before release. See `PRIVACY.md` and
`docs/verification-observations.md`.

## Current handoff state

- Branch: `codex/stabilization`.
- Early-access client: 0.16.0.
- Dataset: 0.3.40 with 175 curated records.
- Certified development target: SimHub 9.11.22 and AMS2 1.6.9.91 on Windows.
- Broader AMS2 verification is deliberately deferred; use
  `docs/ams2-coverage-plan.md` and `research/ams2-coverage-manifest.json` when it
  resumes.
- Icon and naming redesign concepts under `docs/design/` are review-only and are
  not wired into production assets.
