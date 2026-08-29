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

### A shared name is not a shared car

A second simulator's drive joins an existing record as another `simulators[]`
entry, which makes it tempting to match on the name the two games print. That is
the one place where this dataset can be wrong in the direction it is otherwise
designed against. Exact-match identity fails closed: a name no record claims
finds nothing and the driver is told so. Attaching a second simulator's entry to
the wrong record fails *open* - the plugin answers confidently, with another
car's controls.

So before merging, confirm the two games model the same specification, not just
the same nameplate. The recurring traps are:

- **Road against racing.** A homologation special and the car homologated from
  it are different cars with different gearboxes. The E30 M3 Sport Evolution and
  the 190E 2.5-16 Evo II each exist as both, and this dataset's records are the
  racing specifications.
- **Evolution suffixes.** `GT3` and `GT3 EVO`, `GT4` and `GT4 Evo` are different
  cars, and the suffix is often dropped in one game's naming and not the other's.
- **Generations behind one model name.** A 911 GT3 Cup is a 992 in one game and a
  991.2 in another; both are "911 GT3 Cup".
- **Kit variants.** A car and its tuner-kit version - a Cayman GT4 Clubsport
  against the Manthey MR - differ in ways that reach the controls.

Where the specification differs, the answer is a **new record**, not a second
entry: the road car and the racing car are two real cars, and one record per real
car means one each. Record the relationship in `real_world_identity_notes` rather
than letting the pair inherit from each other silently.

Evidence does not cross the same boundary. A homologation form establishing the
racing car's gearbox says nothing about the road car sold under that name, and
the reverse. See `docs/evidence-boundaries.md`.

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

A simulator entry may carry its own `display_name` and `class`, for the case
where a game renames the car or groups it its own way. The Prodrive Ferrari 550
is Milano GT55 in AMS2 and GT Ferruccio 55 V12 in Assetto Corsa, and neither is
the car; `identity` holds what it actually is, and each entry holds what its game
calls it. A client shows the matched simulator's name where one is recorded and
the record's own otherwise, so a car covered by two games never shows one game's
invention during the other's session. Where the summary can, it names the real
car and the alias together, because a driver who chose GT Adonis D9 V12 from a
car list has nothing else to connect it to an Aston Martin DBR9.

## Authentic controls

`authentic_controls` describes the represented car independently of any game:

- transmission family, actuation, H-pattern layout, and forward gears;
- separate upshift/downshift clutch, lift, cut, and blip behavior;
- wheel-rim description;
- optional steering degrees of rotation as troubleshooting/reference metadata.

The model separates `manual_blip` from `automatic_blip`. “No blip required” is
not automatically evidence of an electronic auto-blip; a gearbox may instead
wait for an acceptable engine speed.

### Construction and the running-shift clutch

`upshift.clutch` and `downshift.clutch` describe the technique the driver should
use for a shift already under way, not what the gearbox will physically tolerate.
Construction settles it, the same one way as the blip below:

- `synchromesh` takes `required` - the clutch is how the car is shifted, and a
  clutchless change is a trick that wears the synchros;
- `dogbox` takes `not-required` - clutchless shifting is the authentic technique;
- an unestablished `gearbox_type` leaves the clutch `unknown`.

**A guided drive can never establish this field.** The drive asks whether the
simulator accepts a shift without the clutch, and every simulator accepts one on
a synchromesh car because the real gearbox tolerates it too. Deriving the
authentic value from that answer told 72 H-pattern records that no clutch was
needed to change gear, a Chevette and a 2002 turbo among them, while their own
`standing_start_clutch: required` said the clutch was needed to pull away. The
drive's answer belongs in a simulator override; the authentic value waits for
construction research.

The 1973 Carrera RSR reached this independently through ordinary research, and
its declared deviation states it plainly: Porsche identifies a standard manual
with a mechanically operated clutch, so the authentic technique uses the clutch
"although the fingerprinted package accepts a clutchless upshift after lifting".

One record departs. `lamborghini-miura-sv` carries a reviewed research claim that
its synchronised five-speed supports clutchless running shifts as ordinary
technique. That conclusion is retained rather than overruled, declared as an
archetype deviation, and named in the test that enforces the rule.

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
established a dog box, and must not be promoted to one. Five records are in that
position today, and every one of them takes its blip from a guided drive rather
than from a source about the real car.

**Treat a drive-derived `required` as unsupported, not as a value.** Every time the
construction was later established for a car in that position - Formula Vee Gen2,
Formula Vee FIN, the Diablo SV-R - the authentic value was revised to `optional`
and the simulator's demand moved to an override. Three out of three. A simulator
demanding a blip is therefore no evidence at all about how the gearbox engages,
because it demands one on gearboxes established as synchromesh. The five records
still carrying `required` over an unknown construction are carrying it knowingly.

A car a simulator invented is outside this rule entirely. There is no real gearbox
to be wrong about, so the simulator is the only authority that exists and its
demand is the complete fact about the only version of the car there is. Four
records are in that position and are not counted among the five.

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

**Curation does not produce that state.** The client renders it defensively,
because an older dataset or another consumer's data may contain it, but a
`dogleg-h` is not proposed here until the side is established. All eight curated
doglegs name their side, and the reason to keep it that way is that "dogleg" is
the most inferable value in the dataset: a car's reputation suggests it, period
photographs are read at a glance, and a gate knob is easy to mis-see. Requiring
the side requires a source or a clear look, which is the same work that would
have caught a wrong dogleg. Where the side is not established, `shift_pattern`
stays `unknown` rather than becoming a half-answered dogleg.

This binds curation, not the schema: `first_gear_position` remains optional, and
`unknown` remains a legal value, because a consumer may hold data this project
did not curate.

### Wheel-rim shape

Shape is decided **by the rim itself**, never by the car's racing class. The
question the field answers is which rim a driver should fit, not what the car is
entered as, so a 1967 single-seater with a plain circular wooden rim is `round`,
not `gt-formula`.

The first question is how your hands use the rim, because that decides which
piece of hardware you would fit:

- A **control-panel rim** has molded grips at roughly 9 and 3 with a control
  face between them. Your hands stay where they are put.
- A **conventional rim** can be gripped around its perimeter, even when an upper
  section has been removed.

Take the first value that matches:

1. `gt-formula` - a control-panel rim. Modern GT, formula and prototype cars all
   share it, and it usually carries a display and rev lights.
2. `d-shaped` - a conventional rim with a flattened section.
3. `round` - a conventional rim with a generally circular outline.

Use `unknown` when the rim was not seen.

`gt-style`, `formula`, `prototype`, `yoke`, and `other` are **deprecated**.
The first three split one control family by racing class. `yoke` duplicated the
open-top modifier without a stable boundary from other open-top rims. `other`
did not produce actionable hardware advice. They remain in schema enums only so
old drafts and approvals can be read. Curated records and new drafts must use
only the active values above.

An older road or touring wheel with its top and bottom flattened is a
conventional rim and is recorded `d-shaped`, because you still grip it all the
way around. Flattening alone never makes a rim `gt-formula`; molded grips and a
control face do.

Shape is separate from `integrated_display` and `shift_lights`. `open_top` is a
modifier only for conventional `round` and `d-shaped` rims.

- `integrated_display` - any readout carried **on the rim itself**: a graphical
  LCD, an LED numeric gear indicator, or a segment display. A dash mounted on
  the car rather than the rim does not count, and shift lights alone do not
  count.
- `shift_lights` - shift or rev lights on the rim, recorded independently of
  `integrated_display`.
- `open_top` - for a conventional rim, whether an upper section of the rim is
  removed. Use `not-applicable` for `gt-formula`. A GT or Formula rim's fixed
  grips and central control face already determine the hardware choice, so this
  field does not split that family by outline.

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
