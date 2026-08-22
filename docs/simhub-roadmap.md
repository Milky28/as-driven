# SimHub client roadmap

The SimHub integration is the read-only reference client for the As Driven
authentic-controls layer. The JSON database remains independently useful to
websites, hardware selectors, voice assistants, Stream Deck tools, or other
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

Status: **implemented for AMS2.** The .NET reader rejects
unsupported schemas and escaping index paths, performs exact case-sensitive
identity matching, reports unmatched identifiers, and has a standalone
diagnostic plus regression runner. Plugin version 0.9.1 adds a persistent,
deduplicated JSON Lines log containing exact game version, CarModel, CarId,
class, timestamp, dataset, and SimHub version. The log path and last observed
values are published as properties and the settings page opens its folder.
iRacing awaits curated sample records.

## Phase 2 — minimal SimHub plugin

The plugin detects game/car changes, calls the lookup library, and publishes
properties. It does not draw UI and does not own the database.

Suggested properties:

```text
AsDriven.RecordId
AsDriven.MatchStatus
AsDriven.DisplayName
AsDriven.ShiftType
AsDriven.TechniqueSummary
AsDriven.TechniqueSummaryLine1
AsDriven.TechniqueSummaryLine2
AsDriven.PreviewActive
AsDriven.GearCount
AsDriven.AutoBlip
AsDriven.ShiftCut
AsDriven.WheelRimShape
AsDriven.WheelRimSourceLabel
AsDriven.SteeringDOR                 (optional reference)
AsDriven.VerifiedGameVersion
AsDriven.Confidence
AsDriven.SourceSummary
AsDriven.PopupRevision
```

Suggested actions:

```text
AsDriven.ShowPopup
AsDriven.HidePopup
AsDriven.TogglePopup
AsDriven.RefreshDatabase
AsDriven.OpenDiagnosticsFolder
AsDriven.ReturnToLiveCar
```

`PopupRevision` increments on a matched car/session change. Dash Studio can use
that edge to show a timed overlay while a mapped button calls `ShowPopup`.

Exit criterion: properties refresh exactly once per identity change, unknown
cars do not retain stale values, and the database works from a local path.

Status: **adapter implemented, installed, and live-validated.** On 2026-08-10,
SimHub 9.11.22 loaded plugin version 0.1.0 and dataset 0.2.0 while connected to
AMS2 executable version 1.6.9.91. `McLaren F1 GTR` matched by exact
`telemetry-name`; switching to the unmatched `Ginetta G55 GT4` cleared all
record guidance while preserving the raw identifier; switching back restored
the record. `PopupRevision` was 1, remained 1 for the unmatched car, and became
2 on the returning match. Repeated telemetry frames did not increment it. The
`RefreshDatabase` action produced a fresh successful load of all ten records.

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

Implementation status (2026-08-10): plugin/package version `0.6.0` builds
native Detailed (840×360), Compact (520×300), and Glance (320×120) overlays,
plus the persistent detailed display. The popup setting persists the selected
native size and a 1–60 second duration; Compact and ten seconds are the defaults.
A deterministic antialiased PNG library embedded in every template resource
archive replaces per-size SimHub icon primitives. The same masters cover the
supported wheel-rim and shifter categories, automatic cut, and automatic blip
at all three sizes, with explicit unknown variants. Reusable technique artwork
also includes the revised throttle-lift cue: a proportionate pedal, solid
pressing foot, ghosted lifted foot, and one arrow. Version `0.6.0` was installed
locally on 2026-08-10; package-to-install hashes matched for both assemblies,
the overlay layout, and every bitmap resource archive.
Version `0.6.1` normalizes user-facing control values and match-kind labels to
sentence-style names. It presents `shift_cut = no` as the actionable `Lift
throttle` cue instead of a separate manual-cut concept; automatic cut retains
the drivetrain icon, and the underlying database value is unchanged. Manual
blip uses a tapered, perforated throttle pedal with a hinge arm and floor mount.
Approved high-fidelity raster artwork is stored as project assets and embedded
byte-for-byte in every generated Dash Studio resource archive; automated tests
guard against silently packaging the legacy code-drawn fallback icons.
This packaging correction is version `0.6.2`.
Version `0.6.3` suppresses the redundant Detailed-card technique sentence for
H-pattern cars while retaining the underlying evidence values and the sentence
for other transmission types.
Version `0.6.4` simplifies the Compact match indicator to a checkmark and
normalizes confidence labels, values, and all technique-guidance segments to
sentence capitalization.
Version `0.6.5` removes the duplicate Detailed-card technique sentence for all
transmission types and clarifies the tile values as `Automatic throttle cut`
and `Automatic throttle blip`.
Version `0.7.0` introduces the blue visual system and letter-free wheel/H-gate
brand mark. The three matched popup sizes replace nested control tiles with an
open rail, enlarge the existing raster icons, and explicitly separate physical
hardware from driving technique with spanning group headers.
Version `0.7.1` adds the distinct GT-style wheel category and reviewed GT wheel
asset. AMS2 `GTF1*` source codes now normalize to GT-style instead of Unknown;
`F1*` source codes normalize to Formula, which remains a separate category and
icon. Together with the existing `R*` rule, every populated wheel code in the
v1.0.34 source spreadsheet has a style mapping.
Version `0.8.0` packages dataset `0.3.0` with five newly reviewed Formula-rim
records: Formula V10 Gen2, Formula Reiza, Formula Ultimate Hybrid Gen1,
Formula Ultimate Gen2, and Formula USA 2023. The Formula-rim MetalMoro MRX P2
remains unpromoted because the local SimHub identity inventory contains only a
different P4/Duratec variant.
Version `0.8.1` packages dataset `0.3.1` with four exact Formula variant
identities captured from live AMS2 1.6.9.91 telemetry. It covers the B- and
M-tyre High Downforce Formula V10 Gen2 identities plus the High Downforce
Formula Ultimate Hybrid Gen1 and Formula USA 2023 identities. Matching remains
exact; unobserved aero and speedway variants are not inferred.
Version `0.8.2` packages dataset `0.3.2` with Reiza's official V1.6.9 Formula
rebrands and two exact live identities. Formula Reiza becomes Formula V8 Gen3
and Formula Ultimate Gen2 becomes Formula Hybrid Gen3 in the current UI. Live
telemetry retains `F-Reiza_HD` and `F-Ultimate_Gen2_HD` internal classes,
providing a falsifiable link to the historical records.
Version `0.9.0` adds automatic unmatched-car diagnostics under the current
user's Local AppData. The append-only JSON Lines log is deduplicated across
restarts and records exact game version, CarModel, CarId, class, timestamp,
dataset version, and SimHub version. SimHub properties expose the path, count,
last raw values, and any write error; the plugin settings page and an action
open the diagnostics folder.
Version `0.9.1` corrects live version metadata after validation exposed that
AMS2 publishes comma-separated executable versions and SimHub's EXE metadata
is fixed at `1.0.0.0`. AMS2 version detection now normalizes executable
metadata and uses a cross-process image-path fallback; the SimHub version is
read from its shared startup log.
Version `0.9.2` packages dataset `0.3.3` with the independently researched
Dodge Viper GTS-R. Structured notes distinguish its original FIA-homologated
H-pattern T56, documented privateer sequential conversions, and the sequential
stick plus standing-start clutch behavior tested in AMS2 1.6.9.91. Perceived
automatic cut and blip behavior remains explicitly medium-confidence.
Version `0.9.3` packages dataset `0.3.4` with the exact base `Alpine A424` /
`LMDh` identity verified in AMS2 1.6.9.91. The record separates directly
observed seven-speed paddle behavior, hybrid move-off, automatic blip, and
prototype-style rim from the medium-confidence automatic-cut inference. The
exact Low Downforce identity inherits the base controls as an approved
aero-package alias, with its lack of a separate live test documented.
The same 0.9.3 / 0.3.4 batch adds the Ligier JS P217 after direct Gen1 and Gen2
tests confirmed one model identity, two class IDs, and the same six-speed
paddle technique in both contexts.
The completed batch raises dataset 0.3.4 to 28 records with ten additional
AMS2 1.6.9.91 live verifications: Oreca 07, Lamborghini SC63, Ligier JS P320,
Ligier JS P4, Aston Martin Valkyrie Hypercar, Audi R8 LMS GT4, Chevrolet
Corvette Z06 GT3.R, Lamborghini Huracan Super Trofeo EVO2, Aston Martin
Vantage GT4 Evo, and Aston Martin Vantage GTE. Closed prototype rims with an
integrated display now use `prototype`; open-top no-display GT rims remain
`gt-style`. Approved Low Downforce inheritance is limited to exact observed
Oreca, SC63, and Corvette identities and is explicitly marked untested.
Version `0.9.4` packages dataset `0.3.5` with six live-verified historical GT
records: Lamborghini Murcielago R-GT, Maserati MC12 GT1, Lister Storm GTM,
Panoz Esperante GTLM, Gillet Vertigo Streiff, and Lamborghini Diablo SV-R.
The first five share the directly observed six-speed sequential-stick profile;
the Diablo resolves to a five-speed dogleg H-pattern with manual rev matching.
Exact Murcielago and MC12 Low Downforce identities inherit their verified base
controls and remain explicitly marked as not separately tested.
Version `0.9.5` adds the supported SimHub native feature-page presentation: a
24x24 monochrome-compatible wheel-and-shift-gate menu icon, pinnable
**As Driven** left-menu entry, live car/match/version/error status,
Show/Hide popup controls, database refresh, saved popup settings, and
diagnostics access. Overlay layout and positioning deliberately remain in Dash
Studio. The build smoke-tests both the menu icon dimensions and settings-page
construction against the installed SimHub SDK.
Version `0.9.6` narrows the Detailed overlay from 900 to 840 pixels, reduces
the car-title type size, and adds a full-width `DRIVING TECHNIQUE` summary. The
summary is generated only from structured start, clutch, lift, cut, and blip
values, keeping it actionable without turning evidence notes into unsourced
general driving advice. The installer migrates only untouched 900-pixel
Detailed parts and preserves their center position.
Version `0.9.7` splits that summary into two explicit display lines, maps the
`verified` confidence enum to the visible `Verified` label, and insets the top
accent bar so it follows the card's rounded-corner geometry.
Version `0.9.8` raises the technique text size and fills the first line before
using the second. Dataset `0.3.6` records manual blipping as required authentic
rev matching for the five live-verified historical sequential-stick cars that
have no automatic blip.
Version `0.10.0` adds a sorted curated-car browser to the native SimHub page.
It supports pre-session control planning and popup testing without launching a
simulator, labels the rendered card `PREVIEW`, and automatically yields to live
telemetry when a game session starts. Short technique summaries such as the
Diablo's remain on one line when their rendered space is sufficient.
Version `0.10.1` corrects idle preview behavior by starting the selected
As Driven layout through SimHub's public forced-overlay mode. It also
separates live telemetry status from preview status and tears down the
temporary preview layout when live data resumes.
Version `0.10.2` keeps one forced-preview layout running while the selected car
changes instead of calling SimHub's layout start operation repeatedly. This
fixes the accumulation of duplicate `Window1` overlay windows during a preview
session.
Version `0.10.3` clones only the currently selected popup surface into the
forced idle-preview layout, reducing that preview session to one overlay
window. It also labels previews `PREVIEW — NOT LIVE`, exposes a clear **Close
preview** action on the native page, and adds the two-line driving-technique
summary to the 520×300 Compact card. Glance remains icon-only, while the
Detailed dropdown continues to match its reduced 840×360 surface.
Version `0.10.4` gives the native settings page a blue-and-white brand badge,
removes redundant preview messaging, and introduces Compact-specific technique
lines that fill the available width before wrapping within 520×300.
Version `0.10.5` adopts the selected ImageGen-derived wheel, physical lever, and
simplified H-gate identity across the sidebar, native page, and popup. The
sidebar uses only the transparent white glyph so SimHub's monochrome treatment
does not turn a filled badge into a white square. Compact also uses more of its
first technique line before wrapping.
The `0.10.5` identity is provisional: at small size its combined wheel, lever,
and lower gate can resemble a science-fiction helmet or face. A later design
pass should prioritize an unmistakable controls silhouette and explicitly test
against that reading.
Version `0.10.6` moves Compact's safe wrap boundary to the last word near 116
characters after the live Diablo preview established the actual rendered limit.
Live Alpine A424 preview testing still clipped the final word at that boundary;
version `0.10.7` therefore reduces the target to roughly 110 characters while
retaining the existing two-line area. Dataset `0.3.7` adds the four-car GT1
batch verified on 2026-08-11: Aston Martin DBR9, Chevrolet Corvette C5-R,
Saleen S7-R GT1, and Milano GT55.
Version `0.10.8` packages dataset `0.3.8` and its four-car GT2 2005 batch:
Milano GT36, Porsche 996 GT3 RSR, Spyker C8 Spyder GT2-R, and TVR Tuscan T400R
GT2. The Porsche's verified automatic blip remains distinct from the three
manual-blip records.
Version `0.10.9` packages dataset `0.3.9` with Audi R8 LMP1, Courage C60
Hybrid, and Dallara SP1. The Dallara actuation decision is explicitly
falsifiable: visible paddles and no replay hand-off support paddle use, while
the additional visible cockpit lever remains documented.
Version `0.10.10` packages dataset `0.3.10` with the Lola B05/40 V8 and Turbo.
Both directly verify paddle actuation and clutch-free move-off; the unknown
move-off mechanism is preserved, and the V8 Low Downforce controls remain
explicit untested aero inheritance.
Standard 1920-wide and 5120x1440 top-center layout presets are packaged separately. The installer
preserves existing layout files during upgrades unless replacement is explicitly
requested.
The dogleg H icon is driven by the curated `shift_pattern` value and uses the
R/2/4 upper row with 1/3/5 below. `ShowPopup`, `HidePopup`, and `TogglePopup`
provide manual recall. Generated-artifact tests cover distinct dimensions,
size bindings, icon mappings, unique native item IDs, explicit Unknown
fallbacks, and the unmatched no-assumptions message.
Earlier version `0.3.0` live validation with SimHub `9.11.22` and AMS2
executable version `1.6.9.91` started the native overlay and displayed the
matched-car card in game. Manual recall and hide actions also behaved correctly.
Version `0.4.1` is installed in SimHub `9.11.22`. A saved overlay layout loaded
all three native surfaces, and live switching rendered Detailed, Compact, and
Glance correctly with AMS2 telemetry and dynamic icons. The explicit boolean
visibility properties added in `0.4.1` avoid string comparison in SimHub's
formula engine.

Version `0.5.0` packages a ready-made **As Driven** `.olayout` with all
three surfaces aligned at one safe default position. Users load and position a
single layout instead of constructing three layout parts manually. Automated
tests verify the referenced templates, dimensions, placement, transparency,
and unique part identifiers. Live validation installed the layout, positioned
its surfaces, restarted both SimHub and AMS2, and confirmed automatic popup
behavior remained operational after the restart.

## Phase 4 — updates and broader coverage

- Ship a pinned dataset with the plugin and optionally poll signed GitHub
  releases, never a moving branch.
- Show dataset version and changelog before applying an update.
- Continue the AC EVO and ACC development tracks. ACC was selected next from
  available telemetry, test access, source quality, and shared-car coverage; its
  first reviewed entry is the Audi R8 LMS GT3 Evo II. The existing iRacing
  importer and AC Rally identifier are foundations, not coverage claims.
- Provide an opt-in unmatched-identifier export; do not upload telemetry by
  default.

Exit criterion: rollback-safe updates and clear distinction among authentic
hardware, modeled behavior, and active session rules.
