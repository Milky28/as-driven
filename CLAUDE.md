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
- `release/`: separate database and client release tooling.
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

Build the complete release candidates on Windows with the supported SimHub
SDK installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-release.ps1
```

The release command runs database validation, Python tests, the complete
SimHub build, temporary install and uninstall tests, database rollback tests,
final-ZIP checksum and per-file hash verification, and an install from the
extracted artifact. Outputs go under ignored `dist/release`.

Plugin and database versions describe different things, but ship together:

- plugin and core DLL versions are aligned for an easily audited client build;
- `data/v1/index.json` owns the dataset version;
- every published release ships the full client package carrying the current
  dataset, including a release that exists only because the data changed, so a
  data-only release still bumps the plugin version;
- `release/build-database.ps1` still produces a portable dataset package for
  clients that are not SimHub, and `release/install-database.ps1` remains a
  maintainer tool rather than a user update route.

Users have exactly one update procedure: install the newest release over the
old one. A second route existed on paper but required a repository checkout,
which meant it was never actually available to the people it was written for.

See `docs/install.md`, `docs/releasing.md`, and `release/README.md` before
publishing. Automatic update checks remain out of scope: the check is manual and
notify-only by design, not merely until an endpoint exists. A dataset that
changed under a driver mid-session would rewrite the guidance they verified,
which is why installing stays deliberate.

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

The plugin has no analytics, account, background update check, or automatic
telemetry upload. Its one network feature is a manual update check: an endpoint
that is blank by default and a button that must be pressed. Blank means no
request is possible, the endpoint must be https, and the check reads two version
strings without downloading anything. A build assertion holds all three, because
`PRIVACY.md` states them as properties of the product. Unmatched diagnostics and guided-verification
drafts stay under `%LOCALAPPDATA%\SimHub\AsDriven`. A draft never edits
the curated database or uploads itself. Maintainer validation and explicit
approval are required before release. See `PRIVACY.md` and
`docs/verification-observations.md`.

## Repository history rewrite, 2026-08-29

The history was rewritten twice with `git filter-repo` and force-pushed the same
day. `output/pdf/homologation-form-renders/` (305 JPEG page renders of FIA
homologation forms, referenced by nothing, ~95 MB) and
`docs/design/2026-08-11-icon-brand-concepts/` (5 MB of review-only boards) were
removed from every commit. The pack went from 198.6 MB to 4.96 MB with all
commits intact.

State now: `origin/codex/stabilization` and `origin/main` both point at the
rewritten history, and `main` was fast-forwarded off the initial commit it had
been stranded on. Every commit from `232187a` forward has a new hash, so any
other clone of this repository is on an orphaned history and must re-clone
rather than pull.

- **The backup is still the only complete pre-rewrite copy.**
  `../authentic-controls-db-prepurge-2026-08-29/` holds `full-history.bundle`
  (verified complete, restorable with `git clone`) and the removed images as
  plain files. Do not delete it casually.
- GitHub still reports ~96 MB of disk usage because the unreachable objects have
  not been collected. They are unreachable, not gone. If the homologation scans
  must actually leave GitHub's servers, that needs a support request.
- The repository is still **private**, and the default branch is still
  `codex/stabilization` rather than `main`. Both are deliberate holds, not
  oversights.

Going public was the reason for the rewrite. A stripped-history `main` was
considered and rejected: the project's claim is auditable evidence, and the
history is where corrections are visible.

## Current handoff state

- Branch: `codex/stabilization`, synchronized with `origin`. `main` points at
  the same commit.
- Client: 0.20.2.
- Dataset: 0.5.34 with 279 curated records, and 0.5.34 is installed. The
  installed plugin binaries predate the GPLaps theme commit `c41bb36`; reinstall
  to pick it up.
- Tested target: SimHub 9.11.22 and AMS2 1.6.9.91 on Windows.
  Development has since moved to SimHub 9.12.2 and the drives recorded under
  it carry that in `client_version`; the tested pair is what the release
  claims, and has not been re-tested.
- **Open decisions nobody has made yet**, all deliberately left rather than
  forgotten:
  - `lamborghini-miura-sv` keeps `clutch: not-required` on a synchromesh
    gearbox because its own reviewed research says clutchless running shifts are
    ordinary technique there. Every other synchromesh record now says `required`.
    Either the research is wrong in the same way the importer was, or the Miura
    is a genuine exception. It is declared as an archetype deviation and named
    in `test_a_drive_alone_never_establishes_a_synchromesh_running_clutch`.
  - The manual update check is inert until a stable HTTPS URL serves
    `as-driven-latest.json`. The repository is private, so no such URL exists.
    Serve it from a stable path, never the per-tag release asset URL.
  - The README illustrates the pre-flight card with icon artwork because no
    screenshots of the running overlay exist. Wanted captures and widths are in
    `docs/development.md`.
  - `CHANGELOG.md` dataset history stops at 0.3.31.
- The local contribution queue has 38 accepted cases with published feedback and
  six withdrawn, with nothing waiting on research or final review. Issues 46
  through 48 are published curated-identity comparisons whose reviewed
  corrections produced dataset 0.5.33. Issue 1 for the Chevrolet Cruze
  Stock Car 2021 was restored from its original `new-identity` receipt after an
  exact-resubmission classification hid the already-stored draft, and is now
  published. Issues 31 through 33 are also published comparison cases; none
  needs further reconciliation. Generate each research brief from the workbench, import the
  completed result, then retain
  the explicit final-review and promotion gates. Research can be revisited after
  it completes: a case at final-review or manifest-review offers a regenerate
  and a replacement import beneath its forward action, because the brief gains
  questions over time and a case researched before one existed would otherwise
  carry that gap for good.
- The maintainer workbench is the preferred contribution interface. GitHub
  synchronization is serialized across browser tabs, and editing an issue
  without replacing its attachment preserves the original routing decision.
  Issue 12 exposed that race, was restored as `new-identity`, and is now
  published.
- Of 370 AMS2 identities observed on this PC, 355 are covered exactly and 15
  are closed by written decisions. No observed identity currently awaits guided
  verification. The inventory only holds cars that have been loaded here,
  so new content still needs `docs/ams2-coverage-plan.md` and
  `research/ams2-coverage-manifest.json`.
- Of 279 records, 251 carry an `archetype` classification: 180 match one of the
  23 registered mechanisms, 45 deviate, 15 are undetermined and 11 match none.
  Twenty-eight await classification. An
  archetype is descriptive and supplies no values, so a classification can never
  change a record. See `docs/archetypes.md`.
- **A mechanism the record already establishes settles the technique that follows
  from it.** `upshift.throttle_lift` was blank on 25 records whose own gearbox
  answered it - 21 with an established automatic cut, which is the thing that
  removes the lift, and 4 H-pattern cars with no cut at all - and
  `downshift.manual_blip` was blank on 4 established dog boxes, which cannot
  match the shaft speeds for the driver. Every one of those records listed the
  blank field as a *deviation* from its own registered archetype, so the reviewed
  archetype already held the value the record was missing. 26 records moved from
  deviating to matching. This runs one way only: a mechanism settles the
  technique, and the technique never settles the mechanism. Nothing was derived
  over an `unknown` construction, which is why 53 blips remain open.
- **The running-shift clutch was never a real-car fact until 0.5.34.** The guided
  drive asks whether the simulator accepts a shift without the clutch, and the
  importer wrote that answer straight into `authentic_controls`. 72 H-pattern
  records therefore told the driver no clutch was needed to change gear while
  their own `standing_start_clutch: required` said it was needed to pull away -
  a Chevette, a Copa Fusca and a 2002 turbo among them. Construction settles it:
  35 synchromesh records became `required`, 37 with an unestablished gearbox
  became `unknown`, and 10 dog boxes were already right because clutchless
  shifting is their authentic technique. **The observed acceptance is not
  recorded at all**, because it is not a departure: a real gearbox tolerates a
  clutchless shift too, so a simulator accepting one agrees with the real car
  and only the technique differs. A first pass wrote 142 overrides saying
  otherwise and made 71 entries read as "this simulator differs"; they were
  removed. Only a *refusal* is a departure, and the importer emits an override
  only for that. The 1973 Carrera RSR had reached the same
  conclusion through ordinary research and was deviating from its archetype
  because of it; all four synchromesh archetypes carried the same error, inherited
  from the records they were derived from. `lamborghini-miura-sv` is the one
  record whose own reviewed research says the opposite, so it keeps
  `not-required` as a declared deviation and is named in the test. See
  `docs/data-model.md`.
- **The gearbox construction research is closed.** `gearbox_type` is open in 37
  records: 22 are retired as cars a simulator invented, 5 are Copa Truck records
  a regulation frees, and the remaining 10 have each been searched and documented
  with what would unblock them. Six of those ten can never be settled by
  homologation - Formula One and Group C homologated nothing, and the M1's
  contemporary form predates the FIA synchroniser field - so what is left needs
  constructor or gearbox-specialist documentation. Reopen a record only when such
  a source appears, not by re-running the searches already recorded in
  `docs/gearbox-construction-research.md`.
- **Some records still carry an automatic blip measured before the measurement
  was corrected**, and `research/auto-blip-premeasurement.json` holds the list:
  its `records` array is what remains and its `cleared` array is what has been
  re-driven. Read the counts there rather than here, because this bullet has
  twice been left behind by cars being cleared. Until 2026-08-17 the guided drive
  read the blip from the highest throttle seen since the attempt began, so
  throttle the driver was still carrying before the lift counted as the car
  blipping. The fault could only invent a blip, never hide one, so every `no` is
  sound and only `yes` is exposed, and a false `yes` also derives
  `manual_blip: not-required` - the card then tells a driver no blip is needed on
  a car that needs one. The fourteen stick and dog gearboxes were re-driven and
  seven were wrong; what remains is paddle cars where a blip is expected, and
  each clears when that car is next driven. Do not re-drive them as a batch.
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
  car count, no mod ecosystem yet and no DLC. Seven existing real-car records
  now carry separately reviewed `ac-evo` entries, proving that a second
  simulator's drive can join a record without inheriting another simulator's
  behavior. The client canonicalises SimHub's `AssettoCorsaEvo` to `ac-evo`;
  this remains development coverage rather than part of the tested
  tested target. Roster overlaps, drive order and name matches to avoid
  are in `docs/ac-evo-coverage-plan.md`.
- **Assetto Corsa Competizione** is recognized separately as `acc`. Eighteen exact
  entries are reviewed after the ranked-ten comparison batch; the Audi R8 LMS
  GT3 Evo II is the first car driven in four simulators. ACC drafts pin the Steam
  build id because its executables carry no useful file version. ACC remains
  outside the tested target. Exact overlaps, identity traps and the next
  backlog are in `docs/acc-coverage-plan.md`.
- **Original Assetto Corsa** has 21 reviewed entries: seven AC-only records and
  14 shared with another simulator. Each source fingerprints the exact installed
  implementation. This remains development coverage outside the tested
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
- **RaceRoom Racing Experience is registered as `raceroom`**, and an
  unrecognised simulator is now held rather than lost. The client answers
  `other` for a game it cannot canonicalise, and the draft records
  `source_game_name` exactly as the telemetry client reported it. Intake stores
  such a drive and classifies it `unregistered-simulator`; the case sits in
  `blocked-on-simulator` offering no actions; promotion refuses it outright.
  The evidence is kept, so registering the game later renames those
  observations rather than costing a contributor every drive again. The queue
  groups them by game, because forty held cases are one decision and not forty.
  RaceRoom publishes no engine torque, so its automatic cut is unmeasurable in
  the same way AC's and ACC's are, and an unregistered simulator is assumed
  unmeasurable too. See `docs/registering-a-simulator.md`.
- **Six simulators are registered**, with 261 AMS2 entries, 21 AC, 18 ACC, 7 AC
  EVO, 6 RaceRoom and 5 rFactor 2. `ac-rally` is reserved: it sits in the enums
  so a record naming it validates, and the client does not canonicalise it. See
  `docs/registering-a-simulator.md` for the nine places a registration touches
  and for what a first drive should be read for.
- **A drive from an unregistered simulator is held, not lost.** The client
  answers `other` and records `source_game_name` exactly as the telemetry
  reported it; intake stores the drive, the case sits in `blocked-on-simulator`
  offering no actions, and promotion refuses it. Registering the game releases
  every drive waiting on it through an ordinary sync. That took four separate
  short circuits to make true - the draft's own simulator field, two sync
  shortcuts and intake's duplicate detector - which now share one question,
  `_held_case_is_now_releasable`.
- **RaceRoom cannot answer four of the drive's questions**, and says so rather
  than answering them wrongly: no engine torque for the cut, a clutch channel
  reading 100% at rest, a throttle channel reading 24% at rest, and a gearbox
  that accepts a downshift at any engine speed. Three records had a RaceRoom
  automatic blip retracted to `unknown` once that was measured. It still
  establishes gear count, actuation, gate and rim. See
  `docs/raceroom-downshift-measurement.md`.
- rFactor 2 discriminates where RaceRoom did not: a Radical SR3 produced a
  shift-local torque interruption where a BMW M2 published no torque at all, and
  both report no downshift blip. Its cut was briefly marked unmeasurable on the
  strength of that one M2 drive and the rule was removed again. One drive is a
  fact about one car; a channel that reads wrong *at rest* is a property of the
  simulator and generalises immediately.
- **Where research establishes a real-car control, the record cites the source
  rather than the drive.** The promoter used to bundle upshift, downshift,
  standing-start clutch and the wheel rim into one claim credited to the guided
  drive, so a manufacturer manual's finding was filed as "directly observed
  during the guided drive" - on the Radical, a drive that had observed the
  opposite. The proposal now emits `sourced_control_paths` and the note naming
  what the sources left open is computed rather than constant.
- **207 rim observations predate the wheel-rim vocabulary** of 2026-08-16,
  against 100 after it. Four records where simulators disagree about a rim are
  listed in `docs/wheel-rim-reverification.md`. Exact cockpit evidence resolved
  the GT-R and 911 GT3 R as simulator departures. The R390 and exact 2005 Saleen
  S7-R remain open authentic baselines; restored early-car Saleen photographs
  cannot establish the later second-series wheel. Where an exact manufacturer
  cockpit photograph establishes the rim, a later observation must agree with
  it, and a test says so.
- **The disagreement audit is current and has no immediate research batch.** It
  contains 29 findings across 21 cars: nine supported departures, three
  provisional departures and 17 open authentic baselines. The Milano 55 GT1,
  1974 Porsche 911 RSR manual-blip, and 2018 Volkswagen Virtus wheel findings remain provisional after targeted
  research. Saleen downshift technique and wheel geometry were returned to
  `unknown` for the exact 2005 car while every simulator observation was kept as
  an override. The remaining open findings are documented negative results;
  reopen one only when a new exact-source lead appears.
- Icon and naming redesign concepts under `docs/design/` are review-only and are
  not wired into production assets.
