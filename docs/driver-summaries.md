# Driver summaries

`driver_summary` is the one line of prose the preflight card shows a driver. It
is optional, and a car that needs nothing said should say nothing.

## What it is for

The Fit and Use bands answer **what the car requires**. The summary answers
**what a driver does about it, and why**.

That distinction is the whole point. Nearly every car in the dataset records
`clutch: not-required` for running shifts, because that is what the simulator
accepts. It is also what an experienced driver frequently ignores: a driver of a
2005 GT1 car can bang each gear in and often chooses to clutch instead. The band
can only ever say "no clutch needed", which is true and incomplete. The summary
is where the rest goes.

A summary earns its place when it carries one of three things.

**A named mechanism and what follows from it.** "Hewland FG400" or "three
synchromesh gears and a crash first" tells a driver what they are handling, and
the technique follows from it. A gear count and an actuation do not.

**Permitted against advisable.** Where the car accepts something a driver would
not choose, say so and say why. This is advisory rather than descriptive, and it
is the only part of the record that is.

**Where the simulator and the car part company.** The card marks the divergence
with a row-level flag; the summary explains it in a sentence.

It should not restate the bands. "Six-speed sequential, no clutch needed" is
already on the card twice.

## House order

Three parts, in this order, so that a hundred summaries do not each invent a
shape:

1. **What it is** - the named unit or construction, in a clause.
2. **What to do** - the technique that follows.
3. **What to watch** - the caveat, divergence, or the thing that bites.

Not every summary needs all three. The order holds for the parts that are there.

> Three-synchromesh gearbox: second, third and fourth have synchronisers and
> first does not, on every Mini until September 1968. Blip to ease the
> synchronised gears, and match revs yourself for any downshift into first.

*What it is*, then *what to do*, then *what to watch*.

## Advisory wording

Advice may be firm. "Clutch the downshifts" is more useful than "you may wish to
consider clutching". But what may be asserted depends on what kind of claim it
is, and the two are not symmetric.

**A handling consequence needs no per-car evidence.** Blipping a downshift to
stop the driven wheels locking follows from the mechanism, the way "the synchros
do the matching" does. Say it plainly.

**A damage claim needs evidence.** "This will hurt the gearbox" must rest on
something observed. By that standard the dataset can say it about almost
nothing: across roughly 262 guided drives, the drive's damage outcome has never
been recorded once, and exactly one car - the Mercedes-Benz Actros - recorded a
gearbox that refused the gear outright. AMS2 does not appear to model dog-ring
wear at all.

**Never state damage the simulator does not model**, even where the real car
would suffer for it. A driver instructed to protect a gearbox that cannot break
is being told to drive around a problem that is not there. This is the same
sim-and-real line the override layer draws.

## Where simulator-general advice goes

Advice true of every car in a simulator does not belong in a summary. Written
into a hundred records it becomes a hundred copies free to drift apart, and it
crowds out the car-specific thing the summary exists to say. Record it once
against the simulator instead.

A summary carries what is true of **this car**.

## By equipment

Counts are of curated records at dataset 0.4.32.

### H-pattern, synchromesh (54 cars)

The band says lift to upshift and treats the blip as optional. The summary says
why it is optional: the synchronisers do the rev matching, so the blip eases
them rather than engaging the gear. Worth adding where a particular box is
weaker than the rest of the car, or where a gear is not synchronised at all.

### H-pattern, dog box (10 cars)

Dogs engage by impact. A firm, decisive movement is kinder than a hesitant one,
and rev matching matters more than it does with synchronisers. Name the unit
where a source gives one.

### Sequential stick (58 cars)

The largest gap in the dataset: 58 cars, four summaries. One gear at a time and
no skipping. The box accepts a clutchless shift; whether a driver uses the
clutch anyway is the real question, and depends on the car and the race length.
Blip the downshift where the car does not do it for you - not to save the
gearbox, but to keep the driven wheels from locking.

### Paddle sequential (72 cars)

Seventy-two cars, one summary. Say what the electronics do, so the driver knows
what is being done for them: cut on the upshift, blip on the downshift. Then say
what is still theirs - twenty-five of these still need a clutch to pull away. A
paddle is a request rather than a command, and the box may refuse a downshift
that would over-rev the engine.

### Paddle semi-automatic (20 cars)

The early Formula One pattern: the clutch is hydraulic and the driver only meets
it at the start. The launch procedure is usually the whole story.

### Paddle dual-clutch and automatic (10 cars)

Road-derived boxes that may creep, may shift themselves, and may accept a manual
override that is never required. Say which.

## Writing them

Summaries are written per record with the maintainer, never generated in bulk.
A shared sentence across several cars is fine where the cars genuinely share a
story - seventeen Reiza cars have no real chassis to establish a gearbox from,
and four Copa Truck entries run to one set of regulations - and misleading where
they do not. Eleven category texts once covered seventy-five records, and two of
them were wrong about the car they were printed on.
