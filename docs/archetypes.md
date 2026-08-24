# Control archetypes

**Status: 252 of 255 records are classified** - 158 matches, 68 deviations, 15 undetermined, 11 with no archetype, and 3 awaiting classification. `data/v1/archetypes.json` holds 23 archetypes,
`schema/v1/control-archetype.schema.json` and the optional `archetype` block on
a car record define the contract, and `python -m as_driven_db validate` enforces
the rules below while identifying records that still await classification.

## The observation

Across the 255 curated records there are **72 distinct transmission blocks**.
Nine records in ten restate a pattern that already exists elsewhere in the
dataset. The four largest compatible families alone cover 91 records:

| Records | Mechanism |
| --- | --- |
| 37 | 6-speed sequential stick, clutch to pull away, lift-free upshift with cut, blip every downshift |
| 23 | 6-speed paddles, no clutch to pull away, automatic cut and blip |
| 16 | 6-speed paddles, clutch to pull away, automatic cut and blip |
| 15 | 5-speed standard H-pattern, clutch to pull away, lift on upshift, optional blip |

Only 30 records are one of a kind.

The GT3 records `audi-r8-lms-gt3`, `mclaren-720s-gt3-evo`,
`lamborghini-huracan-gt3-evo2` and `aston-martin-vantage-gt3-evo` share the same
control family, but the Audi and Lamborghini now retain an explicit
`automatic_cut: unknown` evidence gap. Each record was written out by hand,
each carries its own claims, and each required its own approval.

Two costs follow. The first is authoring: the per-record cost caps coverage, and
coverage is the only thing a driver experiences. The second is worse. The
findings that took real research — the Ginetta that is not the G40 Cup, the
Cayman's PDK override, the 98T's gear count — are structurally indistinguishable
from the 91 records around them. They are prose in a `notes` array, sitting
inside a shape that says nothing is unusual here.

## What an archetype is

An archetype is a **named, evidenced bundle of control values** that many cars
share. A record declares which archetype it matches and where it departs from
it. The departure is the point: it is what the research actually found.

## Rules

### 1. Descriptive, not authoritative

A record continues to store its own resolved values in full. The archetype is a
**label plus a validator**, not a source of data. Validation reports whether the
record matches the archetype it claims and lists every field where it does not.

This is the rule the other three depend on. It means an archetype can never
change what a record says, only describe it — so a mistake in an archetype
cannot silently rewrite the answer for 37 cars. It gives up most of the
authoring saving, and that is an acceptable price: the bottleneck on this
project is seat time, not typing.

### 2. Named by mechanism, never by racing class

`docs/data-model.md` already establishes this for wheel rims: shape is decided
by the rim itself, never by the car's racing class. Archetypes follow the same
rule, and the dataset shows why.

The nine curated GT4 cars agree on almost nothing. Three carry seven forward
gears from a road-car dual-clutch (`audi-r8-lms-gt4`, `bmw-m4-gt4`,
`mclaren-570s-gt4`) and six carry six. Three need the clutch to pull away
(`alpine-a110-gt4-evo`, `chevrolet-camaro-gt4-r`, `ginetta-g55-gt4`) and six do
not. A `gt4` archetype would be wrong for two thirds of the class depending on
which field you asked about.

The relationship runs the other way too. The 37-record cluster above spans CART,
GT1 2005, IndyCar, GT2 2005, GT1 and GTR 2004. Every cluster crosses classes and
every class crosses clusters. **Class predicts the archetype badly enough that
naming one after the other would import an error the dataset can already
disprove.**

### 3. An archetype never supplies `unknown`, and never resolves one

Two clusters, of 23 and 12 records, are mechanically identical. They differ on
exactly one field: `upshift.throttle_lift` is `not-required` in one and
`unknown` in the other. `bmw-m4-gt3` is in the second group and
`audi-r8-lms-gt3` is in the first.

That is not a difference in mechanism. It is a difference in **what has been
established**, and it must stay visible per record. So:

- a record may match an archetype while leaving fields `unknown`;
- an archetype must never fill an `unknown` with the value most of its members
  have, and tooling must never offer to;
- an archetype must never be inferred from a record that has `unknown` in the
  fields that define it.

Preserving `unknown` is the rule the whole dataset rests on. An archetype is a
convenient place to break it, which is exactly why it is stated here.

### 4. Provenance is unchanged, and so is approval

Every field keeps its own claim, source references, confidence and basis.
Membership of an archetype is not evidence and never appears as a `source_ref`.
A record that matches an archetype in every field still needs the same evidence
it needs today.

Classifying a record therefore **rides on the approval the record already has**
and never needs one of its own. The classification asserts nothing the approval
has not already covered: it describes values the record states and the approval
approved, and rule 1 stops it from changing any of them. A regression test
classifies a record with `curation/` in place and requires the repository to
stay valid, so this cannot quietly stop being true.

The one thing that would change this is a classification that could alter a
record. Nothing here can, and if that ever stops holding, the approval question
reopens with it.

## Deviations

Where a record departs from its archetype, the departure is declared, not merely
implied by the resolved values disagreeing. A declared deviation is expected and
quiet; an undeclared one is a validation failure. That is what makes the
mechanism safe: it turns an unintended change into a loud one, rather than
letting it pass as just another record that happens to differ.

## Choosing between equally close archetypes

A record can sit one field from several archetypes at once, and the data does
not say which one it departs from. This is not an evidence gap: no drive settles
which mechanism a car is named after, so `undetermined` would be the wrong
state. It needs a rule instead, and the rule is:

1. **Never cross shift actuation.** A stick car is never parented to a paddle
   archetype, whatever the member counts say. Actuation is the piece of hardware
   the driver fits, which is the question this project exists to answer, so a
   difference there is not a detail to be outvoted.
2. **Among what remains, the archetype with the most members wins.** A departure
   is most legible when it is stated against the most established version of the
   mechanism. Members means records that **match**, never records that deviate:
   counting deviations would make the rule depend on the order records were
   classified in, and a car that departs from a mechanism is not evidence of how
   established that mechanism is.
3. **Failing that, prefer a deviation in gear count over one in technique.** Gear
   count changes what the card states; technique changes what the driver does, so
   a record is better described as the archetype it drives like.

The order matters. `metalmoro-mrx-duratec-turbo-p2` is a stick car one field
from a 23-member paddle archetype and a 5-member stick one; member count alone
would parent it to the paddles, which is the wrong answer for the right-looking
reason.

Step 3 is a last resort and it does not always finish the job. `mcr-s2000` sits
one field from four stick archetypes with two matching members each; the rule
narrows it to the two that differ only in gear count, and five gears sit exactly
between four and six. It is recorded against the six-speed by decision, not by
derivation.

Neither step resolves anything about the record's values. Both archetypes were
one field away before the rule and one field away after it; all that changes is
which one the deviation is written against.

## Relationship to the no-silent-inheritance rule

`CLAUDE.md` states: do not silently inherit controls across aero, tyre,
generation, or suffix variants; record and review each intended relationship
explicitly.

Nothing here inherits anything. Records keep their own values, archetypes supply
none, and every relationship is declared in the record and checked by the
validator. The rule is satisfied by construction rather than by exception, and
that is the reason rule 1 is written the way it is.

## What this does not do

- It does not reduce the evidence any record needs.
- It does not let a new car be curated without a drive or a source.
- It does not give a client anything to display. Archetypes are a curation and
  review tool; the preflight card keeps showing resolved values.
- It does not create records. A car nobody has verified stays absent.

## Scope: the whole transmission block

An archetype is the **complete** transmission block: forward gears, actuation,
pattern, first-gear position, and every upshift, downshift and standing-start
field. Not a partial covering only the fields that recur.

### What the registry holds

167 of 242 records are fully specified, and among them there are 31 distinct
blocks. **22 of those blocks are registered as archetypes**; the other 9 have a
single member each and are not registered, because an archetype describes a
mechanism that recurs and a block with one member describes one car.

Three of the 22 are marked in `notes`: both their members are variants of one
car, so the block has not actually been seen to recur across unrelated cars
either. They are candidates for removal.

### How the 251 records fall out

Against that registry:

| | Records |
| --- | --- |
| `matches` an archetype exactly | 166 |
| `deviates` by one field | 12 |
| `deviates` by two fields | 1 |
| `deviates` by three fields | 0 |
| `undetermined` - a gap leaves two or more candidates | 13 |
| a gap, but only one candidate survives it | 49 |
| a gap, and no candidate survives it | 10 |

### Where `no-archetype` actually landed

The state was expected to be rare, and it is not: 14 records carry it, and only
one of them is what the state was written for.

- **Seven dogleg cars.** No registered archetype has a dogleg gate. Six of them
  share an identical block and would form one, but all six leave `gearbox_type`
  unknown and an archetype must be fully specified, so the archetype they belong
  to cannot exist yet. The seventh, the MP4/4, has six gears and the mirrored
  gate, so it does not join them either.
- **Six four-speed H-pattern cars** that need the blip, where the registered
  four-speed leaves it optional. Whether that is a departure or a mechanism of
  its own turns on `gearbox_type`: dog rings need the driver to match revs, which
  would make these an archetype rather than a variation.
- **`super-trophy-trucks`**, seven fields from its nearest peer of the same
  actuation - three ratios, a gearbox that shifts itself, and no clutch fitted
  anywhere. This one is genuinely a different mechanism.

Thirteen of the fourteen are therefore blocked rather than resolved, and the same
field blocks all of them.

**A one-field difference is a deviation, not a failure to classify.** This was
got wrong once already: the nine unregistered blocks were first treated as
`no-archetype`, when eight of them sit one field from a registered archetype and
the ninth sits two. `milano-gt55` is the clearest case - it is the 37-record
stick archetype plus the clutch on downshifts, which is the only such record in
the dataset and is exactly the research finding the classification should make
prominent. `no-archetype` is for a mechanism genuinely unlike anything
registered, and on the current dataset there may be no such record at all.

The 45 single-candidate records are also deviations: a gap is a difference from
the archetype like any other, so it is declared, with a basis saying it is not
yet established. The archetype still supplies nothing.

Those 45 declared 65 open fields between them, and the wording follows the
field, because the fields are not settled the same way:

| Open field | Records | Settled by |
| --- | --- | --- |
| `upshift.throttle_lift` | 22 | a drive - hold the throttle through an upshift |
| `downshift.manual_blip` | 20 | a drive, with an override where the real car differs |
| `gearbox_type` | 18 | **a reviewed source.** No drive separates a synchromesh from a dog box |
| `shift_pattern` | 5 | the cockpit - watch the lever through a shift |

`gearbox_type` is the one that does not yield to seat time, and it is the field
blocking the most records overall once the undetermined 13 are counted.

### The by-product

The undetermined records are a queue that generates itself, and classifying
them showed the queue is shorter than it looks. They fall into two questions,
not fourteen:

- **Eleven cars turn on one question.** Nine period formula cars, the 1974 911
  RSR and the 962C sit between `h-5-dogbox-clutch-start-lift-up-blip-down` and
  `h-5-synchro-clutch-start-lift-up-blip-optional`. Those archetypes differ on
  `gearbox_type` and `downshift.manual_blip`, and the two are **one question**:
  dog rings need the driver to match revs for the gear to engage, where a
  synchromesh leaves the blip optional. Establish the construction and the blip
  follows. No drive can do it, so this is desk research.
- **Three cars turn on the downshift blip alone.** `metalmoro-mrx-duratec-p4`,
  `metalmoro-mrx-duratec-turbo-p3` and `roco-001` sit between
  `stick-6-seq-clutch-start-flat-up-blip-down` and its no-blip twin. One drive
  each settles it.

Where a record has a gap both candidates agree on, the basis says so explicitly.
Otherwise a field that is merely irrelevant to the choice would read as settled
because the classification did not mention it.

## Open questions

- **`undetermined` cannot say "the archetype that fits may not exist yet."** It
  is defined as two or more surviving candidates, so a record with *no* surviving
  candidate falls to `no-archetype` even where the honest answer is that the
  question is open. Thirteen of the fourteen `no-archetype` records are in that
  position. Either the state needs widening or a fifth one is missing.

- Where archetypes live: a new file under `data/v1/`, or `schema/v1/`.
- Whether the three sibling-pair archetypes stay registered.
- Whether the 16 records that no archetype survives are deviations from a
  distant archetype or the first real `no-archetype` cases.
- Whether the 22 singletons get archetypes at all.

## Ordering

Do this before the aero-identity work. Archetypes change what a record
contains; the identity change alters how identities are written. Taking
identities first would mean touching all 242 records twice.
