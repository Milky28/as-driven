# Dash Studio pre-flight cards

`generate.py` creates four native SimHub Dash Studio DJSON artifacts:

- **Authentic Controls Preflight Overlay** — Detailed, 840×360.
- **Authentic Controls Preflight Compact** — Compact, 520×300.
- **Authentic Controls Preflight Glance** — Glance, 320×120.
- **Authentic Controls Preflight Display** — a persistent 900×360 auxiliary
  display that does not use popup visibility.

The three overlay templates are click-through. Each follows its own explicit
boolean property (`PopupDetailedVisible`, `PopupCompactVisible`, or
`PopupGlanceVisible`), so only the selected size becomes visible. A car identity
change shows it for ten seconds
by default. `AuthenticControls.ShowPopup` keeps it visible for button recall,
`AuthenticControls.HidePopup` hides it, and `AuthenticControls.TogglePopup`
supports both operations with one button.

Version 0.7.0 introduced a blue, letter-free visual identity. The current brand
mark combines a steering wheel, physical shift lever, and simplified H-gate,
avoiding the `AC` abbreviation that
sim racers commonly associate with Assetto Corsa. Matched views use an open
four-column rail instead of four nested cards. `PHYSICAL CONTROLS` spans Wheel
and Shift, while `SHIFTING TECHNIQUE` spans Upshift and Downshift. Stronger
center dividers preserve that distinction at all three popup sizes, and the
freed space lets the existing control artwork render substantially larger.

The cards use project-owned 128x128 raster PNG icons packaged in each template's
`.djson.ressources` archive. Detailed, Compact, and Glance therefore render the
same master artwork instead of independently scaling and rotating SimHub shape
primitives. The approved high-fidelity assets live under `dash/assets`; the
generator validates their PNG dimensions and packages their exact bytes. A
regression test prevents an approved asset from silently falling back to the
older code-drawn artwork. Wheel variants cover round, D-shaped, GT-style,
prototype, formula, and yoke rims. GT-style uses the reviewed open-top,
no-display artwork. Prototype uses the reviewed closed display-rim artwork also
used by Formula until a more visually distinct prototype asset is approved;
the popup label still identifies it as `Prototype`.
Shifter variants cover conventional and dogleg H-patterns, sequential stick,
paddles, automatic lever, and direct selection. The reusable technique set maps
automatic cut to its drivetrain icon and no automatic cut to the actionable
throttle-lift icon, which has a full-height pedal, solid pressing foot, ghosted
lifted foot, and one direction arrow. Automatic/manual blip variants remain
separate. Every category has an explicit unknown icon; the UI does not infer
missing values.

Visible values use sentence-style display names consistently (`Round`,
`H-pattern`, `Lift throttle`, and `Manual blip`) rather than exposing raw
database tokens or mixing casing conventions. The popup no longer presents
manual cut as a separate driver action: `shift_cut = no` becomes the actionable
`Lift throttle` cue, while the database value remains unchanged.

All variants have separate matched, unmatched, and waiting/error states. The
unmatched state never retains guidance from the previous car and states that
no hardware or technique values were assumed.

The Detailed and Compact cards add a concise **DRIVING TECHNIQUE** sentence
synthesized from the structured start, clutch, lift, cut, and blip fields.
Compact uses smaller type while retaining both technique lines; Glance remains
icon-only. The guidance describes how to operate the car without copying
internal evidence notes or inventing values for unknown fields.
Compact uses its own approximately 116-character wrap target at 9.5-point type,
filling the available line width without clipping on the narrower card.
Technique segments use consistent sentence capitalization in every plugin
property and consumer, for example `Clutch unknown · Throttle lift unknown ·
No automatic cut`.

The normal `simhub/build.ps1` command generates the artifacts under:

```text
simhub/dist/AuthenticControls/DashTemplates/
  Authentic Controls Preflight Overlay/
  Authentic Controls Preflight Compact/
  Authentic Controls Preflight Glance/
  Authentic Controls Preflight Display/
```

The build remains non-installing. The package also includes the ready-made
**Authentic Controls** overlay layout; load that once instead of creating three
layout parts manually. See [`../overlay/README.md`](../overlay/README.md). The
layout may stay running because the plugin makes only the selected size visible.
Choose the size and 1–60 second automatic duration on the **Authentic Controls**
settings page. Map `TogglePopup` for one show/hide button, or map `ShowPopup`
and `HidePopup` separately.

Plugin version 0.10.5 exposes that settings page as a native pinnable SimHub
feature with a transparent white 24x24 wheel, lever, and gate menu glyph. The page provides live
match and version status plus Show/Hide popup, database refresh, and diagnostics
controls. Dash Studio continues to own layout loading and positioning.
The native page also provides a curated-car preview selector. Previewed records
use the same templates and properties but show a visible `PREVIEW — NOT LIVE`
badge; live
game telemetry automatically takes priority when a session begins.
Idle preview uses SimHub's forced-overlay mode and a temporary layout manager;
it is not dependent on the game-connected overlay host.

The persistent display can be started like any other Dash Studio dashboard and
does not depend on popup visibility or size properties.
