# AMS2 import and SimHub identity audit

Audit date: 2026-08-10

## Live sheet import

The byte-preserving CSV export of Coanda's AMS2 sheet produced **208 car
candidates** after the importer excluded the machine-header row and 11
category-divider rows.

Coverage in the staged candidate file:

| Check | Result |
|---|---:|
| Candidate cars | 208 |
| Missing chassis-manufacturer context | 0 |
| Missing class | 0 |
| Missing gear count | 0 |
| Missing wheel-rim source code | 0 |
| Missing optional DOR | 0 |
| Duplicate display-name groups | 12 |
| Unresolved shift actuation | 4 |

The four unresolved shift-actuation rows are three karts with source value `-`
and the Kart 125cc Shifter with source value `Seq`. The latter establishes a
sequential gearbox but not stick versus paddle actuation, so the importer keeps
actuation unknown. It does not invent controls for the three `-` rows.

The generated review file is `build/ams2-candidates.json`. It is intentionally
ignored by Git because it is reproducible staging output, not curated data.

## What SimHub exposes

The locally installed SimHub 9.11.22 SDK confirms that an `IDataPlugin`
receives `GameReaderCommon.GameData` in `DataUpdate`. The relevant normalized
members are:

```text
data.GameName
data.NewData.CarModel
data.NewData.CarId
data.NewData.CarClass
```

Dash Studio/formula property paths are:

```text
DataCorePlugin.GameData.NewData.CarModel
DataCorePlugin.GameData.NewData.CarId
```

Inspection of the installed AMS2 reader showed:

- `GD_CarModel()` directly returns AMS2 shared-memory `mCarName`;
- the base `GD_CarId()` delegates to `GD_CarModel()`;
- therefore AMS2 `CarId` is not a separate stable internal ID in this reader.

SimHub's generated AMS2 car settings provided a second runtime-derived check.
There were **192 unique observed cars**, and all 192 had identical `CarId` and
`CarModel` values. Examples include `Dallara F301`, `McLaren F1 GTR`, and
`Sauber Mercedes C9`.

## Matching result

Only 51 of the 208 candidate rows had an exact observed SimHub name match (50
unique names because the sheet contains duplicate display names). This is
expected: the sheet often uses shorter names (`F301`) while telemetry includes
chassis-manufacturer or variant detail (`Dallara F301`). Low-downforce packages
also appear as distinct SimHub names.

The conservative alias pass produced **seven high-confidence suggestions**.
It does not use fuzzy or substring matching. F301 was already a seed record;
the other seven were explicitly reviewed in
`curation/ams2-approved-records.json` and promoted into dataset 0.2.0. The
Formula-rim batch in `curation/ams2-approved-formula-wheel-records.json` then
promoted one exact match and four explicitly reviewed observed identities into
dataset 0.3.0. The Formula-rim MetalMoro MRX P2 remains unresolved because the
observed SimHub inventory contains only the distinct P4/Duratec variant. The
remaining 146 unmatched candidate rows stay in the manual-review queue.

A subsequent live test against AMS2 1.6.9.91 showed that several Formula cars
emit tyre and aero qualifiers not present in the older stored identity files.
Dataset 0.3.1 adds only the four exact values captured in that test; their
approval is recorded in `curation/ams2-approved-live-formula-variants.json`.
Control behavior remains attributed to the versioned 1.5.5.2 source rather than
being presented as reverified by the identity-only test.

Reiza's official V1.6.9 announcement establishes that Formula Reiza and the
Formula Ultimate generations were retained under Formula V8 Gen3, Formula
Hybrid Gen2, and Formula Hybrid Gen3 names. Dataset 0.3.2 links Formula Reiza
to the live `Formula V8 Gen3 - High Downforce` / `F-Reiza_HD` identity and the
2022 Formula Ultimate G2 record to `Formula Ultimate Hybrid Gen3 - High
Downforce` / `F-Ultimate_Gen2_HD`. These are exact reviewed identities, not
fuzzy successors; the approval is checked in at
`curation/ams2-approved-current-formula-rebrands.json`.

The plugin's persistent unmatched JSONL can now be fed into
`review-unmatched-ams2`. The first live run consolidated the two diagnostic
observations for `Dodge Viper GTS-R` / `GT1_05`, preferred the corrected AMS2
`1.6.9.91`, SimHub `9.11.22`, and dataset `0.3.2` metadata, and returned
`no-candidate`. The Viper is absent from the versioned 1.5.5.2 source export, so
the tool correctly requires a new source rather than inferring controls or
silently mapping it to another GT1 record.

Dataset 0.3.3 resolves that review item through independent research and a
current-game test rather than retrofitting the old sheet. Reiza's official
release identifies the Dodge Viper GTS-R as a 2005 GT1 entry, while FIA form
GT2-005 documents the original six-speed manual Borg-Warner T56. A first-person
Carsport Holland account establishes that a privateer sequential conversion
also existed. The exact live `Dodge Viper GTS-R` / `GT1_05` identity was then
tested in AMS2 1.6.9.91: sequential-stick shifting worked without the clutch
once moving, the clutch was required from a stop, and automatic cut and blip
appeared active. The latter two remain medium-confidence perceptual observations.
The checked-in approval and record notes preserve the distinction between the
original homologation, privateer conversion evidence, and Reiza's simulated
behavior.

Dataset 0.3.4 adds the exact base `Alpine A424` / `LMDh` identity from the
post-sheet backlog. Primary Alpine and Xtrac material establishes the common
seven-speed pneumatic sequential LMDh transmission, while IMSA documents the
category's ability to move on electric power alone. A live AMS2 1.6.9.91 test
with Auto Clutch disabled confirmed clutch-free hybrid move-off, all seven
paddle-selected gears, no-lift clutch-free upshifts, clutch-free downshifts, a
visible automatic-blip throttle spike, and a closed prototype-style display
rim. Automatic cut remains medium-confidence because the full-throttle shifts
were accepted but no discrete power interruption was perceptible; the result
also relies on the common transmission and the three shift-cut-positive LMDh
peers in the older source. The exact `Alpine A424 - Low Downforce` identity is
approved as an aero-package alias inheriting the verified base controls; its
separate lack of a live control test is explicitly preserved in provenance.
The same dataset batch adds `Ligier JS P217`, whose shared model identity was
tested in both `LMP2` and `LMP2_Gen1` class contexts. Both directly confirmed
six paddle-selected gears, clutch-free move-off, automatic upshift cut,
automatic downshift blip, and a closed prototype-style display rim. The record
does not guess whether AMS2's clutch-free move-off is implemented as automatic
clutch, anti-stall, or another mechanism.

The completed 0.3.4 verification batch adds ten further exact records: Oreca
07, Lamborghini SC63, Ligier JS P320, Ligier JS P4, Aston Martin Valkyrie
Hypercar, Audi R8 LMS GT4, Chevrolet Corvette Z06 GT3.R, Lamborghini Huracan
Super Trofeo EVO2, Aston Martin Vantage GT4 Evo, and Aston Martin Vantage GTE.
All ten were exercised in AMS2 1.6.9.91 with Auto Clutch disabled, every
forward ratio selected, full-throttle upshifts checked for automatic cut, and
off-throttle downshifts checked for automatic blip. The Ligier JS P320 stalled
without clutch input from rest; the other nine moved without physical clutch
input, while their underlying move-off mechanism remains unknown except for
the directly observed hybrid launch of the SC63. Closed display rims use the
new `prototype` category; open-top no-display GT rims remain `gt-style`.

The exact Oreca 07, Lamborghini SC63, and Corvette Z06 GT3.R Low Downforce
identities are approved as aero-package aliases of their directly tested base
cars. Their records explicitly mark the variant controls as inherited and not
separately live-tested. No Low Downforce alias was added for the Valkyrie
because its exact telemetry name was not observed, and the older Huracan LP
620-2 Super Trofeo identity is not silently mapped to the EVO2.

Dataset 0.3.5 adds six historical GT records from a second back-to-back AMS2
1.6.9.91 pass. The Murcielago R-GT, Maserati MC12 GT1, Lister Storm GTM, Panoz
Esperante GTLM, and Gillet Vertigo Streiff each stalled without clutch input
from rest, exposed six sequential-stick gears with no cockpit paddles, accepted
clutch-free full-throttle upshifts with automatic cut, showed no automatic
downshift blip, and used D-shaped no-display rims. Historical sources establish
their sequential hardware with varying strength; manual-blip technique remains
`unknown` rather than being inferred from the absence of automation.

The Diablo SV-R test resolves its five-versus-six-speed source conflict for the
AMS2 representation: five direct bindings were accepted and the cockpit visibly
showed a five-speed dogleg H-pattern, agreeing with manufacturer-derived data.
It requires the clutch from rest, has no automatic cut or blip, requires lift
and rev matching for clutchless upshifts, and requires a manual blip/rev match
for clutchless downshifts. Historical running-shift clutch use remains unknown.
Exact Murcielago and MC12 Low Downforce identities inherit their tested base
controls as approved aero-only assumptions and were not separately live-tested.

The matching contract for AMS2 should therefore be:

1. Gate on the active game.
2. Read `CarModel` (or equivalent `CarId`).
3. Perform an exact match against curated `telemetry-name` identities.
4. Use explicit aliases for verified spelling/variant differences.
5. If unmatched, expose the raw value for contribution; never fuzzy-match
   silently.

`CarClass` may help a reviewer understand a collision, but it should not be the
primary key. Twelve sheet display-name groups are duplicated across years,
classes, engines, or generations, so those candidates need variant-specific
record IDs during promotion.

## Reproduce the audit

```shell
python -m as_driven_db import-ams2 ams2.csv --output build/ams2-candidates.json

python -m as_driven_db audit-simhub-ams2 --candidates build/ams2-candidates.json --cars-dir "C:\Program Files (x86)\SimHub\PluginsData\Automobilista2\Cars" --simhub-version 9.11.22 --output build/ams2-simhub-identity-audit.json --review-csv build/ams2-alias-review.csv

python -m as_driven_db review-unmatched-ams2 --log "%LOCALAPPDATA%\SimHub\AsDriven\Diagnostics\unmatched-identities.jsonl" --candidates build/ams2-candidates.json --data-dir data/v1 --output build/ams2-unmatched-review.json --review-csv build/ams2-unmatched-review.csv

python -m as_driven_db promote-ams2 --candidates build/ams2-candidates.json --audit build/ams2-simhub-identity-audit.json --approvals curation/ams2-approved-records.json --data-dir data/v1
```

The audit preserves unmatched rows for human review. Its suggestion rules are
restricted to formatting-only equality and exact chassis-manufacturer prefixes;
promotion requires a separate checked-in approval.
