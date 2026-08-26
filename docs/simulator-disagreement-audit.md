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

Dataset 0.5.1 contains 26 field-level findings across 20 cars:

- 8 affect pulling away;
- 7 affect running-shift technique;
- 6 affect hardware choice or configuration; and
- 4 affect cockpit display or shift-light equipment.

Seven are **supported departures**, three remain **provisional departures**, and
15 have an **open authentic baseline**. Five launch-clutch findings have
exact-car evidence strong enough for benchmark conclusions: the Audi R8 LMS GT3
Evo II, both Mercedes-AMG GT3 generations, the Mercedes-AMG GT4, and the BMW M6
GT3. Exact manufacturer cockpit photographs now also settle wheel geometry for
the 2018 Nissan GT-R NISMO GT3 and 2019 Porsche 911 GT3 R. A complete review of
the previous provisional queue found that sixteen more baselines had inherited
simulator observations without independent real-car support. They became explicit
open findings rather than weak verdicts; the two exact cockpit sources have since
closed two of those gaps. Simulator agreement or a previously curated answer is
not enough to call one implementation authentic.

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

**Audi R8 LMS GT3 Evo II - pulling away.** Audi's exact technical data for the
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

**Original Mercedes-AMG GT3 - pulling away.** AMG Customer Sports' operation
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

**Mercedes-AMG GT3 Evo (2020) - pulling away.** The exact 2020 operation
manual says on printed page 7 to press the clutch, engage first gear, and ease
in the clutch. Printed page 13 confines clutch use to the neutral-to-first
shift, while page 14 separately documents ECU-controlled double-clutching on
downshifts. The manual does not establish anti-stall or an automated launch.

ACC build 21257365 matches that clutch-required launch. AMS2 1.6.9.91 accepted
clutch-free move-off with assists disabled, making that exact implementation a
supported departure.

Source: [Mercedes-AMG GT3 2020 Operations Manual R01][amg-evo-manual].

**Mercedes-AMG GT4 - pulling away.** The exact drivetrain manual instructs the
driver on printed page 73 of 112 to depress the clutch at idle, engage first,
and ease in the clutch. A first-person exact-car test independently says the
clutch is required in first gear in the pit lane. Neither source establishes
anti-stall or an automated launch.

ACC build 21257365 matches the clutch-required real car. AMS2 1.6.9.91 accepted
clutch-free move-off with assists disabled, making that exact implementation a
supported departure.

Sources: [Mercedes-AMG GT4 Drivetrain Manual R1.0][amg-gt4-manual] and
[Top Gear's exact-car first drive][amg-gt4-first-drive].

**BMW M6 GT3 - pulling away.** BMW's M4/M6 GT3 comparison identifies the M6's
hydraulic clutch on printed page 5, while an exact-car first-person drive says
the M6 still requires the clutch to get moving and describes easing it in. BMW
documents a fully automatic centrifugal clutch only for Alex Zanardi's special
adaptation; that exception does not redefine the baseline customer car.

ACC build 21257365 matches the clutch-required real car. AMS2 1.6.9.91 accepted
clutch-free move-off with assists disabled, making that exact implementation a
supported departure.

Sources: [BMW M4/M6 GT3 comparison][bmw-comparison],
[BMWBLOG's exact-car first drive][bmw-first-drive], and
[BMW's Zanardi adaptation notes][bmw-zanardi].

**Nissan GT-R NISMO GT3 (2018) - wheel geometry.** NISMO identifies the exact
2018-Spec cockpit as an entirely new design with a redesigned steering wheel.
Its official cockpit photograph shows molded side grips around a closed central
control face, which is `gt-formula` in the dataset vocabulary; the flattened
lower edge is not used by itself to classify the wheel.

ACC build 21257365 matches the real wheel category. AMS2 1.6.9.91 models a round
rim, making that exact implementation a supported departure.

Sources: [NISMO's exact 2018 specification][nismo-spec] and
[official 2018-Spec cockpit photograph][nismo-cockpit].

**Porsche 911 GT3 R (991.2, 2019) - wheel geometry.** Porsche's exact launch
material specifies a multifunction CFRP motorsport steering wheel, and its
official cockpit photograph shows molded side grips around a closed central
control face. That establishes `gt-formula`; Porsche lists the Cosworth display
separately, so display location is not being inferred from the wheel shape.

ACC build 21257365 matches the real wheel category. AMS2 1.6.9.91 models a
D-shaped rim, making that exact implementation a supported departure.

Sources: [Porsche's exact 991.2 launch material][porsche-9912] and
[official cockpit photograph][porsche-9912-cockpit].

## Open authentic baselines

**Lotus Renault 98T - forward gears.** The 1986 program used both five- and
six-speed Lotus/Hewland configurations. A period May 1986 report says gearbox
breakages left six-speed units for Senna's two cars while Dumfries used an
old-type five-speed; a retrospective exact-chassis account describes another
allocation. The generic record combines drivers, chassis and race
specifications, so it cannot assign a single authentic count.

AMS2's five gears and AC's six are both compatible with real 98T configurations.
Neither is a demonstrated departure without a narrower simulator identity. The
audit retains the conflict as `authentic-baseline-open`, which makes this a
useful benchmark boundary rather than an unresolved source hunt.

Sources: [period Motor Sport report][lotus-period],
[Classic Team Lotus-licensed 98T issue][lotus-licensed], and
[the surviving Senna 98T-3 account][lotus-98t-3].

The remaining open findings are negative research results, not unfinished bulk
claims:

- Audi's exact 2018 R8 LMS GT4 data does not describe open- versus closed-top
  wheel geometry, and its 2020 GT2-derived wheel cannot be inherited backward.
- Lister Storm GTM, Maserati MC12 GT1, Nissan R390 GT1 and Porsche 911 GT1-98
  sources establish sequential hardware but not driver blipping or ECU
  automatic-blip behavior. Maserati's exact technical data specifies a manual
  sequential six-speed and push-type carbon clutch without describing either
  blip behavior; Porsche Museum likewise identifies the GT1-98's sequential
  six-speed without a rev-match procedure.
- McLaren's exact 2019 720S GT3 product sheet and Evo material do not provide a
  launch procedure; NISMO's exact 2018 GT-R GT3 specification identifies a
  clutch but likewise gives no move-off instruction.
- BMW M6 GT3 media and Nissan R390 history do not identify wheel-mounted shift
  lights. BMW's brochure calls its wheel LEDs status LEDs and identifies them
  with control/status functions, which is not evidence of a rev-light array.
  Ginetta documents a driver display with RPM/shift lights separately from
  wheel controls, so display existence cannot be converted into wheel
  integration.

Each simulator observation remains intact as a scoped override. The open baseline
therefore preserves the cross-sim conflict while refusing to declare a winner.

## Remaining provisional findings

Only three findings still have a real-car answer but fall short of the benchmark's
primary-evidence threshold:

1. **Porsche 911 RSR 1974 - gate pattern.** Research confirms that the exact RSR
   used the RS-derived five-speed Type 915 and that a conventional H is the
   best-supported layout. The period workshop manual and FIA homologation form
   do not expose a readable exact-RSR selector diagram, however, so AMS2's
   conventional gate remains a provisional match and AC's dogleg a provisional
   departure. The January 1974 RSR operating manual is the best remaining lead.
2. **Milano 55 GT1 / Prodrive Ferrari 550 GTS - manual blip.** The exact-car Evo
   technical account says the clutch is used on every downshift and the driver
   blips to match revs. It is strong secondary evidence, but no manufacturer or
   homologation operating procedure has been recovered.
3. **Saleen S7-R - manual blip.** A first-person test of the 2001 Park Place S7R
   instructs clutch use on both shifts and recommends heel-and-toe on braking
   downshifts. This supports the early S7R family at medium confidence, but does
   not prove every 2005 Xtrac revision retained that procedure.

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
[amg-evo-manual]: https://www.scribd.com/document/972539658/Manual-B-ENG-Vehicle-Operations-R01
[amg-gt4-manual]: https://www.scribd.com/document/432746102/Mercedes-Amg-Gt4-drivetrain
[amg-gt4-first-drive]: https://www.topgear.com/car-reviews/mercedes-benz/first-drive-24
[bmw-comparison]: https://www.press.bmwgroup.com/canada/article/attachment/T0334391EN/481490
[bmw-first-drive]: https://www.bmwblog.com/2016/07/06/like-behind-wheel-bmw-m6-gtlm/
[bmw-zanardi]: https://www.press.bmwgroup.com/italy/article/attachment/T0290729IT/423215
[nismo-spec]: https://www.nismo.co.jp/en/products/customerracing/pdf/nissan_gtr_nismo_gt3_2018-spec_en.pdf
[nismo-cockpit]: https://www.nismo.co.jp/en/products/customerracing/img/racingcar/img_comfort_01.jpg
[porsche-9912]: https://newsroom.porsche.com/en/motorsports/porsche-911-gt3-r-customer-racer-gt3-series-2019-racing-911-gt3-rs-aerodynamics-safety-15335.html
[porsche-9912-cockpit]: https://newsroom.porsche.com/.imaging/mte/porsche-templating-theme/teaser_720x406x2/dam/pnr/porsche_newsroom/Motorsport/2018-Motorsport-Saison/911-GT3-R/Der-neue-911-GT3-R/b-M18_1436_fine.jpg/jcr%3Acontent/b-M18_1436_fine.jpg
[saleen-first-drive]: https://www.motortrend.com/reviews/saleen-s7r
[lotus-period]: https://www.motorsportmagazine.com/archive/article/may-1986/23/before-the-dust-had-settled/
[lotus-licensed]: https://d24udp600h4lxn.cloudfront.net/dea/live/media/27-lotus-senna-uk-web/27-lotus-senna-uk-web.pdf
[lotus-98t-3]: https://www.auto-motor-und-sport.de/formel-1/auktion-ayrton-senna-lotus-98t-rm-sothebys/
