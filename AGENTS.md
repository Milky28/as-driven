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

## Maintainer state

- Work on `main`, the only branch, tracking `origin/main` at
  `github.com/Milky28/as-driven`.
- Client: 0.21.2 locally; 0.21.0 is the published release.
- Dataset: 0.5.46 with 282 curated records, and 0.5.37 is installed.
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
