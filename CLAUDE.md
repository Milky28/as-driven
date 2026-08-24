# As Driven development guide

## Project purpose

As Driven is an open, simulator-independent authentic-controls layer that tells
sim racers which physical controls and shifting technique to use for an
authentic experience. The versioned JSON database is the source of truth;
SimHub is the reference client and does not own the data format.

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
- `data/v1/`: curated index, sources, control archetypes, and one JSON record
  per car.
- `curation/`: explicit reviewer approvals required for promotion.
- `as_driven_db/`: dependency-free Python validation, import, audit,
  promotion, and site-rendering tools.
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
- Early-access client: 0.19.0.
- Dataset: 0.4.32 with 263 curated records.
- Certified development target: SimHub 9.11.22 and AMS2 1.6.9.91 on Windows.
- The ignored local contribution queue has four active `identity-research`
  cases: issues 9 through 12, covering the AC Shelby Daytona Coupe, Ferrari 250
  GTO, Lamborghini Miura P400 SV and Kunos Ford Mustang 2015. Generate each
  research brief from the workbench, import the completed result, then retain
  the explicit final-review and promotion gates. No case is currently waiting
  at final review.
- The maintainer workbench is the preferred contribution interface. GitHub
  synchronization is serialized across browser tabs, and editing an issue
  without replacing its attachment preserves the original routing decision.
  Issue 12 exposed that race and has been restored locally as `new-identity`.
- Of 365 AMS2 identities observed on this PC, 349 are covered exactly and 15
  are closed by written decisions. Chevrolet Cruze Stock Car 2021 remains in
  the guided queue. The inventory only holds cars that have been loaded here,
  so new content still needs `docs/ams2-coverage-plan.md` and
  `research/ams2-coverage-manifest.json`.
- Of 260 records, 252 carry an `archetype` classification: 158 match one of the
  23 registered mechanisms, 68 deviate, 15 are undetermined and 11 match none.
  Eight await classification. An
  archetype is descriptive and supplies no values, so a classification can never
  change a record. See `docs/archetypes.md`.
- **The gearbox construction research is closed.** `gearbox_type` is open in 37
  records: 22 are retired as cars a simulator invented, 5 are Copa Truck records
  a regulation frees, and the remaining 10 have each been searched and documented
  with what would unblock them. Six of those ten can never be settled by
  homologation - Formula One and Group C homologated nothing, and the M1's
  contemporary form predates the FIA synchroniser field - so what is left needs
  constructor or gearbox-specialist documentation. Reopen a record only when such
  a source appears, not by re-running the searches already recorded in
  `docs/gearbox-construction-research.md`.
- **Eighty-six records still carry an automatic blip measured before the
  measurement was corrected.** Until 2026-08-17 the guided drive read the blip
  from the highest throttle seen since the attempt began, so throttle the driver
  was still carrying before the lift counted as the car blipping. The fault could
  only invent a blip, never hide one, so every `no` is sound and only `yes` is
  exposed, and a false `yes` also derives `manual_blip: not-required` - the card
  then tells a driver no blip is needed on a car that needs one. The fourteen
  stick and dog gearboxes were re-driven: seven were wrong. The eighty-six that
  remain are paddle cars where a blip is expected, and each clears when that car
  is next driven. Do not re-drive them as a batch. See
  `research/auto-blip-premeasurement.json`.
- A drive-derived `downshift.manual_blip: required` over an unknown construction
  is unsupported rather than established. Every time the construction was later
  established for a car in that position - both Formula Vee records and the
  Diablo SV-R - the authentic value was revised to `optional` and the simulator's
  demand moved to an override. Five real cars still carry it knowingly; four
  cars a simulator invented are outside the rule, because a car with no real
  referent has no real gearbox to be wrong about. See `docs/data-model.md`.
- Guided drives may still establish simulator-only technique while the real-car
  answer remains unknown. The AC BMW 3.0 CSL and Ford GT40 Mk I two-stage tests
  now retain `downshift.manual_blip: required` as simulator overrides rather
  than losing the result or asserting it as authentic real-car behavior.
- Active second simulator: **Assetto Corsa EVO**, chosen for a relatively small
  car count, no mod ecosystem yet and no DLC. Four existing real-car records
  now carry separately reviewed `ac-evo` entries, proving that a second
  simulator's drive can join a record without inheriting another simulator's
  behavior. The client canonicalises SimHub's `AssettoCorsaEvo` to `ac-evo`;
  this remains development coverage rather than part of the certified
  early-access target. Roster overlaps, drive order and name matches to avoid
  are in `docs/ac-evo-coverage-plan.md`.
- **Assetto Corsa Competizione** is recognized separately as `acc`. Eighteen exact
  entries are reviewed after the ranked-ten comparison batch; the Audi R8 LMS
  GT3 Evo II is the first car driven in four simulators. ACC drafts pin the Steam
  build id because its executables carry no useful file version. ACC remains
  outside the certified target. Exact overlaps, identity traps and the next
  backlog are in `docs/acc-coverage-plan.md`.
- **Original Assetto Corsa** has 17 reviewed entries: four AC-only records and
  13 shared with another simulator. Each source fingerprints the exact installed
  implementation. This remains development coverage outside the certified
  target.
- A shared name across simulators is not a shared car. Exact matching fails
  closed, but merging a second simulator's entry onto the wrong record fails
  open - the plugin answers confidently with another car's controls. Road against
  racing, evolution suffixes, generations and kit variants are the recurring
  traps, and a differing specification wants a new record rather than a second
  entry. See `docs/data-model.md`.
- Record IDs name the real car with no simulator prefix. A second simulator's
  drive joins the existing record as another `simulators[]` entry rather than
  forking a second record, and an approval names the simulator it approves.
- Icon and naming redesign concepts under `docs/design/` are review-only and are
  not wired into production assets.
