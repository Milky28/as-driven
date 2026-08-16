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
| `mclaren-mercedes-mp4-12-high-downforce` | round | yes |
| `porsche-911-gt1-98` | d-shaped | yes |

Count: 6.

## 2. Families recorded under more than one shape

A split is not automatically an error: cars in one class can genuinely carry different rims. These are listed because the split follows the old ambiguity rather than any noted difference, so each needs confirming against the outline rule before it is trusted.

### Formula Classic (12 records)

Recorded as: d-shaped x3, round x9.

- `formula-classic-gen1-model2-high-downforce` - d-shaped
- `formula-classic-gen2-model2-high-downforce` - d-shaped
- `formula-classic-gen4-model3-high-downforce` - d-shaped
- `formula-classic-gen1-model1-high-downforce` - round
- `formula-classic-gen2-model1-high-downforce` - round
- `formula-classic-gen2-model3-high-downforce` - round
- `formula-classic-gen3-model1-high-downforce` - round
- `formula-classic-gen3-model2-high-downforce` - round
- `formula-classic-gen3-model3-high-downforce` - round
- `formula-classic-gen3-model4-high-downforce` - round
- `formula-classic-gen4-model1-high-downforce` - round
- `formula-classic-gen4-model2-high-downforce` - round

### Formula Edge (3 records)

Recorded as: d-shaped x1, round x1, yoke x1.

- `formula-edge-model2-high-downforce` - d-shaped
- `formula-edge-model3-high-downforce` - round
- `formula-edge-model1-high-downforce` - yoke

### Formula HiTech (6 records)

Recorded as: d-shaped x1, round x5.

- `formula-hitech-gen2-model3-high-downforce` - d-shaped
- `formula-hitech-gen1-model1-high-downforce` - round
- `formula-hitech-gen1-model2-high-downforce` - round
- `formula-hitech-gen1-model4-high-downforce` - round
- `formula-hitech-gen2-model1-high-downforce` - round
- `formula-hitech-gen2-model2-high-downforce` - round

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

## 3. Rim modifiers never recorded

These records carry a shape but no `integrated_display`, `shift_lights` or `open_top` value. That is an honest gap rather than a contradiction: the fields are optional and were not observed. They are listed so a future pass can fill them in.

- `gillet-vertigo-streiff` - d-shaped
- `lamborghini-murcielago-r-gt` - d-shaped
- `lister-storm-gtm` - d-shaped
- `maserati-mc12-gt1` - d-shaped
- `panoz-esperante-gtlm` - d-shaped
- `alpine-a424` - gt-formula
- `aston-martin-valkyrie-hypercar` - gt-formula
- `aston-martin-vantage-gt4-evo` - gt-formula
- `aston-martin-vantage-gte` - gt-formula
- `audi-r8-lms-gt4` - gt-formula
- `chevrolet-corvette-z06-gt3r` - gt-formula
- `lamborghini-huracan-super-trofeo-evo2` - gt-formula
- `lamborghini-sc63` - gt-formula
- `ligier-js-p217` - gt-formula
- `ligier-js-p320` - gt-formula
- `ligier-js-p4` - gt-formula
- `oreca-07` - gt-formula
- `aston-martin-dbr9` - round
- `chevrolet-corvette-c5-r` - round
- `dodge-viper-gts-r` - round
- `lamborghini-diablo-sv-r` - round
- `milano-gt36` - round
- `milano-gt55` - round
- `porsche-996-gt3-rsr` - round
- `saleen-s7-r-gt1` - round
- `spyker-c8-spyder-gt2-r` - round
- `tvr-tuscan-t400r-gt2` - round

Count: 27.

## Working through this list

Re-observation uses the ordinary guided-verification path: drive the car, record the rim in the contribution form, then import, review and promote the observation. The form now shows the decision order beside each field, so a re-recorded value follows the definitions without the reviewer having to remember them.
