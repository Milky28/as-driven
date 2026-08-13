# AMS2 exact-identity coverage plan

Dataset 0.3.25 contains 101 curated records. The refreshed SimHub 9.11.22
identity inventory contains 225 exact AMS2 identities observed on this PC. The
generated coverage manifest compares those two sources without fuzzy matching.

The machine-readable queue is checked in at:

- `research/ams2-coverage-manifest.json` for complete structured detail;
- `research/ams2-coverage-manifest.csv` for filtering and review;
- `research/build_ams2_coverage_manifest.py` for reproducible refreshes.

## Current coverage snapshot

- 137 observed identities are covered exactly by curated records.
- 88 observed identities are not covered.
- 77 of those need full guided verification, and they are now the only work
  that requires driving.
- 39 of those 85 have an exact legacy spreadsheet candidate that can seed
  historical controls research; the guided drive must still establish current
  AMS2 behavior and cockpit controls.
- 46 require independent control research in addition to current-game testing.
- No Low Downforce identity is inheritance-ready: dataset 0.3.25 promoted the two
  that batch 03 unblocked. Three more wait on unverified bases.
- Seven identities are closed by explicit review rather than driving: three
  retired pre-rename observations of official cars, three third-party mod
  identities, and one out of product scope. Each carries a written basis in
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

Modern-prototype batch 01 was completed in dataset 0.3.19: BMW M Hybrid V8,
Chevrolet Corvette GTP, Porsche 963, MetalMoro AJR Chevrolet, and MetalMoro AJR
Gen2 Chevrolet, with the BMW/Corvette/Porsche `- Low Downforce` aliases carried
as explicit inherited identities.

Start the next guided batch with:

1. Mazda 787B;
2. Nissan R89C;
3. Porsche 962C;
4. MetalMoro MRX Duratec P4.

This batch establishes base records for the Nissan R89C and Porsche 962C pending
Low Downforce identities. The three historic Le Mans cars each carry a legacy
control candidate to seed research; the guided drive still establishes current
AMS2 behavior.

### 3. Verify contemporary GT cars

Process GT3/GTE first, then GT4/one-make cars. Grouping similar cars improves
testing speed but does not permit controls to be inherited across different
models without evidence.

### 4. Verify touring, stock, club, and road cars

Prioritize cars likely to need H-pattern hardware or manual rev matching,
because their guidance most directly changes a user's pre-session hardware.

### 5. Verify open-wheel cars by historical era

The 42-car open-wheel queue is the largest and should be split into Formula
Vintage/Retro/Classic, Formula HiTech, CART/Formula USA historical chassis, and
modern Formula groups. Similar class names are batching aids only; each exact
selectable identity remains independently reviewable.

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
