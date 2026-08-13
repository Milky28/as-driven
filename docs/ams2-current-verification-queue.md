# AMS2 current verification queue

Dataset 0.3.18 completes the earlier audited queue. It deliberately counted
selectable model/configuration identities, not release-note classes, renames, or
generic aero announcements.

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
