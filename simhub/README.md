# SimHub proof of concept

This directory contains a read-only SimHub adapter for the independent JSON
database. The plugin never rewrites curated data and does not contain overlay
UI. Its job is to turn the current SimHub game/car identity into stable
properties that a Dash Studio popup can consume.

## Components

```text
AuthenticControls.Core          JSON reader, exact matcher, guidance formatter
AuthenticControls.Plugin        Minimal SimHub IDataPlugin adapter
AuthenticControls.Diagnostics   Lookup without launching SimHub
AuthenticControls.Core.Tests    Dependency-free .NET regression runner
dash/                           Native Dash Studio pre-flight card generator
build.ps1                       Build, test, and create a SimHub-ready package
install.ps1                     Back up and install without resetting layouts
```

The core library supports schema version `1.0.0`, rejects index paths outside
the data directory, fails on conflicting exact identities, and performs no
fuzzy matching. AMS2 game names are normalized to the database's `ams2` key,
but car identifiers remain exact and case-sensitive.

## Build and test

The build uses the SDK assemblies included with the locally installed SimHub.
It does not download packages or copy anything into SimHub.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

A successful build runs the .NET lookup assertions and creates:

```text
simhub/dist/AuthenticControls/
  AuthenticControls.Plugin.dll
  AuthenticControls.Core.dll
  DashTemplates/Authentic Controls Preflight Overlay/...
  DashTemplates/Authentic Controls Preflight Compact/...
  DashTemplates/Authentic Controls Preflight Glance/...
  DashTemplates/Authentic Controls Preflight Display/...
  OverlayLayouts/Authentic Controls.olayout
  OverlayLayouts/Authentic Controls 5120x1440.olayout
  PluginsData/AuthenticControls/Database/data/v1/...
```

The package mirrors SimHub's folder layout. Installing it is a separate,
explicit step: close SimHub, run `simhub/install.ps1`, restart SimHub, and enable
**Authentic Controls** under Settings > Plugins. The installer creates a
timestamped rollback backup and preserves existing `Authentic Controls*.olayout`
files by default, so upgrades do not reset personalized positions. Pass
`-ReplaceOverlayLayouts` only when intentionally restoring the packaged
positions. The build script itself never performs installation.
When upgrading from the former 900-pixel Detailed surface, the installer keeps
its center position and changes only that part's width to 840 pixels. Any part
already given a different custom width is left untouched.

## Diagnostic lookup

After building, test a telemetry identity without starting SimHub:

```powershell
.\simhub\AuthenticControls.Diagnostics\bin\Release\AuthenticControls.Diagnostics.exe .\data\v1 Automobilista2 "Dallara F301"
```

An exact match exits with code 0. An unknown car exits with code 1 and prints
`MatchStatus=unmatched` plus the raw game/car values.

Plugin version 0.9.5 records live unmatched identities automatically in:

```text
%LOCALAPPDATA%\SimHub\AuthenticControls\Diagnostics\unmatched-identities.jsonl
```

Each JSON Lines entry contains the UTC timestamp, game name and detected
executable version, exact `CarModel`, `CarId`, and class, plus the active
dataset and SimHub versions. Entries are deduplicated by game version and raw
identity across SimHub restarts. A malformed manually edited line does not
prevent later observations from being appended. The **Authentic Controls**
settings page displays this path and provides **Open diagnostics folder**.

## Published SimHub properties

The plugin class is named `AuthenticControls`, so its attached properties are
available under that prefix:

```text
AuthenticControls.HasMatch
AuthenticControls.MatchStatus
AuthenticControls.RawGameName
AuthenticControls.RawCarIdentifier
AuthenticControls.DatabasePath
AuthenticControls.UnmatchedLogPath
AuthenticControls.UnmatchedLogCount
AuthenticControls.LastUnmatchedCarModel
AuthenticControls.LastUnmatchedCarId
AuthenticControls.LastUnmatchedCarClass
AuthenticControls.LastUnmatchedGameVersion
AuthenticControls.UnmatchedLogError
AuthenticControls.DatasetVersion
AuthenticControls.RecordId
AuthenticControls.DisplayName
AuthenticControls.CarClass
AuthenticControls.ShiftType
AuthenticControls.ShiftActuation
AuthenticControls.ShiftPattern
AuthenticControls.GearCount
AuthenticControls.UpshiftGuidance
AuthenticControls.DownshiftGuidance
AuthenticControls.TechniqueSummary
AuthenticControls.TechniqueSummaryLine1
AuthenticControls.TechniqueSummaryLine2
AuthenticControls.TechniqueSummaryCompactLine1
AuthenticControls.TechniqueSummaryCompactLine2
AuthenticControls.StandingStartClutch
AuthenticControls.AutoBlip
AuthenticControls.ShiftCut
AuthenticControls.WheelRimShape
AuthenticControls.WheelRimSourceLabel
AuthenticControls.HasSteeringDOR
AuthenticControls.SteeringDOR
AuthenticControls.VerifiedGameVersion
AuthenticControls.Confidence
AuthenticControls.SourceSummary
AuthenticControls.MatchKind
AuthenticControls.GuidanceSummary
AuthenticControls.PreviewActive
AuthenticControls.PopupRevision
AuthenticControls.PopupVisible
AuthenticControls.PopupDurationSeconds
AuthenticControls.PopupSize
AuthenticControls.PopupDetailedVisible
AuthenticControls.PopupCompactVisible
AuthenticControls.PopupGlanceVisible
```

`PopupRevision` increments once when a new matched car is observed. Repeated
telemetry frames do not change it. Moving to an unknown car immediately clears
the previous record and does not increment the revision.

The plugin also registers `AuthenticControls.RefreshDatabase`,
`AuthenticControls.ShowPopup`, `AuthenticControls.HidePopup`, and
`AuthenticControls.TogglePopup`. It also registers
`AuthenticControls.OpenDiagnosticsFolder` and
`AuthenticControls.ReturnToLiveCar` for optional button/event mappings.
A new car identity automatically shows the
overlay card for ten seconds by default, including an unmatched identity that
needs contribution. The duration can be set from 1–60 seconds on the
**Authentic Controls** SimHub settings page and persists across restarts.
`ShowPopup` keeps the card visible until `HidePopup` is called; `TogglePopup`
provides the same behavior with one mapped button. The database is normally
loaded from:

```text
<SimHub>/PluginsData/AuthenticControls/Database/data/v1
```

For local development, the `AUTHENTIC_CONTROLS_DATA` environment variable can
override that path.

## Map a popup button

In SimHub, open **Controls and events > Controls**, choose **New mapping**, and
capture the wheel or button-box input. In the action picker, search for
`AuthenticControls` and select `AuthenticControls.TogglePopup`. That single
mapping shows the card persistently when it is hidden and hides it when it is
visible. For separate buttons, create one mapping each for
`AuthenticControls.ShowPopup` and `AuthenticControls.HidePopup`.

The automatic timeout is separate from manual recall. Open the **Authentic
Controls** plugin page, choose Detailed (840×360), Compact (520×300), or Glance
(320×120), choose 1–60 seconds, and click **Save popup settings**. Compact and
10 seconds are the defaults; both saved values are reused after restarting
SimHub. Load the included **Authentic Controls** overlay layout once and move it
to the preferred screen position. It already contains all three popup sizes.

## Current boundary

It has been compiled against the installed SimHub 9.11.22 SDK. Client version
0.10.10 is compatible with dataset 0.3.11; the previously installed beta
bundled dataset 0.3.10. It packages the approved high-fidelity 128x128 raster
artwork in every Dash Studio template. The blue open-rail layout groups Wheel
and Shift under `PHYSICAL CONTROLS`, groups Upshift and Downshift under
`SHIFTING TECHNIQUE`, enlarges the existing icons, and replaces the ambiguous
`AC` badge with a letter-free wheel-and-shift-gate mark. This keeps Detailed,
Compact, and Glance artwork aligned while preserving persisted popup size
selection. A live check on 2026-08-10 with
SimHub 9.11.22 and AMS2 executable version 1.6.9.91 confirmed an exact
telemetry-name match for `McLaren F1 GTR`, stale-value clearing for the
unmatched `Ginetta G55 GT4`, and `PopupRevision` transitions of 1, 1, and 2
across matched, unmatched, and matched states. The `RefreshDatabase` action
also reloaded all fifteen dataset records successfully. Dataset 0.3.3 added a
sixteenth independently researched Dodge Viper GTS-R record. Dataset 0.3.4
first added the Alpine A424 and Ligier JS P217, then the completed live batch
raised the curated total to 28 records. Native Dash Studio overlay
and persistent-display artifacts are included; see
[`dash/README.md`](dash/README.md) for their visibility and installation
contract. Version `0.9.1` retains the display-label, lift-throttle mapping,
production raster-icon refinements, and removal of redundant Detailed-card
technique prose for all
transmissions and names the automatic actions `Automatic throttle cut` and
`Automatic throttle blip`. It adds a distinct GT-style wheel category and maps
the documented AMS2 `GTF1*` source family to the reviewed GT wheel icon. Dataset
0.3.0 added five reviewed Formula-rim records: Formula V10 Gen2, Formula Reiza,
Formula Ultimate Hybrid Gen1, Formula Ultimate Gen2, and Formula USA 2023.
Dataset 0.3.1 adds four exact telemetry identities observed live in AMS2
1.6.9.91: the B- and M-tyre High Downforce Formula V10 Gen2 variants, Formula
Ultimate Hybrid Gen1 - High Downforce, and Formula USA 2023 - High Downforce.
No fuzzy or suffix matching is used.
Dataset 0.3.2 follows Reiza's official V1.6.9 rebranding and live telemetry:
Formula Reiza is now displayed as Formula V8 Gen3 and matches
`Formula V8 Gen3 - High Downforce`; Formula Ultimate Gen2 is now displayed as
Formula Hybrid Gen3 and matches `Formula Ultimate Hybrid Gen3 - High
Downforce`. The historical telemetry names remain valid exact identities.
Dataset 0.3.3 adds the exact `Dodge Viper GTS-R` / `GT1_05` identity with the
six-speed sequential stick, standing-start clutch, automatic cut, automatic
blip, and round rim tested or researched for the AMS2 representation. Record
notes retain the original FIA H-pattern T56 and privateer-conversion context;
the perceptually tested cut and blip remain medium-confidence.
Dataset 0.3.4 adds the exact base `Alpine A424` / `LMDh` identity with a
seven-speed paddle sequential, hybrid clutch-free move-off, no-lift running
shifts, directly observed automatic blip, and closed prototype-style display
rim. Automatic cut remains medium-confidence, and the separate Low Downforce
identity is an exact approved aero-package alias whose inherited controls have
not been separately live-tested.
Dataset 0.3.4 also adds the exact `Ligier JS P217` identity, directly verified
with identical six-speed paddle controls in `LMP2` and `LMP2_Gen1` class
contexts.
The completed 0.3.4 batch adds ten more live-verified cars: Oreca 07,
Lamborghini SC63, Ligier JS P320, Ligier JS P4, Aston Martin Valkyrie Hypercar,
Audi R8 LMS GT4, Chevrolet Corvette Z06 GT3.R, Lamborghini Huracan Super
Trofeo EVO2, Aston Martin Vantage GT4 Evo, and Aston Martin Vantage GTE. The
closed display-wheel cars use the distinct `prototype` value; open-top
no-display racing rims use `gt-style`. Exact Low Downforce aliases are included
only for Oreca 07, SC63, and Corvette Z06 GT3.R, with their untested
aero-inheritance status visible in provenance and notes.
Dataset 0.3.5 raises the curated total to 34 with Lamborghini Murcielago R-GT,
Maserati MC12 GT1, Lister Storm GTM, Panoz Esperante GTLM, Gillet Vertigo
Streiff, and Lamborghini Diablo SV-R. The first five use six-speed sequential
sticks, require the clutch from rest, provide automatic cut but no automatic
blip, and use D-shaped no-display rims. The Diablo is a five-speed dogleg
H-pattern with lift/manual-rev-match technique, no automatic cut or blip, and a
round rim. Murcielago and MC12 Low Downforce identities are exact approved
aero aliases whose controls were not separately tested.
Dataset 0.3.6 records manual throttle blipping as the required authentic
driver-supplied rev-matching technique for the five verified historical
sequential-stick cars whose live tests established that no automatic blip is
provided.
Dataset 0.3.7 raises the curated total to 38 with exact live identities for
`Aston Martin DBR9`, `Chevrolet Corvette C5-R`, `Saleen S7-R GT1`, and
`Milano GT55`. All four directly verified a six-speed sequential stick,
standing-start clutch, automatic cut, no automatic blip, required manual rev
matching, and a round no-display rim. DBR9 and C5-R Low Downforce identities
inherit their verified base controls as explicit untested aero assumptions.
Dataset 0.3.8 raises the curated total to 42 with `Milano GT36`, `Porsche 996
GT3 RSR`, `Spyker C8 Spyder GT2-R`, and `TVR Tuscan T400R GT2`. All four use
the directly observed six-speed sequential stick, standing-start clutch,
automatic cut, and round no-display rim. The Porsche has automatic downshift
blipping; the other three require manual rev matching.
Dataset 0.3.9 raises the curated total to 45 with `Audi R8 LMP1`, `Courage C60
Hybrid`, and `Dallara SP1`. All three require the clutch from rest and provide
automatic cut and blip. Their reviewed hardware is respectively paddles/yoke,
sequential stick/D-shaped small-display rim, and replay-animated
paddles/prototype display rim.
Dataset 0.3.10 raises the curated total to 47 with `Lola B05/40 V8` and `Lola
B05/40 Turbo`. Both directly use clutch-free move-off, six paddle gears,
automatic cut and blip, and D-shaped display rims. The V8 Low Downforce exact
identity inherits its verified base controls as an explicit untested aero
assumption.
Version 0.9.5 also follows SimHub's native feature-page convention. A branded
blue-and-white 24x24 wheel-and-shift-gate mark supplies the left-menu icon,
so **Authentic Controls** can be pinned through **Add and remove features**.
The native page shows live match state, current car and record, plugin and
dataset versions, record count, runtime errors, popup Show/Hide controls,
database refresh, popup settings, and diagnostics access. Dash Studio remains
the owner of overlay layout, positioning, and rendering.
Version 0.10.0 adds a searchable curated-car selector to that page. Selecting
**Preview selected car** opens the normal popup with an explicit `PREVIEW`
badge and keeps it available for pre-session hardware planning or layout
testing. **Return to live car** exits preview; starting a simulator session also
returns control to live telemetry automatically.
Version 0.10.1 uses SimHub's forced-overlay mode for idle previews, so the
selected card is rendered even when no game is running. The native page keeps
**Live telemetry** and **Preview active** status separate, and the temporary
preview overlay is stopped when preview ends or a game session begins.
Version 0.10.2 reuses that temporary overlay manager when another car is
selected. This prevents repeated previews from starting duplicate `Window1`
overlay windows while still updating the card immediately.
Version 0.10.3 starts only the selected surface in idle preview mode, so preview
creates one overlay window instead of one each for Detailed, Compact, and
Glance. Preview cards carry a prominent `PREVIEW — NOT LIVE` badge, and the
native page provides a clearly labeled **Close preview** button. Compact grows
to 520×300 and includes the two-line driving-technique summary at a smaller type
size; Glance remains icon-only. Detailed remains 840×360, matching the popup
size dropdown.
Version 0.10.4 replaces the dark transparent settings-page mark with the blue
and white brand badge, removes the duplicate preview explanation above the car
browser, and adds Compact-specific technique wrapping. The Compact lines use a
roughly 125-character wrap target and 9.5-point text so they fill the available
width without changing the 520×300 surface.
Version 0.10.5 adopts the selected ImageGen-derived identity: a steering wheel,
prominent physical shift lever, and simplified lower H-gate. SimHub's sidebar
receives the standalone transparent white glyph instead of a filled tile, while
the settings page and popup use the same mark on the blue badge. Compact now
keeps guidance up to roughly 135 characters on its first line, filling more of
the available width before wrapping.
Version 0.10.6 corrects the measured Compact text boundary after live rendering
showed that a 126-character Diablo sentence still clipped. Compact now wraps at
the last word near 116 characters, placing `downshifts.` safely on line two
while continuing to use nearly all of line one.
Version 0.10.7 moves that safe boundary to approximately 110 characters after
the Alpine A424 preview exposed remaining right-edge clipping at the prior
limit.
Version 0.10.8 packages the subsequent four-car GT2 verification batch without
further surface changes.
Version 0.10.9 packages the three-car LMP1 2005 verification batch without
further surface changes.
Version 0.10.10 packages the two-car LMP2 2005 verification batch without
further surface changes.
Compact uses an unambiguous checkmark-only match indicator,
and confidence labels use consistent sentence capitalization. Detailed, Compact, and Glance
were all live-verified with AMS2 telemetry on 2026-08-10. The packaged
**Authentic Controls** layout was then loaded, positioned, and confirmed to
survive full SimHub and AMS2 restarts with automatic popup behavior intact.
