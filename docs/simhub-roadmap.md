# SimHub client roadmap

The SimHub integration is a read-only client. The JSON database remains useful
to websites, hardware selectors, voice assistants, Stream Deck tools, or other
telemetry applications without SimHub installed.

## Phase 0 — data contracts (this repository)

- Versioned JSON Schema, source registry, claim-level provenance, and tests.
- AMS2 seed records and staging importers for AMS2/iRacing.
- Stable simulator identity types and explicit unknown states.

Exit criterion: a released dataset validates independently of plugin code.

## Phase 1 — lookup library and diagnostics

- Build a small .NET reader for `data/v1/index.json` and car records.
- Validate supported `schema_version` at startup and retain the last known-good
  dataset if an update is invalid.
- Match in priority order: internal ID/car path, telemetry name, display name,
  class-scoped alias. Never fuzzy-match silently.
- For AMS2 specifically, SimHub's `CarId` currently delegates to `CarModel` and
  both contain the raw AMS2 car name. Treat that value as a telemetry-name
  alias, not as an independent internal ID.
- Log unmatched game/car identifiers and expose a copyable diagnostic value.
- Unit-test matching without loading SimHub.

Exit criterion: deterministic lookup for AMS2 and iRacing sample telemetry.

Status: **proof of concept implemented for AMS2.** The .NET reader rejects
unsupported schemas and escaping index paths, performs exact case-sensitive
identity matching, reports unmatched identifiers, and has a standalone
diagnostic plus regression runner. iRacing awaits curated sample records.

## Phase 2 — minimal SimHub plugin

The plugin detects game/car changes, calls the lookup library, and publishes
properties. It does not draw UI and does not own the database.

Suggested properties:

```text
AuthenticControls.RecordId
AuthenticControls.MatchStatus
AuthenticControls.DisplayName
AuthenticControls.ShiftType
AuthenticControls.GearCount
AuthenticControls.AutoBlip
AuthenticControls.ShiftCut
AuthenticControls.WheelRimShape
AuthenticControls.WheelRimSourceLabel
AuthenticControls.SteeringDOR                 (optional reference)
AuthenticControls.VerifiedGameVersion
AuthenticControls.Confidence
AuthenticControls.SourceSummary
AuthenticControls.PopupRevision
```

Suggested actions:

```text
AuthenticControls.ShowPopup
AuthenticControls.HidePopup
AuthenticControls.RefreshDatabase
AuthenticControls.CopyUnmatchedIdentifier
```

`PopupRevision` increments on a matched car/session change. Dash Studio can use
that edge to show a timed overlay while a mapped button calls `ShowPopup`.

Exit criterion: properties refresh exactly once per identity change, unknown
cars do not retain stale values, and the database works from a local path.

Status: **adapter implemented and installed; live runtime check pending.** The
plugin compiles against the locally installed SimHub 9.11.22 SDK, publishes
popup-ready properties, increments `PopupRevision` on a new match, clears stale
values on unknown cars, and supports an explicit database refresh action. The
installed DLL hashes and database copy have been verified, but the plugin has
not yet been loaded by a running SimHub session.

## Phase 3 — Dash Studio “pre-flight card”

Display hardware first, technique second, and evidence last:

```text
McLaren F1 GTR — GT1
Round rim (RM)
6-speed sequential stick
Upshift: automatic cut · Downshift: no auto-blip
Verified for AMS2 1.5.5.2 · confidence: medium
```

Unknown values are shown as “Unknown,” never hidden as “No.” An unmatched card
shows the raw identity needed for a contribution. Support both a timed overlay
and a persistent auxiliary display.

Exit criterion: readable at racing distance, recallable by button, and safe on
unmatched/partially known cars.

## Phase 4 — updates and broader coverage

- Ship a pinned dataset with the plugin and optionally poll signed GitHub
  releases, never a moving branch.
- Show dataset version and changelog before applying an update.
- Expand curated coverage to iRacing, then AC EVO and AC Rally.
- Provide an opt-in unmatched-identifier export; do not upload telemetry by
  default.

Exit criterion: rollback-safe updates and clear distinction among authentic
hardware, modeled behavior, and active session rules.
