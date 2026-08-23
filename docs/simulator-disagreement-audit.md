# Simulator disagreement audit

The comparison site can establish that two reviewed simulators give different
answers. That is not yet a verdict about authenticity. This audit connects each
conflict to the curated real-car baseline, the evidence supporting that exact
field, the simulator versions that were tested, and the next action required
before publishing a benchmark conclusion.

The checked-in artifact is
`research/simulator-disagreement-audit.json`. Regenerate it after any record or
simulator-entry change:

```shell
python -m research.build_simulator_disagreement_audit
```

The website refuses an audit whose dataset version differs from the release
index. Tests also compare its complete finding set with the site's independently
calculated conflicts, so a new disagreement cannot appear on the page without
entering the audit.

## Current result

Dataset 0.4.20 contains 25 field-level findings across 19 cars:

- 8 affect pulling away;
- 7 affect running-shift technique;
- 6 affect hardware choice or configuration; and
- 4 affect cockpit display or shift-light equipment.

All 25 are currently **provisional departures**. The simulator observations
conflict, and the curated authentic baseline gives an answer, but none of the
exact disputed fields has both high confidence and a registered manufacturer or
homologation source. This is a useful negative result: simulator agreement or a
previously curated answer is not enough to call one implementation authentic.

The audit uses three statuses:

- `supported-departure`: the exact authentic field has high-confidence
  manufacturer or homologation support;
- `provisional-departure`: the baseline gives an answer, but its source strength
  is not yet sufficient for a benchmark verdict; and
- `authentic-baseline-open`: the real-car field is unknown, so neither simulator
  can yet be judged against it.

Unknown simulator values do not enter the audit. One simulator knowing less than
another is an evidence gap, not a disagreement. No majority vote can rewrite the
authentic baseline.

## First research queue

Research should begin with findings that materially change hardware or driving
technique and have a realistic path to primary evidence:

1. **Audi R8 LMS GT3 Evo II — pulling away.** AMS2, AC EVO and ACC accept a
   clutch-free launch; the fingerprinted AC implementation requires clutch
   input. Find Audi documentation that establishes whether the real car has a
   driver-operated clutch pedal or launch-clutch control.
2. **Lotus Renault 98T — forward gears.** AC models six and AMS2 models five.
   The curated six-speed baseline is currently secondary-source-backed, making
   a period Lotus, Renault or Hewland document the cleanest route to a verdict.
3. **Porsche 911 RSR 1974 — gate pattern.** AMS2 models a conventional 915 gate;
   the reviewed AC implementation models a dogleg. A Porsche parts diagram,
   workshop manual or homologation document should be able to settle the 915
   selector layout directly.
4. **Mercedes-AMG GT3 — pulling away.** AMS2 accepts a clutch-free launch while
   ACC requires physical clutch input. The target is documentation of the
   original car's clutch pedal, hand-clutch or anti-stall/launch arrangement,
   kept separate from the 2020 Evo.

Cockpit display and shift-light conflicts remain recorded, but follow these
driver-technique and hardware findings unless a primary cockpit source is
already at hand.

## What a published finding must say

A supported benchmark finding names the real-car evidence, every exact
simulator version and implementation tested, the values that match and depart,
and any telemetry boundary that prevents a stronger conclusion. It does not
infer why a simulator differs, generalize from one mod to another, or score an
entire simulator from one car.
