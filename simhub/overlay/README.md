# Ready-made overlay layout

Two native SimHub overlay presets contain the Detailed, Compact, and Glance
popup templates plus the Guided Verification surface. Only the popup size
selected on the plugin settings page becomes visible during normal use; the
verification surface appears separately while a guided drive is active:

Detailed is 840×360, Compact is 520×300, and Glance is 320×120. Compact includes
the smaller driving-technique summary; Glance intentionally remains icon-only.

- `As Driven.olayout` centers all sizes near the top of a 1920-wide
  display.

A second preset positioned for a 5120x1440 super-ultrawide display shipped until
0.21.0. It was dropped because a driver repositions the overlay once anyway, and
a second preset only added a choice to get wrong. Drag the overlay where you
want it; the installer preserves that position across upgrades.

The package installs it under:

```text
<SimHub>/OverlayLayouts/As Driven.olayout
```

In SimHub, open **Dash Studio > Overlays** and click **Load** beside
the preset. The layout is configured to remain available in menus
and while paused because the plugin owns the card's timed visibility. Enable
layout auto-start after positioning it if desired.

Edit the installed or user-saved layout to choose a different screen position;
do not edit the source layout merely for a local monitor arrangement. The
repository installer preserves existing layout files by default so plugin
upgrades do not reset these personalized positions. Version 0.11.0 adds the
verification surface to an existing preserved layout relative to its Detailed
card, without moving the user's existing parts.
