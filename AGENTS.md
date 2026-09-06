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
- A mechanism the record establishes settles the technique that follows from it,
  and never the reverse. An established automatic cut settles the upshift lift;
  a dog box settles the downshift blip; an H-pattern gate settles
  `standing_start_clutch: required`, which is the only one of the three that does
  not also need `gearbox_type`. Tests enforce all three. See
  `docs/data-model.md`.
- Every registered source must be cited by a claim, or declare
  `"establishes": "nothing"` and say in its notes what was examined and why it
  settled nothing. Research that established nothing is worth keeping; a citation
  dropped by accident is not, and without the declaration the two are
  indistinguishable. Validation refuses either half being wrong.
- An override must not restate the authentic value. Only a refusal is a
  departure; an override that agrees makes the card announce a difference that is
  not there. 48 pre-existing overrides still do this and are a known cleanup, not
  a licence to add more.

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

## Maintainer state

- Work on `main`, the only branch, tracking `origin/main` at
  `github.com/Milky28/as-driven`.
- Client: 0.21.4 prepared locally; 0.21.3 is installed and published.
- Dataset: 0.5.50 with 285 curated records, and 0.5.49 is installed.
- Tested target: SimHub 9.11.22 and AMS2 1.6.9.91 on Windows.
- The history was rewritten on 2026-08-29. An older clone must re-clone rather
  than pull; see `docs/maintainer-handoff.md` for the full history note and
  current operational state.
- Read `docs/maintainer-handoff.md` only when the task concerns contribution
  processing, simulator coverage, known disagreements, or release history.
- `validate` compares the dataset version and record count quoted in this file,
  `README.md`, `CLAUDE.md`, `AGENTS.md`, and `docs/*.md` against
  `data/v1/index.json`. Update the dataset line above with the index, or
  validation fails.

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
- `driver_summary` is optional and usually absent. The generator drafts one only
  where a record's simulators disagree on driver technique; everything else it
  could assemble is already a Fit or Use row on the card. A promotion proposing
  no summary is working correctly, not failing. Write one by hand only with the
  maintainer. See `docs/driver-summaries.md`.
- `research/ams2-coverage-manifest.json` is checked in but generated from two
  machine-local inputs that are not: the audit under ignored `build/`, and the
  plugin's live diagnostics log under `%LOCALAPPDATA%`. `finalize_release` now
  refuses to write a manifest smaller than the committed one. If it does refuse,
  an input was unreadable on this machine - restore it. Do not force past it and
  do not commit the smaller file; a release that touched nothing about coverage
  once dropped 145 of 370 identities that way.
