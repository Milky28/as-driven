# AMS2 exact-identity coverage plan

Dataset 0.3.18 contains 85 curated records. The refreshed SimHub 9.11.22
identity inventory contains 225 exact AMS2 identities observed on this PC. The
generated coverage manifest compares those two sources without fuzzy matching.

The machine-readable queue is checked in at:

- `research/ams2-coverage-manifest.json` for complete structured detail;
- `research/ams2-coverage-manifest.csv` for filtering and review;
- `research/build_ams2_coverage_manifest.py` for reproducible refreshes.

## Current coverage snapshot

- 102 observed identities are covered exactly by curated records.
- 123 observed identities require some action.
- 95 currently appear to need full guided verification.
- 44 of those 95 have an exact legacy spreadsheet candidate that can seed
  historical controls research; the guided drive must still establish current
  AMS2 behavior and cockpit controls.
- 51 require independent control research in addition to current-game testing.
- Seven exact Low Downforce identities already have a curated base record and
  can be reviewed as explicitly untested aero inheritance.
- Ten more Low Downforce identities can inherit only after their base car is
  verified.
- Four unqualified/configuration identities require an explicit relationship
  review against an already curated qualified configuration.
- Five stored identities need rename/removal/history review before deciding
  whether to test them.
- One whitespace-only identity needs an explicit alias review.
- The BMW M3 Safety Car is held for a product-scope decision.

These counts describe observed telemetry identities, not guaranteed current
selector entries. SimHub retains a file after observing a car, so an identity
can outlive a rename or removal.

## Work order

### 1. Resolve inexpensive identity work

Review the seven `aero-inheritance-ready`, four
`configuration-inheritance-review`, one `formatting-only-review`, five
`identity-history-review`, and one `special-purpose-review` entries first.
Nothing is silently aliased. Every accepted identity remains explicit and any
untested aero inheritance is disclosed in record notes and provenance.

### 2. Verify modern prototypes

Start the next guided batch with:

1. BMW M Hybrid V8;
2. Chevrolet Corvette GTP;
3. Porsche 963;
4. MetalMoro AJR Chevrolet;
5. MetalMoro AJR Gen2 Chevrolet.

This batch is small, has high pre-session hardware value, and establishes base
records for three pending Low Downforce identities. Mazda 787B, Nissan R89C,
Porsche 962C, and MetalMoro MRX Duratec P4 follow in the next prototype batch.

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
python -m authentic_controls_db audit-simhub-ams2 `
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
