# AMS2 exact-identity coverage plan

Dataset 0.3.30 contains 134 curated records. The refreshed SimHub 9.11.22
identity inventory contains 225 exact AMS2 identities observed on this PC. The
generated coverage manifest compares those two sources without fuzzy matching.

The machine-readable queue is checked in at:

- `research/ams2-coverage-manifest.json` for complete structured detail;
- `research/ams2-coverage-manifest.csv` for filtering and review;
- `research/build_ams2_coverage_manifest.py` for reproducible refreshes.

## Current coverage snapshot

- 172 observed identities are covered exactly by curated records.
- 53 observed identities are not covered.
- 42 of those need full guided verification, and they are now the only work
  that requires driving.
- 16 of those 42 have an exact legacy spreadsheet candidate that can seed
  historical controls research; the guided drive must still establish current
  AMS2 behavior and cockpit controls.
- 26 require independent control research in addition to current-game testing.
- 1 Low Downforce identities wait on unverified base cars; none is
  inheritance-ready.
- 10 identities are closed by explicit review rather than driving: retired
  pre-rename observations of official cars, third-party mod content, and one
  vehicle out of product scope. Each carries a written basis in
  `research/ams2-identity-decisions.json`.

Every review-only queue is now empty. Dataset 0.3.20 promoted the seven
`aero-inheritance-ready` identities, and 0.3.21 promoted the four unqualified
configuration identities and the single whitespace-only identity as explicit
aliases, then recorded the retired and out-of-scope decisions.

`simhub_max_gears` in the manifest is a weak hint, not evidence. It is the
highest gear index SimHub observed, so a spurious reading inflates it; the
inventory contains values such as 42, 119, and 150. Use it to prompt a
question, never to set a gear count.

These counts describe observed telemetry identities, not guaranteed current
selector entries. SimHub retains a file after observing a car, so an identity
can outlive a rename or removal.

An observed identity is also not proof of official content. SimHub records any
car it sees, including third-party mods, so the inventory can contain cars AMS2
never shipped. Three confirmed examples come from the ThunderFlash mods pack:
the two FIA-GT1 prefixed cars and a Huracan Super Trofeo ported from Project
CARS 2. AMS2 and Project CARS 2 share an engine lineage, so ports are common
and their identities look plausible at a glance.

Two signals identified them, and neither is an observation date on its own:

- a class-style prefix or a run-together internal name that does not match
  Reiza's spacing convention;
- an observation that predates the official car's release announcement, where
  the official car exists separately under its own name.

Thirty-nine queued identities were last observed before 2025 and are ordinary
official cars, so age alone proves nothing. Check provenance when a name looks
irregular, and record the outcome in
`research/ams2-identity-decisions.json`.

## Work order

### 1. Resolve inexpensive identity work

Complete. Datasets 0.3.20 and 0.3.21 cleared every review-only queue: seven
aero inheritances, four unqualified configurations, and one whitespace-only
identity became explicit aliases, and six identities were closed as reviewed
decisions rather than pending work.

Nothing was silently aliased. Every accepted identity is written into the
record and disclosed in its curation approval, and any untested aero or
configuration inheritance says so in the record notes.

A retired identity is deliberately not aliased onto its renamed record. It is
not selectable in the certified build, so inherited controls could not be
verified there; `research/ams2-identity-decisions.json` records the successor
name and the reasoning instead.

### 2. Verify modern prototypes

Complete. Batch 01 in dataset 0.3.19 covered BMW M Hybrid V8, Chevrolet Corvette
GTP, Porsche 963, MetalMoro AJR Chevrolet, and MetalMoro AJR Gen2 Chevrolet.
Batch 02 in 0.3.22 covered Nissan R89C, Porsche 962C, and MetalMoro MRX Duratec
P4; Mazda 787B was dropped as modded content, because Reiza holds no Mazda
licence. Datasets 0.3.20 and 0.3.23 promoted the unlocked `- Low Downforce`
aliases.

### 3. Verify contemporary GT cars

Complete. Batch 03 in dataset 0.3.24 covered seven paddle-shift GT3 cars plus the
sequential-lever Ginetta G55 GT3; batch 04 in 0.3.26 covered six GT4 cars and
introduced the dataset's first simulator override; batch 05 in 0.3.27 covered the
late-1990s GT1 cars, two modern GTE cars, and the misclassified Puma GTE road
car. Datasets 0.3.23 and 0.3.25 promoted the unlocked `- Low Downforce` aliases.

Grouping similar cars improved testing speed but never permitted controls to be
inherited across different models without evidence, and the GT4 batch proved why:
three of its six cars carry seven gears from a road-car dual clutch.

### 4. Verify touring, stock, club, and road cars

Complete. Batch 06 in dataset 0.3.28 completed the touring and stock cars and
produced the first records whose gate pattern was read from a guided drive rather
than a specification. Batch 07 in 0.3.29 completed the club and road cars.

Batch 07 also settled what `manual_blip` asserts. It now states mechanical
necessity: `required` is reserved for a gearbox that cannot engage the gear
without a blip, and a synchronised gearbox is `optional`, because the blip is
authentic technique and eases the synchros but is not needed. Three earlier
synchromesh records were corrected to match, since they had been recorded under
two different readings of the same field.

That makes `gearbox_type` load-bearing rather than descriptive, and it is not
always sourceable: Caterham's own motorsport partner offers the Type 9 five-speed
in both synchronised and dog-engagement variants, so those two records rest on an
inference from road-legality and say so.

### 5. Verify open-wheel cars by historical era

The 42-car open-wheel queue is now all that remains besides six sports and
touring cars, and is split into Formula Vintage/Retro/Classic, Formula HiTech,
CART/Formula USA historical chassis, and modern Formula groups. Similar class
names are batching aids only; each exact selectable identity remains
independently reviewable.

Batch 08 in dataset 0.3.30 completed the earliest era, 1967 to 1979: Formula
Vintage Gen1 Model1 and Model2, Brabham BT26A, Lotus 49C, Formula Retro V12 and
Formula Retro Gen2. All six are five-speed H-pattern cars on a standard gate with
no automation whatever.

A dogleg gate was expected in this era and none was found. The prediction rested
on a search summary of a forum post; the reachable sources do not support it, and
no dogleg was recorded on that basis. The gates were read by watching the lever
and the driver's hand through a shift, because these cars have no gate plate.

Batch 08 also produced the dataset's first `dogbox` records from evidence rather
than from a drive. Brabham BT26A and Lotus 49C use racing Hewlands, engaged by
dog rings rather than synchronisers, so their downshift blip is `required`. The
four Reiza cars carry no real-world chassis, so their gearbox construction and
downshift blip stay `unknown` rather than being inferred from period practice.

**The current next batch is the remaining Formula Vintage/Retro/Classic cars:**
the seven Formula Classic identities, plus Lotus 98T and Brabham BMW BT52 from
the same era.

Two identities in the wider queue need provenance review before driving rather
than after: `Porsche 911 RSR 1974` and `Porsche 911 RSR 74` are more likely a
rename pair than two cars. Neither is open-wheel, so this does not block the
batch above.

## Refresh procedure

After AMS2 or SimHub adds identities, regenerate the exact identity audit and
manifest:

```powershell
python -m as_driven_db audit-simhub-ams2 `
  --candidates build/ams2-candidates.json `
  --cars-dir "C:\Program Files (x86)\SimHub\PluginsData\Automobilista2\Cars" `
  --simhub-version 9.11.22 `
  --output build/ams2-simhub-identity-audit.json `
  --review-csv build/ams2-alias-review.csv

python research/build_ams2_coverage_manifest.py
```

The SimHub inventory is opportunistic: cars not yet loaded on this PC do not
appear. Final roster completeness therefore also requires comparison with the
current in-game selector or another authoritative current roster source.
