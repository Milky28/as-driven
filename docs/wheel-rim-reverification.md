# Wheel-rim re-verification worklist

The wheel-rim vocabulary was defined in dataset 0.3.56, after most records had already been curated. Until then the enum mixed two axes: `round`, `d-shaped` and `yoke` describe a rim's outline, while `gt-style`, `prototype` and `formula` described the kind of car. Most rims satisfy one of each, so both answers were always defensible and the recorded values drifted.

`docs/data-model.md` now defines shape by the rim itself. This file lists the records whose recorded values cannot be reconciled with those definitions. Nothing here has been corrected by inference: a rim that was not looked at again is not re-described.

One caveat applies to every record, not only those listed below. The definitions ask first whether a rim is a control-panel rim (molded grips at 9 and 3, hands fixed) or a conventional one (a continuous band gripped anywhere). That question was never put to a reviewer before these definitions existed, so the boundary between `gt-formula`, `d-shaped` and `round` was drawn without it throughout. The distinction is untested rather than confirmed.

## Already resolved

**The three racing-class values were merged.** `gt-style`, `prototype` and `formula` all described one rim: molded grips at 9 and 3 with a control face between them. They are now a single `gt-formula` value across 56 records and their approvals. This was a vocabulary merge, not a new observation, and each record carries a note saying so.

Merging also settled the largest contradiction this file used to list. All 15 `formula` records recorded `open_top: no`, which conflicted with a definition that made `formula` mean *open across the top*. The reviewer was right and the definition was wrong: modern formula rims close over the top much as GT rims do, and eight records said so in prose, describing "a closed Formula rim". `open_top` is now descriptive and decides nothing, so those records are consistent as they stand.

## 1. Shape and open-top contradict each other

`yoke` means open across the top, and `d-shaped` and `round` are conventional rims closed over the top. In each record below the shape and `open_top` state the opposite of each other, so one of them is wrong and only a look at the cockpit can say which. `gt-formula` records cannot appear here: that value implies nothing about the top.

| Record | Shape | open_top |
| --- | --- | --- |
| `audi-r8-lmp1` | yoke | unknown |
| `f309` | round | yes |
| `formula-trainer-advanced` | d-shaped | yes |
| `formula-trainer` | d-shaped | yes |
| `mclaren-mercedes-mp4-12` | round | yes |
| `porsche-911-gt1-98` | d-shaped | yes |

Count: 6.

## 1b. One car recorded under more than one shape across simulators

A record is one real car, so its simulator entries describe one rim. These four
disagree about it. That is worth separating from the family splits below: those
compare different cars, while these compare the same car seen twice.

| Record | Recorded as | Authentic |
| --- | --- | --- |
| `nissan-gt-r-nismo-gt3` | round (ams2), gt-formula (acc) | gt-formula |
| `nissan-r390-gt1` | round (ams2), d-shaped (ac) | unknown |
| `porsche-911-gt3-r` | d-shaped (ams2), gt-formula (acc) | gt-formula |
| `saleen-s7-r-gt1` | round (ams2, ac), d-shaped (raceroom) | round |

Count: 4.

None of these is established as a modelling difference. Two split on
round against gt-formula and two on round against d-shaped, which are precisely
the boundaries the caveat above says were drawn before the definitions existed.
A simulator genuinely modelling a different wheel would be a real finding; the
same rim classified twice is not.

The Saleen is the one with a photograph behind it. The maintainer looked for
period images of the S7R cockpit and found the rim carries so slight a flat that
it could reasonably be called either, which explains a split across three
simulators without any of them modelling anything different. Reference supplied
by the maintainer: `csms.cz` 2009 photo gallery, "Look into the cockpit of the
car SALEEN S7R". It is not registered in `sources.json`, because nothing has been
claimed from it yet - registering it is the first step if the real-car shape is
to be re-decided rather than merely doubted.

Settling one of these needs a look at the rim in each simulator against the
decision order in `docs/data-model.md`, asking the control-panel question first.
Until then the recorded values stand: they are what somebody saw, and the split
is a question about the vocabulary rather than about the cars.

## 2. Families recorded under more than one shape

A split is not automatically an error: cars in one class can genuinely carry different rims. These are listed because the split follows the old ambiguity rather than any noted difference, so each needs confirming against the outline rule before it is trusted.

### Formula Classic (12 records)

Recorded as: d-shaped x3, round x9.

- `formula-classic-gen1-model2` - d-shaped
- `formula-classic-gen2-model2` - d-shaped
- `formula-classic-gen4-model3` - d-shaped
- `formula-classic-gen1-model1` - round
- `formula-classic-gen2-model1` - round
- `formula-classic-gen2-model3` - round
- `formula-classic-gen3-model1` - round
- `formula-classic-gen3-model2` - round
- `formula-classic-gen3-model3` - round
- `formula-classic-gen3-model4` - round
- `formula-classic-gen4-model1` - round
- `formula-classic-gen4-model2` - round

### Formula Edge (3 records)

Recorded as: d-shaped x1, round x1, yoke x1.

- `formula-edge-model2` - d-shaped
- `formula-edge-model3` - round
- `formula-edge-model1` - yoke

### Formula HiTech (6 records)

Recorded as: d-shaped x1, round x5.

- `formula-hitech-gen2-model3` - d-shaped
- `formula-hitech-gen1-model1` - round
- `formula-hitech-gen1-model2` - round
- `formula-hitech-gen1-model4` - round
- `formula-hitech-gen2-model1` - round
- `formula-hitech-gen2-model2` - round

### Formula Vee (3 records)

Recorded as: round x2, yoke x1.

- `formula-vee-fin` - round
- `formula-vee-gen1` - round
- `formula-vee-gen2` - yoke

### GT3 / GT4 / GTE (30 records)

Recorded as: d-shaped x5, gt-formula x19, round x6.

- `ginetta-g55-gt3` - d-shaped
- `ginetta-g55-gt4` - d-shaped
- `ginetta-g55-gt4-supercup` - d-shaped
- `mclaren-570s-gt4` - d-shaped
- `porsche-911-gt3-r` - d-shaped
- `aston-martin-vantage-gt3-evo` - gt-formula
- `aston-martin-vantage-gt4-evo` - gt-formula
- `aston-martin-vantage-gte` - gt-formula
- `audi-r8-lms-gt3` - gt-formula
- `audi-r8-lms-gt3-evo-ii` - gt-formula
- `audi-r8-lms-gt4` - gt-formula
- `bmw-m4-gt3` - gt-formula
- `bmw-m4-gt4` - gt-formula
- `bmw-m6-gt3` - gt-formula
- `chevrolet-camaro-gt4-r` - gt-formula
- `chevrolet-corvette-z06-gt3r` - gt-formula
- `lamborghini-huracan-gt3-evo2` - gt-formula
- `mclaren-720s-gt3` - gt-formula
- `mclaren-720s-gt3-evo` - gt-formula
- `mercedes-amg-gt3` - gt-formula
- `mercedes-amg-gt3-evo` - gt-formula
- `mercedes-amg-gt4` - gt-formula
- `porsche-911-rsr-gte` - gt-formula
- `porsche-992-gt3-r` - gt-formula
- `alpine-a110-gt4-evo` - round
- `milano-gt36` - round
- `nissan-gt-r-nismo-gt3` - round
- `porsche-996-gt3-rsr` - round
- `porsche-cayman-gt4-clubsport-mr` - round
- `puma-gte` - round

## 3. Shift lights never observed

`integrated_display` and `shift_lights` are recorded independently: a rim can
carry a readout, shift lights, both or neither. The guided-drive vocabulary only
grew to capture lights partway through curation - later source labels say so
outright (`live-cockpit-round-shift-lights`,
`live-cockpit-formula-display-shift-lights`), while these records carry the older
forms (`live-cockpit-round-no-display`, `live-cockpit-gt`, or a plain
`live-cockpit-observation`). So this is one vocabulary change rather than 31
separate mysteries, and only a look at the cockpit closes it.

The field was absent from 30 of these rather than recorded as `unknown`. It is
now `unknown` everywhere, which changes nothing a driver sees - the client
already read an absent state as unknown - but makes the gap countable and puts
the one record that already said `unknown` in with the rest.

**19 records have a known display and unobserved lights.** These are the useful
ones to re-check: half the answer is already there.

| Record | Display | Shape |
| --- | --- | --- |
| `aston-martin-dbr9` | no | round |
| `aston-martin-vantage-gt4-evo` | no | gt-formula |
| `aston-martin-vantage-gte` | no | gt-formula |
| `audi-r8-lmp1` | no | yoke |
| `audi-r8-lms-gt4` | no | gt-formula |
| `chevrolet-corvette-c5-r` | no | round |
| `chevrolet-corvette-z06-gt3r` | no | gt-formula |
| `gillet-vertigo-streiff` | no | d-shaped |
| `lamborghini-diablo-sv-r` | no | round |
| `lamborghini-murcielago-r-gt` | no | d-shaped |
| `lister-storm-gtm` | no | d-shaped |
| `maserati-mc12-gt1` | no | d-shaped |
| `milano-gt36` | no | round |
| `milano-gt55` | no | round |
| `panoz-esperante-gtlm` | no | d-shaped |
| `porsche-996-gt3-rsr` | no | round |
| `saleen-s7-r-gt1` | no | round |
| `spyker-c8-spyder-gt2-r` | no | round |
| `tvr-tuscan-t400r-gt2` | no | round |

**11 records have a display and unobserved lights.** Worth noting that a rim with
a readout is the likelier one to also carry lights, so these are not safely
assumed either way.

| Record | Display | Shape |
| --- | --- | --- |
| `alpine-a424` | yes | gt-formula |
| `aston-martin-valkyrie-hypercar` | yes | gt-formula |
| `cadillac-v-series-r` | yes | gt-formula |
| `dallara-sp1` | yes | gt-formula |
| `lamborghini-sc63` | yes | gt-formula |
| `ligier-js-p217` | yes | gt-formula |
| `ligier-js-p320` | yes | gt-formula |
| `ligier-js-p4` | yes | gt-formula |
| `lola-b05-40-turbo` | yes | d-shaped |
| `lola-b05-40-v8` | yes | d-shaped |
| `oreca-07` | yes | gt-formula |

**One record has neither observed.** `dodge-viper-gts-r` is sourced from
`period-cockpit` rather than a drive, so it is a different problem from the rest
of this list: there is no simulator cockpit to go back to for the real car's rim.

Count: 31.

### What the card shows meanwhile

The FIT band used to answer "Display not recorded" whenever lights were absent,
which was wrong in both directions. For the 19 records with `display: no` it
denied a display that had been recorded. For the 11 with `display: yes` it read
as a complete answer - ordinary text, no hedge - while dropping the lights
silently, which is the worse of the two.

It now says which half is missing: "No display, lights unknown" or "Display,
lights unknown", and both halves must be established before the line loses its
grey. See `PreflightLabels.WheelFeatures`.

## Working through this list

Re-observation uses the ordinary guided-verification path: drive the car, record the rim in the contribution form, then import, review and promote the observation. The form now shows the decision order beside each field, so a re-recorded value follows the definitions without the reviewer having to remember them.
