# Assetto Corsa EVO coverage plan

Assetto Corsa EVO is the second simulator. It was chosen for a relatively small
car count, no mod ecosystem yet and no DLC, which makes it a clean test of the
sim-independence the schema claims rather than a test of mod identity at the same
time. Roster comparison is against AC EVO 0.8 and the AMS2-curated records.

The client recognises SimHub's game name `AssettoCorsaEvo` and canonicalises it
to `ac-evo`. Until one record names the simulator the plugin still reports the
game as not covered yet, which is true; it records car identities to the local
diagnostics log anyway, because otherwise there is no way to learn the identities
the first record needs. See `docs/verification-observations.md` for the pipeline
and `PRIVACY.md` for where drafts live.

## Overlaps worth driving

Every one of these already has a curated AMS2 record with `gearbox_type`
established, so a drive contributes a second `simulators[]` entry rather than a
new car.

| AC EVO car | Record | Match quality |
| --- | --- | --- |
| Lamborghini Huracán Super Trofeo EVO2 | `lamborghini-huracan-super-trofeo-evo2` | Exact |
| Audi R8 LMS GT3 Evo II | `audi-r8-lms-gt3-evo-ii` | Exact |
| Porsche 718 Cayman GT4 Clubsport MR | `porsche-cayman-gt4-clubsport-mr` | Exact if the MR variant is selected |
| Caterham Seven Academy Racer | `caterham-academy` | Probable; confirm the model-year specification before merging |

Kunos's current official roster lists all four families. The 0.3 release
introduced the Lamborghini, Cayman and Caterham; 0.7 names the Audi; the 0.4
update notes refer explicitly to the "Porsche GT4 Clubsport MR".

## Drive order

**First: the Lamborghini Huracán Super Trofeo EVO2.** The same EVO2 one-make race
car in both games, and the AMS2 record explicitly excludes the earlier Huracán LP
620-2 Super Trofeo with no predecessor alias attached, so it tests exact identity
matching rather than family matching. Its controls are straightforward six-speed
sequential paddles, every field is established, and it carries **no overrides** -
so anything that goes wrong is the pipeline rather than the car. It has been in
AC EVO since 0.3.

What that drive actually tests, in order: the plugin sees AC EVO at all; it logs
the car identity; `import-observation` accepts an `ac-evo` source id under the
naming convention; review; `promote-observation` finds the existing record and
calls `merge_simulator_entry` rather than creating a second one; the claim
pointers remap from `/simulators/0` to `/simulators/1`; the approval writes as
`ac-evo-approved-lamborghini-huracan-super-trofeo-evo2.json`.

**Second: the Caterham Academy.** It exercises the more interesting branch -
five-speed H-pattern, clutch start, lift on upshift, manual blipping - where the
Huracán exercises none of it. Confirm the precise Academy generation from AC EVO's
own car information before treating it as the same real-world specification; the
AMS2 record is a sealed Academy specification around a Ford Sigma 1.6.

The Cayman is a good third rather than a second: its record carries an override,
and an override belongs to the simulator that earned it. A second simulator's
entry does not inherit one, which is worth testing deliberately rather than as a
variable in an earlier drive.

## Name matches to avoid

These are not merge candidates. Each is a different specification wearing a name
the other game also uses, and attaching a second entry to one of these records
would fail open: the plugin would answer confidently with another car's controls.
Where AC EVO's car is genuinely a different real car, it wants a **new record**,
not a second entry on this one.

| AC EVO car | Curated record | Why they are different cars |
| --- | --- | --- |
| E30 M3 Sport Evo | `bmw-m3-sport-evo-group-a` | AC EVO's is the road homologation car; the record is the Group A racer |
| 190E Evo II | `mercedes-benz-190e-2-5-16-evo-ii-dtm` | AC EVO presents the road homologation car; the record is the DTM specification |
| BMW M4 GT3 EVO | the M4 GT3 record | AC EVO has the EVO; the record is the original |
| 911 GT3 Cup (992) | the Cup 4.0 record | Different generations: 992 against 991.2 |
| Audi R8 LMS GT4 Evo | the earlier GT4 record | AC EVO has the Evo; the record is the earlier car |

The first two carry a specific hazard. Both records had their gearbox
construction established from **Group A homologation forms**, which describe the
racing specification. That evidence does not transfer to the road cars AC EVO
models, and a merge would silently attach it to them. The general rule is in
`docs/data-model.md` under "A shared name is not a shared car".

## Open

- AC EVO's aero-package spelling, if it has one. A record declaring
  `aero_packages` for `ac-evo` currently fails validation with a clear message,
  which is the intended gate: the suffix table has no `ac-evo` entry. When the
  spelling is known it goes in both `AERO_SUFFIXES` and C#
  `BuildAeroSuffixes`, which are pinned against each other and against the
  schema enum by tests.
- Whether AC EVO reports a class token comparable to AMS2's, which
  `promote_observation.resolve_class` expects.
- `ac-rally` is in the simulator enum and SimHub's name for it appears to be
  `AssettoCorsaRally`, but the client does not canonicalise it and nothing has
  been driven in it.
