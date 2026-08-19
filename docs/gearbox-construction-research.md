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

The initial car-level source pass covered BMW M1 Procar, Porsche 962C, Porsche
911 RSR 1974, BMW M3 Group A, and Mercedes-Benz 190E Evo II DTM. It returned
gear count, manufacturer and often the gate immediately, but no specification
page, marque history or auction listing stated whether the gears engage through
synchronisers or dog rings. Those sources all stop in the same place.

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

**Resolved: the blip moved to the simulator layer.** The real car's blip is now
`optional`, which is what a synchromesh leaves it, and AMS2's demand is a sourced
override. The client builds its card from the effective controls, so a driver in
AMS2 is still told to blip; the record simply stopped claiming the real car needs
it. Both records now match their synchromesh archetype exactly rather than
deviating, which is the tell that the value was in the wrong layer rather than
wrong.

The approvals were amended to match, following the pattern the 98T and the Cayman
already set: `approved_controls` records the real car's value and
`confidence_notes` explains the simulator difference. The note says the blip was
approved as required from the drive and revised when the construction was
established, so the amendment is legible rather than silent.

What follows is the reasoning as it stood before that, kept because it is why the
override is shaped this way.

**The blip was left where the drive put it at first, and it did not agree.** Both records
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

The FIA form now supplies the missing construction detail for several permitted
M3 gearboxes, but not the identity of the gearbox used by the simulated car.

- The base Getrag five-speed marks all five forward gears as `synchro`.
- 12/08 VO, valid 1 July 1988, is a six-speed whose `synchro` column is blank
  (a dash) for every forward gear, reverse and the constant ratio.
- 24/11 VO, valid 1 April 1989, is a six-speed that marks all six forward gears
  as `synchro`; it is limited to the named 04/01 ET and 14/01 ES evolutions.
- 38/20 VO, valid 1 November 1991, identifies a six-speed **Hollinger** box but
  does not state synchroniser or dog engagement.

The non-synchronised 12/08 VO is material evidence, but it is not a statement of
dog engagement. An unsynchronised gearbox must not be promoted to `dogbox` by
assumption. Nor can the current record select one homologated option from the
form without evidence tying that option to the particular car represented in the
simulator.

**Recommendation: leave `gearbox_type` unknown.** The same conclusion applies to
`mercedes-benz-190e-2-5-16-evo-ii-dtm`: the form establishes permitted
synchromesh alternatives, not the DTM car's installed gearbox.

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
| `mercedes-benz-190e-2-5-16-evo-ii-dtm` | FIA form lists synchronised five- and six-speed alternatives, including a Prodrive six-speed | exact fitted construction |

## What to decide next

1. ~~Copa Truck.~~ Decided: unknown, with Article 15 cited.
2. ~~Formula Vee.~~ Taken: synchromesh at medium on both, knowingly reversing the
   earlier call. The blip tension it exposes is the thing left to look at.
3. ~~The 911 RSR.~~ Taken: synchromesh at medium.
4. ~~Retire the 17 fictionalised records.~~ Done.
5. For the remaining real cars, look for homologation papers and period workshop
   documentation. Car histories have been tried and do not reach it. What that
   search found is below.

The live queue is now 18 records: 17 real cars plus `formula-junior`. Of the
original 43, three are answered - the 911 RSR and the two Formula Vee cars - and
22 are closed with a written reason, 5 by the Copa Truck regulation and 17 by
retirement.


## The homologation papers: read, with a curation limit

The FIA Historic Database at `historicdb.fia.com` is the archive, and this
project already cites six of its forms. Two of the queue's cars have theirs:

| Car | Form | URL |
| --- | --- | --- |
| BMW M3 Group A | 5327, Group A, 2 March 1987 | `https://historicdb.fia.com/sites/default/files/car_attachment/1662735601/homologation_form_number_5327_group_a.pdf` |
| Mercedes-Benz 190E | 5269, Group A, from 2 May 1985 | `https://historicdb.fia.com/sites/default/files/car_attachment/1601062201/homologation_form_number_5269_group_a.pdf` |

Both scans were rendered and read on 2026-08-19. The M3 form has 131 pages and
the 190E form 173. The direct PDF links remain live; the FIA HTML pages are not
needed to inspect the forms.

**BMW M3, A-5327.** Page 6 establishes the base five-speed manual Getrag as
synchromesh. It also lists an alternative five-speed, likewise synchronised.
Later extensions list the explicitly non-synchronised 12/08 VO six-speed, the
synchronised 24/11 VO six-speed, and the 38/20 VO six-speed by Hollinger name
only. This is strong evidence about the variants homologated, but it does not
identify the installed gearbox of the simulator car.

**Mercedes-Benz 190E, A-5269.** The form's 29/02 ES sport evolution, valid 1
June 1990, explicitly renames the model to **Mercedes-Benz 190 E 2.5-16/EVO II**.
The base page 6 Getrag five-speed and its alternative five-speed both mark every
forward gear `synchro`. The subsequently listed six-speeds are also explicit:

- 19/18 VO, valid 1 April 1988: six forward ratios, every gear marked
  `synchr.: ja/yes`.
- 24/21 VO, valid 1 July 1989 and restricted to 21/01 ES: six forward ratios,
  every gear marked `synchr.: ja/yes`.
- 33/27 VO, valid 1 April 1992: an additional **Prodrive** gearbox, a six-speed
  with every forward gear marked `synchro`.

This closes the earlier claim that the Evo II extension had not been located and
upgrades the 190E form from a future lead to a checked source. It still does not
show that the AMS2 DTM car ran one of these synchronised variants, so it is not a
basis for changing the curated `gearbox_type` from `unknown`.

## Group C cannot be settled this way at all

`sauber-mercedes-c9` and `porsche-962c` were listed as homologation candidates.
They are not, and no amount of searching will change it: **Group C was a pure
prototype class with no homologation requirement**, neither a minimum production
run nor the use of series components. Cars were built to the formula rather than
homologated, so no form exists for either and none ever will.

Those two need a different source class entirely - constructor or team
documentation, or a specialist on the specific gearbox, which is the route that
worked for the 911 RSR's Type 915.

Of the dogleg six, `bmw-m1-procar`, `formula-inter-mg15` and
`lamborghini-diablo-sv-r` have not been searched for papers yet. The M1 is the
most promising: it was homologated for Group 4, so a form should exist.
