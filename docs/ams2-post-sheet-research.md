# AMS2 post-sheet research backlog

The checked-in post-sheet backlog tracks Automobilista 2 car-content changes
after the community spreadsheet's AMS2 1.5.5.2 snapshot (17 January 2024).
It is research staging, not curated release data. Nothing in the backlog is
eligible for runtime matching until its identity and controls have been
reviewed and promoted through the normal approval workflow.

Review artifacts:

- `research/ams2-post-1.5.5.2-backlog.json` retains full release, comparison,
  source-evidence, uncertainty, and in-game-check detail;
- `research/ams2-post-1.5.5.2-backlog.csv` is the compact sortable work queue;
- `research/build_ams2_post_sheet_backlog.py` reproducibly merges the staged
  annual research files in `build/`.

## Inventory boundary

The inventory begins immediately after AMS2 1.5.5.2 and currently ends at
AMS2 1.6.9.91. Official Reiza release announcements and changelogs establish
whether an item was added, renamed, replaced, or introduced as a configuration
variant. A class announcement is not automatically treated as a selectable
car, and an aero or tyre configuration is not automatically treated as a
separate telemetry identity.

Three questions are kept separate for every event:

1. Was it absent from the 1.5.5.2 spreadsheet?
2. Is its current telemetry identity known exactly?
3. Is there enough evidence to curate its authentic controls?

A yes to one question does not imply a yes to the others.

## Current snapshot

The first pass contains **98 official release events**: 75 additions, 13
variants, six renames, three replacements, and one unresolved configuration.
Every event has been compared with the cutoff spreadsheet, the curated
database, and the locally observed SimHub identity inventory.

There are 81 model/configuration events with dedicated control research. Of
those, 79 have at least one verified source URL; the Super Trophy Truck and
fictional Milano GT36 remain explicit source gaps. The other 17 events are
class, rename, or configuration bookkeeping covered by a model member or
predecessor rather than duplicated as standalone control research. Across the
model research there are 110 source citations representing 87 unique URLs.
The base Alpine A424 identity has since completed live verification and was
promoted as `ams2.alpine-a424` in dataset 0.3.4; its Low Downforce identity
is approved as an exact aero-package alias inheriting the base controls, with
the lack of a separate live control test explicitly documented.
The Ligier JS P217 was also promoted in dataset 0.3.4 after direct tests of its
shared model identity and controls in both `LMP2` and `LMP2_Gen1` class
contexts. A subsequent ten-car live batch brought the curated total to 28
records: Oreca 07, Lamborghini SC63, Ligier JS P320, Ligier JS P4, Aston
Martin Valkyrie Hypercar, Audi R8 LMS GT4, Chevrolet Corvette Z06 GT3.R,
Lamborghini Huracan Super Trofeo EVO2, Aston Martin Vantage GT4 Evo, and Aston
Martin Vantage GTE. Each was tested in AMS2 1.6.9.91 with Auto Clutch disabled.
Dataset 0.3.5 adds a six-car historical GT batch: Lamborghini Murcielago R-GT,
Maserati MC12 GT1, Lister Storm GTM, Panoz Esperante GTLM, Gillet Vertigo
Streiff, and Lamborghini Diablo SV-R. The first five directly share a
six-speed sequential-stick, standing-start-clutch, automatic-cut, no-auto-blip,
D-shaped-rim profile. The Diablo instead directly confirms a five-speed dogleg
H-pattern, required lift and manual rev matching, no automatic cut or blip, and
a round rim. Dataset 0.3.7 adds Aston Martin DBR9, Chevrolet Corvette C5-R,
Saleen S7-R GT1, and Milano GT55 after exact telemetry capture and back-to-back
live testing, bringing the curated dataset to 38 records. Their shared modeled
profile is a six-speed sequential stick, standing-start clutch, automatic cut,
no automatic blip, required manual rev matching, and a round no-display rim.
Dataset 0.3.8 adds the four-car GT2 2005 batch: Milano GT36, Porsche 996 GT3
RSR, Spyker C8 Spyder GT2-R, and TVR Tuscan T400R GT2. All four directly use a
six-speed sequential stick, standing-start clutch, automatic cut, and round
no-display rim; only the Porsche provides an observed automatic blip. The
curated dataset now contains 42 records.
Dataset 0.3.9 adds the Audi R8 LMP1, Courage C60 Hybrid, and Dallara SP1 after
exact `LMP1_05` telemetry capture. All three require the clutch from rest and
provide automatic cut and blip. The Audi uses paddles and a yoke-style rim,
the Courage uses a sequential stick and D-shaped small-display rim, and the
Dallara uses the replay-animated paddles and prototype display rim. The
curated dataset now contains 45 records.
Dataset 0.3.10 adds the Lola B05/40 V8 and Turbo after exact `LMP2_05`
telemetry capture. Both moved without physical clutch input, used six paddle
gears with automatic cut and blip, and showed D-shaped display rims. The V8
Low Downforce identity inherits its verified base controls as an explicit
untested aero assumption. The curated dataset now contains 47 records.
The backlog now marks 21 release events as promoted, including aero variants
that share a record, leaving 60 researched model/configuration events awaiting
review or live validation.

## Suggested verification order

Start with cars that already have an exact observed SimHub identity and strong
hardware evidence. This yields useful records with the least identity risk:

1. Alpine A110 GT4 Evo, Aston Martin Vantage GT3 Evo, Formula Vee Gen2, Spyker
   C8 Spyder GT2-R, and Chevrolet Corvette C3.R Convertible.

Keep generic Formula models, Stock USA generations, Super Trophy Truck, and
Milano models in a later identity-first wave. Their release labels do not yet
support a safe real-world mapping, so testing them before that mapping is
resolved should capture simulator behavior without claiming historical
authenticity.

## Source priority

Control research uses this order of preference:

1. FIA or series homologation and technical regulations;
2. manufacturer, constructor, gearbox supplier, or official team technical
   documentation;
3. period manuals, press kits, and clearly attributable cockpit photographs;
4. reputable contemporary engineering or motorsport reporting;
5. current in-game observation for simulator-specific behavior.

Sources are annotated with both what they establish and what they do not.
Gearbox hardware does not by itself establish clutch technique, ignition-cut
logic, automatic blipping, or how AMS2 models those systems. A related real
car may be recorded as an analogue, but not silently substituted for a generic
or fictional Reiza model.

## Required in-game pass

Before promotion, load the exact selectable car/configuration in the target
AMS2 build and capture:

- SimHub `CarModel`, `CarId`, and `CarClass`;
- the selected aero, tyre, or class variant when relevant;
- shifter input accepted by the game;
- clutch behavior from rest, on upshift, and on downshift;
- throttle trace or another falsifiable check for automatic cut and blip;
- a cockpit view sufficient to classify the wheel-rim category.

Record the exact AMS2 version, SimHub version, and check date. Preserve
`unknown` whenever the evidence does not establish a value. Exact telemetry
names require explicit review; normalization and reviewer suggestions in the
backlog must never become silent fuzzy matching.

## Promotion

Research records remain outside `data/v1`. Promotion requires a checked-in
approval, source entries in `data/v1/sources.json`, a car record with
claim-level provenance, and the normal validation/test suite. Renames and
replacements should reuse an existing real-world control profile only when the
official relationship and the simulated configuration both support doing so.
