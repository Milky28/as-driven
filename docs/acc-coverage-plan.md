# Assetto Corsa Competizione coverage plan

Assetto Corsa Competizione is the third official-content simulator used for
cross-simulator development. It is a strong comparison target because its
roster overlaps AMS2 heavily, exposes a stable internal car id through SimHub,
and contains several generations of the same GT3 nameplate. It is not a target
for indiscriminate roster completion: another modern paddle-shift GT record is
useful only when it audits an existing claim, establishes a distinct mechanism,
or prevents an identity mistake.

ACC remains development coverage outside the certified early-access target.
The certified target is still SimHub 9.11.22 and AMS2 1.6.9.91 on Windows.

## Roster baseline

The comparison uses KUNOS's current [ACC car roster][acc-roster]. The [free 2025
season update][acc-2025] added liveries and drivers but no cars, so it does not
change the identity set described here. The relevant official package lists are the
[GT4 Pack][gt4-pack], [2020 GT World Challenge Pack][gtwc-2020],
[Challengers Pack][challengers], and [2023 GT World Challenge Pack][gtwc-2023].
The [McLaren 720S GT3 EVO][mclaren-evo] and [Ford Mustang GT3][mustang] arrived
as separate free updates.

As reviewed through 2026-08-23, 18 exact ACC identities are curated. The ranked
ten and six-car exact-overlap follow-up were captured with SimHub 9.12.1 and ACC
Steam build 21257365; that is development evidence and does not change the
certified SimHub 9.11.22 target.

| ACC car | Record | Other reviewed simulators | Status |
| --- | --- | --- | --- |
| Audi R8 LMS GT3 Evo II (2022) | `audi-r8-lms-gt3-evo-ii` | AMS2, AC EVO, AC | Reviewed and promoted |
| Lamborghini Huracan ST EVO2 (2021) | `lamborghini-huracan-super-trofeo-evo2` | AMS2, AC EVO | Reviewed and promoted |
| BMW M4 GT3 (2021 telemetry label) | `bmw-m4-gt3` | AMS2 | Reviewed and promoted |
| Ginetta G55 GT4 (2012) | `ginetta-g55-gt4` | AMS2 | Reviewed and promoted |
| Chevrolet Camaro GT4 R (2017) | `chevrolet-camaro-gt4-r` | AMS2 | Reviewed and promoted |
| Porsche 992 GT3 R (2023) | `porsche-992-gt3-r` | AMS2 | Reviewed and promoted |
| Mercedes AMG GT3 Evo (2020 telemetry label) | `mercedes-amg-gt3-evo` | AMS2 | Reviewed and promoted |
| Nissan GT R Nismo GT3 (2018) | `nissan-gt-r-nismo-gt3` | AMS2 | Reviewed and promoted |
| BMW M6 GT3 (2017 telemetry label) | `bmw-m6-gt3` | AMS2 | Reviewed and promoted |
| Porsche 911 II GT3 R (2019) | `porsche-911-gt3-r` | AMS2 | Reviewed and promoted |
| McLaren 720S GT3 Evo (2023) | `mclaren-720s-gt3-evo` | AMS2 | Reviewed and promoted |
| Lamborghini Huracan GT3 Evo2 (2023) | `lamborghini-huracan-gt3-evo2` | AMS2 | Reviewed and promoted |
| Audi R8 LMS GT4 (2016 telemetry label) | `audi-r8-lms-gt4` | AMS2 | Reviewed and promoted |
| BMW M4 GT4 (2018) | `bmw-m4-gt4` | AMS2 | Reviewed and promoted |
| McLaren 570S GT4 (2016 telemetry label) | `mclaren-570s-gt4` | AMS2 | Reviewed and promoted |
| McLaren 720S GT3 (2019) | `mclaren-720s-gt3` | AMS2 | Reviewed and promoted |
| Mercedes AMG GT3 (2015 telemetry label) | `mercedes-amg-gt3` | AMS2 | Reviewed and promoted |
| Mercedes AMG GT4 (2016 telemetry label) | `mercedes-amg-gt4` | AMS2 | Reviewed and promoted |

The Audi is the first record reviewed in four simulators. The Super Trofeo is
the first ACC drive after it and agrees with the established controls wherever
ACC exposes enough telemetry to decide.

## What an ACC drive can and cannot establish

An ACC contribution records both the telemetry display name and stable internal
car id. Identity review uses both; neither a similar visible name nor a shared
class is enough to merge a record. The draft also pins the exact Steam content
build from `appmanifest_805550.acf`.

ACC does not expose engine torque through SimHub. A guided drive can establish
that a full-throttle upshift is accepted, but it cannot directly establish the
power interruption used to accept it. `shift_cut` therefore remains `unknown`
for ACC unless a future attributable channel or other direct evidence settles
it. A brief throttle dip may instead be traction control, driver input, or
telemetry filtering and is not cut evidence. The importer degrades that answer
from older ACC drafts to `unknown`; repeating the maneuver does not close the
gap.

A simulator drive establishes simulator behavior, not the real car. Where the
authentic record has `throttle_lift: unknown`, an ACC result must remain scoped
to the ACC entry through an override; it must not silently turn the authentic
unknown into `not-required`. The same boundary applies to clutch, blip, wheel,
display, and shift-light disagreements.

The clutch channel observed in the first two ACC drives already read fully
engaged while the physical pedal was untouched. It is useful as simulator state,
not as proof that the driver pressed a pedal. Move-off conclusions must continue
to come from the guided physical-clutch maneuver and its assist-state record.

## Completed ranked drive order

These ten drives were completed and promoted on 2026-08-23. They remain ordered
by the claim they were chosen to challenge, not by convenience.

| Rank | ACC selection | Curated record | Why this is worth a drive |
| ---: | --- | --- | --- |
| 1 | BMW M4 GT3 (2022) | `bmw-m4-gt3` | Free content, exact year, and a clean next test of the pipeline. AMS2 leaves authentic throttle-lift use open while directly establishing the no-clutch-pedal start and automatic cut/blip behavior. Preserve that authentic gap and record ACC's accepted maneuver separately. |
| 2 | Ginetta G55 GT4 | `ginetta-g55-gt4` | First ACC GT4 and a high-value outlier: the curated car requires the clutch to pull away and still has unknown throttle-lift use. It also tests a conventional GT4 wheel with integrated display and shift lights rather than another current GT3 rim. Requires the GT4 Pack. |
| 3 | Chevrolet Camaro GT4.R | `chevrolet-camaro-gt4-r` | A second clutch-required GT4 start, but with flat upshift already established in AMS2. Agreement would strengthen the unusual start pattern; disagreement would be immediately driver-relevant. Requires the GT4 Pack. |
| 4 | Porsche 911 (992) GT3 R (2023) | `porsche-992-gt3-r` | Exact modern generation with authentic throttle-lift use still open. The explicit `992` and `GT3 R` tokens make this a useful positive control for the identity rules that reject the nearby Cup car. Requires the 2023 GT World Challenge Pack. |
| 5 | Mercedes-AMG GT3 (2020) | `mercedes-amg-gt3-evo` | ACC's visible selection omits “Evo,” while SimHub captures `Mercedes AMG GT3 Evo 2020` and internal id `mercedes_amg_gt3_evo`; preserve that exact telemetry identity while mapping it to the real-world 2020 Evo record. Tests the update separately from the original AMG GT3. Authentic throttle-lift use is open, and the real-world transmission source currently describes the GT3 family rather than the Evo update specifically. Requires the 2020 GT World Challenge Pack. |
| 6 | Nissan GT-R Nismo GT3 (2018) | `nissan-gt-r-nismo-gt3` | ACC also contains a 2015 variant. Selecting the 2018 car and capturing its internal id tests whether the exact identity contract keeps those generations apart; throttle-lift use is also open. |
| 7 | BMW M6 GT3 | `bmw-m6-gt3` | Another base-game exact overlap with open throttle-lift use. Its recorded wheel shift lights distinguish it from most of the current GT3 batch and give the cockpit review independent value. |
| 8 | Porsche 991II GT3 R (2019) | `porsche-911-gt3-r` | ACC also contains the earlier 2018 991 GT3 R. Only the `991II` 2019 selection belongs on this record. It is a deliberate identity test and carries an open throttle-lift claim. |
| 9 | McLaren 720S GT3 EVO (2023) | `mclaren-720s-gt3-evo` | A free exact overlap whose established controls are already strong. It is a regression/control drive after the higher-risk entries, and must remain distinct from the 2019 non-Evo 720S. |
| 10 | Lamborghini Huracan GT3 EVO2 (2023) | `lamborghini-huracan-gt3-evo2` | Compares the GT3 EVO2 with the already-driven Super Trofeo EVO2 on the same platform. The value is proving that the shared manufacturer and EVO2 suffix do not collapse two different race cars. Requires the 2023 GT World Challenge Pack. |

## Completed exact-overlap follow-up

These six lower-risk exact overlaps were driven and promoted after the ranked
queue. The telemetry suffix remains an exact simulator identity and does not
silently replace a manufacturer-sourced debut or specification year.

| ACC car | Record | Finding |
| --- | --- | --- |
| McLaren 720S GT3 (2019) | `mclaren-720s-gt3` | The non-Evo internal id stayed separate from the 2023 Evo; ACC requires a launch clutch. |
| Mercedes-AMG GT3 (original) | `mercedes-amg-gt3` | The original internal id stayed separate from the 2020 Evo; ACC requires a launch clutch and accepts a no-lift upshift. |
| Audi R8 LMS GT4 | `audi-r8-lms-gt4` | ACC models a closed rim with no lights; AMS2 models an open top and leaves the lights unestablished. |
| BMW M4 GT4 | `bmw-m4-gt4` | The 2018 internal identity maps to the F82 seven-speed dual-clutch car and accepts a no-lift upshift. |
| McLaren 570S GT4 | `mclaren-570s-gt4` | ACC accepts a no-lift upshift; the authentic lift claim remains open. |
| Mercedes-AMG GT4 | `mercedes-amg-gt4` | ACC requires a launch clutch and accepts a no-lift upshift; both answers remain simulator-scoped. |

The ACC Audi R8 LMS (2015) is not in this table yet. The existing
`audi-r8-lms-gt3` record deliberately says only "base model" and does not pin a
year in its identity. Resolve whether that record is exactly the 2015 ACC car
before driving or merging it. Treating "not Evo" as sufficient identity would
repeat the generation error this project is designed to prevent.

## Identity traps and non-matches

These names are close enough to invite a wrong merge. Stop after identity
capture and research them before promotion when any token is missing or differs.

| ACC car | Nearby curated record | Decision |
| --- | --- | --- |
| Alpine A110 GT4 | `alpine-a110-gt4-evo` | Not the same specification. ACC lists the original GT4; AMS2 curates the later Evo. |
| Aston Martin Vantage GT4 | `aston-martin-vantage-gt4-evo` | Not the same specification. ACC lists the 2019 V8 GT4; AMS2 curates the 2024 Evo. |
| Aston Martin V8 Vantage GT3 (2019) | `aston-martin-vantage-gt3-evo` | Not the same specification. The curated record is the 2024 Evo. |
| Audi R8 LMS Evo (2019) | `audi-r8-lms-gt3-evo-ii` | Not the same evolution. The curated record is the 2022 Evo II. |
| Lamborghini Huracan GT3 / GT3 Evo | `lamborghini-huracan-gt3-evo2` | Neither predecessor is the 2023 EVO2. |
| Porsche 992 GT3 Cup (2021) | `porsche-992-gt3-r` | Cup and GT3 R are different cars even though both are 992-generation racers. It also must not join the AMS2 991.2 Cup record. |
| Porsche 718 Cayman GT4 Clubsport | `porsche-718-cayman-gt4-clubsport` | Possible 2019 982 match, but the ACC roster omits the MR token that the existing AC EVO record carries. Confirm the modeled variant before merging. Never attach it to the 2016 981 record. |
| Nissan GT-R Nismo GT3 (2015) | `nissan-gt-r-nismo-gt3` | The curated record is the 2018 car. ACC contains both. |
| Porsche 991 GT3 R (2018) | `porsche-911-gt3-r` | The curated record is the 2019 991.2 car. ACC contains both. |

Two tempting AMS2 records have no current ACC counterpart: the Chevrolet
Corvette Z06 GT3.R and Aston Martin Vantage GT3 Evo. ACC's 2024 and 2025 season
updates added entries, liveries and drivers, not those car models. The Ford
Mustang GT3 is present in ACC as free content but has no curated As Driven
record, so it is a possible new record rather than an overlap.

The modern GT2 Pack has no exact curated overlap today. Defer its six new
records until either a mechanism differs materially from the existing paddle
archetypes or a contributor needs one. Coverage count alone is not a reason to
turn As Driven into an ACC catalogue.

## Contribution and review rules

1. Confirm automatic clutch, automatic shifting, and throttle-blip assist state
   before the guided run. Reconfirm when any setting changes.
2. Capture both display name and internal car id. Do not pre-register guessed
   ids from a roster page.
3. Complete the cockpit review independently for every model and evolution;
   flattening alone does not make a rim `gt-formula`.
4. Leave automatic cut unknown. The present ACC/SimHub telemetry boundary does
   not measure it directly.
5. Stage and review each identity before promoting a nearby generation. A batch
   may contain several cars only after every mapping is independently settled.
6. Register the already-observed ACC `GT3` and `ST` class tokens before the next
   promotion. Add `GT4` on its first observation, rather than making every later
   reviewer restate the same class name.
7. Preserve authentic unknowns. Record an ACC-only answer as a simulator
   override unless a registered real-world source independently closes the
   authentic claim.

## Exit criteria

The first ACC phase is complete when:

- six exact ACC overlaps are reviewed, including at least one GT4;
- the Ginetta or Camaro has tested the clutch-required GT4 start pattern;
- at least one generation trap has been exercised with the exact internal id;
- every promoted entry carries an exact Steam build and check date; and
- the website can present the resulting cross-simulator agreements and
  disagreements without requiring a reader to infer them from prose.

At that point, stop prioritising additional ACC cars by roster order. Build the
comparison-first website mode, then use its visible evidence gaps to choose the
next drives.

**Completed 2026-08-23:** the site now provides `All`, `Multi-sim`, and
`Disagreements` modes. Disagreements require two conflicting established values;
an established value beside `unknown` remains an evidence gap. Expanded rows
list each simulator's answer separately and keep real-car departures under the
distinct `differs from car` label.

[acc-roster]: https://assettocorsa.gg/assetto-corsa-competizione/
[gt4-pack]: https://assettocorsa.gg/the-gt4-pack-dlc/
[gtwc-2020]: https://assettocorsa.gg/2020-gt-world-challenge-pack/
[challengers]: https://assettocorsa.gg/challengers-pack-dlc/
[gtwc-2023]: https://assettocorsa.gg/2023-gt-world-challenge-pack/
[mclaren-evo]: https://assettocorsa.gg/720s-gt3-evo-mclaren/
[mustang]: https://assettocorsa.gg/ford-mustang-gt3-race-car/
[acc-2025]: https://assettocorsa.gg/free-assetto-corsa-competizione-2025-season-update/
