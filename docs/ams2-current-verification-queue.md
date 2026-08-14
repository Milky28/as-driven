# AMS2 current verification queue

## Completed in dataset 0.3.29 (club and road batch 07)

Ten cars, which finish every category except open-wheel.

Eight are ordinary synchromesh H-pattern cars with no automation of any kind:
Caterham Academy and Supersport, Chevrolet Chevette, Copa Fusca, Ginetta G40 Cup,
Gol Classic B and FL, Puma GTB and Puma P052. Each needs the clutch to pull away
and a throttle lift to upshift, and each takes an optional downshift blip.

The two GT5 cars were found under a class of their own, and one of them is the
batch's real finding. **Ginetta G40 is not the G40 Cup.** The Cup car is a
five-speed synchromesh H-pattern; the GT5 Challenge car is a six-speed Quaife
sequential, and the drive found automatic blip without automatic cut, a pairing
no other curated sequential-stick car has. Its downshift blip stays `unknown`:
AMS2 blips for the driver, but nothing establishes that the real Quaife box does,
and a dog-engagement sequential would normally need one. Sharing a nameplate was
never grounds to share controls, and here it would have been badly wrong.

This batch also settled what `manual_blip` asserts. It now means mechanical
necessity, so `required` is reserved for gearboxes that cannot engage without a
blip and synchromesh cars are `optional`. Audi V8 quattro DTM, Dodge Viper ACR
and Lamborghini Miura SV were corrected to match; they had been recorded under
two contradictory readings of the same field. The Miura's basis was rewritten
too, because it asserted synchromesh from evidence that mentioned only a
five-speed H-pattern manual, and the blip now depends on that construction.

Both Caterhams are `medium` confidence for the same reason: Caterham's own
motorsport partner offers the Type 9 five-speed in synchronised and
dog-engagement forms, so their construction is inferred from the cars being road
legal rather than stated by a source, and each record says so.

The Caterham Academy drove as a five-speed against a SimHub hint of four.

## Completed in dataset 0.3.28 (touring and stock batch 06)

Six cars, and the first records whose gate pattern comes from a guided drive
rather than a reviewer reading a specification.

BMW M1 Procar, Mercedes-Benz 190E 2.5-16 Evolution II and BMW M3 Sport Evolution
were all observed with a dogleg gate in the cockpit, and all three are
independently corroborated: a ZF five-speed with first out of the shift plane for
the M1, a dog-leg Getrag for the 190E, and a Getrag 265 for the M3. Each needs
the clutch to pull away, a throttle lift to upshift and a manual blip to
downshift.

Chevrolet Omega Stock Car 1999 shares that manual technique but was observed on a
standard gate. Its identity and straight-six engine are sourced; no reviewed
source documents its gearbox, so its transmission rests on the drive alone and
the record is medium confidence.

Super V8 is Reiza's fictionalised Australian Supercars car. The championship
confirmed that Gen3 retains a manual stick shift on the Albins six-speed
sequential transaxle, which is why it is shifted by a lever where a modern GT
uses paddles.

Toyota Corolla Stock Car 2022 is the modern outlier: paddles, six gears and full
automation, reviewed independently of the curated 2024 Corolla.

Zakspeed Ford Capri Group 5 and BMW 320 Turbo Gr5 were dropped from the batch as
third-party content that is not installed.

## Completed in dataset 0.3.27 (historic GT and GTE batch 05)

Five cars that complete the GT family, splitting three ways.

Nissan R390 GT1 and Porsche 911 GT1-98 are late-1990s Le Mans cars: sequential
lever, six gears, clutch to pull away, automatic cut but no automatic blip, so
the driver supplies the downshift blip. Both carry their `- Low Downforce` alias
as an explicit inherited identity.

Chevrolet Corvette C8.R and Porsche 911 RSR are modern GTE cars and behave like
the GT3 group: clutch-free move-off, six paddle gears, automatic cut and blip.

Puma GTE is not a GTE racer at all. It is a Brazilian road car built from 1970
to 1980 on Volkswagen running gear, classed by AMS2 under Copa Classic B, and it
has no automation whatever: four H-pattern gears, clutch to pull away, a throttle
lift to upshift and a manual blip to downshift. Its 150-gear telemetry hint was
the worst seen in the inventory; the real count is four.

The GT family is now fully verified.

## Completed in dataset 0.3.26 (GT4 batch 04)

Six GT4 cars, and unlike the GT3 batch they are not uniform.

Three are dual-clutch cars whose gearbox comes from the road car rather than a
racing sequential, which is why they carry seven gears where most GT4 cars have
six: BMW M4 GT4 (F82, a seven-gear dual clutch with motorsport software),
McLaren 570S GT4 (Oerlikon Graziano seven-speed dual clutch SSG), and Porsche
718 Cayman GT4 Clubsport MR (six-speed PDK).

Mercedes-AMG GT4 uses a purpose-built pneumatic sequential six-speed transaxle.
Ginetta G55 GT4 and G55 GT4 Supercup use the Hewland six-speed of the G55
platform and require the clutch to pull away; the Supercup is classed separately
by AMS2 and is reviewed independently rather than inherited from the GT4 car.

The Cayman carries the first `simulators[].overrides` entry in the dataset. Its
real gearbox is a PDK with no clutch pedal, so the record states that the
standing-start clutch is not required, while an explicit sourced override
records that AMS2 1.6.9.91 requires clutch input to move off. The client applies
overrides when building guidance, so the driver is told to use the clutch
in-sim while the real-car value stays true.

## Completed in dataset 0.3.25 (aero inheritance, no driving)

`BMW M4 GT3 - Low Downforce` and `Porsche 992 GT3 R - Low Downforce` became
explicit aliases of the base records verified in batch 03, each disclosed as an
untested aero configuration. No control value changed and no record was added.
Three Low Downforce identities still wait on unverified base cars.

## Completed in dataset 0.3.24 (contemporary GT batch 03)

Eight GT cars, promoted through `import-observation` and `promote-observation`.

Seven are paddle-shift GT3 cars with identical controls: clutch-free move-off,
six paddle gears, automatic cut and blip. BMW M4 GT3 and M6 GT3, Mercedes-AMG
GT3 and GT3 Evo, Nissan GT-R NISMO GT3, and Porsche 911 GT3 R (991.2) and 911
GT3 R (992). Each carries a manufacturer source for its six-speed sequential
transmission; BMW state that the M4 GT3 has no clutch pedal at all, which
corroborates the clutch-free move-off rather than merely matching it.

Ginetta G55 GT3 is the outlier and was verified independently: AMS2 classes it
as GT Open, it is shifted by a sequential lever, and it requires the clutch to
pull away. The drive detected automatic cut and blip despite the lever, a
pairing with no precedent among curated cars, so its throttle lift and manual
blip stay `unknown` rather than being inferred.

Verifying the BMW M4 GT3 and Porsche 992 GT3 R makes their `- Low Downforce`
identities inheritance-ready.

## Completed in dataset 0.3.23 (aero inheritance, no driving)

`Nissan R89C - Low Downforce` and `Porsche 962C - Low Downforce` became explicit
aliases of the base records verified in batch 02, each disclosed as an untested
aero configuration. No control value changed and no record was added. Five Low
Downforce identities still wait on unverified base cars.

## Completed in dataset 0.3.22 (modern-prototype batch 02)

Promoted through `import-observation` and `promote-observation`, the first batch
to use that command end to end rather than an ad-hoc script:

1. Nissan R89C (Group C, 1989) - clutch to pull away, five H-pattern gears,
   throttle lift to upshift, manual blip to downshift, no automatic cut or blip.
   Nissan's heritage record supplies the VGC five-speed and Lola-built chassis.
2. Porsche 962C (Group C, 1987) - same manual technique. Gearbox construction
   and H-pattern layout stay unknown: the reviewed sources establish only a
   five-speed manual.
3. MetalMoro MRX Duratec P4 - sequential stick, six gears, clutch to pull away,
   automatic cut, no automatic blip, so the driver supplies the downshift blip.
   Metalmoro fixes no transmission for the MRX, so the sequential six-speed is
   medium confidence as the configuration modeled in AMS2.

Mazda 787b was dropped from the batch: it is modded content, and Reiza holds no
Mazda licence, so AMS2 ships no official Mazda.

Verifying these bases moves `Nissan R89C - Low Downforce` and
`Porsche 962C - Low Downforce` to inheritance-ready.

Dataset 0.3.18 completes the earlier audited queue. It deliberately counted
selectable model/configuration identities, not release-note classes, renames, or
generic aero announcements.

## Completed in dataset 0.3.21 (identity review, no driving)

Explicit aliases added to already curated records:

1. Formula Edge Model1, Model2, and Model3, and Formula V8 Gen1 (B). Each plain
   name is the same car observed before its aero suffix existed, inherited from
   the verified `- High Downforce` configuration and disclosed as not separately
   tested.
2. `Stock USA Gen1 - Speedway ` with trailing whitespace. Runtime matching is
   exact and untrimmed, so without this alias that stored identity would be
   reported unmatched to the driver.

Closed as reviewed decisions in `research/ams2-identity-decisions.json`:

- Three retired pre-rename identities of official cars: Formula V10 Gen2,
  Formula Vee Fin, and Formula V12. AMS2 v1.6.9.5 rebranded the single-make
  Formula V12 class as Formula Edge and identifies the former V12 car as
  Model 1. Formula V10 Gen2 is the only one without a single successor, because
  it predates the tyre and aero split into two curated records.
- None of the three is aliased onto its renamed record, because none is
  selectable in AMS2 1.6.9.91. Formula V12 additionally must not inherit, since
  its rebrand accompanied the rule changes that caused the largest downforce
  drop since 1983, so the retired identity is not the same car to drive.
- Three third-party identities from the ThunderFlash mods pack: FIA-GT1
  Lamborghini Murcielago R-SV GT1, FIA-GT1 Maserati MC12 GT1, and
  LamborghiniHuracanLP6202SuperTrofeo, the last a mod ported from Project CARS
  2. AMS2 never shipped a Murcielago R-SV, and the official Murcielago R-GT,
  Maserati MC12 GT1, and Huracan Super Trofeo EVO2 are separate cars curated
  under their own identities. None of the modded identities is aliased onto
  them, and the Huracan one leaves the guided-verification queue, which drops
  from 90 to 89.
- BMW M3 Safety Car is out of product scope as a non-racing vehicle and stays
  unmatched in the client rather than receiving guessed controls.

## Completed in dataset 0.3.20 (aero-inheritance review, no driving)

Seven exact `- Low Downforce` identities whose base record was already verified
became explicit aliases with an untested-aero disclosure: Audi R8 LMP1, Courage
C60 Hybrid, Dallara SP1, Dodge Viper GTS-R, McLaren 720S GT3 Evo, McLaren F1
GTR, and Sauber Mercedes C9. No control value changed and no record was added.

The `aero-inheritance-ready` queue is now empty. Seven Low Downforce identities
remain blocked behind an unverified base car.

## Completed in dataset 0.3.19 (modern-prototype batch 01)

Guided-verification drives promoted through the `import-observation` staging
tool, then reviewed with registered real-world sources:

1. BMW M Hybrid V8 (LMDh) — clutch-free move-off, seven paddle gears, automatic
   cut and blip; prototype display rim.
2. Porsche 963 (LMDh) — as above; the live drive confirmed seven forward gears.
3. Chevrolet Corvette GTP (1988 IMSA GTP) — H-pattern, five gears, standing-start
   clutch required, throttle lift to upshift, manual blip to downshift, no
   automatic cut or blip (Hewland VGC racing gearbox).
4. MetalMoro AJR Chevrolet (P1) — clutch-free move-off, six paddle gears,
   automatic cut and blip.
5. MetalMoro AJR Gen2 Chevrolet (P1Gen2) — reviewed independently from the base
   AJR; six paddle gears, automatic cut and blip.

The BMW, Porsche, and Corvette base records each carry their exact `- Low
Downforce` alias as an explicit inherited identity with an untested-aero note.

The next prototype batch is Mazda 787B, Nissan R89C, Porsche 962C, and MetalMoro
MRX Duratec P4 (see `docs/ams2-coverage-plan.md`).

## Completed in dataset 0.3.18

1. Stock USA Gen3 LM.
2. F-Edge Model1.
3. F-Edge Model2.
4. F-Edge Model3.
5. Formula V10 Gen3 (B).
6. Formula V10 Gen3 (M).
7. Formula V8 Gen1 (B).
8. Formula V8 Gen1 (M).
9. Formula V8 Gen2 M1, observed under the exact telemetry label
   `Formula V8 Gen2 - High Downforce`.

## Not separate car tests

- Stock Car Pro Series 2024 is represented by its tested Cruze and Corolla
  members.
- Formula Hybrid Gen1/Gen3, Formula V8 Gen3, and Formula V10 Gen2 current names
  are linked to their verified records.
- Formula V10 Gen3, Formula V8 Gen1, Formula V8 Gen2, Formula Edge, 2004 GTR,
  2005 GT1/GT2/LMP1/LMP2, Ligier European Series, and GT2 2005 are class-level
  release events; their selectable members are the test units.
- Generic High Downforce and Low Downforce announcements do not require a full
  duplicate test when the base controls are verified. Each inherited identity
  must still be explicit and carry an untested-configuration note.
- Cadillac V-Series.R was verified earlier in the live prototype batch: hybrid
  clutch-free move-off, seven paddle gears, automatic cut and blip, and a closed
  prototype display rim. Its Low Downforce identity inherits those controls with
  an explicit untested-aero note.
- The unnamed second Aston Martin Vantage GT3 Evo configuration remains an
  identity-research note until an exact selectable/telemetry name is observed.
