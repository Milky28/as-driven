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

One is now a **supported departure** and the other 24 remain **provisional
departures**. The Audi launch-clutch finding has exact-car evidence strong enough
for a benchmark conclusion; the remaining conflicts still lack both high
confidence and a registered manufacturer or homologation source for the exact
disputed field. Simulator agreement or a previously curated answer is not enough
to call one implementation authentic.

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

## First supported finding

**Audi R8 LMS GT3 Evo II — pulling away.** Audi's exact technical data for the
2022 car specifies an electrohydraulically operated three-plate racing clutch on
printed page 8 of 16. A first-person track test of the exact Evo II then states,
"Anfahren ist mit dem am Lenkrad montierten Kupplungshebel ein Kinderspiel,"
directly establishing use of the steering-wheel-mounted clutch lever to move
off. Neither source establishes a clutch pedal, anti-stall mode, or automated
launch procedure.

The fingerprinted AC RSS v2 implementation matches that clutch-required launch.
AMS2 1.6.9.91, Assetto Corsa EVO 0.8.1, and ACC build 21257365 each accepted
clutch-free move-off with automatic clutch and shifting disabled, so those exact
reviewed implementations are supported departures from the real-car baseline.
This finding does not infer why the simulators differ.

Sources: [Audi technical data for the 2022 R8 LMS][audi-technical] and
[AUTO BILD's Evo II track test][autobild-track-test].

## Next research queue

Research should begin with findings that materially change hardware or driving
technique and have a realistic path to primary evidence:

1. **Lotus Renault 98T — forward gears.** AC models six and AMS2 models five.
   The curated six-speed baseline is currently secondary-source-backed, making
   a period Lotus, Renault or Hewland document the cleanest route to a verdict.
2. **Porsche 911 RSR 1974 — gate pattern.** AMS2 models a conventional 915 gate;
   the reviewed AC implementation models a dogleg. A Porsche parts diagram,
   workshop manual or homologation document should be able to settle the 915
   selector layout directly.
3. **Mercedes-AMG GT3 — pulling away.** AMS2 accepts a clutch-free launch while
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

[audi-technical]: https://www.audi-mediacenter.com/system/production/uploaded_files/19514/file/259808bc1b08337b8b1096c2f4008a6fcde1be67/Technische_Daten_Audi_R8_LMS_GT3_2021_GB.pdf
[autobild-track-test]: https://www.autobild.de/artikel/tracktest-audi-r8-lms-gt3-evo-ii-27575473.html
