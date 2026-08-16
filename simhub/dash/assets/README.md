# Popup raster assets

`brand-mark.svg` is the scalable production master for the As Driven mark.
`brand-mark.png` is its generated raster counterpart used by the current SimHub
dashboard package. Both use the `rim-lever` geometry from
`simhub/dash/brand_mark.py`: a thin rim with a raked lever set off-centre inside
it. Regenerate the SVG and both shipped PNG copies, including the plugin's
embedded `Assets/as-driven-mark.png`, with:

```powershell
python simhub/dash/brand_mark.py --production
```

It replaced an ImageGen-derived mark that read as a helmeted face, because a
closed rim, symmetric spokes, a centred mass, and a bar cluster below it stacked
into brow, nose, and mouth. Offsetting the lever and dropping the spokes removes
the reading; `docs/design/2026-08-12-mark-candidates/` records the alternatives
and why the first attempt failed.

These 128x128 PNG files are the production crops of the user-reviewed raster
icon sheets generated with the built-in ImageGen workflow. The crops retain a
subtle feathered dark surround so black leather and gunmetal edges remain
legible against the popup tile at Detailed, Compact, and Glance sizes.

`icons.py` loads these files before its dependency-free drawing fallback and
validates their PNG signature and dimensions. The fallback currently remains
for the yoke category until a distinct yoke design is approved.

`wheel-gt-formula.png` is the approved closed display-rim artwork, previously
shipped as `wheel-formula.png`. It now covers the single merged `gt-formula`
category: the rim modern GT, formula and prototype cars share. The separate
`wheel-gt-style.png` and `wheel-prototype.png` crops were removed with those
categories; both remain in git history if a distinct design is ever wanted.
