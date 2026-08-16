# Brand mark

`brand-mark.svg` is the scalable production master for the As Driven mark.
`brand-mark.png` is its generated raster counterpart, used to title the
preflight card in the SimHub dashboard package. Both use the `rim-lever`
geometry from `simhub/dash/brand_mark.py`: a thin rim with a raked lever set
off-centre inside it. Regenerate the SVG and both shipped PNG copies, including
the plugin's embedded `Assets/as-driven-mark.png`, with:

```powershell
python simhub/dash/brand_mark.py --production
```

It replaced an ImageGen-derived mark that read as a helmeted face, because a
closed rim, symmetric spokes, a centred mass, and a bar cluster below it stacked
into brow, nose, and mouth. Offsetting the lever and dropping the spokes removes
the reading; `docs/design/2026-08-12-mark-candidates/` records the alternatives
and why the first attempt failed.

## What used to live here

This directory also held eighteen 128x128 raster crops from a user-reviewed
ImageGen icon sheet: wheel rims, shift mechanisms, and separate cut, blip and
lift marks. They belonged to the four-tile preflight card, which the banded
Fit / Use card replaced, and the drawing code in `icons.py` that fell back to
them went with it.

The card now draws the flat family in `../preflight-assets/`, which is
deterministic geometry rather than reviewed artwork and covers rims, shifters,
the clutch and throttle rows, and the note mark. The removed crops remain in git
history if a design is ever wanted back.
