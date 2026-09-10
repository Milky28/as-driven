# Convention guidance

## The problem this solves

529 technique fields across the curated records are `unknown` - counting the
eleven per record that describe launch and shift technique - and most will stay
that way. A three-car research pilot found the reason: gearbox
architecture is published everywhere, while launch technique, running-shift
technique and cockpit detail are published almost nowhere. Every source named
the gearbox, its gear count and its actuation; not one named whether the driver
needs the clutch to pull away.

Left alone that produces an overlay which answers "not established" for a large
part of the database, which helps nobody. The gap widens as older cars are
added, where concrete sources are least likely to exist and, at the same time,
the general answer is most nearly certain: a 1950s H-pattern car needed the
clutch to pull away.

## What it is, and what it is not

Convention guidance is a third layer, beside the two the dataset already keeps
apart:

- `authentic_controls` - what the real car is established to have done;
- `simulators[].behavior` - what a simulator was observed doing;
- convention guidance - what cars of this mechanism and era usually did.

It never becomes an authentic value. `authentic_controls` stays exactly as
strict as it is today, and a field that is `unknown` stays `unknown`. Convention
guidance is displayed instead of a blank, phrased so a driver knows which one
they are reading: the real technique is not established, and this is how such a
car was usually driven.

## Rules, not per-car text

The reviewed unit is the rule, not the sentence on a car. A rule carries its
scope, its basis and its strength, and is applied wherever its antecedent is
established and the target field is unknown. Nothing is written into a car
record; the client and the public catalog apply matching rules when they render.

That is deliberate. most open fields sit on an established mechanism,
so per-car text would be hundreds of things to review, each able to go stale on its own
and each looking exactly like an authentic value once written into a record. A
rule is reviewed once, corrected everywhere at once, and cannot be quietly wrong
for a single car without being wrong for the class.

The dataset already derives technique from mechanism this way. "An H-pattern
gate settles the standing-start clutch" and "a dog box cannot match the shaft
speeds for the driver" are era and type generalisations, accepted because every
curated record and every registered archetype agreed and none dissented. Those
write into `authentic_controls` because the evidence is unanimous. Convention
guidance is the same machinery where the evidence is weaker, and the output is
labelled rather than curated.

## Two forms of the same sentence

Every rule carries its guidance twice: the full sentence, and a card-length
`short_guidance` that keeps the hedge and the instruction and drops the
reasoning.

That is not a convenience. The catalog can spend a paragraph on a rule and the
overlay card can spend one line, and the difference is large enough that a
client which only had the long form would have to truncate it. Truncation cuts
wherever the width runs out, which is as likely to drop what the driver should
do as the reasoning behind it. Writing the short form decides in advance what
survives.

Both forms must say the real value is not established before saying what such
cars usually did, because the wording is the only thing separating convention
from a finding about the car in front of the driver. The schema caps the short
form at 72 characters as a coarse guard; the binding limit is width, and the
client tests measure the resolved line against the narrower of the two packaged
cards and fail if it ellipsises.

The public catalog shows both, short form first. That makes this page the
"elsewhere" the card's reasoning lives: a driver who reads one line on the
overlay can find out here why it says what it says.

## Rules that must hold

- A rule fills an `unknown`. It never overrides, contradicts or outranks an
  established value. `lamborghini-miura-sv` is the standing counter-example: its
  own reviewed research says clutchless running shifts are ordinary on that
  synchromesh gearbox, against the pattern of every other synchromesh record. A
  rule that overwrote it would be wrong about a real car.
- Convention text can never be promoted into `authentic_controls` without a
  source. Promotion requires evidence, not agreement with a rule.
- Each rule declares its own scope and strength. A rule's confidence is
  inversely proportional to how much its era varied: a pre-war or 1950s
  driver-shifted car is nearly certain, while "modern GT3 cars blip
  automatically" is manufacturer-dependent and would be a bad rule. Rules are
  admitted individually, on their own evidence, not by blanket policy.
- A rule is evidence about a class and is cited as such. It is never presented
  as a finding about the specific car.

## The steering-DOR decision

Steering degrees of rotation was kept but not pursued, on the grounds that what
the field would hold is "a subjective or by-era generalisation, which is the one
thing this dataset does not do". This narrows that decision rather than
reversing it. DOR had no mechanism to key on, so a value would have been an era
guess with nothing beneath it. These rules key on hardware the record already
establishes, and their output is never stored as the real car's answer. DOR
remains out of scope.

## The standard a rule has to meet

The first two rules written against this design settled what admission requires,
because only one survived.

`h-pattern-unestablished-construction-running-clutch` was admitted. Of the
H-pattern records whose construction is established, 46 of 59 are synchromesh,
and where it is synchromesh the running-shift clutch is required in 38 of 39
cases. So the antecedent is right about 78% of the time, which on its own would
not be enough. What admits it is the asymmetry: a dog box accepts the clutch, it
simply does not need it, so a driver following this guidance is never wrong even
on the fifth of cars where it is unnecessary. It reaches 84 open fields.

A second rule, that a lever-shifted sequential gearbox is blipped on the way
down, was written and then dropped. The dataset says 33 such records require the
blip and 13 do not, and narrowing the antecedent to cars with no automatic blip
only moved it to 33 against 7 while reaching four open fields. The determining
fact is whether the box is dog-ring, which those records do not establish -
so the rule was generalising over exactly the gap that makes the value unknown.
That is the guess this dataset refuses, and a majority is not a licence for it.

So: a rule needs a near-unanimous base, or an asymmetry that makes following it
harmless when it is wrong. A simple majority over an unestablished determining
factor is not a rule, and reach does not compensate for it.

## Checking

```shell
python -m as_driven_db conventions
```

Reports how many open fields the rules reach, and fails if any rule contradicts
a value a record establishes. A contradiction is a defect in the rule, not an
exception to it: the record knows about one real car and the rule only knows
about a class.

## The SimHub client

`AsDriven.Core.ConventionRules` reads `conventions.json` from beside the dataset
and resolves rules against a record's authentic controls, not against the values
a simulator overrides, because the gap being filled is the real car's. The same
note therefore applies to every simulator view of a record. A database published
before conventions existed simply has no file, which yields no guidance rather
than an error, so an older dataset still loads.

The plugin publishes `AsDriven.ConventionGuidance` and its wrapped
`ConventionGuidanceLine1-4` and `ConventionGuidanceCompactLine1-4`, so any
dashboard can bind them. It also publishes `AsDriven.ConventionGuidanceShort`
and the two single-line forms `ConventionGuidanceShortLine` and
`ConventionGuidanceShortCompactLine`, already fitted to the note width of the
detailed and compact cards. The short form is published as one property rather
than a numbered set on purpose: a card needing a second line wants the long
form and the room to hold it. All of them are empty for most cars, and a panel
bound to them should hide itself rather than reserve blank space, exactly as the
driver note does.

## The packaged card

The card is a fixed layout with no room for a panel of its own: the note panel
occupies 264 to 363 and the footer rule sits at 371. So guidance shares the note
panel, which is drawn in three states, chosen by expression and mutually
exclusive:

- a summary alone, across five lines - the card as it was;
- a summary across four lines with the guidance line beneath it;
- the guidance line alone, at the top of the panel, for a car with no summary.

Sharing spends the fifth summary line on the cars carrying both, which is the
cheapest thing available: of the 39 such records, none uses the fifth line on
the detailed card and one - `bmw-3-0-csl-imsa-1975` - uses it on the compact
card. Nothing else on the card moves, so an overlay a driver has already
positioned stays where they put it.

The guidance line is drawn in the accent tone rather than the text tone. It is
the only line in that panel not about the car in front of the driver, and the
colour says so before the sentence does.

One consequence is worth naming, because it would otherwise lose text in
silence. The summary is pre-wrapped by the client, and a wrap for five rows
drawn into four would simply not draw whatever landed on the fifth. A greedy
wrap breaks the earlier rows the same way whatever its limit, so only the last
row differs: the client publishes `DriverSummaryLine4Of4` and its compact twin,
the last row of a four-row wrap, which ellipsises the tail. The shared state
binds rows 1 to 3 from the five-row wrap and its last row from that one.
