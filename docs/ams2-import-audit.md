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
There were **191 unique observed cars**, and all 191 had identical `CarId` and
`CarModel` values. Examples include `Dallara F301`, `McLaren F1 GTR`, and
`Sauber Mercedes C9`.

## Matching result

Only 50 of the 208 candidate rows had an exact observed SimHub name match (49
unique names because the sheet contains duplicate display names). This is
expected: the sheet often uses shorter names (`F301`) while telemetry includes
chassis-manufacturer or variant detail (`Dallara F301`). Low-downforce packages
also appear as distinct SimHub names.

The conservative alias pass produced **eight high-confidence suggestions**:
three exact chassis-manufacturer prefixes and five formatting-only differences.
It does not use fuzzy or substring matching. F301 was already a seed record;
the other seven were explicitly reviewed in
`curation/ams2-approved-records.json` and promoted into dataset 0.2.0. The
remaining 150 unmatched candidate rows stay in the manual-review queue.

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
python -m authentic_controls_db import-ams2 ams2.csv --output build/ams2-candidates.json

python -m authentic_controls_db audit-simhub-ams2 --candidates build/ams2-candidates.json --cars-dir "C:\Program Files (x86)\SimHub\PluginsData\Automobilista2\Cars" --simhub-version 9.11.22 --output build/ams2-simhub-identity-audit.json --review-csv build/ams2-alias-review.csv

python -m authentic_controls_db promote-ams2 --candidates build/ams2-candidates.json --audit build/ams2-simhub-identity-audit.json --approvals curation/ams2-approved-records.json --data-dir data/v1
```

The audit preserves unmatched rows for human review. Its suggestion rules are
restricted to formatting-only equality and exact chassis-manufacturer prefixes;
promotion requires a separate checked-in approval.
