# Authentic Controls Database project guidance

## Purpose

Build and maintain a simulator-independent, open-source database that tells a
sim racer which physical controls and shifting technique to use for an
authentic experience. SimHub is the first client, not the data format owner.

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
- `curation/`: checked-in reviewer approvals.
- `authentic_controls_db/`: dependency-free Python import, audit, promotion,
  and validation tools.
- `simhub/`: read-only .NET lookup library, SimHub adapter, diagnostics, and
  packaging.
- `tests/`: Python regression tests and legally safe parser fixtures.
- `docs/`: data-model, importer, provenance, audit, and integration guidance.

## SimHub plugin development

Act as an expert C# game telemetry developer. We are building a
[**SimHub**](https://www.simhubdash.com/) custom plugin using the standard
SimHub SDK. Adhere strictly to the required boilerplate classes (`IPlugin`,
`PluginManager`). Do not add multi-layered architectures, hypothetical
edge-case wrappers, or heavy abstractions. Use small, direct modifications.

## Required checks

Run these after data, schema, importer, or Python tooling changes:

```powershell
python -m authentic_controls_db validate
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
