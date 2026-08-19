# Gearbox construction research

**Status: research notes for review. Nothing here has been written into
`data/v1`, and nothing should be until a reviewer accepts the basis.** Imported
candidates stay outside the curated data until reviewed, and a value that turns
on inference should not be promoted by whoever inferred it.

## Why this field

`gearbox_type` is unestablished in 43 records, more than any other field: open
in 19 deviations, deciding 11 of the 14 undetermined, and holding back the
dogleg and four-speed archetypes behind 13 of the 14 that match no archetype.

It travels with `downshift.manual_blip`, because dog rings need the driver to
match revs where a synchromesh leaves the blip optional. That coupling is a
reason to research the field, **not** a licence to derive one value from the
other. Establishing the construction is evidence; reading the blip off it is
inference. Each still needs its own basis.

## Correcting the earlier framing

This was previously described as desk research rather than seat time. That was
too optimistic, and the correction matters more than the optimism did.

Five well-documented cars were searched - BMW M1 Procar, Porsche 962C, Porsche
911 RSR 1974, BMW M3 Group A, Mercedes-Benz 190E Evo II DTM. Every search
returned gear count, manufacturer and often the gate immediately. **Not one
returned whether the gears engage through synchronisers or dog rings.**
Specification pages, marque histories and auction listings all stop in the same
place.

The fact is reachable, but not from anything written about the *car*. What
reached it was a governing body's technical regulations and a specialist writing
about the *gearbox*. That is a narrower and slower class of source than a general
search, and it is where the remaining work has to go.

## How the 43 actually divide

| Group | Records | Status |
| --- | --- | --- |
| Copa Truck | 5 | **Settled.** The regulation leaves the gearbox free, and is now cited |
| Formula Vee | 2 | **Taken.** synchromesh at medium, reversing an earlier call |
| Porsche 911 RSR 1974 | 1 | **Taken.** synchromesh at medium confidence |
| Reiza's fictionalised cars | 17 | **Retired.** No source can exist for these |
| Other real cars | 18 | Open, and needing homologation-class sources |

The 17 is the number that should change how this queue is read: nearly two in
five of these records are not waiting on a source anyone could find.

## Settled: Copa Truck

`iveco-stralis`, `man-tgx`, `mercedes-benz-actros`, `volkswagen-constellation`,
`vulkan-truck`.

CBA 2025 Copa Truck technical regulations, Article 15 (CÂMBIO):

> **15.1** - O câmbio terá que estar acoplado diretamente ao motor. **O câmbio é
> livre para todas as marcas.**
>
> **a)** Proibida a utilização de câmbio automático ou automatizado, sendo
> obrigatório o uso de alavanca de câmbio, para troca de marcha manual em padrão H.
>
> **b)** Proibido para todas as marcas, qualquer alteração no sistema de troca de
> marchas, que não seja através de varão ou cabo de aço (troca mecânica).

Two findings, pointing opposite ways.

**The gate is confirmed by regulation.** A lever and a manual H-pattern change
are mandatory, automatic and automated boxes are prohibited, and the linkage must
be mechanical. That corroborates `shift_actuation: h-pattern` and
`shift_pattern: standard-h` on all five from a primary source, where they
currently rest on the drive alone.

**The gearbox is explicitly free.** "O câmbio é livre para todas as marcas"
leaves the unit to the team, and *sincronizado* and *garras* appear nowhere in
the document. There is no single construction to curate.

**Decided: `gearbox_type` stays unknown on all five, with the regulation cited as
the reason.** Registered as `cba.copa-truck-2025.technical-regulations`
(`homologation`, retrieved 2026-08-18) and added to the claim that covers the gear
count, actuation, pattern and gearbox type on each record.

This is the first place in the dataset where `unknown` is a documented conclusion
rather than outstanding work, and the records say so: the deviation basis now
reads that no further reading of the regulations will close it.

It is also an evidence upgrade rather than only a citation. The records already
asserted that "the regulations mandate a mechanically operated H-pattern manual
gearbox but leave its design free" - but the claim rested on a Wikipedia article
and a community AMS2 wiki restating the regulations. It now rests on Article 15.

## Taken: Formula Vee

`formula-vee-fin` (four-speed), `formula-vee-gen2` (five-speed).

**Correction to an earlier draft of this note.** These were described as a new
find. They are not: `fasp.formula-vee-2025-regulations` was already registered
and is already cited by `formula-vee-gen2`, which still carries
`gearbox_type: unknown`. Someone has read this source and left the field open,
so what follows argues against a standing decision rather than filling a gap, and
should be read that way.

What is new here is narrower: Article 7.1 quoted directly, the four-speed variant
identified alongside the five-speed, the observation that the two permitted
transmissions match the two records' gear counts, and the independent
corroboration from other national Formula Vee regulations. `formula-vee-fin` does
not currently cite the FASP source at all.

FASP 2025 Fórmula Vee technical regulations, Article 7 (TRANSMISSÕES):

> **7.1** São permitidas duas transmissões: **Quatro Marchas originárias de
> Fusca/Kombi e outros VW refrigerados a Ar. Cinco Marchas originárias de Gol
> Longitudinal.** As CAIXAS DE CÂMBIO de Quatro e Cinco Marchas serão fornecidas
> pela PROMOTORA e/ou fornecedores indicados e serão **LACRADAS**.

And the two chassis, at 2.1.2 and 2.1.3: the Naja 01 runs the four-speed
air-cooled VW box, the Naja 01-D the five-speed longitudinal Gol box. **Those are
the two records' gear counts exactly**, which is good corroboration that the
records model these two variants.

**Recorded: `synchromesh` for both at `medium`**, and both records say the field
was contested rather than merely unfilled, because a reader who finds a value
here should know it had been left open once with the same source cited.

**The two are not equally evidenced, and their bases differ accordingly.** The
Irish Formula Vee regulations were fetched and read rather than taken from a
search summary, and Section 3 says outright: "A fully synchromesh VW Type 1 or 3
gearbox must be used. All four forward gears as well as reverse gear must be
present and in operative condition", with the internals "assembled as originally
intended by the manufacturer".

That covers the **air-cooled four-speed**, which is `formula-vee-fin`, and covers
it well. It says nothing about the **Brazilian five-speed Gol** unit in
`formula-vee-gen2`, which is a different production gearbox in a different
championship. That one rests on the Brazilian regulation naming the unit and
sealing it, plus the Gol being a production road car. Both are medium; only one
has a regulation using the word.

Falsifiable by a Brazilian clause or a promoter's specification showing the
sealed boxes carry dog engagement.

**The blip was left exactly where it was, and it does not agree.** Both records
carry `manual_blip: required` from a guided drive at `verified` confidence - the
simulator rejected a clutchless downshift until the driver blipped. A synchromesh
does not need a blip to engage, so a required blip sits oddly against the
construction now recorded. That tension is left standing as each record's
declared deviation rather than resolved, because the construction is a
medium-confidence claim and cannot overrule a drive. If it is ever resolved the
likely shape is a simulator override, not a change to the real car's value.

**The tension is confined to these two.** A sweep of all 242 records for a
construction that disagrees with its blip found nothing else. Two Carrera Cup
cars looked like the inverse case - dog rings with no blip demanded - until their
`automatic_blip: yes` explained it: the gearbox needs rev-matching and the car
supplies it, which is consistent rather than contradictory. Seven sequential cars
need no blip while nothing blips for them, and each says in its own notes that
the downshift was accepted with no pedal input; those are the records the 0.3.79
blip recheck corrected, and they are observed rather than inconsistent. A test
now requires any record whose construction disagrees with its blip to say so, so
the combination cannot spread silently.

Sources: `https://fasp.faspnet.com.br/wp-content/uploads/2025/02/Formula-Vee-2025-tecnico.pdf`
(FASP, type `homologation`), `https://fvee.com.br/index.php/a-categoria/os-carros`
(category promoter), and for the corroboration
`https://www.iccr.ie/wp-content/uploads/2021/06/2021-Tech-Regs-Formula-Vee.pdf`.

## Taken: Porsche 911 RSR 1974

The Type 915 is described by a marque specialist as using "Porsche's own
synchromesh design", distinguished from the later G50's Borg-Warner synchro. The
RSR ran the 915/08, described elsewhere as a magnesium-cased race-type 915 with
the dogleg first the family is known for.

**Recorded: `synchromesh` at `medium`.** The bundled claim that held the gear
count, actuation, pattern and construction together at `high` was split, because
the construction could not ride at that confidence. It now has a claim of its own
whose basis says the last step is inferred from the family rather than stated by
a source - which is what keeps it honest and what the confidence test keys on.

**The blip was not taken with it.** `downshift.manual_blip` stays unknown and is
now the record's declared deviation from the synchromesh archetype. A synchromesh
usually leaves a blip optional, and following that through would derive one
unestablished field from another that is itself only at medium.

**A trap was found and closed on the way.** The record's gate had no evidence of
its own - the claim's basis established H-pattern actuation, not the gate - and
one secondary source describes the 915 as having a dogleg first gear. It does
not. The 915 *replaced* the 901's dogleg with a conventional H, first up and
left, announced by Porsche in 1972. Had anyone acted on that description the card
would have sent drivers to the wrong side of the gate for first. The correcting
source is registered and cited, so the record's `standard-h` is now evidenced
rather than defaulted.

`first_gear_position` was deliberately not added, though the same source
supports `up-left`. The archetype carries no value there, so recording one would
manufacture a second deviation, and the card already renders a standard gate as
first up and left. Worth taking only if the archetype gains the field too.

Sources: `https://www.paul-stephens.com/magazine/type-915-gearbox-vs-g50-gearbox/`,
`https://www.stuttcars.com/porsche-911-carrera-rsr-3-0-1974-1975-specifications-performance/`

## Not proposed: BMW M3 Group A, and why

The road and homologation car used the Getrag 265 dogleg five-speed, a
synchromesh production gearbox. Group A cars commonly ran dog-engaged
straight-cut gearkits fitted into that same case; several vendors sell exactly
that and describe it as a Group A homologated fitment.

That establishes period practice. It does not establish what this car ran, and
the sources are commercial listings.

**Recommendation: leave unknown.** A medium dogbox claim here would rest on "cars
like this often had one", which is the shape of reasoning this dataset exists to
refuse. The same applies to `mercedes-benz-190e-2-5-16-evo-ii-dtm` and the rest
of the Group A and DTM entries. What would settle it is the FIA Group A
homologation papers, which list the permitted transmission variants.

## Retired: the fictionalised cars

`formula-classic-gen1` through `gen4` (9), `formula-retro-*` (3),
`formula-vintage-*` (4), `formula-dirt` (1).

These are Reiza's own cars, standing in for an era rather than representing a
chassis. There is no manufacturer, no homologation sheet and no registry, so no
real-world source could establish their construction, and any value assigned
would be reasoning from the era the car evokes rather than evidence about the
car.

**Done: all 17 are retired from the queue**, each stating in its archetype basis
that the gap is permanent. Nine were `undetermined` and eight `deviates`; the
classifications are unchanged and so is every value. The only thing that changed
is that the records no longer promise a reviewed source will eventually settle
them, which both bases previously did.

**Being fictionalised is not on its own what makes the field unreachable**, and
the first version of this note got that wrong. Three cars in these same families
- `formula-classic-gen3-model2`, `gen4-model1` and `gen4-model2` - carry an
established `semi-automatic` gearbox, because they are paddle-shift and the
mechanism is visible from the cockpit. What no drive can see and no chassis
exists to research is whether an H-pattern box engages through synchronisers or
dog rings, and every one of the retired 17 is H-pattern. A test pins that
distinction so a later pass cannot fill the field in from the era.

`formula-junior` is deliberately not retired. Formula Junior was a real
international category with a technical formula, so it stays in the researchable
group even though it has not been researched yet.

## Corroborated, but no further

Searched, and the record's existing values were confirmed without reaching
construction. Listed so the search is not repeated.

| Record | Corroborated | Still open |
| --- | --- | --- |
| `bmw-m1-procar` | ZF five-speed, dogleg, 1st down and left | construction |
| `porsche-962c` | five-speed manual | construction |
| `mercedes-benz-190e-2-5-16-evo-ii-dtm` | Group A five-speed dogleg | construction |

## What to decide next

1. ~~Copa Truck.~~ Decided: unknown, with Article 15 cited.
2. ~~Formula Vee.~~ Taken: synchromesh at medium on both, knowingly reversing the
   earlier call. The blip tension it exposes is the thing left to look at.
3. ~~The 911 RSR.~~ Taken: synchromesh at medium.
4. ~~Retire the 17 fictionalised records.~~ Done.
5. For the remaining real cars, look for homologation papers and period workshop
   documentation. Car histories have been tried and do not reach it.

The live queue is now 18 records: 17 real cars plus `formula-junior`. Of the
original 43, three are answered - the 911 RSR and the two Formula Vee cars - and
22 are closed with a written reason, 5 by the Copa Truck regulation and 17 by
retirement.
