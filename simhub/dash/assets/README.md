# Popup raster assets

`brand-mark.png` uses the selected wheel, physical lever, and simplified H-gate
identity on the established blue badge. The same transparent ImageGen-derived
master supplies the SimHub sidebar and settings-page marks.

These 128x128 PNG files are the production crops of the user-reviewed raster
icon sheets generated with the built-in ImageGen workflow. The crops retain a
subtle feathered dark surround so black leather and gunmetal edges remain
legible against the popup tile at Detailed, Compact, and Glance sizes.

`icons.py` loads these files before its dependency-free drawing fallback and
validates their PNG signature and dimensions. The fallback currently remains
for the yoke category until a distinct yoke design is approved.

`wheel-gt-style.png` is the approved open-top, no-display GT wheel.
`wheel-formula.png` is the approved closed display-rim artwork. The generator
currently reuses it for the separate `prototype` category while displaying a
`Prototype` label; a distinct prototype bitmap can replace that alias later
without changing database records.
