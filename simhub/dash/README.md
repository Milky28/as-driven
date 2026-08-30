# Dash Studio pre-flight cards

`generate.py` creates four native SimHub Dash Studio DJSON artifacts:

- **As Driven Preflight Overlay** - Detailed, 720×428.
- **As Driven Preflight Compact** - Compact, 520×360.
- **As Driven Preflight Display** - a persistent 780×360 auxiliary
  display that does not use popup visibility.
- **As Driven Verification Drive** - a 700×220 in-simulator prompt
  surface for the guided verification drive.

The popup templates are click-through. Each follows its own explicit boolean
property (`PopupDetailedVisible` or `PopupCompactVisible`), so only the selected size becomes visible. A car identity
change shows it for ten seconds
by default. `AsDriven.ShowPopup` keeps it visible for button recall,
`AsDriven.HidePopup` hides it, and `AsDriven.TogglePopup`
supports both operations with one button.

The verification surface is independent of popup size and timeout. It becomes
visible only while a guided test drive is active and shows the current maneuver,
live gear/clutch/throttle/speed values, and the detected result. Map
`VerificationDriveNext`, `VerificationDriveRetry`, `VerificationDriveSkip`, and
`VerificationDriveCancel` to convenient wheel or button-box inputs so the test
can be completed without alt-tabbing.
An introductory screen explains the repeated tester workflow. Captured results
use a short one-line summary and prominent green check, avoiding truncation in
the overlay while the complete evidence text remains available to the form.

Version 0.7.0 introduced a blue, letter-free visual identity. The current brand
mark combines a steering wheel, physical shift lever, and simplified H-gate,
avoiding the `AC` abbreviation that sim racers commonly associate with Assetto
Corsa. Matched views use two compact bands: highlighted `FIT` hardware first,
then highlighted `USE` guidance with separate Launch, Upshift, and Downshift
sections. This keeps the pre-session decision order explicit without nested
cards or decorative technique icons.

Each pre-flight surface packages nine palettes behind one shared information
layout: Modern Night Vision, Modern Light Studio White, 1960s Roadbook, 1970s
Works, 1980s Black Gold, 1990s Touring Works, 2000s Endurance Alloy, and 2010s
Hybrid Vector, plus the manual GPL Classic historic-broadcast palette.
`AsDriven.PopupTheme` selects exactly one layer. The settings
page can pin any palette or resolve it automatically from the curated start
year. Endurance Alloy covers 2000 through 2009, Hybrid Vector covers 2010
through 2019, and 2020 or newer uses Modern. Missing years deliberately fall
back to Modern. The period treatments
use original colour combinations and small stripe motifs rather than sponsor
logos or copied livery graphics. GPL Classic likewise uses the channel's
burnt-orange, ochre, denim-blue and cream relationships without copying its
wordmark; the As Driven mark remains at the top left.

The cards use project-owned 128x128 raster PNG icons packaged in each template's
`.djson.ressources` archive. Detailed and Compact therefore render the
same master artwork instead of independently scaling and rotating SimHub shape
primitives. The approved high-fidelity assets live under `dash/assets`; the
generator validates their PNG dimensions and packages their exact bytes. A
regression test prevents an approved asset from silently falling back to the
older code-drawn artwork. Active wheel variants cover round and D-shaped rims
in closed and open-top forms, GT / Formula rims, plus an explicit unknown state.
Older package assets for the
retired wheel values remain only so a legacy dataset can still render.
Shifter variants cover conventional and dogleg H-patterns, sequential stick,
paddles, automatic lever, and direct selection. Launch, Upshift, and Downshift
remain separate text-led sections; technique icons are intentionally omitted.
Every hardware category has an explicit unknown icon, and the UI does not infer
missing values.

Visible values use sentence-style display names consistently (`Round`,
`H-pattern`, `Lift throttle`, and `Manual blip`) rather than exposing raw
database tokens or mixing casing conventions. The popup no longer presents
manual cut as a separate driver action: `shift_cut = no` becomes the actionable
`Lift throttle` cue, while the database value remains unchanged.

All variants have separate matched, unmatched, and waiting/error states. The
unmatched state never retains guidance from the previous car and states that
no hardware or technique values were assumed.

Detailed and Compact retain the driver-summary note with the circled information
mark. The note is pre-wrapped by the core model because Dash Studio text items do
not reliably wrap at runtime.

The normal `simhub/build.ps1` command generates the artifacts under:

```text
simhub/dist/AsDriven/DashTemplates/
  As Driven Preflight Overlay/
  As Driven Preflight Compact/
  As Driven Preflight Display/
  As Driven Verification Drive/
```

The build remains non-installing. The package also includes the ready-made
**As Driven** overlay layout; load that once instead of creating three
layout parts manually. See [`../overlay/README.md`](../overlay/README.md). The
layout may stay running because the plugin makes only the selected size visible.
Choose the size and 1–60 second automatic duration on the **As Driven**
settings page. Map `TogglePopup` for one show/hide button, or map `ShowPopup`
and `HidePopup` separately.

The plugin exposes its settings page as a native pinnable SimHub feature with a
transparent white 24x24 wheel, lever, and gate menu glyph. Garage mirrors the
current FIT and USE guidance beside an embedded popup preview and visual theme
choices. A persistent health strip shows simulator, match, dataset, and popup
readiness; database coverage, reload, and diagnostics live under System. Dash
Studio continues to own layout loading and positioning.
The native page also provides a curated-car preview selector. Previewed records
use the same templates and properties but show a visible `PREVIEW - NOT LIVE`
badge; live
game telemetry automatically takes priority when a session begins.
Idle preview uses SimHub's forced-overlay mode and a temporary layout manager;
it is not dependent on the game-connected overlay host.

The persistent display can be started like any other Dash Studio dashboard and
does not depend on popup visibility or size properties.

The guided verification surface uses two fixed, short prompt lines rather than
depending on Dash Studio text wrapping. This keeps the full instruction visible
at the packaged 700 x 220 size.
