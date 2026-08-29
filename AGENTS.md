# As Driven project guidance

## Purpose

Build and maintain an open, simulator-independent authentic-controls layer that
tells a sim racer which physical controls and shifting technique to use for an
authentic experience. The versioned JSON database is the source of truth;
SimHub is the reference client, not the data format owner.

## Scope

Keep the core dataset focused on controls that materially affect the user's
pre-session hardware choice or driving technique:

- wheel-rim category;
- shifter actuation, pattern, and forward gear count;
- clutch use for starts, upshifts, and downshifts;
- throttle lift, shift cut, and manual/automatic blipping;
- optional steering DOR as reference metadata.

Do not expand the core model into a general car database. TC, ABS, other driver
aids/electronics, general specifications, and handbrake construction are out of
scope unless a future proposal establishes a direct authentic-controls use case.

## Data rules

- Preserve `unknown` when evidence does not establish a value. Never convert it
  to `no` by assumption.
- Every material claim needs source references, confidence, and a falsifiable
  basis.
- Simulator behavior needs an exact verified game version and check date.
- Keep imported candidates separate from curated `data/v1` records.
- Require explicit review approvals before promotion.
- Match simulator identities exactly. Never introduce silent fuzzy matching.
- Treat chassis manufacturer as identity context, not automatically the vehicle
  marque.

## Repository map

- `schema/v1/`: versioned JSON Schema contracts.
- `data/v1/`: curated release index, sources, and car records.
- `curation/`: checked-in reviewer approvals and promotion review manifests.
- `as_driven_db/`: dependency-free Python import, audit, promotion,
  and validation tools.
- `research/`: checked-in research manifests, deterministic generators, and
  `ams2-identity-decisions.json`, the written reviewer outcomes for observed
  identities that are retired, third-party, or out of scope.
- `simhub/`: read-only .NET lookup library, SimHub adapter, diagnostics, and
  packaging.
- `tests/`: Python regression tests and legally safe parser fixtures.
- `docs/`: data-model, importer, provenance, audit, and integration guidance.

## Verification pipeline

A car reaches the database through this sequence. The user drives; that step
cannot be automated.

1. The user records a guided drive in the SimHub plugin's contribution
   workflow. Drafts land in
   `%LOCALAPPDATA%\SimHub\AsDriven\Verification\Drafts`.
2. `python -m as_driven_db import-observation <draft> --output
   build/staged.json` stages a bundle. Real-world identity is deliberately left
   as `REVIEW-REQUIRED`, because a drive cannot establish it.
3. A reviewer supplies identity and registered sources in a manifest under
   `curation/`.
4. `python -m as_driven_db promote-observation <manifest>` writes the
   record, approval, source, and index together. It refuses missing fields, any
   remaining `REVIEW-REQUIRED`, unregistered sources, and overwriting a curated
   record, and writes nothing unless every entry passes.
5. Regenerate `python -m research.build_ams2_coverage_manifest`, then validate.

An observed SimHub identity is not proof of official content. SimHub records any
car it sees, including mods. Check provenance when a name looks irregular or
predates the official car's release, and record the outcome as a decision rather
than silently queueing verification work.

## Current handoff state

- Branch: `codex/stabilization`; private remote `origin` at
  `github.com/Milky28/as-driven`.
- Client: 0.20.2.
- Dataset: 0.5.34 with 279 curated records.
- Certified development target: SimHub 9.11.22 and AMS2 1.6.9.91 on Windows.
- The ignored local contribution queue has 38 accepted cases with published
  feedback and six withdrawn, with nothing waiting on research or final review.
  Issues 46 through 48 are published curated-identity comparisons whose reviewed
  corrections produced dataset 0.5.33. Issue 1 for the Chevrolet
  Cruze Stock Car 2021 was restored from its original `new-identity` receipt
  after an exact-resubmission classification hid the already-stored draft, and
  is now published. Issues 31 through 33 are also published comparison cases;
  none needs further reconciliation.
- Use the maintainer workbench for contribution processing. Synchronization is
  serialized across browser tabs, and a same-issue retry with an unchanged
  attachment preserves the original classification. Issue 12 was restored as
  `new-identity` after exposing the former race and is now published.
- Of 370 AMS2 identities observed on this PC, 355 are covered exactly and 15
  are closed by written decisions. No observed identity currently awaits guided
  verification. New content can still be absent because the inventory only contains
  cars loaded here. See
  `docs/ams2-coverage-plan.md`.
- Six simulators are registered: 261 AMS2 entries, 21 AC, 18 ACC, 7 AC EVO, 6
  RaceRoom and 5 rFactor 2, with `ac-rally` reserved in the enums and not
  wired into the client. A drive from an unregistered game is held rather than
  lost and released when that game is registered; see
  `docs/registering-a-simulator.md`, and
  `docs/raceroom-downshift-measurement.md` for what a simulator's telemetry can
  and cannot establish.
- Assetto Corsa EVO is the active second-simulator development track. Seven
  records now carry reviewed AC EVO entries; this is development coverage, not
  part of the tested target. `docs/ac-evo-coverage-plan.md` owns
  its drive order and open questions.
- Assetto Corsa Competizione is recognized as `acc`; 18 exact entries are
  reviewed, including the completed ranked-ten comparison batch.
  ACC drafts record the exact Steam content build because its executables expose
  no useful file version. This remains development coverage outside the
  certified target. `docs/acc-coverage-plan.md` owns its drive order and identity
  traps.
- Original Assetto Corsa development now covers 21 records: seven AC-only and
  14 shared with another simulator. Each source fingerprints the exact installed
  implementation; this remains development coverage outside the certified
  tested target.
- The AC BMW 3.0 CSL and Ford GT40 Mk I guided drives require a manual blip in
  those implementations. That result is stored as a simulator override while
  the authentic real-car manual-blip field remains unknown.
- The disagreement audit contains 29 findings across 21 cars: nine supported
  departures, three provisional departures and 17 open authentic baselines. The
  Milano 55 GT1, 1974 Porsche 911 RSR manual-blip, and 2018 Volkswagen Virtus
  wheel findings are the three provisional cases after targeted research. The
  exact 2005 Saleen S7-R wheel and downshift procedure remain open; early-car
  evidence cannot be inherited.
  Treat the remaining gaps as documented negative results, not an active batch
  to search again without a new exact-source lead.
- `validate` compares the dataset version and record count quoted in this file,
  `README.md`, `CLAUDE.md`, `AGENTS.md`, and `docs/*.md` against
  `data/v1/index.json`. Update the line above with the dataset, or validation
  fails.
- Icon and brand-mark concepts under `docs/design/` are review-only and are not
  wired into production assets.

## SimHub plugin development

Act as an expert C# game telemetry developer. We are building a
[**SimHub**](https://www.simhubdash.com/) custom plugin using the standard
SimHub SDK. Adhere strictly to the required boilerplate classes (`IPlugin`,
`PluginManager`). Do not add multi-layered architectures, hypothetical
edge-case wrappers, or heavy abstractions. Use small, direct modifications.

## Required checks

Run these after data, schema, importer, or Python tooling changes:

```powershell
python -m as_driven_db validate
python -m unittest discover -s tests -v
```

Run this after .NET lookup or SimHub adapter changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

The SimHub build must remain non-installing: it may compile, test, and package
inside `simhub/dist`, but routine builds must not write to the installed SimHub
directory. Installation is a separate explicit user action.

## Change discipline

- Keep the JSON database independently usable without SimHub.
- Prefer small, reviewable record additions over bulk unverified coverage.
- Update schemas, documentation, validation, and tests together when changing
  a data contract.
- Do not commit generated `build/`, `dist/`, `bin/`, `obj/`, Python cache, or
  local telemetry artifacts.
- Preserve user changes and avoid destructive Git operations.
