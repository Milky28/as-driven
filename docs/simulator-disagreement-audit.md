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

Two are now **supported departures**, 22 remain **provisional departures**, and
one has an **open authentic baseline**. The Audi and original Mercedes-AMG GT3
launch-clutch findings have exact-car evidence strong enough for benchmark
conclusions. The Lotus 98T research established real configuration variation
rather than a winning simulator answer. Simulator agreement or a previously
curated answer is not enough to call one implementation authentic.

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

## Supported findings

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

**Original Mercedes-AMG GT3 — pulling away.** AMG Customer Sports' operation
manual, version 03, says on printed page 12 that the clutch has to be operated
when shifting from neutral to first; printed page 6 instructs the driver to ease
the clutch in. A first-person March 2016 test of the exact original car
independently identifies its clutch pedal as the control racers use to get the
car moving. Neither source establishes anti-stall or an automated launch clutch.

ACC build 21257365 matches the clutch-required real car. AMS2 1.6.9.91 accepted
clutch-free move-off with assists disabled, making that exact implementation a
supported departure.

Sources: [AMG Customer Sports operation manual][amg-manual] and
[Car and Driver's exact 2016 first drive][amg-first-drive].

## Resolved as a scope ambiguity

**Lotus Renault 98T — forward gears.** The 1986 program used both five- and
six-speed Lotus/Hewland configurations. Senna is documented choosing the
five-speed while the six-speed development configuration also ran. The generic
record combines drivers, chassis and race specifications, so it cannot assign a
single authentic count.

AMS2's five gears and AC's six are both compatible with real 98T configurations.
Neither is a demonstrated departure without a narrower simulator identity. The
audit retains the conflict as `authentic-baseline-open`, which makes this a
useful benchmark boundary rather than an unresolved source hunt.

Sources: [Classic Team Lotus-licensed 98T issue][lotus-licensed] and
[the surviving Senna 98T-3 account][lotus-98t-3].

## Next research queue

Research should begin with findings that materially change hardware or driving
technique and have a realistic path to primary evidence:

1. **Porsche 911 RSR 1974 — gate pattern.** Research confirms that the exact RSR
   used the RS-derived five-speed Type 915 and that a conventional H is the
   best-supported layout. The period workshop manual and FIA homologation form
   do not expose a readable exact-RSR selector diagram, however, so AMS2's
   conventional gate remains a provisional match and AC's dogleg a provisional
   departure. The January 1974 RSR operating manual is the best remaining lead.
2. **BMW M6 GT3 — pulling away.** AMS2 accepts a clutch-free launch while ACC
   requires clutch input. Seek an exact manufacturer operation manual or direct
   cockpit test, keeping launch control and anti-stall separate from the physical
   clutch hardware.
3. **Mercedes-AMG GT3 Evo — pulling away.** Audit the 2020 Evo independently of
   the original car just resolved; shared transmission lineage cannot establish
   an unchanged launch procedure by itself.

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
[amg-manual]: https://www.scribd.com/document/972539624/Manual-B-ENG-Vehicle-Operation-R03
[amg-first-drive]: https://www.caranddriver.com/reviews/a15101465/mercedes-amg-gt3-race-car-first-drive-review/
[lotus-licensed]: https://d24udp600h4lxn.cloudfront.net/dea/live/media/27-lotus-senna-uk-web/27-lotus-senna-uk-web.pdf
[lotus-98t-3]: https://www.auto-motor-und-sport.de/formel-1/auktion-ayrton-senna-lotus-98t-rm-sothebys/
