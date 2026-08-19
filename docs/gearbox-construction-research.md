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
| Copa Truck | 5 | **Answered.** The regulation leaves the gearbox free |
| Formula Vee | 2 | **Candidate**, on a primary Brazilian regulation |
| Porsche 911 RSR 1974 | 1 | **Candidate**, at medium confidence |
| Reiza's fictionalised cars | 17 | **Not researchable.** No source can exist |
| Other real cars | 18 | Open, and needing homologation-class sources |

The 17 is the number that should change how this queue is read: nearly two in
five of these records are not waiting on a source anyone could find.

## Answered: Copa Truck

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

**Recommendation: leave `gearbox_type` unknown on all five, and record the
regulation as the reason.** This is the better of the two available outcomes -
not a gap awaiting a source, but a closed question with a citation. It would be
the first place in the dataset where `unknown` is documented as the correct final
answer rather than outstanding work, which is worth deciding deliberately.

Source if accepted: CBA Copa Truck technical regulations 2025, publisher
Confederação Brasileira de Automobilismo, type `homologation`, retrieved
2026-08-18,
`https://www.cba.org.br/upload/downloads//806/copa-truck-regulamento-tecnico-2025-.pdf`

## Candidate: Formula Vee

`formula-vee-fin` (four-speed), `formula-vee-gen2` (five-speed).

These were nearly missed. Formula Vee is a real category with a technical
formula, not one of Reiza's inventions, and it was in the unresearchable pile
until the grouping was checked.

FASP 2025 Fórmula Vee technical regulations, Article 7 (TRANSMISSÕES):

> **7.1** São permitidas duas transmissões: **Quatro Marchas originárias de
> Fusca/Kombi e outros VW refrigerados a Ar. Cinco Marchas originárias de Gol
> Longitudinal.** As CAIXAS DE CÂMBIO de Quatro e Cinco Marchas serão fornecidas
> pela PROMOTORA e/ou fornecedores indicados e serão **LACRADAS**.

And the two chassis, at 2.1.2 and 2.1.3: the Naja 01 runs the four-speed
air-cooled VW box, the Naja 01-D the five-speed longitudinal Gol box. **Those are
the two records' gear counts exactly**, which is good corroboration that the
records model these two variants.

**Candidate: `synchromesh` for both, confidence `medium`.**

The basis is a chain, and the weak link should be visible: the regulation
mandates specific unmodified production Volkswagen road gearboxes and requires
them sealed, and production VW road gearboxes are synchromesh. The regulation
itself never says *sincronizada* - that last step is the inference. It is
corroborated independently: national Formula Vee regulations elsewhere state the
requirement outright, that "a fully synchromesh VW Type 1 or 3 gearbox must be
used".

That is a much stronger basis than era or period practice, but it is still one
step short of a Brazilian clause using the word. A reviewer could reasonably
argue for higher than medium; medium is what a researcher should propose.

Falsifiable by a Brazilian clause or a promoter's specification showing the
sealed boxes carry dog engagement.

Sources: `https://fasp.faspnet.com.br/wp-content/uploads/2025/02/Formula-Vee-2025-tecnico.pdf`
(FASP, type `homologation`), `https://fvee.com.br/index.php/a-categoria/os-carros`
(category promoter), and for the corroboration
`https://www.iccr.ie/wp-content/uploads/2021/06/2021-Tech-Regs-Formula-Vee.pdf`.

## Candidate: Porsche 911 RSR 1974

The Type 915 is described by a marque specialist as using "Porsche's own
synchromesh design", distinguished from the later G50's Borg-Warner synchro. The
RSR ran the 915/08, described elsewhere as a magnesium-cased race-type 915 with
the dogleg first the family is known for.

**Candidate: `synchromesh`, confidence `medium`.** Basis: the 915 family is
established as synchromesh by a specialist source and the RSR's 915/08 is a
variant within it; no reviewed source says the race variant replaced the
synchronisers with dog rings. Falsifiable by a period Porsche workshop manual or
homologation sheet showing dog engagement in the 915/08.

**Do not let this decide the blip.** This record's `downshift.manual_blip` is
also unestablished, and resolving it from a medium-confidence construction would
answer one unknown with another.

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

## Not researchable: the fictionalised cars

`formula-classic-gen1` through `gen4` (9), `formula-retro-*` (3),
`formula-vintage-*` (4), `formula-dirt` (1).

These are Reiza's own cars, standing in for an era rather than representing a
chassis. There is no manufacturer, no homologation sheet and no registry, so no
real-world source could establish their construction, and any value assigned
would be reasoning from the era the car evokes.

**Recommendation: leave unknown and stop counting them as research debt.** They
are not waiting on a source that exists. Classifying them would need a deliberate
decision about what a fictionalised car's authentic controls mean, which is a
data-model question rather than a research one.

`formula-junior` is deliberately not in this list. Formula Junior was a real
international category with a technical formula, so it belongs with the
researchable records even though it has not been researched yet.

## Corroborated, but no further

Searched, and the record's existing values were confirmed without reaching
construction. Listed so the search is not repeated.

| Record | Corroborated | Still open |
| --- | --- | --- |
| `bmw-m1-procar` | ZF five-speed, dogleg, 1st down and left | construction |
| `porsche-962c` | five-speed manual | construction |
| `mercedes-benz-190e-2-5-16-evo-ii-dtm` | Group A five-speed dogleg | construction |

## What to decide next

1. **Copa Truck.** The only group where an answer exists now, and the answer is
   that the regulation leaves the gearbox free. Deciding this also decides
   whether a documented, permanent `unknown` is a state this project wants.
2. **Formula Vee.** Whether the sealed-production-unit chain clears the bar at
   medium, for two records.
3. **The 911 RSR**, on a weaker version of the same kind of chain.
4. **Retire the 17 fictionalised records** from the queue, or decide what could
   ever settle them.
5. For the remaining 18 real cars, look for homologation papers and period
   workshop documentation. Car histories have been tried and do not reach it.
