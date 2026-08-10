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
