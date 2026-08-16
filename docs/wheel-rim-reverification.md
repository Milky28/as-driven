# Wheel-rim re-verification worklist

The wheel-rim vocabulary was defined in dataset 0.3.55, after most records had already been curated. Until then the enum mixed two axes: `round`, `d-shaped` and `yoke` describe a rim's outline, while `gt-style`, `prototype` and `formula` described the kind of car. Most rims satisfy one of each, so both answers were always defensible and the recorded values drifted.

`docs/data-model.md` now defines shape by outline alone. This file lists the records whose recorded values cannot be reconciled with those definitions. Nothing here has been corrected by inference: a rim that was not looked at again is not re-described.

## Already resolved

The retired `prototype` shape was remapped to `gt-style` across 13 records and their approvals. That was a definitional collapse rather than a new observation, and every one of those records already described the rim in prose as *closed*, which is consistent with `gt-style` and rules out an open top. Each record carries a note saying the rim was not observed again.

## 1. Shape and open-top contradict each other

Shape and `open_top` are not independent. `formula` means no rim material across the top, so it implies `open_top: yes`; `gt-style`, `d-shaped` and `round` are all closed over the top, so they imply `no`; a `yoke` is always `yes`. In each record below the two values state the opposite of each other, so one of them is wrong and only a look at the cockpit can say which.

The `formula` rows are the striking case: all 15 of them carry `open_top: no`, without exception. That is far too consistent to be fifteen separate slips, so `open_top` was being answered as a different question entirely — most likely about the car rather than the rim. Expect the fix there to be a single systematic correction rather than fifteen individual judgments.

| Record | Shape | open_top |
| --- | --- | --- |
| `audi-r8-lmp1` | yoke | unknown |
| `audi-r8-lms-gt3` | gt-style | yes |
| `f309` | round | yes |
| `formula-inter-mg15` | formula | no |
| `formula-reiza` | formula | no |
| `formula-trainer-advanced` | d-shaped | yes |
| `formula-trainer` | d-shaped | yes |
| `formula-ultimate-2019` | formula | no |
| `formula-ultimate-2022` | formula | no |
| `formula-ultimate-hybrid-gen2-high-downforce` | formula | no |
| `formula-usa-2023` | formula | no |
| `formula-v10-g2` | formula | no |
| `formula-v10-gen3-b-high-downforce` | formula | no |
| `formula-v10-gen3-m-high-downforce` | formula | no |
| `formula-v8-gen1-b-high-downforce` | formula | no |
| `formula-v8-gen1-m-high-downforce` | formula | no |
| `formula-v8-gen2-high-downforce` | formula | no |
| `mclaren-mercedes-mp4-12-high-downforce` | round | yes |
| `porsche-911-gt1-98` | d-shaped | yes |
| `renault-r25-high-downforce` | formula | no |
| `renault-r26-high-downforce` | formula | no |
| `renault-r28-high-downforce` | formula | no |

Count: 22.

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

Recorded as: d-shaped x5, gt-style x19, round x6.

- `ginetta-g55-gt3` - d-shaped
- `ginetta-g55-gt4` - d-shaped
- `ginetta-g55-gt4-supercup` - d-shaped
- `mclaren-570s-gt4` - d-shaped
- `porsche-911-gt3-r` - d-shaped
- `aston-martin-vantage-gt3-evo` - gt-style
- `aston-martin-vantage-gt4-evo` - gt-style
- `aston-martin-vantage-gte` - gt-style
- `audi-r8-lms-gt3` - gt-style
- `audi-r8-lms-gt3-evo-ii` - gt-style
- `audi-r8-lms-gt4` - gt-style
- `bmw-m4-gt3` - gt-style
- `bmw-m4-gt4` - gt-style
- `bmw-m6-gt3` - gt-style
- `chevrolet-camaro-gt4-r` - gt-style
- `chevrolet-corvette-z06-gt3r` - gt-style
- `lamborghini-huracan-gt3-evo2` - gt-style
- `mclaren-720s-gt3` - gt-style
- `mclaren-720s-gt3-evo` - gt-style
- `mercedes-amg-gt3` - gt-style
- `mercedes-amg-gt3-evo` - gt-style
- `mercedes-amg-gt4` - gt-style
- `porsche-911-rsr-gte` - gt-style
- `porsche-992-gt3-r` - gt-style
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
- `alpine-a424` - gt-style
- `aston-martin-valkyrie-hypercar` - gt-style
- `aston-martin-vantage-gt4-evo` - gt-style
- `aston-martin-vantage-gte` - gt-style
- `audi-r8-lms-gt4` - gt-style
- `chevrolet-corvette-z06-gt3r` - gt-style
- `lamborghini-huracan-super-trofeo-evo2` - gt-style
- `lamborghini-sc63` - gt-style
- `ligier-js-p217` - gt-style
- `ligier-js-p320` - gt-style
- `ligier-js-p4` - gt-style
- `oreca-07` - gt-style
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
