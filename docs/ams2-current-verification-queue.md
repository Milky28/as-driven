# AMS2 current verification queue

## Completed in dataset 0.3.50 (batch 19: the last five drives)

Five cars, and the drive queue is down to three identities that need a decision
rather than a drive.

BMW 2002 turbo returned five gears. The source gives the turbo a strengthened
Getrag 232 four-speed unique to that model, or the optional Getrag 235/5
close-ratio five-speed, so AMS2 models the optional gearbox rather than the
standard one. Chevrolet Corvette C3 returned four, and the source names three
different four-speeds, so no specific unit is claimed.

Porsche 911 RSR 1974 is selectable and was driven, which settles half of a
pending question: `Porsche 911 RSR 74` is the doubtful name, not this one. Its
source gives a five-speed carried over from the RS but no construction, so the
downshift blip stays unknown.

Mercedes-Benz CLK LM and McLaren Mercedes MP4/12 both carry automatic cut and
blip, the CLK LM on a six-speed sequential and the MP4/12 on McLaren's six-speed
longitudinal semi-automatic sequential.

The manifest test that required at least one pending aero variant was relaxed. It
drains as base cars are verified and reached zero here, so the assertion that one
must exist was reporting success as failure. The invariant it guards, the shape
of any entry still pending, is unchanged.

## Completed in dataset 0.3.49 (batch 18: F-USA Gen3, Formula Vee, Formula Vintage Gen2)

Ten cars, and the open-wheel queue is now empty.

The seven 2000-season CART cars are uniform: six gears through a sequential
stick, automatic cut, no automatic blip, a clutch to pull away. Five of the seven
were invisible to the queue until loaded, and the sources list every one of their
engines, so all are official content. Lola B2K00 Ford-Cosworth anchors the four
configurations, base, high downforce, Speedway and Superspeedway.

The Reynards carry a D-shaped rim where the Lolas of the same class carry a round
one. The drives recorded that per car rather than sharing a rim across the class.

Formula Vee Gen1 is the first record whose gate is `unknown` because the driver
could not read it rather than because a lever hid it. Its gearbox is sourced
twice over: the category runs the Volkswagen Beetle four-speed, and the transaxle
source already registered describes that unit as constant-mesh with balk ring
synchronisers, so the downshift blip is `optional`.

Formula Vintage Gen2 Model1 and Model2 were found in a class believed finished.
The Brabham BT26A and Lotus 49C were curated from it in dataset 0.3.30, and these
two were never in the queue at all. They inherit nothing from those cars: the
Brabham and Lotus run racing Hewlands and carry a required blip, while these are
Reiza's fictionalised cars with no chassis assigned, so their construction stays
unknown.

## Completed in dataset 0.3.48 (CART batch 17, F-USA Gen2)

Six cars of the 1998 CART season, and the class is uniform: six gears through a
sequential stick, automatic cut, no automatic blip, and a clutch to pull away.

Four of the six were invisible to the coverage queue until they were loaded. Only
Lola T98/00 Ford-Cosworth and Reynard 98i Ford-Cosworth were known; the Reynard's
Honda, Mercedes-Benz and Toyota variants and the entire Swift 009.c had never
been seen on this PC. The source lists all four Reynard engines, so they are
official content rather than anything irregular.

This class runs **four** configurations: base, high downforce, Speedway and
Superspeedway. Lola T98/00 Ford-Cosworth was observed in all four and anchors the
identity format; the rest take their extra identities from the stored inventory
where it holds them and by derivation where it does not, each labelled
accordingly.

Swift 009.c is `medium` confidence alone among the six. Its Wikipedia entry
establishes the chassis and the Ford-XD V8 but states no transmission at all, so
its gearbox rests on the guided drive rather than on a real-world specification,
and the record says so.

## Completed in dataset 0.3.46 (CART batch 16, F-USA Gen1)

Four of the five 1995 IndyCar chassis: Lola T95/00 in Ford-Cosworth and
Mercedes-Benz form, and Reynard 95i in Ford-Cosworth and Honda form. All are
six-speed sequential sticks with automatic cut, no automatic blip and a clutch
to pull away, so the driver supplies the downshift blip.

Reynard 95i Honda was absent from the coverage queue entirely until it was
loaded. Wikipedia lists the Honda Indy V8 turbo among the 95I's engines, so it is
official content that had simply never been seen on this PC.

This class runs three configurations rather than two: base, high downforce and
`- Speedway`, an oval package. Lola T95/00 Ford-Cosworth was observed in all
three and anchors the identity format for the rest; the others take their extra
identities from SimHub's stored inventory where it holds them, and by derivation
where it does not, each labelled accordingly.

Reynard 95i Mercedes-Benz followed in dataset 0.3.47. Its high-downforce attempt
was the only one of the class's five cars to report an automatic blip. The same
car was then driven in its Speedway configuration and reported none, and aero
configuration does not change a gearbox, so the same car contradicted itself. The
guided drive reads any throttle above fifteen percent during the attempt as a
spike, which makes a brushed pedal and a car blipping for itself
indistinguishable. The spike is recorded as an artefact of that one attempt and
the blip as absent, matching the second drive and the four classmates.

That second drive also confirmed the Speedway identity rather than inheriting it,
which is the second Speedway configuration in the dataset established by driving
it.

## Completed in dataset 0.3.44 (Formula Ultimate Hybrid Gen2 and a Speedway identity)

Formula Ultimate Hybrid Gen2 is a new record: eight paddle gears with automatic
cut and blip and no clutch needed to pull away. All three of its aero identities
were observed, so nothing is derived.

It also untangles a naming trap. **AMS2's Formula Ultimate class numbering is
offset from its car numbering by one.** The Gen2 car sits in `F-Ultimate`,
`F-Ultimate_HD` and `F-Ultimate_LD`; the Gen3 car sits in `F-Ultimate_Gen2`,
`F-Ultimate_Gen2_HD` and `F-Ultimate_Gen2_LD`. Reading either number as the other
would merge two separate cars.

`Formula USA 2023 - Speedway` was driven rather than inherited, and returned the
same six paddle gears, clutch-free move-off, automatic cut and automatic blip as
the high-downforce car. It is carried on the existing record as a confirmed match
rather than an untested configuration, which is the first time a `- Speedway`
identity has been established by driving it.

One question is left open. `Formula Ultimate Gen2` is the primary identity of
`ams2.formula-ultimate-2022`, whose every other identity is a
`Formula Ultimate Hybrid Gen3` name. The certified build did not report it while
every Gen2 and Gen3 configuration was being loaded, so it is a pre-rename
identity, and which of the two cars it named is not established. The stored car
files cannot separate them: every Formula Ultimate shares eight gears, 12,500 rpm
and a 147-litre tank. It is left in place pending a decision rather than moved or
removed on a guess.

## Completed in dataset 0.3.43 (formula batch 14)

Eight cars from five classes, none of which offers an aero variant: the
selection screen shows no package for `F-Dirt`, `F-Junior`, `F-Retro_Gen1`,
`F-Trainer` or `F-Trainer_A`, and only the plain identity has ever been
observed. That is the first time a sweep has closed classes outright rather than
leaving aero work behind.

Brabham BT44, Lotus 72E and McLaren M23 are the real cars, all on the Hewland
FG400 five-speed, so they carry the same dog-engagement reasoning as the Brabham
BT26A and Lotus 49C: the downshift blip is `required`, inferred from Hewland's
design approach rather than stated by the sources. Formula Retro V8 shares their
class and is Reiza's fictionalised car, so its construction stays unknown, as do
Formula Dirt and Formula Junior.

**Formula Trainer and Formula Trainer Advanced are sequential, not H-pattern.**
Community summaries report a four-speed H-pattern, and the drive found a
sequential stick with automatic cut and blip. A Reiza forum thread settles it: a
member who tested the car states it is definitely sequential for both, and a
Reiza internal tester explains that an H-shifter can be bound to a sequential
gearbox in game for players without sequential hardware, and that the selection
menu states no transmission at all. That menu gap is where the mistake comes
from, and the drive read the gearbox rather than the menu.

Formula Edge gained its low-downforce identities. The tester loaded Model1 at
Daytona, which proved the `FE-G1` class offers the package; Model2 and Model3
are derived from their observed high-downforce names and recorded as derived.

## Completed in dataset 0.3.39 (formula batch 13, Classic Gen3 and Gen4)

Nine cars, and the classes are deliberately mixed rather than uniform. Formula
Classic Gen3 holds three H-pattern manual cars and one paddle car; Gen4 holds two
paddle cars and one manual, plus the MP4/6. That is period-correct: teams adopted
semi-automatic gearboxes at different times around 1990, so a manual car and a
paddle car raced in the same field. Nothing is inherited between models on the
strength of a shared class, and this batch is the clearest reason why.

McLaren Honda MP4/5B is the 1990 car on the transverse Weismann/McLaren six-speed
manual.

**McLaren Honda MP4/6 is the standout, and its cockpit disagrees with itself.**
The visible lever and its animation are those of a sequential stick, while the
gearbox accepts direct gear selection, which a sequential cannot do, and requires
the driver to match revs. Wikipedia gives it a Weismann/McLaren transverse
six-speed manual and records it as the last Formula One car to win a World
Championship using a manual transmission, so the mechanics agree with the real
car and the lever is the outlier.

The mechanism is therefore recorded as `h-pattern`, and the gate as `unknown`: a
lever animated as a sequential cannot be read for a gate, and no reviewed source
describes the MP4/6's shift pattern. The sequential-looking lever is treated as a
modelling detail, not as evidence about the transmission.

## Completed in dataset 0.3.37 (formula batch 12)

Twelve cars across three classes, and the batch reads as a history of how
Formula One gearboxes changed between 1988 and 1993.

**Formula Classic Gen2, the 1988 manual cars.** Six H-pattern gears, a clutch to
pull away, and no automatic cut or blip, so the driver lifts and blips. Running
shifts went through without the clutch, which a tester found strange. It is
period-correct and is itself a sign of dog engagement: a dog box is routinely
shifted clutchlessly where a synchronised gearbox resists it. That is recorded as
a supporting observation, and the gearbox type stays `unknown` until a source
states the engagement.

McLaren Honda MP4/4 is the real car of that group, on a Weismann-McLaren
six-speed manual. Its gate is a dogleg **mirrored horizontally**, with first at
the bottom right rather than the bottom left, which no other dogleg in the
dataset does. The schema records `dogleg-h`, which is true of it, and the
mirroring is kept in the record notes because no enum value expresses it.

Formula Classic Gen2 Model2 is the exception in its own class, corrected in
dataset 0.3.38. It engages every gear immediately, up and down, with no lift, no
blip, and no cut or blip from the car, while its three classmates only engage
once the revs match. The automatic-cut test returned inconclusive because there
is no cut to find: the gearbox simply takes the gear. That was first recorded as
`unknown`, which understated a behaviour the drive had established and the driver
then confirmed. It is now recorded as observed, with a note that a 1988 gearbox
would not behave this way and that this most likely reflects how the simulator
models this car.

**Formula HiTech Gen1, 1991 to 1992.** Semi-automatic paddles with automatic cut
and blip, but a clutch still needed to pull away, which is the pattern of the
era. McLaren Honda MP4/7A is the exception and the explanation: it was the first
McLaren with a semi-automatic transmission, and its electro-hydraulic clutch is
why it pulls away without one. Model1 carries seven gears where the others carry
six, so nothing is inherited between them.

**Formula HiTech Gen2, 1993, and the batch's find.** All four upshift by
themselves. That is the gearbox rather than an assist, because automatic shifting
was disabled for every drive, and it is period-correct: the MP4/8's transmission
is recorded as semi-automatic *"which could be switched over to fully
automatic"*. A tester flagged the behaviour as unusual and the source explained
it. The upshift fields, which describe an automatic cut, understate this, so each
record says plainly that the driver does not request upshifts at all.

Every car in this batch was observed only in its high-downforce configuration.
The low-downforce identities are not recorded, because they have not been seen
and an exact match cannot be guessed. A Daytona pass would capture them, and
would also settle whether `McLaren MP4/8` in the queue is the low-downforce name
or a retired pre-rename identity like `Lotus 98T` proved to be.

## Completed in dataset 0.3.36 (Copa Uno)

Held back from batch 11 because the drive read an H-pattern while the reviewed
reference lists a sequential stick. The driver re-checked the cockpit and
confirmed the H-pattern, so the observation is recorded and the disagreement is
written into the record.

The observation was preferred on three grounds rather than one: the same driver
identified a sequential stick on the Chevrolet Montana in the same session, so
the two were being told apart; the absence of automatic cut and blip fits a
road-derived H-pattern rather than a racing sequential; and the same reference
overstates the ARC Camaro gear count. That reference is still registered,
because it supplies the engine, output and weight, with its shifter field noted
as contradicted.

## Completed in dataset 0.3.35 (Copa Classic FL)

Fusca Classic FL and Passat Classic FL, both four- and five-speed H-pattern cars
with no automation, recorded independently of their Copa Classic B counterparts.
Same models, separate selectable identities, nothing inherited between them.

These two were missed when batch 10 and batch 11 were processed, because drafts
were selected by the time they were written rather than by whether their
identity was already curated. One fell between the two windows and the other
three minutes before a cutoff. Selecting drafts by what is not yet covered finds
them regardless of when they were driven, and is what should be used.

Copa Classic FL now holds four curated identities: Fusca, Gol, Passat and Puma
GTB.

## Completed in dataset 0.3.34 (class sweep batch 11)

Six of seven promoted, from three classes the queue had never seen.

The five Copa Trucks are the interesting ones. A tester found first gear
effectively unavailable in normal running and took it for a fault; it is the
real specification faithfully modelled. The championship's trucks use a
five-speed plus a launch gear, with first only used to pull away, which is
exactly the six gears the drive observed. The regulations mandate a
mechanically operated H-pattern manual gearbox but leave its design free, so
engagement type is not established and the downshift blip stays `unknown`.

Iveco Stralis, MAN TGX, Mercedes-Benz Actros and Volkswagen Constellation all
appear in the championship's own list of competing manufacturers. Vulkan does
not, so it is recorded as Reiza's own entry with no real-world truck claimed,
at medium confidence.

Chevrolet Montana is a pickup-bodied racer of the 2010 to 2012 Copa Chevrolet
Montana: a 5.7-litre V8 on a sequential stick, with automatic cut and blip, so
the driver supplies neither.

Copa Uno is held back. The drive read an H-pattern with no automation, while a
community AMS2 reference lists a sequential stick. The same reference was wrong
about the ARC Camaro's gear count, and the tester distinguished a sequential
stick on the Montana in this very batch, so the observation is the stronger
evidence. It is worth one confirming look before a record tells drivers to fit
the wrong shifter.

## Completed in dataset 0.3.32 (class sweep batch 10)

The first batch driven by walking the simulator's own class list rather than the
generated queue, and it justified the change immediately: **all six cars were
absent from the 231-identity queue entirely.** Not queued and unverified, but
invisible, because nothing in the pipeline can see a car that has never been
loaded on this PC. Copa Classic B was known to hold three cars; this sweep found
three more in it.

Five are promoted here. Caterham 620R and Caterham Superlight are sequential
six-speeds with automatic cut, which makes them different cars from the curated
Caterham Academy and Supersport, five-speed H-pattern cars sharing only the Seven
name. Nothing is inherited between them. MINI Cooper S 1965 B, Passat Classic B
and Uno Classic B are H-pattern road cars with no automation.

The Mini exposes a limit of the `manual_blip` field. Its four-speed is the
three-synchromesh type fitted to all Minis from 1959 to 1968, so second, third
and fourth are synchronised but **first gear is unsynchronised**. The blip is
recorded `optional`, because the synchronised gears are the ones changed while
racing, and the first-gear exception is written into the record notes rather than
forced into a field that cannot express it.

ARC Camaro followed in dataset 0.3.33 once its gear count was settled. It is an
Aussie Racing Car: a silhouette racer of the Australian one-make championship
carrying a Camaro body on a spaceframe, powered by a second-hand Yamaha FJR1300
motorcycle engine whose gearbox it uses. Chevrolet is not its manufacturer.

A community AMS2 database lists six gears. The drive found five, the driver
confirmed five in-game, and the donor FJR1300 is a five-speed until 2016, so
five is recorded and independently corroborated by the engine it came from.

Its downshift blip is `required` on the reasoning that a motorcycle-derived
racing sequential engages by dogs. Descriptions of the championship car as
having a dog engagement gearbox appear in search results attributed to the
championship but could not be retrieved from its site, so that wording is not
cited and the construction is recorded as an inference.

## Completed in dataset 0.3.31 (open-wheel batch 09, 1983 to 1986 turbo era)

Five cars, each carrying two identities. Brabham BMW BT52, McLaren Cosworth
MP4/1C and Lotus Renault 98T are real cars on racing Hewlands, so their downshift
blip is `required`; Formula Classic Gen1 Model1 and Model2 are Reiza's
fictionalised cars and keep `unknown` gearbox construction. All five are
five-speed H-pattern on a standard gate with no automation.

These were driven twice. The first pass used the guided drive before its
downshift engagement check existed, and that detector could accept a damaged
gearbox that never engaged. The redrive on the fixed build returned identical
values for all five, so the readings stand on an instrument that cannot
false-pass.

**Aero configurations follow the circuit, not the driver.** Reiza's v1.4.1.0
notes state that selection screens show the variant appropriate to the current
circuit, and driving at Laguna Seca then loading at Daytona produced two
identities per car. Each record therefore carries both: the driven
`- High Downforce` identity and the plain low-downforce name as an untested aero
configuration. Without that, a driver would be reported unmatched purely for
choosing a different track.

Which name means which variant cannot be guessed. Here the suffix marks high
downforce and the plain name is low; among the curated sports and GT cars the
plain name is the default and the suffix marks low downforce.

**Lotus Renault 98T carries the first gear-count override.** Its real gearbox is
a Lotus/Hewland six-speed; AMS2 models five. The drive reported five, which is
only a minimum, so the count was confirmed deliberately in-game before recording
the deviation. The record keeps the sourced six and states five as an explicit
simulator override.

`Lotus 98T` is retired rather than aliased. It is a pre-rename identity that the
certified build no longer produces in either aero configuration.

## Completed in dataset 0.3.30 (open-wheel batch 08, earliest era)

Six cars from 1967 to 1979, and they are uniform: five H-pattern gears on a
standard gate, clutch to pull away, a throttle lift to upshift, and no automatic
cut or blip anywhere. Round rims with no display or shift lights.

A dogleg gate was expected here and none was found. The expectation came from a
search summary of a forum post claiming most early Hewlands place first left and
back; the reachable sources do not support it, so no dogleg was recorded. These
cars have no gate plate, and the gates were read by watching the lever and the
driver's hand through a shift. That method read three doglegs in dataset 0.3.28
which registered sources then corroborated, so it distinguishes the two gates
rather than defaulting to one.

Brabham BT26A and Lotus 49C are the first `dogbox` records established from
evidence rather than observed behaviour. Both use racing Hewlands, engaged by
dog rings rather than synchronisers, so a downshift blip is `required`. Their
sources name the gearbox model but not its engagement, so the dog-ring
construction is an inference from Hewland's design approach and each record says
what would falsify it.

Formula Vintage Gen1 Model1 and Model2, Formula Retro V12 and Formula Retro Gen2
are Reiza's fictionalised cars. No real-world chassis is assigned, so their
gearbox construction and downshift blip stay `unknown`. The two Vintage models
were reviewed independently of each other.

## Completed in dataset 0.3.29 (club and road batch 07)

Ten cars, which finish every category except open-wheel.

Eight are ordinary synchromesh H-pattern cars with no automation of any kind:
Caterham Academy and Supersport, Chevrolet Chevette, Copa Fusca, Ginetta G40 Cup,
Gol Classic B and FL, Puma GTB and Puma P052. Each needs the clutch to pull away
and a throttle lift to upshift, and each takes an optional downshift blip.

The two GT5 cars were found under a class of their own, and one of them is the
batch's real finding. **Ginetta G40 is not the G40 Cup.** The Cup car is a
five-speed synchromesh H-pattern; the GT5 Challenge car is a six-speed Quaife
sequential, and the drive found automatic blip without automatic cut, a pairing
no other curated sequential-stick car has. Its downshift blip stays `unknown`:
AMS2 blips for the driver, but nothing establishes that the real Quaife box does,
and a dog-engagement sequential would normally need one. Sharing a nameplate was
never grounds to share controls, and here it would have been badly wrong.

This batch also settled what `manual_blip` asserts. It now means mechanical
necessity, so `required` is reserved for gearboxes that cannot engage without a
blip and synchromesh cars are `optional`. Audi V8 quattro DTM, Dodge Viper ACR
and Lamborghini Miura SV were corrected to match; they had been recorded under
two contradictory readings of the same field. The Miura's basis was rewritten
too, because it asserted synchromesh from evidence that mentioned only a
five-speed H-pattern manual, and the blip now depends on that construction.

Both Caterhams are `medium` confidence for the same reason: Caterham's own
motorsport partner offers the Type 9 five-speed in synchronised and
dog-engagement forms, so their construction is inferred from the cars being road
legal rather than stated by a source, and each record says so.

The Caterham Academy drove as a five-speed against a SimHub hint of four.

## Completed in dataset 0.3.28 (touring and stock batch 06)

Six cars, and the first records whose gate pattern comes from a guided drive
rather than a reviewer reading a specification.

BMW M1 Procar, Mercedes-Benz 190E 2.5-16 Evolution II and BMW M3 Sport Evolution
were all observed with a dogleg gate in the cockpit, and all three are
independently corroborated: a ZF five-speed with first out of the shift plane for
the M1, a dog-leg Getrag for the 190E, and a Getrag 265 for the M3. Each needs
the clutch to pull away, a throttle lift to upshift and a manual blip to
downshift.

Chevrolet Omega Stock Car 1999 shares that manual technique but was observed on a
standard gate. Its identity and straight-six engine are sourced; no reviewed
source documents its gearbox, so its transmission rests on the drive alone and
the record is medium confidence.

Super V8 is Reiza's fictionalised Australian Supercars car. The championship
confirmed that Gen3 retains a manual stick shift on the Albins six-speed
sequential transaxle, which is why it is shifted by a lever where a modern GT
uses paddles.

Toyota Corolla Stock Car 2022 is the modern outlier: paddles, six gears and full
automation, reviewed independently of the curated 2024 Corolla.

Zakspeed Ford Capri Group 5 and BMW 320 Turbo Gr5 were dropped from the batch as
third-party content that is not installed.

## Completed in dataset 0.3.27 (historic GT and GTE batch 05)

Five cars that complete the GT family, splitting three ways.

Nissan R390 GT1 and Porsche 911 GT1-98 are late-1990s Le Mans cars: sequential
lever, six gears, clutch to pull away, automatic cut but no automatic blip, so
the driver supplies the downshift blip. Both carry their `- Low Downforce` alias
as an explicit inherited identity.

Chevrolet Corvette C8.R and Porsche 911 RSR are modern GTE cars and behave like
the GT3 group: clutch-free move-off, six paddle gears, automatic cut and blip.

Puma GTE is not a GTE racer at all. It is a Brazilian road car built from 1970
to 1980 on Volkswagen running gear, classed by AMS2 under Copa Classic B, and it
has no automation whatever: four H-pattern gears, clutch to pull away, a throttle
lift to upshift and a manual blip to downshift. Its 150-gear telemetry hint was
the worst seen in the inventory; the real count is four.

The GT family is now fully verified.

## Completed in dataset 0.3.26 (GT4 batch 04)

Six GT4 cars, and unlike the GT3 batch they are not uniform.

Three are dual-clutch cars whose gearbox comes from the road car rather than a
racing sequential, which is why they carry seven gears where most GT4 cars have
six: BMW M4 GT4 (F82, a seven-gear dual clutch with motorsport software),
McLaren 570S GT4 (Oerlikon Graziano seven-speed dual clutch SSG), and Porsche
718 Cayman GT4 Clubsport MR (six-speed PDK).

Mercedes-AMG GT4 uses a purpose-built pneumatic sequential six-speed transaxle.
Ginetta G55 GT4 and G55 GT4 Supercup use the Hewland six-speed of the G55
platform and require the clutch to pull away; the Supercup is classed separately
by AMS2 and is reviewed independently rather than inherited from the GT4 car.

The Cayman carries the first `simulators[].overrides` entry in the dataset. Its
real gearbox is a PDK with no clutch pedal, so the record states that the
standing-start clutch is not required, while an explicit sourced override
records that AMS2 1.6.9.91 requires clutch input to move off. The client applies
overrides when building guidance, so the driver is told to use the clutch
in-sim while the real-car value stays true.

## Completed in dataset 0.3.25 (aero inheritance, no driving)

`BMW M4 GT3 - Low Downforce` and `Porsche 992 GT3 R - Low Downforce` became
explicit aliases of the base records verified in batch 03, each disclosed as an
untested aero configuration. No control value changed and no record was added.
Three Low Downforce identities still wait on unverified base cars.

## Completed in dataset 0.3.24 (contemporary GT batch 03)

Eight GT cars, promoted through `import-observation` and `promote-observation`.

Seven are paddle-shift GT3 cars with identical controls: clutch-free move-off,
six paddle gears, automatic cut and blip. BMW M4 GT3 and M6 GT3, Mercedes-AMG
GT3 and GT3 Evo, Nissan GT-R NISMO GT3, and Porsche 911 GT3 R (991.2) and 911
GT3 R (992). Each carries a manufacturer source for its six-speed sequential
transmission; BMW state that the M4 GT3 has no clutch pedal at all, which
corroborates the clutch-free move-off rather than merely matching it.

Ginetta G55 GT3 is the outlier and was verified independently: AMS2 classes it
as GT Open, it is shifted by a sequential lever, and it requires the clutch to
pull away. The drive detected automatic cut and blip despite the lever, a
pairing with no precedent among curated cars, so its throttle lift and manual
blip stay `unknown` rather than being inferred.

Verifying the BMW M4 GT3 and Porsche 992 GT3 R makes their `- Low Downforce`
identities inheritance-ready.

## Completed in dataset 0.3.23 (aero inheritance, no driving)

`Nissan R89C - Low Downforce` and `Porsche 962C - Low Downforce` became explicit
aliases of the base records verified in batch 02, each disclosed as an untested
aero configuration. No control value changed and no record was added. Five Low
Downforce identities still wait on unverified base cars.

## Completed in dataset 0.3.22 (modern-prototype batch 02)

Promoted through `import-observation` and `promote-observation`, the first batch
to use that command end to end rather than an ad-hoc script:

1. Nissan R89C (Group C, 1989) - clutch to pull away, five H-pattern gears,
   throttle lift to upshift, manual blip to downshift, no automatic cut or blip.
   Nissan's heritage record supplies the VGC five-speed and Lola-built chassis.
2. Porsche 962C (Group C, 1987) - same manual technique. Gearbox construction
   and H-pattern layout stay unknown: the reviewed sources establish only a
   five-speed manual.
3. MetalMoro MRX Duratec P4 - sequential stick, six gears, clutch to pull away,
   automatic cut, no automatic blip, so the driver supplies the downshift blip.
   Metalmoro fixes no transmission for the MRX, so the sequential six-speed is
   medium confidence as the configuration modeled in AMS2.

Mazda 787b was dropped from the batch: it is modded content, and Reiza holds no
Mazda licence, so AMS2 ships no official Mazda.

Verifying these bases moves `Nissan R89C - Low Downforce` and
`Porsche 962C - Low Downforce` to inheritance-ready.

Dataset 0.3.18 completes the earlier audited queue. It deliberately counted
selectable model/configuration identities, not release-note classes, renames, or
generic aero announcements.

## Completed in dataset 0.3.21 (identity review, no driving)

Explicit aliases added to already curated records:

1. Formula Edge Model1, Model2, and Model3, and Formula V8 Gen1 (B). Each plain
   name is the same car observed before its aero suffix existed, inherited from
   the verified `- High Downforce` configuration and disclosed as not separately
   tested.
2. `Stock USA Gen1 - Speedway ` with trailing whitespace. Runtime matching is
   exact and untrimmed, so without this alias that stored identity would be
   reported unmatched to the driver.

Closed as reviewed decisions in `research/ams2-identity-decisions.json`:

- Three retired pre-rename identities of official cars: Formula V10 Gen2,
  Formula Vee Fin, and Formula V12. AMS2 v1.6.9.5 rebranded the single-make
  Formula V12 class as Formula Edge and identifies the former V12 car as
  Model 1. Formula V10 Gen2 is the only one without a single successor, because
  it predates the tyre and aero split into two curated records.
- None of the three is aliased onto its renamed record, because none is
  selectable in AMS2 1.6.9.91. Formula V12 additionally must not inherit, since
  its rebrand accompanied the rule changes that caused the largest downforce
  drop since 1983, so the retired identity is not the same car to drive.
- Three third-party identities from the ThunderFlash mods pack: FIA-GT1
  Lamborghini Murcielago R-SV GT1, FIA-GT1 Maserati MC12 GT1, and
  LamborghiniHuracanLP6202SuperTrofeo, the last a mod ported from Project CARS
  2. AMS2 never shipped a Murcielago R-SV, and the official Murcielago R-GT,
  Maserati MC12 GT1, and Huracan Super Trofeo EVO2 are separate cars curated
  under their own identities. None of the modded identities is aliased onto
  them, and the Huracan one leaves the guided-verification queue, which drops
  from 90 to 89.
- BMW M3 Safety Car is out of product scope as a non-racing vehicle and stays
  unmatched in the client rather than receiving guessed controls.

## Completed in dataset 0.3.20 (aero-inheritance review, no driving)

Seven exact `- Low Downforce` identities whose base record was already verified
became explicit aliases with an untested-aero disclosure: Audi R8 LMP1, Courage
C60 Hybrid, Dallara SP1, Dodge Viper GTS-R, McLaren 720S GT3 Evo, McLaren F1
GTR, and Sauber Mercedes C9. No control value changed and no record was added.

The `aero-inheritance-ready` queue is now empty. Seven Low Downforce identities
remain blocked behind an unverified base car.

## Completed in dataset 0.3.19 (modern-prototype batch 01)

Guided-verification drives promoted through the `import-observation` staging
tool, then reviewed with registered real-world sources:

1. BMW M Hybrid V8 (LMDh) — clutch-free move-off, seven paddle gears, automatic
   cut and blip; prototype display rim.
2. Porsche 963 (LMDh) — as above; the live drive confirmed seven forward gears.
3. Chevrolet Corvette GTP (1988 IMSA GTP) — H-pattern, five gears, standing-start
   clutch required, throttle lift to upshift, manual blip to downshift, no
   automatic cut or blip (Hewland VGC racing gearbox).
4. MetalMoro AJR Chevrolet (P1) — clutch-free move-off, six paddle gears,
   automatic cut and blip.
5. MetalMoro AJR Gen2 Chevrolet (P1Gen2) — reviewed independently from the base
   AJR; six paddle gears, automatic cut and blip.

The BMW, Porsche, and Corvette base records each carry their exact `- Low
Downforce` alias as an explicit inherited identity with an untested-aero note.

The next prototype batch is Mazda 787B, Nissan R89C, Porsche 962C, and MetalMoro
MRX Duratec P4 (see `docs/ams2-coverage-plan.md`).

## Completed in dataset 0.3.18

1. Stock USA Gen3 LM.
2. F-Edge Model1.
3. F-Edge Model2.
4. F-Edge Model3.
5. Formula V10 Gen3 (B).
6. Formula V10 Gen3 (M).
7. Formula V8 Gen1 (B).
8. Formula V8 Gen1 (M).
9. Formula V8 Gen2 M1, observed under the exact telemetry label
   `Formula V8 Gen2 - High Downforce`.

## Not separate car tests

- Stock Car Pro Series 2024 is represented by its tested Cruze and Corolla
  members.
- Formula Hybrid Gen1/Gen3, Formula V8 Gen3, and Formula V10 Gen2 current names
  are linked to their verified records.
- Formula V10 Gen3, Formula V8 Gen1, Formula V8 Gen2, Formula Edge, 2004 GTR,
  2005 GT1/GT2/LMP1/LMP2, Ligier European Series, and GT2 2005 are class-level
  release events; their selectable members are the test units.
- Generic High Downforce and Low Downforce announcements do not require a full
  duplicate test when the base controls are verified. Each inherited identity
  must still be explicit and carry an untested-configuration note.
- Cadillac V-Series.R was verified earlier in the live prototype batch: hybrid
  clutch-free move-off, seven paddle gears, automatic cut and blip, and a closed
  prototype display rim. Its Low Downforce identity inherits those controls with
  an explicit untested-aero note.
- The unnamed second Aston Martin Vantage GT3 Evo configuration remains an
  identity-research note until an exact selectable/telemetry name is observed.
