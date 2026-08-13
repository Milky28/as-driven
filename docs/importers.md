# Importer and curation design

Importers are adapters from unstable external layouts into a stable review
format. They never write curated car files.

```text
source snapshot -> candidate JSON -> identity audit -> approval manifest -> curated record
```

The candidate keeps raw source values next to conservative normalization. This
makes source-layout changes visible and prevents a parser assumption from
silently becoming database truth.

## AMS2 Google Sheet

### Input

Use a CSV export of the car-data tab (`gid=2095352073`). The live sheet has a
human header row, a second machine-name row, class-divider rows, and duplicate
display headers elsewhere in the table. The importer addresses required fields
by the first matching display-header position rather than converting the whole
row to a dictionary, so duplicate unrelated headers do not corrupt parsing.

Imported columns (all except Steering DOR are required by this adapter):

| Source column | Candidate field |
|---|---|
| Car | identity display name and initial AMS2 alias |
| Chassis Manufacturer | candidate chassis-manufacturer context; not automatically the vehicle marque |
| Class, Year | identity context |
| # of Gears | transmission forward gears |
| Shift Type | source-facing value plus conservative actuation mapping |
| Auto Blip, Shift Cut | simulator behavior |
| Steering DOR | optional steering reference metadata |
| Wheel Rim Type | raw rim code plus conservative shape normalization |

The source author documents that blanks in indicator columns mean No. The
adapter applies that rule only to the imported Auto Blip and Shift Cut fields.
A documented `GTF1` prefix is normalized to `gt-style` (including compound
codes such as `GTF1FL2`), an `F1` prefix is normalized to `formula` (including
`F1M`), and an `R` prefix is normalized to `round`. Unrecognized rim codes
remain `unknown`.
A missing or blank DOR is omitted and an unknown shift label stays unknown. TC,
ABS, handbrake, and general car specifications are not imported because they do
not serve the project's pre-session hardware-and-technique purpose.

### Promotion checks

1. Diff row count and source-header fingerprints against the previous snapshot.
2. Resolve the simulator display name to telemetry/internal identifiers.
3. Verify the real car/season identity; do not assume a game name is exact.
4. Decode wheel-rim shorthand only from a documented legend.
5. Add a reproducible in-game check for the current AMS2 version where possible.
6. Review source reuse terms before any bulk publication.

The AMS2 promotion command enforces the machine-checkable part of this review:
the approved source row, sheet name, and telemetry name must appear together in
the identity audit's conservative alias suggestions. Approval manifests live in
`curation/` so identity decisions remain visible in code review. The promoter
refuses to overwrite an existing record and leaves unsupported clutch and
throttle technique as `unknown`.

### Unmatched diagnostics review

Plugin `0.9.1` writes unmatched live identities as JSON Lines under the current
user's Local AppData. Correlate that append-only log with staged candidates and
the current curated dataset using:

```powershell
python -m as_driven_db review-unmatched-ams2 `
  --log "$env:LOCALAPPDATA\SimHub\AuthenticControls\Diagnostics\unmatched-identities.jsonl" `
  --candidates .\build\ams2-candidates.json `
  --data-dir .\data\v1 `
  --output .\build\ams2-unmatched-review.json `
  --review-csv .\build\ams2-unmatched-review.csv
```

The command tolerates malformed lines, ignores non-AMS2 observations, removes
exact duplicate log entries, and consolidates repeated observations by exact
`CarModel` / `CarId` / class. The latest known game, SimHub, and dataset
versions are preferred over `unknown`, while the complete observed version
history remains in the output.

Review statuses are conservative:

- `already-curated`: the exact telemetry value is already in `data/v1`;
- `exact-candidate`: exactly one staged source name equals the logged model;
- `suggested-candidate`: one formatting-only or chassis-prefix rule matches;
- `ambiguous-candidate`: more than one source row remains possible;
- `no-candidate`: the source export has no conservative match.

This command never creates records, aliases telemetry, or promotes candidates.
Every status still requires source and identity review appropriate to the
material claim.

## iRacing transmission article

### Input

Save the official HTML article locally and pass it to the staging importer. The
adapter recognizes documented transmission-category headings and assigns the
category's technique to each list item. It extracts a parenthetical gear count
and preserves `[Legacy]` as content status.

The article provides category-level facts such as:

- shifter family (paddle/stick/H-pattern);
- upshift lift and clutch requirements;
- throttle-cut presence;
- downshift clutch and blip requirements;
- start/anti-stall notes.

The first adapter deliberately does not turn the article modification date into
`verified_game_version`: a web publication date is not a simulator build. During
promotion, match the display name to iRacing's stable car path or telemetry name
and record the actual build/season checked.

### Parser hardening

The official article's HTML is presentation-oriented and may change. Keep a
small legally safe structural fixture in `tests/fixtures`, add a snapshot test
for every newly observed category layout, and fail closed when an unknown
category appears. Never infer a car's category from its name.

## Candidate contract

Candidate JSON is intentionally noncanonical and may change within the 0.x
tooling line. Every candidate includes:

- importer and source IDs;
- import date and source-specific rules;
- raw source row/list value;
- conservative normalized fields;
- `review_required: true` at the document level.

Promotion requires a reviewer-supplied record ID, real-world manufacturer and
model labels, identity notes, exact telemetry name, checked source row, game
version context, and approval date. Candidate JSON remains staging data and is
never treated as a curated release by itself.
