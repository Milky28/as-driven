# AMS2 exact-identity coverage plan

Dataset 0.3.98 contains 242 curated records. The identity inventory contains 333
exact AMS2 identities observed on this PC, reconciled from two sources: SimHub's
stored car files, and the plugin's live unmatched-identity diagnostics log. The
generated coverage manifest compares those against curated records without fuzzy
matching.

Neither source is a roster. An identity absent here may simply never have been
loaded on this PC, so these counts are a floor on the identity space rather than
a count of the cars AMS2 ships. A published car list is also not directly
comparable, because one car can present several telemetry identities: AMS2
selects the aero configuration from the circuit, and only observation reveals
which cars have variants.

Each entry records which source it came from. Stored car files are not rewritten
when Reiza renames a car, so an entry seen only in stored files may carry a name
the game no longer reports, while `live-diagnostics` entries are current.

The machine-readable queue is checked in at:

- `research/ams2-coverage-manifest.json` for complete structured detail;
- `research/ams2-coverage-manifest.csv` for filtering and review;
- `research/build_ams2_coverage_manifest.py` for reproducible refreshes.

## Current coverage snapshot

- 318 observed identities are covered exactly by curated records.
- 15 observed identities are not covered, and none of them needs driving.
- 0 need full guided verification. Every observed AMS2 identity is now either
  curated or closed by an explicit reviewer decision.
- 15 identities are closed by explicit review rather than driving: retired
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

### 6. Sweep the simulator's class list

Adopted after batch 10. The generated queue cannot see a car that has never been
loaded on this PC, and the published roster is around 253 cars against roughly
179 distinct cars observed here, so a queue-driven order leaves about 74 cars
permanently invisible. Walking the in-sim class list replaces inference with
enumeration and is the only source that reflects current content.

Per class: load every car, including ones believed already covered, because the
plugin reports matched or unmatched and memory does not. Drive the unmatched
ones. A rename is invisible to memory and obvious to the plugin, which is how
`Lotus 98T` was missed.

A sweep captures one aero configuration per car, whichever the current circuit
selects, so cars with variants still need passes at other circuits. Loading is
enough; no drive is needed to capture an identity.

There are up to three aero states, and how many a car has depends on its class.
A tester found one car showing high downforce at Laguna Seca, low downforce at
Daytona, and no package at all at Imola, so a base configuration exists alongside
the two suffixed ones. The batch 09 classes, `F-Retro_Gen3` and
`F-Classic_Gen1`, offer no low-downforce package at all: their unsuffixed name is
the base, and they have two aero identities rather than three.

An unsuffixed name is therefore not evidence of low downforce. Dataset 0.3.40
corrected five records that had described it that way, and 0.3.42 recorded them
as base configurations once the selection screen confirmed no low-downforce
package exists for those classes. The number of variants has to be read per
class; it cannot be assumed from another car.

Dataset 0.3.42 completed the aero identities for the classes that offer more
than one package: twenty observed directly, and forty-two derived by a reviewer
from each car's observed high-downforce name and marked as derived.

Dataset 0.3.98 replaced all of that with a declaration. A record names its base
telemetry name once and lists the packages it covers, and the exact spellings are
produced when the database is read. Nothing is derived by hand any more, so the
forty-two derived identities and the approvals disclosing them are gone; what
remains to establish is only **which** packages a car offers, never how they are
spelled. See `docs/data-model.md`.

That still has to be read per class rather than assumed from another car, and
the vehicle selection screen is the cheap way to read it: it names the packages
a car has without needing the car loaded at every circuit.

One caution survives the change. The inventory contains
`Stock USA Gen1 - Speedway ` with a trailing space, which no selection screen
would reveal and no declaration can produce. An identity like that is written out
literally, as its own exact string, and stays that way.

Batch 10 in dataset 0.3.32 was the first sweep: six cars, all six absent from the
queue beforehand.

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

Batch 09 in dataset 0.3.31 completed the 1983 to 1986 turbo era: Brabham BMW
BT52, McLaren Cosworth MP4/1C, Lotus Renault 98T, and Formula Classic Gen1
Model1 and Model2. All five are five-speed H-pattern cars, and the three real
cars all use Hewlands, so their downshift blip is `required`.

Batch 09 established how AMS2 aero configurations reach the driver, which
changes how identities must be read.

The configuration follows the circuit, not the driver. Reiza's v1.4.1.0 release
notes state that vehicle selection, showroom and lobby display the appropriate
downforce variant for the current circuit, and driving each car at Laguna Seca
and then loading it at Daytona produced two different identities. A record
therefore needs every aero identity of its car, or a driver is reported unmatched
purely because of the track they chose.

Which name means which variant is not inferable. For these formula classes the
suffixed name is high downforce and the plain name is low; for the sports and GT
cars already curated, the plain name is the default and the suffix marks low
downforce. The suffix marks the non-default variant, and the default differs by
class, so a plain name proves nothing on its own.

The SimHub inventory that generates this queue is keyed on a stored car file per
observed identity, and those files are not rewritten when Reiza renames a car.
The queue therefore listed `Lotus 98T` and plain `Brabham BMW BT52` while the
current game reports `Lotus Renault 98T - High Downforce` and
`Brabham BMW BT52 - High Downforce`. Five current identities were missing from
this queue entirely, and `Lotus 98T` proved to be a genuine rename rather than an
aero variant; it is recorded as a retired identity.

The plugin's unmatched-identity diagnostics log is the accurate source. It
records the live car model, car id, class, game version and date every time an
uncurated car is loaded, needs no guided drive, and captured all five current
identities plus their aero counterparts in a few minutes. This queue should
reconcile against that log rather than the stored car files alone.

Lotus Renault 98T carries the dataset's first gear-count override. Its real
gearbox is a Lotus/Hewland six-speed and AMS2 models five, confirmed deliberately
in-game, because a guided drive establishes only the highest gear actually
selected and cannot distinguish an unreached gear from an absent one.

**The current next batch is the remaining Formula Classic cars:** Gen2 Model1 and
Model2, Gen3 Model1, Gen4 Model1, and Gen4 Model2 - Low Downforce. Their queued
names predate the aero reorganisation, so confirm each exact identity from the
diagnostics log after loading rather than trusting the name recorded here.

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

The refresh reads the plugin's diagnostics log by default and accepts
`--live-log` to point elsewhere. The log records the live model, id and class of
every uncurated car the plugin sees, so loading a car is enough to correct its
entry; no guided drive is needed. Load the candidates for a batch before relying
on the names in this queue, because an entry that has only ever come from stored
car files may carry a name Reiza has since changed.

The SimHub inventory is opportunistic: cars not yet loaded on this PC do not
appear. Final roster completeness therefore also requires comparison with the
current in-game selector or another authoritative current roster source.
