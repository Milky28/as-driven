# Convention guidance

## The problem this solves

279 technique fields across the curated records are `unknown`, and most will
stay that way. A three-car research pilot found the reason: gearbox
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

That is deliberate. 240 of the 279 open fields sit on an established mechanism,
so per-car text would be 240 things to review, each able to go stale on its own
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
