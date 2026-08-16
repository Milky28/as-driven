# Preflight icon family v1

This review sheet evaluates the flat monochrome icon family intended for the
row-based overlay proposal in the Claude artifact `As Driven Preflight Spec`.

The family follows the proposal's four fixed rows—Wheel, Shifter, Clutch, and
Throttle—while covering every value the current database can expose. The
information symbol belongs to the optional driver-summary panel. `You`, `Car`,
`n/a`, and `?` remain text tags rather than pictograms.

The sheet shows the 128-pixel transparent masters at 84 pixels and again at the
24-pixel target used by the detailed and compact row layouts. Production assets
live in `simhub/dash/preflight-assets`; their deterministic source is
`simhub/dash/icons.py`.

The existing raster As Driven mark remains the popup title icon, as requested.
