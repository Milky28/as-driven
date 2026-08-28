# Flat preflight icon family

These 128×128 transparent PNG masters are the production-oriented icon set for
the row-based preflight overlay proposal. They are intentionally not wired into
the current four-tile dashboards yet; the overlay redesign can adopt the family
as one change instead of mixing old and new visual languages.

The source is deterministic geometry in `../icons.py`. Regenerate the files
without an image-generation model or external package:

```powershell
python simhub/dash/icons.py
```

## Design rules

- one off-white colour on transparency; row rails and `You` / `Car` tags own
  semantic colour;
- a common 128-pixel grid, roughly 16 pixels of outer breathing room, and
  7–11 pixel master strokes;
- no embedded tile, shadow, lighting, texture, or class-based styling;
- shapes remain distinguishable at the proposal's approximately 24-pixel row
  size;
- the wheel icon describes rim construction only. Round and D-shaped rims have
  separate open-top variants; display and shift-light state stays in text,
  matching the database contract;
- the current raster As Driven mark remains the title icon and is not duplicated
  in this family.

## Assets

| Group | Files |
| --- | --- |
| Wheel rims | `wheel-round`, `wheel-round-open-top`, `wheel-d-shaped`, `wheel-d-shaped-open-top`, `wheel-gt-formula`, `wheel-unknown` |
| Shift controls | `shift-h-pattern`, `shift-dogleg-h`, `shift-sequential-stick`, `shift-sequential-paddles`, `shift-automatic-lever`, `shift-direct-selection`, `shift-unknown` |
| Driver and note rows | `control-clutch`, `control-throttle`, `note-info` |

The review sheet is at
`../../../docs/design/2026-08-16-preflight-icons/preflight-icon-family-v1.png`.
