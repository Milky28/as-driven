# Registering a simulator

This project cannot enumerate every racing simulator that exists, and it should
not try. What it can do is make the unrecognised case cheap: a drive from a game
nobody has registered is kept, is attributed to the game it came from, and is
released in bulk the day that game is registered.

## What happens to a drive from an unrecognised game

The client canonicalises SimHub's game name to a simulator id. When it does not
recognise the name it answers `other`, and everything downstream treats that as
**held, not rejected**:

- the guided drive still runs, and the draft is still written;
- the draft records `source_game_name`, exactly as the telemetry client supplied
  it, which is the only surviving record of which game was driven;
- intake stores the observation and classifies it `unregistered-simulator`;
- the review case sits in `blocked-on-simulator` and offers no actions, because
  none of them are the reviewer's to take;
- promotion refuses it outright, independently of what any interface offered.

The refusal is not fussiness. `other` is a bucket rather than an identity: two
unrelated games promoted under it would be indistinguishable inside a record,
and there is no prefix to name either one's sources with. A record answers a
driver with *this car, in this game*, and `other` cannot say which game.

`source_game_name` is provenance and never a lookup key. It is not normalised,
nothing is matched against it, and it exists so that registering a simulator
later releases the observations waiting on it rather than asking a contributor
to drive forty cars again.

## How a held drive is released

Registering the game is the whole action. `Sync GitHub submissions` picks the
held cases up by itself, and `intake-observation` releases a local draft the
same way. The observation on disk is never rewritten: it records what the client
knew when the drive was taken, and keeps saying `other`. What changes is the id
the case is filed under, which is what was blocking it.

That took more than it looks. Registering a simulator changes nothing about the
issue - same body, same attachment, same timestamp, same bytes - so every
shortcut on the sync path reported it unchanged and returned before intake could
look again. There were four: the draft's own `simulator` field, `_case_is_current`,
`_same_attachment_case`, and intake's duplicate detector. Each was right on its
own and together they made the promise above false. They share one question now,
`_held_case_is_now_releasable`, so the next shortcut added to that path has an
obvious place to ask it.

## Seeing what is waiting

`review-submissions queue` groups held cases by the game that produced them,
commonest first, so a contributor's large batch reads as one decision rather
than as many identical disappointments:

```
47 observations from unregistered simulators
  RRRE   41 cases, 23 distinct cars
  LMU     6 cases,  6 distinct cars
```

The name shown is the string the client reported. That is deliberately the same
string the canonicaliser will have to accept.

## Registering one

A simulator id is permanent and appears in source ids, so choose it once and
choose it plainly. The set is a mix of abbreviation and product name: `ams2`,
`ac`, `acc`, `ac-evo`, `ac-rally`, `iracing`, `raceroom`, `rfactor2`. Prefer a name a reader
can decode without a glossary.

Then add it in each of these places. The list is short by design, and a test
holds every one of them:

1. `schema/v1/car-record.schema.json` - the `simulatorEntry` enum.
2. `schema/v1/curation-approval.schema.json` - two enum sites.
3. `schema/v1/verification-observation.schema.json` - the observation enum.
4. `as_driven_db/validate.py` - `SIMULATORS`. `OBSERVING_SIMULATORS` derives
   from it and drives the source-naming convention.
5. `as_driven_db/site.py` - the display name and the filter label.
6. `simhub/AsDriven.Core/VerificationObservation.cs` - the writer's whitelist.
7. `simhub/AsDriven.Core/AsDrivenDatabase.cs` - `CanonicalizeSimulator`, and the
   three name maps.
8. `simhub/AsDriven.Plugin/AsDriven.cs` - the display name.
9. `simhub/AsDriven.Core/VerificationReviewRules.cs` - whether its telemetry can
   settle an automatic cut, and whether its gearbox refuses a downshift it should
   refuse. See below.

Accept every spelling a person might reasonably supply, as the Assetto Corsa and
RaceRoom entries do, and compare each one whole. Prefix matching would let one
game's name swallow another's.

## Whether the cut is measurable

`AutomaticCutIsMeasurable` decides whether review may ask a contributor to
settle `automatic_cut`. The test reads engine torque, because the cut is
ignition-side, so a simulator that does not publish torque through SimHub can
never answer it however many times the car is driven.

AC, ACC and RaceRoom do not publish it. An unregistered simulator is treated the
same way, because nothing is known about what it publishes. That is the safe
direction: a review that fails to ask for a measurable cut costs one value,
where a review that demands an unmeasurable one sends a contributor back to the
car forever.

When registering a simulator, drive one car and read the draft's method text.
It reports what it found rather than what it assumed:

- `automatic_cut_method` says in terms whether engine torque was published.
- the blip result says what the throttle read with the car stopped, which
  decides whether a spike on that channel can be attributed to anything.
- a clutch caveat appears only when the clutch channel disagreed with the test,
  and names the resting reading when it has one.

rFactor 2 was registered this way on 2026-08-26 and its first drive was read too
confidently. The throttle reading of 0% at rest and the absent clutch caveat did
settle that both channels follow the pedal. The same drive reported no engine
torque, and its cut was added to the unmeasurable list on that alone - then
removed again hours later when a Radical SR3 in the same simulator produced a
shift-local torque interruption. The channel exists; the first car did not
publish through it.

**One drive is a fact about one car.** A channel that reads wrong at rest is a
property of the simulator and generalises immediately. A channel that produced
nothing on one shift does not: it may be the simulator, the car, or that shift.
Wait for the second car before writing a rule, and prefer the per-attempt
message, which already separates "published no torque" from "torque held through
the change" without needing one.

**Registration flips the default.** An unregistered simulator is assumed
unmeasurable on every count, because nothing is known about it. A registered one
is trusted until a drive shows otherwise, which is why the first drive is worth
reading carefully rather than promoting.

## What registering does not do

It does not promote anything by itself. Held observations rejoin the ordinary
pipeline - identity research, review, the explicit promotion gate - with their
evidence intact. The simulator id answers which game; every question about which
car it is remains open, and is still decided the same way.
