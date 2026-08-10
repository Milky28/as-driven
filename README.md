# Authentic Controls Database

A simulator-independent, versioned JSON database describing how a real car is
controlled and how individual simulators implement or override that behavior.
The first consumer is planned to be a SimHub popup, but SimHub is deliberately
not part of the data format.

The project separates three questions:

1. **What controls did the real car have?** (`authentic_controls`)
2. **How does a simulator represent them?** (`simulators[].behavior`)
3. **What evidence supports each claim?** (`provenance.claims` and
   `data/v1/sources.json`)

An explicit `unknown` is different from `no`. A blank source cell is converted
to `no` only when that source documents that convention.

## Project scope

The database answers a narrow pre-session question: **which physical controls
should I use, and how should I operate them authentically?** Core data covers:

- wheel-rim category;
- shifter actuation, gear count, and unusual patterns such as dogleg;
- clutch use for starting, upshifts, and downshifts;
- throttle lift, automatic shift cut, and manual/automatic blipping.

Steering DOR is optional reference metadata because most simulators and modern
wheelbases apply it automatically. General specifications, driver aids and
electronics, and handbrake construction are intentionally outside the MVP.
Importers select only relevant source columns rather than mirroring a general
car spreadsheet.

## Repository layout

```text
schema/v1/                   JSON Schemas for records, sources, and the index
data/v1/index.json           Dataset release manifest
data/v1/sources.json         Reusable provenance/source records
data/v1/cars/*.json          One curated car record per file
curation/                    Explicit, reviewable promotion approvals
authentic_controls_db/       Dependency-free validator and staging importers
tests/                       Unit tests and small source-layout fixtures
docs/data-model.md           Field semantics and confidence policy
docs/importers.md            AMS2 and iRacing import/review design
docs/ams2-import-audit.md    Live import coverage and SimHub identity findings
docs/simhub-roadmap.md       Planned read-only SimHub client
simhub/                      .NET lookup library, plugin adapter, and diagnostics
```

## Quick start

Python 3.11 or newer is the only requirement.

```shell
python -m authentic_controls_db validate
python -m unittest discover -s tests -v
```

The optional SimHub adapter has its own build and test command on Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

See [simhub/README.md](simhub/README.md) for its properties, diagnostic command,
packaging layout, and installation boundary.

Stage a local export of the AMS2 sheet for review:

```shell
python -m authentic_controls_db import-ams2 ams2.csv --output build/ams2-candidates.json
```

Stage a saved copy of the official iRacing transmission article:

```shell
python -m authentic_controls_db import-iracing iracing.html --output build/iracing-candidates.json
```

Compare AMS2 candidates with car identities already observed by SimHub:

```shell
python -m authentic_controls_db audit-simhub-ams2 --candidates build/ams2-candidates.json --cars-dir "C:\Program Files (x86)\SimHub\PluginsData\Automobilista2\Cars" --output build/ams2-simhub-identity-audit.json --review-csv build/ams2-alias-review.csv
```

Promote only the aliases recorded in the reviewed approval manifest:

```shell
python -m authentic_controls_db promote-ams2 --candidates build/ams2-candidates.json --audit build/ams2-simhub-identity-audit.json --approvals curation/ams2-approved-records.json --data-dir data/v1
```

Importers and audits do not modify `data/`. They produce candidates containing
normalized values alongside raw source values. The promotion command requires
an explicit approval manifest and accepts only aliases present in the audit's
conservative suggestion set. A person must still resolve identity, review
source metadata and reuse rights, and approve each promoted record.

## Data versioning

- `schema_version` follows semantic versioning and describes structure.
- `dataset_version` follows semantic versioning and describes a curated data
  release.
- `verified_game_version` belongs to every simulator entry. It says when that
  implementation was last checked; it does not claim newer game versions are
  equivalent.
- Breaking schema changes create a new directory such as `schema/v2` and
  `data/v2`. Existing releases remain readable.

## Contributing a correction or car

1. Create or edit one file in `data/v1/cars/`.
2. Add each new source once to `data/v1/sources.json`.
3. Cite every material claim with JSON Pointer paths in `provenance.claims`.
4. Record a confidence level and a short, falsifiable basis.
5. For simulator behavior, include the exact `verified_game_version` and check
   date. Do not write `latest`.
6. Run the validator and tests.

Primary sources (manufacturer manuals, homologation documents, simulator
documentation) are preferred. High-quality community research is welcome when
identified as such. Search snippets, unattributed reposts, and AI-generated
claims are not acceptable sources. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the full review policy.

## Initial data status

Dataset 0.2.0 contains ten curated AMS2 records: three seed records and seven
records promoted through the reviewed identity workflow. They demonstrate the
model; they are not a claim of broad coverage. Simulator fields reproduce
selected values from Coanda's Extended Car Info sheet as published for AMS2
1.5.5.2. Raw wheel-rim codes are retained, unsupported driving technique stays
`unknown`, and only conservative identity normalization is applied.

## Licensing

Software is MIT licensed. The original database selection and arrangement is
CC BY 4.0; third-party sources retain their own rights. See
[DATA_LICENSE.md](DATA_LICENSE.md).
