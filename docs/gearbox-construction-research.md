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

## Settled: the M3 and the 190E are synchromesh

The five-speeds are unanimous, and the pages were read here as well as by Codex:
A-5327 p.6, A-5269 p.6 and A-5269 p.101 were inspected directly, and the two
tables not inspected match the same pattern verbatim.

Both records now carry `gearbox_type: synchromesh` at `medium`, cited to their own
form. The remaining step - from what a form permits to what a car was built with -
is inference, which is what keeps it at medium rather than higher.

**The gear count is what makes this answerable.** The M3's form does homologate a
gearbox of other construction: 12/08 VO, whose synchro column is blank throughout.
It is a six-speed, and both records are five-speeds. Restricted to five ratios
every option on both forms is marked synchronised, so nothing is being chosen
between - which is a different thing from picking the convenient option, and the
basis on each record says so.

**The forms also settled something nobody was looking for.** Section 603 f) of
each draws the gear-change gate - reverse above first, 1, 3 and 5 on the lower
plane - so the dogleg and first-down-left now rest on a primary source rather
than on the cockpit alone. That went to the existing claim, which was already at
high confidence and is now better supported.

### What it unlocked

The pair share a byte-identical block, which made them the first fully specified
dogleg cars in the dataset and registered
`h-5-synchro-dogleg-clutch-start-lift-up-blip-down`. Its id carries the gate where
no other id does, because without it the archetype would be indistinguishable
from the standard-gate five-speed synchromesh one.

Four dogleg cars that had been `no-archetype` purely because that archetype could
not exist - `bmw-m1-procar`, `formula-inter-mg15`, `lamborghini-diablo-sv-r` and
`sauber-mercedes-c9` - now deviate from it, each declaring the gearbox gap and
pointing at the FIA form as the route to close it. `mclaren-honda-mp4-4` still
matches nothing, and its basis now says why: six gears, and first down and to the
right, the mirrored gate.

## Superseded: were the five-speeds unanimous?

The recommendation to leave both records unknown rests on the forms listing
gearboxes of differing construction, so that picking one would be a guess. That
is plainly right for the six-speeds. It may not be right for these two records,
because **both curate a five-speed** - `forward_gears: 5`, and both identity
notes name a five-speed Getrag dogleg.

Every option read so far that is not clearly synchronised is a six-speed: the
M3's blank-column 12/08 VO and its unstated Hollinger 38/20 VO. Restricted to
five forward ratios, every option read so far on both forms is synchronised. If
that is the complete picture, the forms do not leave a choice for these cars -
the options agree, and `synchromesh` follows without selecting between them.

That turns on a question only a reader of the scans can answer:

> On A-5327 and A-5269, enumerate **every** homologated gearbox with **five**
> forward ratios - the base entry, any alternative on the same page, and any VO,
> ES or ET extension. For each one, quote the synchro column verbatim for every
> forward gear, and say explicitly where a marking is blank, dashed or absent
> rather than reading it as a no. Give the page number for each.
>
> The claim to defeat: *no five-speed variant on either form lacks an explicit
> synchronised marking.* A single five-speed with a blank synchro column defeats
> it, and the records stay unknown.

If the five-speeds are unanimous, both records can take `synchromesh` at medium,
which would make them the first fully specified dogleg pair in the dataset and
create the dogleg archetype the four remaining dogleg cars are waiting on. It
would also put a required blip on a synchromesh, the same shape as the Formula
Vee pair, which is handled as a simulator override rather than by revising the
construction.

## The blip follows the construction, and nine records were ahead of theirs

A synchromesh does not need a blip to engage a gear, so the dataset records
`optional` for one and reserves `required` for gearboxes that do. That rule was
already in the data - the same sentence appears in thirty-two records - but it
was written down nowhere central until now. It is in `docs/data-model.md`.

Stating it exposed that the M3 and 190E had broken it. Establishing their
construction while leaving their blip at `required` made them the only
synchromesh records in 242 demanding a blip, and it was inconsistent with the
Formula Vee pair handled one step earlier. Both are corrected: the blip is
`optional`, the archetype they define is now
`h-5-synchro-dogleg-clutch-start-lift-up-blip-optional`, and the synchromesh
column reads 34 optional, 1 unknown and no required at all.

**No override was written for them, and that distinction is the useful part.**
The Formula Vee drives recorded a clutchless downshift *refused* until the driver
blipped, which is a simulator requirement and belongs in an override. These
drives recorded a downshift *accepted after* a blip, which shows blipping works
and nothing more. Writing an override from that would assert a test nobody ran.

### The cost, and what it exposed

The four dogleg cars that briefly deviated from the archetype - `bmw-m1-procar`,
`formula-inter-mg15`, `lamborghini-diablo-sv-r`, `sauber-mercedes-c9` - are back
to `no-archetype`, and for a sharper reason than before. It is not their
unestablished construction that excludes them, which would be a gap. It is their
blip: `required` is a known value, and the archetype has `optional`.

So through the blip they assert a construction their `gearbox_type` does not
establish. Ten records were in that position when this was written. The Diablo
SV-R has since been settled, and the remaining nine were closed out in two
groups.

**Four dissolved.** `chevrolet-corvette-c3-r`,
`chevrolet-corvette-c3-r-convertible`, `stock-usa-gen1` and `stock-usa-gen2` are
cars a simulator invented. For a car with no real referent there is no real
gearbox to be right or wrong about, so the simulator is the only authority that
exists and its demand is the complete fact about the only version of the car
there is. The rule reserving `required` for gearboxes that need the blip governs
claims about real cars; it never reached these four. `required` stands as a known
value.

**Five stand, knowingly.** `bmw-m1-procar`, `chevrolet-omega-stock-car-1999`,
`formula-inter-mg15`, `puma-gte` and `sauber-mercedes-c9` are real cars whose
construction is unestablished and whose research routes are exhausted. Each now
records what would unblock it.

The uncomfortable part is recorded with them. Where the construction was later
established for a car in this position - Formula Vee Gen2, Formula Vee FIN and
the Diablo SV-R - the authentic blip was revised to `optional` every time and the
simulator's demand moved to an override. Three out of three. So these five carry
a value that is more likely wrong than right. It stays because no source
establishes the construction that would settle it, and the dataset does not
convert a value by assumption - but it is carried in the open rather than
quietly.

That also disposes of any temptation to read the blip as evidence of a dog box.
AMS2 demands a blip on gearboxes established as synchromesh, so its demand
establishes the technique a driver must use and says nothing about how the
gearbox engages.

What does differ between them, and has to be read per record rather than swept,
is what the drive actually recorded. `stock-usa-gen1` says clutchless running
shifts *require* a lift and a blip, which would justify an override the moment
its construction turns out synchromesh. `sauber-mercedes-c9` says only that a
guided drive established the running-shift technique. Those two do not support
the same conclusion, and the difference decides whether an override belongs.

## The retirement was keyed on the wrong thing

The first retirement matched record ids - `formula-classic`, `formula-retro`,
`formula-vintage`, `formula-dirt` - rather than asking whether the car is one
Reiza invented. Four records meet the criterion and do not match those names:
`chevrolet-corvette-c3-r-convertible`, `stock-usa-gen1`, `stock-usa-gen2` and
`formula-junior`. All four are retired now, and the test is re-keyed on what the
record says about itself.

**`formula-junior` was not merely missed, it was argued out.** The earlier note
kept it in the queue on the grounds that Formula Junior was a real international
category with a technical formula, which is true of the category and irrelevant to
this car. Its own identity note reads: "Reiza's fictionalised Formula Junior
category open-wheel car ... No real-world chassis identity is assigned, so the
gearbox construction is not established". The record had the answer in it, and a
plausible argument about the category name talked over it.

The Corvette Convertible is the same shape: B-260's own source note calls it
"Reiza's fictionalized C3.R Convertible" and says the form gives manual-gearbox
context rather than this car's construction. Only the closed **C3.R coupe** has a
real referent - a 1971 sheet identity - and it does not cite B-260 at all.

Re-keying the test also caught the same error inside the test. It asserted that a
fictionalised car with an established gearbox must be paddle-shifted, which was a
proxy for the real principle rather than the principle. `stock-usa-gen3` and
`super-v8` are sequential sticks, equally visible from the cockpit. What no drive
can see is whether an **H-pattern** box engages through synchronisers or dog
rings, and that is what the test now asserts.

The live queue is 12.

## Answered, and left unknown: the M1 Procar

The M1 has three FIA records - 670 in Group 4 and its FISA transfer to Group B,
both dated 2 December 1980, and 240 in Group B from 2 March 1983. Codex read all
three. The falsification test came back negative in the direction that matters:
**no M1 five-speed is shown dog-engaged on any of them**, so the dogleg
archetype's shape is not challenged and the other dogleg cars do not become
ambiguous between two archetypes.

**The construction stays unknown, and the reason is the point.** The form
contemporary with the Procar is 670, and it predates the article 603 layout: its
equivalent fields are 92, 93 and 96, which carry **no synchroniser field at all**.
Its three five-speeds are therefore silent, not negative, and an absent field is
not a no. B-240 does mark both its five-speeds synchronised, and they are
recognisably the same ZF unit by their ratios - but it postdates the Procar by
three years, the Procar has no form of its own, and 670's one ratio set that
appears nowhere else was struck through on the transfer.

**This is where the M3 and 190E differ, and why the answers differ.** There,
every five-speed on each car's *own contemporary* form carried an explicit mark,
so the options were unanimous and nothing was being chosen between. Here the
contemporary form does not ask the question and the marks come from a later one.
That is a longer reach, and the same criterion that promoted the first pair
declines the second.

What the forms did settle is the gate. B-240's 603 f) draws reverse above first
with 1, 3 and 5 on the lower plane, so the M1's dogleg and first-down-left now
rest on a primary source as well as the cockpit - the third car to gain that from
these forms. Both M1 forms are registered.

Codex also confirmed there is no Procar-labelled gearbox or Procar-specific
extension on any M1 form. The series was one-make and bespoke, and the FIA record
does not describe it, which is worth knowing before anyone searches again.

`bmw-m1-procar` now deviates from the dogleg archetype on `gearbox_type` alone.
It is the best remaining candidate for the FIA route, because unlike the Group C
cars the M1 was homologated - for Group 4 - so a form should exist. What is
already established: a ZF five-speed, dogleg, first down and left, with first,
third and fifth sharing the lower plane.

> Find the FIA homologation form for the **BMW M1 (E26)** on
> `historicdb.fia.com` - Group 4, and note any later Group B form or extension.
> From **article 603 Getriebe**:
>
> 1. **603 b)** the manual gearbox make as written.
> 2. **603 e)** every homologated gearbox with **five** forward ratios - the base
>    `Handschaltung`, any `Zusätzl. Getriebe` on the same sheet, and any VO, ES or
>    ET extension carrying its own ratio table. Quote the **synchro column
>    verbatim per gear**, and say explicitly where a marking is blank, dashed or
>    absent rather than reading it as a no. Page number for each.
> 3. **603 f)** the `Schalt-Schema`, described as drawn - which positions carry
>    reverse and first, and which gears share the lower plane.
> 4. Whether any extension describes the **Procar** specification specifically,
>    rather than the road car. The Procar was a one-make series and its gearbox
>    may be covered by an extension, or may not appear on the form at all.
>
> **The answer matters in both directions.** If the five-speeds are synchronised,
> the M1 joins the archetype. If any is dog-engaged, that is the more interesting
> result: it would mean a dogleg five-speed can be either construction, and
> `formula-inter-mg15`, `lamborghini-diablo-sv-r` and `sauber-mercedes-c9` would
> move from deviating on a gap to genuinely undetermined between two archetypes.
> A blank or absent marking is a real finding, not a failed search.

## Searched: Puma, Lotus 23 and the C3.R

All three came back, none changed a value, and each failed differently. Three
sources are registered and B-260's note is corrected, because it turned out to be
explicit where it had been described as context.

**Puma GTE - closed by the category, not by a missing source.** No source names
the transaxle, but that stopped mattering. Copa Classic article 8.1 requires a
casing from the car or engine maker while allowing it to be freely reworked, and
makes the gears themselves free; category B also permits a more modern gearbox
matched to the engine. So the category does not preserve the road car's internals,
and naming the Volkswagen unit would not have established what the raced car
turns. Both `gearbox_type` and `shift_pattern` stay unknown.

**Lotus 23 - the claim is defeated.** A period Autosport test of an as-raced Type
23 names a four-speed Renault and contrasts it with the five-speed Hewland it
calls standard by late 1962. The Renault is a synchromesh production unit; the
Hewland runs dog rings. The options do not agree, so the argument that carried the
Group A pair does not apply here.

The tempting move is to let the gear count decide, as it did for the M3: the
record has four gears and the Hewland Mk3 is a five-speed. It is not taken.
Hewland's earliest boxes were four-speed conversions, so a gear count does not
separate the two families without a source that says it does - and the whole point
of the M3 argument was that the form itself made the separation.

**Corvette C3.R - the evidence is there and the identity is not.** Form 3039,
homologated 2 June 1971 and contemporary with the car AMS2 models, states
"Synchronised forward ratios: all four". The 1966 and 1968 forms agree, the 1984
Group B form marks its Doug Nash four-speed synchronised on every forward gear,
and **no FIA Corvette four-speed is marked non-synchronised anywhere**. The 1962
and 1965 forms carry no synchroniser field and are silent rather than negative.

This clears the bar the M1 failed, where the contemporary form was the silent one.
What it does not clear is identity: the record is an AMS2 sheet identity for a
1971 GT Classics Corvette, and no reviewed source ties it to the LS6 that form
3039 homologates rather than to the C3 family at large. The missing piece is the
bridge, not the evidence at the far end of it - which is a different kind of gap
from the rest of this queue, and the one open judgment left in it.

## Retired: the C3.R has nothing to bridge to

The search for an identity bridge found there is none, and the record is retired
on the Convertible's logic - "a unique real-world referent is not established".

Reiza's release adds the Corvette C3 and the Corvette C3 "R" Spec and names no
model year, chassis, engine, team or series. "C3.R" is not a Chevrolet
designation; it renders "R Spec". The 1971 in the record comes from the Coanda
sheet, which is simulator specification data rather than an identity note and
cites nothing for the year. `TC70S` is an internal runtime class id, not a real
racing class - Reiza's published class is GT Classics, which also holds the real
1974 Porsche 911 RSR, so the class says nothing either way.

**The sharper correction is about form 3039, and it is a correction to this
note.** The previous entry described the Corvette forms as the right evidence
waiting on a bridge. They are not: form 3039 homologates the Sting Ray LS6 at
7,446 cc, and the sheet specifies a 7.0-litre L88. Different engines. The form was
never about this specification, so there was nothing at the far end of the bridge
to reach. The synchroniser finding stands for the cars those forms describe and is
explicitly not inherited here.

That is a failure mode worth naming, because it nearly worked. The evidence was
real, contemporary, explicit and consistent across two decades of forms, and it
was about a different car. Checking the displacement is what separated them, and
nothing in the earlier reasoning had asked.

## Superseded: the C3.R's identity bridge

This is the only record in the queue whose gap is identity rather than evidence.
Form 3039, contemporary and explicit, says all four forward ratios are
synchronised. What is missing is anything tying the AMS2 identity to the car that
form homologates rather than to the C3 family at large.

The bridge is a different kind of claim from the construction, and it takes a
different kind of source. A Reiza statement is `official-simulator`, which this
project forbids as evidence about a real car - but the bridge is a question about
**what the game models**, which is exactly what a simulator source can answer.
So the two halves have different sources by design: a simulator source
establishes `/identity`, and the homologation form establishes the construction of
whatever that identity turns out to name.

> For AMS2's **Chevrolet Corvette C3.R** - class id `TC70S`, recorded as 1971:
>
> 1. Does **Reiza** state what real car it represents? Release notes, development
>    updates, forum posts by the team, or the in-game car description. A year, a
>    model designation, an engine or a racing series would each be a bridge.
> 2. Does the **Coanda Extended Car Info sheet** carry identity notes for this
>    entry beyond the name, and where does the **1971** in the record come from -
>    the sheet, or an assumption?
> 3. **Was "C3.R" ever a real designation?** Chevrolet never sold a car by that
>    name as far as this project can tell. If it is Reiza's own construction for a
>    generic C3-era racer, say so.
> 4. What era or class does `TC70S` place it in?
>
> **This question can close the record either way, and both outcomes are better
> than the present one.** If a source names a real 1971 Corvette, the construction
> follows from form 3039 and the record takes `synchromesh`. If nothing ties it to
> a specific car, then it has no unique real-world referent - which is precisely
> the finding that retired its own Convertible variant, whose note reads "a unique
> real-world referent is not established". That would close it as a car Reiza
> assembled rather than represents, and retire it from this queue permanently.
>
> A null result here is therefore not a failed search. It is the second of two
> answers.

## Open: the Puma GTE, one link short

`puma-gte` is a real car and the chain is nearly closed with sources already in
the registry. `supercars-net.puma-gte` has it built "on Volkswagen running gear,
with an air-cooled flat four and a four-speed manual gearbox", and
`iccr.formula-vee-technical-regulations` states that a fully synchromesh VW Type
1 or 3 gearbox has four forward gears with its internals as the manufacturer
assembled them. A fact about a component carries to any car using that component.

The loose link is the identification. The Puma source says "Volkswagen running
gear" and "four-speed manual", not "Type 1" - so reading it as the Fusca or
Brasilia transaxle is currently inference rather than something a source states.

> For the **Puma GTE** (Brazil, 1970-1980, VW-based, four-speed):
>
> 1. Does any reviewed source **name the transaxle** - Type 1, Fusca, Brasilia,
>    or a VW part number - rather than saying "Volkswagen running gear"? A
>    Brazilian source, a Puma factory brochure or a Copa Classic technical
>    regulation would all do.
> 2. Does any source state the **gear-change gate**? This record has
>    `shift_pattern: unknown`, which is unusual for a road-derived car, and a
>    standard H with first up and left is the expectation rather than a finding.
>    Note that a cockpit read settles this one, so it does not need a document.
> 3. Does any source describe the Copa Classic B specification as modifying the
>    gearbox internals?
>
> If the transaxle is named, the construction follows from a regulation already
> registered and the record can take `synchromesh` at medium. If nothing names
> it, it stays unknown - "VW running gear" is not the same claim as "the Type 1
> transaxle", and the difference is exactly what medium confidence is for.

## Open: the Omega Stock Car, and a period regulation

`chevrolet-omega-stock-car-1999` is a real car in a real championship, and its
own note says the reviewed source does not document the gearbox, so the
transmission currently rests on the guided drive alone. 1999 was the last Stock
Car Brasil season built on production-car chassis, which makes the gearbox
question live: a production Chevrolet unit and a purpose-built racing box have
different constructions and the record cannot tell them apart.

The route that worked twice already is a governing body's technical regulations.
The project already registers `cba.stock-car-pro-2024.technical-regulations`,
which prescribes an Xtrac paddle-shift and so describes a completely different
era of the same championship.

> For **Stock Car Brasil in the Omega era, 1994-1999**:
>
> 1. Is a **period technical regulation** archived by the CBA or elsewhere? The
>    CBA site serves recent years; 1999 may only exist in a motorsport archive,
>    a period press kit or a team document.
> 2. If one exists, quote the gearbox article: how many forward ratios, whether
>    the gearbox must be a production unit or is free, and whether it says
>    anything about synchronisers or dog engagement. Copa Truck's article 15 is
>    the shape to look for, and its answer - "o cambio e livre" - is a real
>    possible outcome here too.
> 3. Failing a regulation, does any period source name the gearbox fitted to the
>    1999 Omega?
>
> A regulation that leaves the gearbox free is as good an answer as one that
> fixes it: it would close this record the way Copa Truck closed five, as a
> documented permanent unknown rather than an outstanding task.

## Open: the Lotus 23, where the options may agree again

`lotus-23` is a real 1962 Group 4 sports racer and its own note carries the
shape that settled the M3 and the 190E. Lotus states the gearbox choices
"typically included Renault or Volkswagen units", and the drive found four
forward gears. Both of those are production road transaxles, and one of them is
already established: `iccr.formula-vee-technical-regulations` has the VW Type 1
and 3 four-speed as fully synchromesh.

So if the Renault unit is synchromesh too, the two candidates agree and the
construction follows without choosing between them - which is exactly the
argument that carried the Group A pair, and it does not need the specific unit
identified.

> For the **Lotus 23** (1962, four-speed):
>
> 1. Which **Renault** transaxle did the Type 23 use, and is it synchronised? A
>    period Lotus specification, a Type 23 restoration guide or a Renault
>    workshop source would all do.
> 2. Does any source list a **third** gearbox option beyond Renault and
>    Volkswagen - a Hewland, for instance? A Hewland would be dog-engaged and
>    would break the agreement, which makes it the finding to look for rather
>    than a footnote.
> 3. Does any source say which unit the **23 as raced in period** carried, as
>    against the choices offered?
>
> The claim to defeat: *every gearbox the Type 23 was offered with is a
> synchronised production transaxle.* One racing dog box among the options and it
> stays unknown.

## Open: one gearbox, three McLarens

`mclaren-honda-mp4-4`, `mclaren-honda-mp4-5b` and `mclaren-honda-mp4-6` all name
the same unit - a **Weismann/McLaren transverse six-speed manual** - so a single
source settles three records. The MP4/6 is recorded as the last car to win a world
championship with a manual gearbox, which makes this a well-documented corner of
the sport.

**Do not look for a homologation form.** Formula One cars are built to technical
regulations and were never homologated, the same reason the Group C cars have no
paperwork. Five of the twelve records still live are in classes that never
homologated anything, and that route is permanently closed for all five. The
period Formula One technical regulations this project already registers cap ratio
counts and describe clutch control; they say nothing about engagement.

> For the **Weismann/McLaren transverse six-speed** of 1988-1991:
>
> 1. Does any source state whether it engages through **dog rings or
>    synchronisers**? A Weismann company description, a period technical
>    write-up, a McLaren team account or a restorer of these cars are the likely
>    places - the equivalent of the specialist source that settled the Porsche
>    915.
> 2. Is the gearbox in the **MP4/4** the same unit as in the **MP4/5B** and
>    **MP4/6**, or did it change across those seasons? The records assume one
>    family; a change would split them.
> 3. The three disagree on the gate: MP4/4 is recorded dogleg with first down and
>    to the **right**, MP4/5B standard, MP4/6 unrecorded. Does any source describe
>    the gate for any of them?
>
> All three have `manual_blip: unknown` as well as an unknown construction, so
> unlike most of this queue they assert nothing they cannot support. One answer
> settles both fields on three cars, under the rule in `docs/data-model.md`, with
> no override question to resolve.

## Part-settled: Formula Inter, a real car with an unreachable gearbox

`formula-inter-mg15` keeps `gearbox_type: unknown`, and the search was still worth
running. It answered a bigger question than the one being counted.

**The car is real and the record does not retire.** The F-Inter MG-15 is a
purpose-built Brazilian single-seater constructed by **Minelli Racing** for
Fórmula Inter, a category FASP ran in its Paulista championship. This record's
identity had rested on the Coanda spreadsheet alone - every source on it
simulator-derived - and it is now held at high on a 2015 launch report naming the
model and its constructor. No reliable source expands "MG", so it stays a model
designation rather than a person or a year.

Putting the identity question first is what produced that. Had the question opened
on the gearbox, the search would have returned nothing and the record would have
kept a simulator-only identity indefinitely.

**The gearbox routes are narrower than expected, not merely unsearched.** Two
findings close them:

- The gearbox was **made in-category**: "Produzida pela própria equipe técnica da
  Fórmula Inter, a caixa de câmbio conta com cinco marchas dispostas em 'H'".
  Because no donor production unit is named, the reasoning that settled Formula
  Vee - a sealed production gearbox is a road unit, therefore synchromesh - does
  not reach this car. The one route that looked most promising is the one this
  finding removes.
- FASP's 2024 sporting regulation carries "ANEXO 5 - FÓRMULA INTER" on page 38,
  which proves the category and contains a **points table and nothing else**: no
  gearbox article, no prescribed, sealed or free rule, no ratios. No CBA, FASP or
  promoter *technical* regulation for the 2015-2023 MG-15 was located. A bounded
  negative, not an unfinished search.

Neither launch account uses `sincronizado` or `garras`. The construction is absent
from the record rather than denied.

**Two things recorded rather than resolved.** The launch accounts disagree on
ratio count - five in one, four in the other, both naming this car and Minelli
Racing. The record keeps five, which the guided drive established directly and the
more detailed account corroborates; no source explains the difference and it is
not read as evidence about the construction either way. And the **dogleg has no
real-world corroboration at all**: both accounts say only "H", which is generic,
and neither gives a first-gear position. The dogleg with first down and left is
simulator-observed only.

That last point is worth carrying beyond this record. The archetype note excludes
this car because its blip is `required` - a known value - where the dogleg
synchromesh archetype has it optional. The gate that puts it near that archetype
in the first place is itself only observed in the simulator.

**What would still settle it**: Minelli Racing's own documentation, a gearbox
specialist writing about the category, or a technical regulation that is published
somewhere the public web does not reach. The routes tried are exhausted.

## Settled: the Diablo SV-R, and a lead that did not survive

`lamborghini-diablo-sv-r` is **synchromesh at medium confidence**, and the
downshift blip is **optional** with the simulator's demand carried as an override.
Both clutch fields stay `unknown`. The interesting part is how it got there: the
lead this search was built on was wrong, and the search is what showed it.

**The lead was that a dogleg is not a road-car gate.** If the road Diablo used a
standard H, the SV-R's dogleg would mean a gearbox changed for racing, and a
racing gearbox for a one-make series is far likelier to be dog-engaged. That
reasoning was recorded here as making a dog box "the likelier answer".

**The road Diablo SV is itself a gated dogleg five-speed.** So the gate came with
the car the SV-R derives from, implies no change of internals, and was never
evidence of anything. The caution added to the question - that a dogleg can be
produced by re-gating rather than replacing a box - understated it: there was no
re-gating either. The dataset already held two dogleg synchromesh cars in the M3
Sport Evolution and the 190E Evo II, which should have made the pairing look
unremarkable before the question was written rather than after.

The one source that characterises the construction says the opposite of what the
lead predicted: a marque-specialist sheet reading "Lamborghini five-speed +
reverse manual all-synchromesh". Explicit wording, not a blank or a dash.

**Why medium.** It is one secondary source. Lamborghini's own heritage sheet gives
the hardware - a five-speed manual, a dry single-plate clutch - and is silent on
construction rather than negative, so it neither corroborates nor contradicts.
That is the 1974 911 RSR's standard exactly: marque-specialist secondary sources,
no homologation, taken at medium. The identity check the C3.R failed passes here,
and it mattered: the heritage sheet's 5,707 cm3 and 540 CV separate this car from
the 5,992 cm3, 590 CV Diablo GTR listed beside it.

**The homologation route is closed for good.** No FIA HistoricDB vehicle form
exists for the SV-R, and ACI Sport's safety-cage register lists it with an
explicit `/` in the vehicle form-number column - an absent number, not an unfilled
field. That register has no gearbox or synchroniser columns at all. A one-make
series car with no vehicle form has no primary route to this field, so "retain
`unknown` pending better evidence" would have been a permanent hold rather than an
interim one. That is what made deciding now the right call rather than waiting.

**What it did not do.** It does not found a dogleg dog-box archetype; that pairing
still has no member and no evidence behind it. Nor does the record `match` the
dogleg synchromesh archetype, because `matches` demands exact equality and the two
clutch fields are still open - `unknown` is a wildcard only when deciding whether
an archetype remains a candidate. The record `deviates` on those two gaps against
a single candidate archetype. What did change is that the contradiction its old
`no-archetype` note recorded is gone: it no longer asserts through a required blip
a construction its `gearbox_type` leaves open.

**Clutch use on running shifts is unestablished and stays that way.** The factory
sheet gives the clutch hardware, which is what the clutch is and not when the
driver uses it. No Supertrofeo regulation, driver instruction or period technical
source found speaks to it. The simulator accepts clutchless shifts, but that is
the simulator's behaviour, not the real car's technique.

## Group C cannot be settled this way at all

`sauber-mercedes-c9` and `porsche-962c` were listed as homologation candidates.
They are not, and no amount of searching will change it: **Group C was a pure
prototype class with no homologation requirement**, neither a minimum production
run nor the use of series components. Cars were built to the formula rather than
homologated, so no form exists for either and none ever will.

Those two need a different source class entirely - constructor or team
documentation, or a specialist on the specific gearbox, which is the route that
worked for the 911 RSR's Type 915.

Of the dogleg six, `formula-inter-mg15` has not been searched for papers yet.
`bmw-m1-procar` has: its Group 4 form exists but predates the article 603 layout
and carries no synchroniser field, so it is silent rather than negative.
`lamborghini-diablo-sv-r` is settled above, and its search established that the
car was never homologated as a vehicle at all.
