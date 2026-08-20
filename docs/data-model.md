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

### Aero packages

A simulator may report one car under several names, one per aero configuration,
and it picks the configuration from the circuit rather than from the driver.
Writing every spelling out by hand cost 158 of 404 curated telemetry names and
forty-two reviewer-derived identities that nobody had ever observed.

A `telemetry-name` may instead declare `aero_packages`, and the base name grows
one exact key per package when the database is read:

```json
{ "kind": "telemetry-name",
  "value": "Lola B2K00 Ford-Cosworth",
  "aero_packages": ["base", "high-downforce", "speedway", "superspeedway"] }
```

This is not fuzzy matching and it does not soften exact matching. Expansion
produces exact strings once, at load, and nothing is rewritten when an incoming
name is compared, so a package a record does not declare still fails to match,
still logs as unmatched, and still shows a blank card rather than another car's
answer. Which packages a car offers is read per class and never assumed from
another car: two AMS2 open-wheel classes offer no low-downforce package at all.

How a package is spelled belongs to the simulator, not the record. AMS2 appends
` - High Downforce` and its siblings and renders `base` as the bare name; a
simulator that names its variants unsystematically declares nothing and writes
its identities out literally. `as_driven_db.validate` and the client hold the
same table, and a round-trip test requires expansion to reproduce every string
the records used to spell out.

The package is deliberately absent from guidance. It changes no rim, no shifter
and no technique, so every configuration of a car resolves to one record and one
card, and a curated `display_name` carries no package either.

A record is **one real car**, with an entry in `simulators[]` for each simulator
that covers it, so its `record_id` names the car and never the simulator. Until
dataset 0.3.67 every id carried an `ams2.` prefix, which was true only because
AMS2 happened to cover them first; the same car verified in a second simulator
would have collided with its own prefix and forked into two records for one car.
A second simulator's drive joins the existing record instead, and it never
rewrites the real car: a disagreement is either a correction made deliberately
or a deviation recorded as an override.

`source_id` keeps its simulator prefix, and so does an observation id. That
evidence really does belong to one drive in one game.

## Authentic controls

`authentic_controls` describes the represented car independently of any game:

- transmission family, actuation, H-pattern layout, and forward gears;
- separate upshift/downshift clutch, lift, cut, and blip behavior;
- wheel-rim description;
- optional steering degrees of rotation as troubleshooting/reference metadata.

The model separates `manual_blip` from `automatic_blip`. “No blip required” is
not automatically evidence of an electronic auto-blip; a gearbox may instead
wait for an acceptable engine speed.

### Construction and the downshift blip

A synchromesh matches the shaft speeds itself, so a blip on the way down eases
the synchros and is authentic technique rather than a requirement. Dog rings do
not, so the driver must match revs or the gear will not engage cleanly. The
dataset records that difference consistently:

- `synchromesh` takes `manual_blip: optional` - a decided fact, not a hedge;
- `required` is reserved for gearboxes that need the blip to engage.

**The mapping runs one way only.** An established construction settles the
technique. The technique does not settle the construction: a record carrying
`manual_blip: required` while `gearbox_type` is `unknown` has not thereby
established a dog box, and must not be promoted to one. Ten records are in that
position today, and every one of them takes its blip from a guided drive rather
than from a source about the real car.

That is also why the two can disagree without either being wrong. Where a
simulator demands a blip the real gearbox does not need, the real car keeps the
construction's answer and the simulator's demand is recorded as an override - and
an override needs a drive that found the shift *refused* without a blip, not one
that merely found it accepted with one.

### Where first gear sits

`shift_pattern` names the layout; optional `first_gear_position` says where
first gear actually is. The two are not the same fact. `dogleg-h` establishes
that first sits outside the racing plane, but not which side of it: the McLaren
MP4/4's gate is mirrored, with first at the bottom right. A client must not
infer the side from the pattern. Where the field is absent or `unknown` the
guidance says first is outside the plane and stops there, and a dogleg may not
record first as being up.

### Wheel-rim shape

Shape is decided **by the rim itself**, never by the car's racing class. The
question the field answers is which rim a driver should fit, not what the car is
entered as, so a 1967 single-seater with a plain circular wooden rim is `round`,
not `gt-formula`.

The first question is how your hands use the rim, because that decides which
piece of hardware you would fit:

- A **control-panel rim** has molded grips at roughly 9 and 3 with a control
  face between them. Your hands stay where they are put.
- A **conventional rim** is a continuous band you can grip anywhere and slide
  your hands around, whatever its outline.

Take the first value that matches:

1. `gt-formula` — a control-panel rim. Modern GT, formula and prototype cars all
   share it, and it usually carries a display and rev lights.
2. `yoke` — two grips with nothing joining them over the top.
3. `d-shaped` — a conventional rim flattened at the bottom, the top, or both.
4. `round` — a conventional rim that is a continuous circle.

Use `other` for a rim that genuinely matches none of these, and `unknown` when
the rim was not seen.

`gt-style`, `formula` and `prototype` are **deprecated**. They split one rim
three ways along racing class, which is information the car's name already
carries: a driver who knows they are about to drive a formula car does not need
the database to tell them to fit a smaller rim. The three produced the same
client icon, and the boundaries between them were not decidable from the
cockpit — modern formula and GT rims are closed over the top alike, so no
geometric test separated them. They remain in the enum so existing records and
drafts stay valid, but new records must not use them.

An older road or touring wheel with its top and bottom flattened is a
conventional rim and is recorded `d-shaped`, because you still grip it all the
way around. Flattening alone never makes a rim `gt-formula`; molded grips and a
control face do.

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
