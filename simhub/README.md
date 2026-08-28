# SimHub reference client

This directory contains the reference client for the independent As Driven JSON
database. The plugin never rewrites curated data. It turns the current SimHub
game/car identity into stable properties consumed by the packaged pre-flight
cards and guided-verification overlay, and it writes local draft observations
for later human review.

## Components

```text
AsDriven.Core          JSON reader, exact matcher, guidance formatter
AsDriven.Plugin        Minimal SimHub IDataPlugin adapter
AsDriven.Diagnostics   Lookup without launching SimHub
AsDriven.Core.Tests    Dependency-free .NET regression runner
dash/                           Native Dash Studio pre-flight card generator
build.ps1                       Build, test, and create a SimHub-ready package
install.ps1                     Back up and install without resetting layouts
uninstall.ps1                   Back up and remove binaries while preserving data
test-install.ps1                Exercise installation in a temporary directory
test-uninstall.ps1              Exercise removal in a temporary directory
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
simhub/dist/AsDriven/
  AsDriven.Plugin.dll
  AsDriven.Core.dll
  DashTemplates/As Driven Preflight Overlay/...
  DashTemplates/As Driven Preflight Compact/...
  DashTemplates/As Driven Preflight Glance/...
  DashTemplates/As Driven Preflight Display/...
  DashTemplates/As Driven Verification Drive/...
  OverlayLayouts/As Driven.olayout
  OverlayLayouts/As Driven 5120x1440.olayout
  PluginsData/AsDriven/Database/data/v1/...
```

The package mirrors SimHub's folder layout. A public release adds
`Install As Driven.cmd` at the ZIP root. Close SimHub, double-click that file,
restart SimHub, and enable **As Driven** under Settings > Plugins. Developers
can run `simhub/install.ps1` directly. The installer creates a
timestamped rollback backup and preserves existing `As Driven*.olayout`
files by default, so upgrades do not reset personalized positions. Pass
`-ReplaceOverlayLayouts` only when intentionally restoring the packaged
positions. The build script itself never performs installation.
When upgrading from the former 900-pixel Detailed surface, the installer keeps
its center position and changes only that part's width to 840 pixels. Any part
already given a different custom width is left untouched.

To remove the plugin, close SimHub and run `simhub/uninstall.ps1`. By default it
backs up and removes only the As Driven binaries and packaged Dash
Studio templates. It preserves the database, settings, diagnostics,
verification drafts, and customized overlay layouts. Pass
`-RemovePackagedLayouts` only when those layout files should also be backed up
and removed.

## Diagnostic lookup

After building, test a telemetry identity without starting SimHub:

```powershell
.\simhub\AsDriven.Diagnostics\bin\Release\AsDriven.Diagnostics.exe .\data\v1 Automobilista2 "Dallara F301"
```

An exact match exits with code 0. An unknown car exits with code 1 and prints
`MatchStatus=unmatched` plus the raw game/car values.

Plugin version 0.9.5 records live unmatched identities automatically in:

```text
%LOCALAPPDATA%\SimHub\AsDriven\Diagnostics\unmatched-identities.jsonl
```

Each JSON Lines entry contains the UTC timestamp, game name and detected
executable version, exact `CarModel`, `CarId`, and class, plus the active
dataset and SimHub versions. Entries are deduplicated by game version and raw
identity across SimHub restarts. A malformed manually edited line does not
prevent later observations from being appended. The **As Driven**
settings page displays this path and provides **Open diagnostics folder**.

## Published SimHub properties

The plugin class is named `AsDriven`, so its attached properties are
available under that prefix:

```text
AsDriven.HasMatch
AsDriven.MatchStatus
AsDriven.RawGameName
AsDriven.RawCarIdentifier
AsDriven.DatabasePath
AsDriven.UnmatchedLogPath
AsDriven.UnmatchedLogCount
AsDriven.LastUnmatchedCarModel
AsDriven.LastUnmatchedCarId
AsDriven.LastUnmatchedCarClass
AsDriven.LastUnmatchedGameVersion
AsDriven.UnmatchedLogError
AsDriven.DatasetVersion
AsDriven.RecordId
AsDriven.DisplayName
AsDriven.CarClass
AsDriven.ShiftType
AsDriven.ShiftActuation
AsDriven.ShiftPattern
AsDriven.GearCount
AsDriven.UpshiftGuidance
AsDriven.DownshiftGuidance
AsDriven.TechniqueSummary
AsDriven.TechniqueSummaryLine1
AsDriven.TechniqueSummaryLine2
AsDriven.TechniqueSummaryCompactLine1
AsDriven.TechniqueSummaryCompactLine2
AsDriven.StandingStartClutch
AsDriven.AutoBlip
AsDriven.ShiftCut
AsDriven.WheelRimShape
AsDriven.WheelOpenTop
AsDriven.WheelRimSourceLabel
AsDriven.HasSteeringDOR
AsDriven.SteeringDOR
AsDriven.VerifiedGameVersion
AsDriven.Confidence
AsDriven.SourceSummary
AsDriven.MatchKind
AsDriven.GuidanceSummary
AsDriven.PreviewActive
AsDriven.PopupRevision
AsDriven.PopupVisible
AsDriven.PopupDurationSeconds
AsDriven.PopupSize
AsDriven.PopupDetailedVisible
AsDriven.PopupCompactVisible
AsDriven.PopupGlanceVisible
AsDriven.VerificationDriveVisible
AsDriven.VerificationDriveCompleted
AsDriven.VerificationDriveResultReady
AsDriven.VerificationDriveResultSuccessful
AsDriven.VerificationDriveStepNumber
AsDriven.VerificationDriveStepCount
AsDriven.VerificationDriveTitle
AsDriven.VerificationDrivePrompt
AsDriven.VerificationDrivePromptLine1
AsDriven.VerificationDrivePromptLine2
AsDriven.VerificationDriveStatus
AsDriven.VerificationDriveResult
AsDriven.VerificationDriveResultDetail
AsDriven.VerificationDriveLiveValues
```

`PopupRevision` increments once when a new matched car is observed. Repeated
telemetry frames do not change it. Moving to an unknown car immediately clears
the previous record and does not increment the revision.

The plugin also registers `AsDriven.RefreshDatabase`,
`AsDriven.ShowPopup`, `AsDriven.HidePopup`, and
`AsDriven.TogglePopup`. It also registers
`AsDriven.OpenDiagnosticsFolder`,
`AsDriven.OpenVerificationFolder`, and
`AsDriven.ReturnToLiveCar` for optional button/event mappings.
The unmatched-car popup directs contributors to the As Driven page,
where **Contribute this car** captures the live identity and opens the workflow.
Guided verification also registers `AsDriven.VerificationDriveNext`,
`AsDriven.VerificationDriveRetry`,
`AsDriven.VerificationDriveSkip`, and
`AsDriven.VerificationDriveCancel`.
A new car identity automatically shows the
overlay card for ten seconds by default, including an unmatched identity that
needs contribution. The duration can be set from 1–60 seconds on the
**As Driven** SimHub settings page and persists across restarts.
`ShowPopup` keeps the card visible until `HidePopup` is called; `TogglePopup`
provides the same behavior with one mapped button. The database is normally
loaded from:

```text
<SimHub>/PluginsData/AsDriven/Database/data/v1
```

For local development, the `AUTHENTIC_CONTROLS_DATA` environment variable can
override that path.

## Map a popup button

In SimHub, open **Controls and events > Controls**, choose **New mapping**, and
capture the wheel or button-box input. In the action picker, search for
`AsDriven` and select `AsDriven.TogglePopup`. That single
mapping shows the card persistently when it is hidden and hides it when it is
visible. For separate buttons, create one mapping each for
`AsDriven.ShowPopup` and `AsDriven.HidePopup`.

The automatic timeout is separate from manual recall. Open the **As Driven**
plugin page, choose Detailed (840×360), Compact (520×300), or Glance (320×120),
choose 1–60 seconds, and click **Save popup settings**. Compact and 10 seconds
are the defaults; both saved values are reused after restarting SimHub.

Load the included **As Driven** overlay layout once and move it to the preferred
screen position. It places the Compact card and the guided-verification surface,
which matches the default popup size. Detailed and Glance ship inside the same
layout but are not placed, because the three are alternative sizes of one card
rather than three things to show together: SimHub renders every placed overlay in
its own window, so placing all three costs three renderers and three alt-tab
entries to show the same information. Place whichever size is preferred from Dash
Studio and unplace Compact.

This is the packaged default. `install.ps1` preserves existing `As Driven*.olayout`
files, so an installation that already has a customized layout keeps it.

## Certified boundary and development coverage

Client version 0.20.2 is built against the SimHub 9.11.22 SDK and packages
dataset 0.5.17. The certified early-access target is AMS2 1.6.9.91 on Windows.
The client also recognizes Assetto Corsa EVO and Assetto Corsa for active
development. Assetto Corsa Competizione has 18 reviewed entries, each captured
with its exact Steam content build. None is part of the certified release target.

The reference client packages the approved high-fidelity 128x128 raster
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
so **As Driven** can be pinned through **Add and remove features**.
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
Glance. Preview cards carry a prominent `PREVIEW - NOT LIVE` badge, and the
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
Version 0.10.11 adds guided in-game verification to the native settings page.
It captures exact live identity, game/client versions, timestamp, and SimHub's
reported gear-count suggestion, then saves the tester's assist, shift,
cut/blip, cockpit-actuation, and wheel-detail answers as a local draft JSON.
Drafts are never promoted automatically and can be opened from the settings
page or the `AsDriven.OpenVerificationFolder` action.
Version 0.11.0 adds a dedicated in-simulator verification surface and mapped
Next, Retry, Skip, and Cancel actions. Telemetry can prefill reviewable results
for move-off, gear count/direct selection, shift acceptance, cut, and blip;
uncertain results remain unknown or not tested. The settings form now names the
simulator beside its version, distinguishes simulator assist configuration,
captures direct H-pattern selection, and makes successful draft saving more
apparent before collapsing the completed form.
Version 0.11.1 corrects the guided detector's clutch interpretation. SimHub's
reported value is vehicle clutch state, not a direct measurement of the user's
pedal, so internal/automatic clutch activity no longer rejects move-off or
shift tests. The activity is shown as `Vehicle clutch` and retained as evidence.
Version 0.11.2 arms the move-off test from a stationary telemetry sample rather
than requiring first gear and throttle to coincide at zero speed. This captures
internal-clutch creep that begins as soon as a forward gear is selected.
Version 0.11.3 ignores an engine that is already stopped when the move-off test
begins. A standing-start stall is recorded only after telemetry first confirms
that the engine was running; the overlay prompt now tells the tester to start it.
Version 0.11.4 adds a numbered tester workflow and an introductory overlay
screen, recommended AMS2 assist defaults with mandatory tester confirmation,
short non-clipping result summaries, and a prominent green capture indicator.
Selecting a sequential or paddle primary mechanism marks the direct H-pattern
test `Not applicable`; full detection evidence remains in the review form.
Version 0.11.5 shortens and slightly reduces the move-off prompt so it fits the
overlay, visibly labels every telemetry-populated form value `AUTO-FILLED`, and
keeps the guided-start button disabled until assist settings are confirmed.
Gear telemetry no longer auto-confirms direct H-pattern selection; choosing a
sequential or paddle primary mechanism supplies `Not applicable` instead.
Version 0.11.6 renders every maneuver prompt as two intentionally short fixed
lines so the move-off instruction cannot be clipped by Dash Studio. Guided
form badges now distinguish usable `AUTO-DETECTED` values from orange
`REVIEW NEEDED` unknown/not-tested results; a valid `Not applicable` value
inferred from the selected primary mechanism is labeled `DERIVED`.
Version 0.12.0 separates contribution from ordinary plugin settings in a
collapsed, visually distinct contribution workflow. An unmatched
live car exposes a **Contribute this car** handoff on the plugin page and the
unmatched popup identifies the mapped `BeginCarContribution` action. The form
now highlights the current next-step button, explicitly explains why the
assist confirmation is required, marks optional cockpit and wheel fields for
review without blocking incomplete drafts, and requires new supporting notes
when a tester replaces an unresolved guided result with a definite answer.
This preserves partial observations: reviewers can use a later, more complete
draft to improve individual claims without silently replacing established
evidence for the whole car.
Version 0.12.1 prevents a brief roll caused by selecting first gear from being
accepted as clutch-free move-off. The detector now requires at least 600 ms of
sustained movement while the engine remains running; movement followed by an
immediate stall is explicitly recorded as requiring the standing-start clutch.
Version 0.13.0 removes the redundant contribution action mapping and redesigns
the contributor UI as a left setup/workflow rail beside a focused review area.
Confirmed assist profiles persist per simulator, the green confirmation is the
clear next action, guided driving starts directly with the first maneuver, and
the review highlight advances through unresolved optional fields. Captured
driving details remain available in a collapsed section and incomplete drafts
remain valid.
Version 0.13.1 keeps a selected database preview active while telemetry from
the same live car continues underneath it; preview mode now exits only when a
different non-empty live identity arrives or the user closes it. Guided
automatic-cut detection now uses an armed, shift-local trace, retains zero
torque samples, and recognizes a brief throttle interruption only when it
recovers immediately around the gear change. Ambiguous traces still remain
`unknown`.
Version 0.13.2 packages the five-car guided-verification batch and gives Yoke
and Prototype dedicated high-fidelity raster artwork. Every supported wheel,
shifter, cut, blip, and lift category now has a checked packaged bitmap; the
Prototype category no longer reuses the Formula icon.
Version 0.13.3 packages ten additional guided records without changing the
client workflow. Stock USA identities remain exact to the tested Speedway or
Superspeedway configurations, and the Audi R8 V10 GT record corrects the
research lineage to the later seven-speed S tronic generation.
Version 0.14.0 reorganizes the native settings page into Overlay, Car browser,
Contribute data, and Advanced workspaces. Preview and popup actions now provide
local feedback, popup settings show an explicit unsaved state, and the
contributor workflow uses a responsive four-step progression with a compact
persisted simulator-setup summary. The overlay frame and accent use symmetric
safe areas, car name and class have separate fitted header lines, and Detailed
and Compact technique text is fitted by rendered-width estimates with tests
against every curated record.
Version 0.14.1 recalibrates the Segoe UI width estimator used by Detailed and
Compact driving-technique text. It uses the available second line before
ellipsis, keeps the complete Saleen S7-R GT1 sentence visible, and retains
rendered-width fit checks across every curated record.
Version 0.14.2 makes the contribution workspace responsive to both page width
and workflow state. Setup uses the full available width while the review form
is absent; an active review stacks at ordinary window sizes and changes to a
balanced two-column layout only when enough width is available. Settings tab
content can also use up to 1120 pixels without stretching indefinitely.
Version 0.14.3 identifies the installed dataset version, record count, and
bundled plugin version on the Advanced page. It moves the disk reload control
under troubleshooting and distinguishes that action from the planned,
separately versioned GitHub dataset update flow. The contribution page removes
repeated workflow copy, states that drafts are never uploaded automatically,
and provides persistent access to the local drafts folder while public GitHub
submission remains unavailable.
Version 0.14.4 disables manual popup display when neither live telemetry nor a
catalog preview can supply a car, and reports success only after a displayable
state is available. The plugin version moves to the page introduction while
dataset version and car count remain in Advanced. Detailed, Compact, and Glance
cards now place physical controls and shifting technique in separate subtle
outlined panels for faster category recognition.
Version 0.14.5 adds ten pixels of clearance between Detailed section headings
and their icons, extends the paired group panels to preserve value spacing, and
reflows the technique and evidence rows within the same 840 by 360 surface. It
also removes the redundant central cyan divider from all popup sizes; the panel
borders and gutter now provide the category separation.
Version 0.14.6 consolidates popup actions, guided-drive state, and live
verification identity without changing the user interface. SimHub Show and
Toggle mappings now use the same availability guard as the settings page; Dash
properties share one snapshot refreshed after each telemetry update or user
action; and one capture context replaces seven parallel live-identity fields.
Version 0.14.7 moves the contribution form's static WPF layout into XAML while
keeping its telemetry, validation, responsive behavior, and draft saving in
direct code-behind. This removes the large imperative UI constructor and its
obsolete control factories without adding MVVM, services, or another project.
The SimHub build smoke test now validates rendered controls and behavior instead
of depending on private field and method names, so routine layout edits are less
brittle. Guided-result, next-step, and evidence badges remain intact.
Version 0.14.8 retires a completed contribution automatically when a different
live car is detected, presenting a fresh Capture current car action without
discarding unsaved work or the confirmed simulator-assist profile. It moves the
saved-drafts information below the tester workflow and increases enabled button
contrast while keeping disabled actions visually distinct.
Version 0.14.9 resets guided-result expansion for each captured car and opens it
only when an applicable driving result needs review. Direct H-pattern selection
now depends on choosing an H-pattern/direct-selection mechanism and its explicit
confirmation no longer requires a duplicate evidence note. The active workflow
button also uses a stronger filled highlight.
Version 0.15.0 establishes the documented early-access compatibility boundary,
aligns plugin and core binary versions, adds separate checksummed plugin and
database release artifacts, and adds a tested uninstaller that preserves local
data and customized layouts by default. The client remains offline; automatic
GitHub update checking waits for a stable public release endpoint.
Version 0.18.1 makes guided-result review capability-aware. Direct H-pattern
selection waits for the cockpit mechanism and becomes derived for paddle,
sequential-stick, and automatic mechanisms. ACC's unresolved automatic-cut
result remains `unknown` evidence but is labeled `NOT EXPOSED` and no longer
counted as contributor review work because ACC does not publish engine torque
through SimHub.
Version 0.18.2 removes throttle interruption as automatic-cut evidence. A
throttle dip can be traction control, driver input, or telemetry filtering; only
a shift-local torque collapse under sustained throttle demand now establishes
an ignition cut. The importer also degrades automatic-cut answers from older ACC
drafts to `unknown`, preserving the drafts without promoting false certainty.
Version 0.19.0 added the explicit public observation handoff without adding an
uploader. New drafts record the exact loaded dataset version. After saving, the
client can select that JSON, create a separately marked anonymous copy without
installed-package identity, or open the GitHub simulator-observation form. The
contributor still attaches the file manually. The corresponding intake command
strictly validates and hashes the untrusted draft, treats only identical bytes
as a duplicate, and separates corroboration from contradictions and changed
implementations.
Compact uses an unambiguous checkmark-only match indicator,
and confidence labels use consistent sentence capitalization. Detailed, Compact, and Glance
were all live-verified with AMS2 telemetry on 2026-08-10. The packaged
**As Driven** layout was then loaded, positioned, and confirmed to
survive full SimHub and AMS2 restarts with automatic popup behavior intact.
