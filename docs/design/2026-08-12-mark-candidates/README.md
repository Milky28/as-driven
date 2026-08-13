# Generated brand-mark candidates

Review-only. These do not replace the production mark at
`simhub/AuthenticControls.Plugin/Assets/authentic-controls-mark.png`, and the
plugin does not reference them.

Unlike the earlier ImageGen concept boards, these are produced by
`simhub/dash/brand_mark.py` using the same dependency-free canvas that draws the
control icons. A silhouette change is therefore a readable code edit rather than
an opaque binary, and any size can be regenerated exactly:

```powershell
python simhub/dash/brand_mark.py --output docs/design/2026-08-12-mark-candidates --size 256 --on-dark
```

`--on-dark` paints an ink disk behind the mark purely so a white-on-transparent
symbol is visible against a light page. The shipped asset has no background.

## Why the production mark reads as a helmeted face

Five cues stack up, and they reinforce each other:

| Element | Reads as |
| --- | --- |
| Closed enclosing circle | Helmet outline |
| Symmetric pair of horizontal spokes | Brow or eye line |
| Central mass at top centre | Nose or respirator |
| Cluster of vertical bars below it | Mouth grille |
| Exact bilateral symmetry | Faces are symmetric |

The circle is not the fault. The symmetric internal arrangement is, and the
respirator-plus-grille pairing is what makes the reading specific rather than
merely face-like.

## Candidates

- `mark-rim-lever-256.png` keeps a clean rim so the mark still reads as a
  steering wheel, then places a raked lever off-centre inside it with generous
  negative space. No spokes, no centred mass, no bar cluster. It survives at 48
  pixels, though the rim stroke is close to its lower limit there.
- `mark-lever-256.png` drops the wheel and shows only the lever. The strongest
  silhouette of the three and the most legible when small, at the cost of losing
  the steering half of the idea; it can read as a joystick out of context.
- `mark-gate-256.png` uses an H-pattern gate with the lever resting in one gate.
  Conceptually apt, but it reads as the letter H, so it would need reworking to
  look like a diagram rather than a wordmark.

## What the first attempt got wrong

The first pass attached the lever to an open arc at the same stroke weight. The
shapes fused into a single outline and both candidates read as letterforms, an
`a` and a `Q`. Two rules came out of looking at the renders:

1. Nothing touches the rim. Keep negative space between the arc and any inner
   element, or the silhouette collapses.
2. Vary the weight. A thin rim with a bold lever separates the two ideas; equal
   weights merge them.
