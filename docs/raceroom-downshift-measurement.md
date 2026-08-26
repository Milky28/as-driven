# What a RaceRoom drive can and cannot establish

RaceRoom Racing Experience was registered as `raceroom` on 2026-08-26 and four
cars were driven in it the same day. Three of its telemetry channels turn out not
to answer the questions the guided drive asks of them. This note records which,
so nobody re-drives a car hoping for a different result.

None of this is a complaint about the simulator. It is a statement about what its
published telemetry can support as evidence.

## The downshift never refuses

The drive learns from a **refusal**. A gearbox that will not take the gear
without a blip is telling you the driver has to supply one, and the manual-blip
test runs only when the coast test fails that way.

Driving the Mercedes 190E Evo II DTM, the maintainer found the car took a
clutchless downshift at any engine speed. Nothing was ever refused, so
"clutchless downshift accepted" is a fact about RaceRoom's transmission model
rather than about the car, and the manual-blip test behind a refusal is
unreachable.

The 190E is the clearest possible case. It is already curated from AMS2 as a
dogleg H-pattern **synchromesh** with `automatic_blip: no` - a 1990 touring car
with an ordinary manual gearbox, which has no mechanism to blip for anybody.

## The throttle spike cannot be attributed

All four cars reported `automatic_blip: yes`. The measured peaks were 98% on the
Saleen S7R and 29% on the 190E: not two readings of one phenomenon.

The assist was off in every case. RaceRoom's transmission setting offers Manual,
Manual with auto-blip, Manual with auto-clutch and blip, and Automatic, and the
drives were done on plain **Manual**. The assist being off does not by itself
make a blip impossible - a modern GT3 rev-matches because the car does, not the
assist - but it removes the obvious explanation for a 1990 saloon.

**Settled 2026-08-26: the throttle channel does not report the pedal either.**
A re-drive of the Saleen with the resting reading in place returned:

> A throttle spike was detected, peaking at 98% (the threshold is 15%). The
> throttle already read 24% with the car stopped before any test began, so this
> channel is not reporting the pedal alone and the spike is not evidence that the
> car blipped.

24% with the car stopped and nobody touching anything. RaceRoom publishes engine
or idle state on this channel, as it already does on the clutch channel, which
reads 100% at rest. A spike on such a channel appears on every car and attributes
to none of them. That is why all four cars driven here reported the same
`automatic_blip: yes` while their peaks ranged from 29% to 98%.

The drive now records `unknown` rather than `yes` when the resting reading
disqualifies the channel, matching what the automatic cut already does when
nothing could be measured. Neither `yes` nor `no` is available on a channel like
that: the absence of a spike would be as meaningless as its presence.

## The automatic cut cannot be measured

RaceRoom publishes no engine torque through SimHub. The cut is ignition-side and
the test reads torque, so nothing is measured however often the car is driven.
This is the same gap as AC and ACC, and it was recorded from the first drive.

## What a RaceRoom drive still establishes

Forward gear count, shift actuation, the gate, and the wheel rim. That is real
coverage and worth having. It is the shift-technique fields that the simulator
cannot speak to.

## What the client does about it

`VerificationReviewRules.AutomaticCutIsMeasurable` and
`DownshiftEngagementIsMeasurable` both answer false for `raceroom`, so review
stops asking a contributor to settle values no drive there can produce. Both also
answer false for `other`, because an unregistered simulator has been
characterised even less.

## What was retracted

`saleen-s7-r-gt1` and `alfa-romeo-156-super-touring` were promoted with a
RaceRoom `automatic_blip: yes` and a `manual_blip: not-required` override taken
from these drives. Both are now `unknown`, in the record and in the approval,
with the observation kept and its interpretation withdrawn.

`bmw-m4-gt3` was retracted too, once the channel was measured rather than
suspected. It was held back at first on the grounds that the car genuinely
rev-matches and the value agreed with the AMS2 and ACC entries on the same
record. Both are still true, and neither is a reason for its RaceRoom entry to
assert something that drive could not have observed. The record says the same
thing without it: the real car's `automatic_blip: yes` rests on the other two
simulators and is untouched.

That is the distinction worth keeping in view. What was retracted is what
RaceRoom was said to do, not what the car does.

## What would reopen this

A resting throttle of zero on a RaceRoom drive, which would show the channel does
follow the pedal, or a downshift RaceRoom refuses, which would show its gearbox
model discriminates after all. Either one is a single drive away.
