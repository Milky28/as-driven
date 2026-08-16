# Data model v1

Version 1 uses one JSON file per car plus a source registry and release index.
The normative structures are the JSON Schemas in `schema/v1/`; this document
explains the modeling choices.

## Identity

`identity` names the represented real-world car or closest known variant. A
simulator marketing name does not silently become the real identity. Use
`real_world_identity_notes` when a game car blends seasons, trims, or fictional
attributes.

Simulator lookup keys live in `simulators[].identities`. Multiple typed values
allow a consumer to try a stable internal ID first and a display-name alias
last. Record IDs are stable project keys and must not be derived at runtime.

## Authentic controls

`authentic_controls` describes the represented car independently of any game:

- transmission family, actuation, H-pattern layout, and forward gears;
- separate upshift/downshift clutch, lift, cut, and blip behavior;
- wheel-rim description;
- optional steering degrees of rotation as troubleshooting/reference metadata.

The model separates `manual_blip` from `automatic_blip`. “No blip required” is
not automatically evidence of an electronic auto-blip; a gearbox may instead
wait for an acceptable engine speed.

### Wheel-rim shape

Shape is decided **by the rim itself**, never by the car's racing class. The
question the field answers is which rim a driver should fit, not what the car is
entered as, so a 1967 single-seater with a plain circular wooden rim is `round`,
not `formula`.

The first question is how your hands use the rim, because that decides which
family of hardware you would fit:

- A **control-panel rim** has molded grips at roughly 9 and 3 with a control
  face between them. Your hands stay where they are put. Modern formula and GT
  rims are both this.
- A **conventional rim** is a continuous band you can grip anywhere and slide
  your hands around, whatever its outline.

Take the first value that matches:

1. `yoke` — two separate grips with nothing connecting them, neither across the
   top nor across the middle.
2. `formula` — a control-panel rim that is **open across the top**: no rim
   material joins the two grips over the top.
3. `gt-style` — a control-panel rim with a **closed perimeter**, usually
   flattened at the top and the bottom.
4. `d-shaped` — a conventional rim flattened at the bottom, the top, or both.
5. `round` — a conventional rim that is a continuous circle.

Use `other` for a rim that genuinely matches none of these, and `unknown` when
the rim was not seen.

A closed perimeter is not a grippable one. A GT rim carries molded grips at 9
and 3 exactly as a formula rim does; what separates them is only whether rim
material arcs over the top, not where you would hold it. Equally, an older road
or touring wheel with its top and bottom flattened is a conventional rim and is
recorded `d-shaped`, not `gt-style`, because you still grip it all the way
around.

`prototype` is **deprecated**: it described a racing category rather than a rim,
and the rims it covered are the same closed control-panel form as `gt-style`. It
remains in the enum so existing records and drafts stay valid, but new records
must not use it.

Shape is separate from the optional `integrated_display`, `shift_lights`, and
`open_top` fields, so any shape may be recorded with or without each of them.

- `integrated_display` — any readout carried **on the rim itself**: a graphical
  LCD, an LED numeric gear indicator, or a segment display. A dash mounted on
  the car rather than the rim does not count, and shift lights alone do not
  count.
- `shift_lights` — shift or rev lights on the rim, recorded independently of
  `integrated_display`.
- `open_top` — whether the rim is open across the top. It is a modifier that
  applies to any shape, so a `formula` rim records `open_top: yes` and a
  `gt-style` rim records `no`. A `yoke` is always `open_top: yes`.

Because these definitions replaced an ambiguous earlier rule, values recorded
before them may not follow the decision order. See
`docs/wheel-rim-reverification.md` for the records that need another look.

## Simulator behavior and overrides

Each simulator entry has lookup identities, a compact `behavior` view suitable
for clients, and an exact `verified_game_version`. `overrides` describe
conditional deviations from the represented real controls. An override uses a
JSON Pointer path into the authentic controls, the effective value, a
human-readable condition, source references, and confidence.

The v1 `behavior` block intentionally retains common source-facing fields:
`shift_type`, `auto_blip`, `shift_cut`, and `wheel_rim_type`. `steering_dor` is
optional. This makes the initial AMS2 data useful without binding future
consumers to a spreadsheet vocabulary or turning the project into a general
vehicle database.

Simulator-observed wheel details may also appear in
`behavior.wheel_rim_type`. They do not silently establish the real rim. See
`docs/evidence-boundaries.md` for the authentic, simulator, and effective
guidance rules.

## Unknown, no, and not applicable

- `unknown`: evidence is missing or ambiguous.
- `no`: evidence supports nonexistence.
- `not-applicable`: the question has no meaning for this mechanism.

Importers may apply a different source rule only when documented. The AMS2
sheet says blank indicator cells mean “No,” so its importer converts blanks in
the imported Auto Blip and Shift Cut columns to `no`. It does not apply that
convention to other columns or sources.

## Provenance and confidence

Sources are registered once in `data/v1/sources.json`. Claims connect one or
more JSON Pointer paths to source IDs, a confidence level, and a concise basis.
Consumers may show record-level summaries, but the claim is the authoritative
unit of evidence.

Confidence levels are `verified`, `high`, `medium`, `low`, and `unknown`.
Confidence measures the strength and review state of the evidence, not how
strongly someone believes the value.

## Compatibility

Additive optional fields may ship in a minor schema revision. New required
fields, changed meanings, or removed enum values require a new major schema
directory and a migration tool. Dataset releases may advance independently of
the schema.
