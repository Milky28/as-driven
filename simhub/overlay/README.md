# Ready-made overlay layout

Two native SimHub overlay presets contain the Detailed, Compact, and Glance
popup templates. Only the size selected on the plugin settings page becomes
visible:

Detailed is 840×360, Compact is 520×300, and Glance is 320×120. Compact includes
the smaller driving-technique summary; Glance intentionally remains icon-only.

- `Authentic Controls.olayout` centers all sizes near the top of a 1920-wide
  display.
- `Authentic Controls 5120x1440.olayout` centers all sizes near the top of a
  5120x1440 super-ultrawide display.

The package installs it under:

```text
<SimHub>/OverlayLayouts/Authentic Controls.olayout
<SimHub>/OverlayLayouts/Authentic Controls 5120x1440.olayout
```

In SimHub, open **Dash Studio > Overlays** and click **Load** beside
the preset matching the display. The layout is configured to remain available in menus
and while paused because the plugin owns the card's timed visibility. Enable
layout auto-start after positioning it if desired.

Edit the installed or user-saved layout to choose a different screen position;
do not edit the source layout merely for a local monitor arrangement. The
repository installer preserves existing layout files by default so plugin
upgrades do not reset these personalized positions.
