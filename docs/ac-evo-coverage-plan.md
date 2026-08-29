# Assetto Corsa EVO coverage plan

Assetto Corsa EVO is the second simulator. It was chosen for a relatively small
car count, no mod ecosystem yet and no DLC, which makes it a clean test of the
sim-independence the schema claims rather than a test of mod identity at the same
time. Roster comparison is against AC EVO 0.8 and the AMS2-curated records.

The client recognises SimHub's game name `AssettoCorsaEvo` and canonicalises it
to `ac-evo`. Three existing real-car records now carry reviewed AC EVO entries and
one car is curated from AC EVO alone,
so the client recognizes those exact identities while every other AC EVO car
still fails closed and is recorded in the local diagnostics log. AC EVO remains
development coverage rather than part of the tested target. See
`docs/verification-observations.md` for the pipeline and `PRIVACY.md` for where
drafts live.

## Overlaps worth driving

Every one of these already has a curated AMS2 record, so a drive contributes a
second `simulators[]` entry rather than a new car. The Porsche was listed here
and does not belong: the two games model different generations, and it is in the
traps table below.

| AC EVO car | Record | Status |
| --- | --- | --- |
| Lamborghini Huracán Super Trofeo EVO2 | `lamborghini-huracan-super-trofeo-evo2` | Reviewed and promoted |
| Audi R8 LMS GT3 Evo II | `audi-r8-lms-gt3-evo-ii` | Reviewed and promoted |
| Caterham Seven Academy Racer | `caterham-academy` | Reviewed and promoted for the 2014–2025 five-speed specification |

Kunos's current official roster lists all four families. The 0.3 release
introduced the Lamborghini, Cayman and Caterham; 0.7 names the Audi; the 0.4
update notes refer explicitly to the "Porsche GT4 Clubsport MR".

## Drive order

The Lamborghini completed the end-to-end pipeline first: AC EVO recognition,
local identity capture, `ac-evo` observation import, merge into an existing
record, claim-pointer remapping, and a simulator-specific approval. The Caterham
then proved that a shared name needs a bounded real-world specification; its AC
EVO entry belongs to the same 2014–2025 five-speed package, not to the six-speed
formula introduced for 2026. The Audi became the first second-simulator drive to
derive its own throttle-lift and manual-blip technique from the two-stage tests.

The Porsche was expected to be the fourth merge and became the first new record
instead. Its AMS2 entry carried a standing-start clutch override, which is why it
looked interesting; what it actually exposed was that AMS2 models the 2016
Clubsport of the 981 generation while AC EVO models the 2019 718 of the 982.
`porsche-718-cayman-gt4-clubsport` is that later car, curated from AC EVO alone.

**Next: no exact overlap remains.** Further AC EVO drives are either new records
or belong to the traps below, so the ranking that governed the first four -
whichever tests the pipeline most cleanly - has done its work. Rank what comes
next by which curated claim is weakest instead: a second entry on an
already-curated car shows a driver nothing new, and its whole value is
falsification. Medium-confidence automatic-cut observations and values resting on
a single drive with no real-world source are the ones worth aiming at.

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
| 718 Cayman GT4 Clubsport | `porsche-cayman-gt4-clubsport-mr` | AC EVO has the 2019 718 of the 982 generation; that record is the 2016 Clubsport of the 981 |

The first two carry a specific hazard. Both records had their gearbox
construction established from **Group A homologation forms**, which describe the
racing specification. That evidence does not transfer to the road cars AC EVO
models, and a merge would silently attach it to them. The general rule is in
`docs/data-model.md` under "A shared name is not a shared car".

The Porsche is the one that got as far as a promotion attempt, and it is the most
useful entry in this table because nobody predicted it. Both games call the car a
Cayman GT4 Clubsport MR and both are right; the generations differ, and the
telemetry said so in the one token nobody read - AMS2 omits the "718" that marks
the 982. The merge refused on a steering-rim disagreement, which turned out to be
a symptom rather than the fault: a 981 cockpit and a 982 cockpit, correctly
modelled by each game. Chasing the rim found the wrong car underneath, and the
spreadsheet author's own correction of his year confirmed it.

Two things follow for anything driven from here. A near-match in a name is worth
reading character by character, because the token that differs is often the
generation. And a cockpit disagreement between two games is worth taking
seriously as evidence about identity, not just about a rim.

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
  been driven in it. It is a *reserved* id: enums only, no client wiring. A
  test names it as such, so the gap is a stated decision rather than an
  oversight. See `docs/registering-a-simulator.md` for what promoting it to a
  live id involves.
