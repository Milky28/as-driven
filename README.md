# As Driven Database

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

The format is simulator-independent, but a released dataset only covers the
simulators it carries records for. That list is derived from the records
themselves rather than declared, so the SimHub client can show it on its
settings page and report an uncovered game plainly instead of reporting every
car in it as unmatched. Automobilista 2 is the only covered simulator today.

## Repository layout

```text
schema/v1/                   JSON Schemas for records, sources, and the index
data/v1/index.json           Dataset release manifest
data/v1/sources.json         Reusable provenance/source records
data/v1/archetypes.json      Named control mechanisms records classify against
data/v1/cars/*.json          One curated car record per file
curation/                    Explicit, reviewable promotion approvals
as_driven_db/                Dependency-free validator and staging importers
as_driven_db/site.py         Renders the database as one browsable page
tests/                       Unit tests and small source-layout fixtures
docs/data-model.md           Field semantics and confidence policy
docs/evidence-boundaries.md  Real, simulated, and effective guidance layers
docs/verification-observations.md  Guided in-game verification contract
docs/importers.md            AMS2 and iRacing import/review design
docs/ams2-import-audit.md    Live import coverage and SimHub identity findings
docs/ams2-post-sheet-research.md  Post-1.5.5.2 car/source backlog and test order
docs/simhub-roadmap.md       Planned read-only SimHub client
docs/releasing.md            Early-access build, QA, and publishing process
simhub/                      .NET lookup library, plugin adapter, and diagnostics
release/                     Independent database-release packaging
```

## Quick start

Python 3.11 or newer is the only requirement.

```shell
python -m as_driven_db validate
python -m unittest discover -s tests -v
```

Audit private-beta records that still need their real-world and simulator
evidence separated:

```shell
python -m as_driven_db audit-boundaries --output build/evidence-boundaries.json
```

Validate a draft exported by SimHub's guided verification form:

```shell
python -m as_driven_db validate-observation observation.json
```

Stage a curated-record candidate from that draft, then promote the reviewed
bundle once its real-world identity and sources are resolved:

```shell
python -m as_driven_db import-observation observation.json --output build/staged.json
```

```shell
python -m as_driven_db promote-observation curation/review-batch.json
```

Read the whole database in a browser, with no install and no JSON. One
self-contained page, filterable by shifter, clutch and blip, written to the
ignored `dist/` directory:

```shell
python -m as_driven_db build-site
```

Dataset 0.3.81 contains 242 reviewed records. Its newest records complete the
audited post-sheet queue and the first modern-prototype verification batch,
while retaining official or manufacturer evidence separately from simulator
behavior. Broader AMS2 roster coverage remains a versioned, explicitly
classified backlog rather than guessed matches.

The optional SimHub adapter has its own build and test command on Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

Build a standalone database package without SimHub binaries:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-database.ps1
```

Install that database snapshot into an existing SimHub installation without
replacing the As Driven plugin, dashboards, overlays, or settings:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\install-database.ps1
```

Database and plugin versions advance independently. A plugin package may carry
a known-good data snapshot for first installation, while database-only releases
can update compatible data without changing the client.

Build the complete early-access release candidates on the supported Windows
release machine:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-early-access.ps1
```

See [EARLY_ACCESS.md](EARLY_ACCESS.md) for supported versions, installation,
known limitations, and rollback. The plugin is offline and stores optional
diagnostics and verification drafts locally as described in
[PRIVACY.md](PRIVACY.md).

See [simhub/README.md](simhub/README.md) for its properties, diagnostic command,
packaging layout, and installation boundary.

Stage a local export of the AMS2 sheet for review:

```shell
python -m as_driven_db import-ams2 ams2.csv --output build/ams2-candidates.json
```

Stage a saved copy of the official iRacing transmission article:

```shell
python -m as_driven_db import-iracing iracing.html --output build/iracing-candidates.json
```

Compare AMS2 candidates with car identities already observed by SimHub:

```shell
python -m as_driven_db audit-simhub-ams2 --candidates build/ams2-candidates.json --cars-dir "C:\Program Files (x86)\SimHub\PluginsData\Automobilista2\Cars" --output build/ams2-simhub-identity-audit.json --review-csv build/ams2-alias-review.csv
```

Promote only the aliases recorded in the reviewed approval manifest:

```shell
python -m as_driven_db promote-ams2 --candidates build/ams2-candidates.json --audit build/ams2-simhub-identity-audit.json --approvals curation/ams2-approved-records.json --data-dir data/v1
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

Dataset 0.3.81 contains 242 curated AMS2 records promoted through the reviewed
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
Dataset 0.3.14 promotes Audi V8 quattro DTM, Lamborghini Veneno Roadster, Audi
R8 LMS GT3, Chevrolet Corvette C8 Z06 (+Z07 Upgrade), and Super Trophy Trucks.
The Audi DTM draft also demonstrates reviewed correction of a false move-off
caused by a slight roll before stalling. Super Trophy Trucks preserves its
automatic construction separately from its visible sequential manual-override
lever, and all unresolved automatic-cut behavior remains `unknown`.
Dataset 0.3.15 promotes Maserati GT2 Stradale, the road-going Aston Martin
Valkyrie, and the exact High Downforce identities for Renault R25, R26, and
R28. The two road cars retain medium-confidence manually confirmed automatic
cut claims; the Renault guided tests captured shift-local automatic cut and
blip traces directly. Untested Renault aero identities are not silently added.
Dataset 0.3.16 promotes ten exact guided identities: Ligier JS2 R,
Lamborghini Miura SV and Revuelto, Audi R8 V10 GT, Dodge Viper ACR, BMW M3
E46 GTR, Maserati GranSport Trofeo, and three configuration-specific Stock USA
records. Stock USA mappings remain fictionalized and configuration-scoped;
the Audi record uses the later seven-speed S tronic generation rather than the
unrelated 2010 six-speed R tronic car.
Dataset 0.3.17 revalidates the fifteen remaining spreadsheet-era records in
AMS2 1.6.9.91 and corrects their exact identities and simulator observations.
Dataset 0.3.18 promotes the final nine reviewed entries from that audit,
including exact high-downforce and tyre-specific identities. The separate AMS2
coverage manifest now classifies the larger current roster for later research
and verification; it is not silently included in the curated dataset.
Dataset 0.3.19 promotes the first modern-prototype verification batch: BMW M
Hybrid V8, Porsche 963, Chevrolet Corvette GTP, MetalMoro AJR Chevrolet, and
MetalMoro AJR Gen2 Chevrolet. The two LMDh cars use the category's spec
seven-speed paddle transmission with automatic cut and blip, while the 1988
IMSA GTP Corvette is the batch's only manual-technique car: a five-speed
H-pattern requiring the clutch to pull away, a throttle lift to upshift, and a
manual blip to downshift. The two MetalMoro prototypes are reviewed
independently of one another rather than inherited across the generation.
Dataset 0.3.20 promotes the seven remaining aero-inheritance-ready identities
as explicit Low Downforce aliases of already verified base records. No control
value changes and no record is added; each alias is disclosed as an untested
aero configuration in its record notes and curation approval.
Dataset 0.3.21 closes the remaining review-only queue. Four unqualified Formula
identities and one whitespace-only Stock USA identity become explicit aliases of
their curated records, and six identities are closed as written decisions in
`research/ams2-identity-decisions.json`: five retired pre-rename observations
that are deliberately not aliased because they are not selectable in the
certified build, and the BMW M3 Safety Car as outside product scope. Guided
verification is now the only remaining category of open work.
Dataset 0.3.22 promotes modern-prototype batch 02: Nissan R89C, Porsche 962C,
and MetalMoro MRX Duratec P4. The two Group C cars are manual-technique cars,
each a five-speed H-pattern needing the clutch to pull away, a throttle lift to
upshift, and a manual blip to downshift. The MRX uses a sequential stick with an
automatic cut but no automatic blip. Nissan's own heritage record supplies the
R89C five-speed VGC transmission and Lola-built chassis, while Metalmoro states
the MRX fixes no transmission, so its sequential six-speed is recorded at medium
confidence as the configuration modeled in AMS2. Verifying these bases makes the
R89C and 962C Low Downforce identities inheritance-ready.
Dataset 0.3.23 promotes those two as explicit Low Downforce aliases, again without
driving and without changing any control value.
Dataset 0.3.24 promotes the first contemporary GT batch: seven paddle-shift GT3
cars whose controls proved identical, and the Ginetta G55 GT3, which AMS2 classes
as GT Open and which uses a sequential lever and needs the clutch to pull away.
Its throttle lift and manual blip stay unknown because a lever paired with
automatic cut and blip has no precedent among curated cars.
Dataset 0.3.26 promotes the GT4 batch, which is deliberately not uniform. BMW M4
GT4, McLaren 570S GT4, and Porsche 718 Cayman GT4 Clubsport MR carry road-derived
dual-clutch gearboxes, which is why two of them have seven gears where most GT4
cars have six, while the Mercedes-AMG GT4 and both Ginetta G55 variants use
conventional racing sequentials. The Cayman carries the first simulator override
in the dataset: its real PDK has no clutch pedal, so the record says the
standing-start clutch is not required while a sourced override records that AMS2
requires clutch input to move off.
Dataset 0.3.27 completes the GT family with two late-1990s Le Mans GT1 cars, two
modern GTE cars, and the Puma GTE, which despite its name is a 1970s Brazilian
road car on Volkswagen running gear with four H-pattern gears and no automation.
Dataset 0.3.28 promotes the touring and stock batch, whose three period European
cars carry the first dogleg gates recorded from a guided drive rather than from a
specification: the BMW M1 Procar, the Mercedes-Benz 190E 2.5-16 Evolution II and
the BMW M3 Sport Evolution. Super V8 is Reiza's fictionalised Australian
Supercars car, which retains a manual stick shift on a six-speed sequential
transaxle.
Dataset 0.3.29 promotes the club and road batch, finishing every category except
open-wheel. Eight are ordinary synchromesh H-pattern cars with no automation. The
tenth is the batch's finding: `Ginetta G40` is the GT5 Challenge car on a
six-speed Quaife sequential, not the five-speed synchromesh H-pattern of
`Ginetta G40 Cup`, so a shared nameplate again proved to be no basis for shared
controls. This release also settles what `manual_blip` asserts: mechanical
necessity, so `required` is reserved for gearboxes that cannot engage without a
blip and synchromesh cars are `optional`. Three earlier records were corrected to
match.
Dataset 0.3.30 opens the open-wheel queue with the 1967 to 1979 era: six
five-speed H-pattern cars with no automation. Brabham BT26A and Lotus 49C are the
first `dogbox` records established from evidence rather than observed behavior,
because both use racing Hewlands engaged by dog rings rather than synchronisers,
which makes their downshift blip required. The four Reiza cars carry no
real-world chassis, so their gearbox construction stays `unknown`.
Dataset 0.3.31 adds the 1983 to 1986 turbo era and establishes how simulator aero
configurations reach a driver. AMS2 selects the downforce variant from the
circuit rather than from the player, so one car reports different telemetry
identities at different tracks; each record now carries every observed aero
identity, or a driver would be reported unmatched purely for choosing a
different track. Lotus Renault 98T carries the first gear-count override: its
real gearbox is a six-speed and AMS2 models five.

## Licensing

Software is MIT licensed. The original database selection and arrangement is
CC BY 4.0; third-party sources retain their own rights. See
[DATA_LICENSE.md](DATA_LICENSE.md).
