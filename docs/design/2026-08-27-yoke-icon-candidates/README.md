# Yoke icon candidates

These are review-only replacements for the current preflight yoke symbol. They
use the same dependency-free `Canvas`, white silhouette, 128-pixel authoring
grid and 24-pixel readability target as the production icon family.

The current icon combines two rising grips, a circular hub and a downward spoke.
That arrangement reads too much like a head, arms and torso. Every candidate
removes the circular hub and vertical body line.

| Candidate | Direction | Tradeoff |
| --- | --- | --- |
| A, open arc | Pure open-top rim with no internal structure | Clearest at 24 pixels, but least specific about spokes or controls |
| B, grip arc | Open rim plus visibly heavier hand grips | Best expression of the physical object, slightly busier at 24 pixels |
| C, low hub | Angular rim with the center boss moved low | Most steering-wheel-like, but still has internal detail |
| D, center bar | Broad race-yoke crossbar and rectangular center plate | Strong equipment silhouette, but leans toward a modern racing yoke |

Run `python docs/design/2026-08-27-yoke-icon-candidates/build.py` to regenerate
the transparent 128-pixel masters and 24-pixel review renders. Nothing here is
referenced by the plugin or copied over the approved production asset.
