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
docs/evidence-boundaries.md  Real, simulated, and effective guidance layers
docs/verification-observations.md  Guided in-game verification contract
docs/importers.md            AMS2 and iRacing import/review design
docs/ams2-import-audit.md    Live import coverage and SimHub identity findings
docs/ams2-post-sheet-research.md  Post-1.5.5.2 car/source backlog and test order
docs/simhub-roadmap.md       Planned read-only SimHub client
simhub/                      .NET lookup library, plugin adapter, and diagnostics
release/                     Independent database-release packaging
```

## Quick start

Python 3.11 or newer is the only requirement.

```shell
python -m authentic_controls_db validate
python -m unittest discover -s tests -v
```

Audit private-beta records that still need their real-world and simulator
evidence separated:

```shell
python -m authentic_controls_db audit-boundaries --output build/evidence-boundaries.json
```

Validate a draft exported by SimHub's guided verification form:

```shell
python -m authentic_controls_db validate-observation observation.json
```

Dataset 0.3.13 contains 55 reviewed records. Its eight newest records were
promoted from versioned guided AMS2 observations while retaining official or
manufacturer evidence separately from simulator behavior.

The optional SimHub adapter has its own build and test command on Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

Build a standalone database package without SimHub binaries:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-database.ps1
```

Database and plugin versions advance independently. A plugin package may carry
a known-good data snapshot for first installation, while database-only releases
can update compatible data without changing the client.

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

Dataset 0.3.13 contains 55 curated AMS2 records promoted through the reviewed
identity workflow. They demonstrate the model and expand current-game coverage;
they are not a claim of complete coverage. Older records retain selected values
from Coanda's Extended Car Info sheet as published for AMS2 1.5.5.2, while
post-sheet cars use independent primary-source research and exact AMS2
1.6.9.91 tests. Raw wheel-rim codes are retained, unsupported driving
technique stays `unknown`, and only explicitly reviewed exact identities are
matched.
The 0.3.6 review resolves the five verified historical sequential-stick cars
with no automatic blip to `manual_blip = required`, making the driver-supplied
rev-matching technique explicit.
The 0.3.7 review adds Aston Martin DBR9, Chevrolet Corvette C5-R, Saleen S7-R
GT1, and Milano GT55 from exact AMS2 1.6.9.91 identities and live control
tests. Each uses a six-speed sequential stick, standing-start clutch,
automatic upshift cut, manual downshift blipping, and a round no-display rim.
The 0.3.8 review adds Milano GT36, Porsche 996 GT3 RSR, Spyker C8 Spyder
GT2-R, and TVR Tuscan T400R GT2. The Porsche directly verified automatic
downshift blipping; the other three require driver blipping.
The 0.3.9 review adds Audi R8 LMP1, Courage C60 Hybrid, and Dallara SP1. The
Dallara's paddle classification is supported by visible paddles and replay
animation while retaining its visible cockpit lever as an explicit caveat.
The 0.3.10 review adds the Lola B05/40 V8 and Turbo. Both directly verified
clutch-free move-off, six paddle gears, automatic cut and blip, and D-shaped
display rims; the move-off mechanism remains unknown.
Dataset 0.3.11 adds orthogonal simulator wheel observations for display,
shift-light, and open-top construction without changing the five cars' shape
categories. It also introduces schema-enforced approvals, automatic backlog
reconciliation, and the staged guided-verification contract. The SimHub client
version remains independent.
Dataset 0.3.12 promotes four separately reviewed guided-verification drafts:
Alpine A110 GT4 Evo, Aston Martin Vantage GT3 Evo, Formula Vee Gen2, and
Chevrolet Corvette C3.R Convertible.
Dataset 0.3.13 promotes Audi R8 LMS GT3 Evo II, Lamborghini Huracan GT3 EVO2,
Chevrolet Cruze Stock Car 2024, and Toyota Corolla Stock Car 2024. Guided
telemetry directly established most controls; each automatic-cut claim is
separately disclosed at medium confidence because the tester manually observed
a brief throttle-graph interruption that the detector did not classify.

## Licensing

Software is MIT licensed. The original database selection and arrangement is
CC BY 4.0; third-party sources retain their own rights. See
[DATA_LICENSE.md](DATA_LICENSE.md).
