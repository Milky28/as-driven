# Driver summaries

`driver_summary` is a short paragraph shown on the preflight card. FIT and USE
already describe equipment and shifting requirements. The summary should add
something useful, distinctive or interesting about this car.

## What to write

Prefer supported design, historical or competition context: why the car exists,
what distinguishes it, or the real racing category and era it represents.
Relevant technique is welcome when it explains something helpful or interesting,
especially when no stronger contextual story is available. A particular gearbox
quirk, launch procedure, or difference between permitted and advisable technique
can earn its place. An ordinary five-speed road manual does not need its FIT and
USE rows repeated as prose.

For generic or fictional simulator classes, describe the supported real-world
category and era, typical construction and driving. A shared paragraph across a
genuine class or generation is preferable to blanks. Distinguish class context
from exact chassis identity: a class inspired by a Formula One era does not prove
which real car each model depicts or which physical controls it has. Confirm
changes between generations before sharing text. Historical rules are not claims
that the simulator implements those rules.

Keep an existing useful summary. Avoid generic praise, repeated controls,
research-process caveats and filler such as "not established, so use it to be
safe". If no supported useful information can be found, omit the optional field.
Do not manufacture a story to meet a completeness target.

## Evidence and wording

Every material assertion needs cited support and correct applicability. Read the
source text, not just its title. Record sources, exact locators, confidence and
a falsifiable basis in the research/review packet. Prefer manufacturer, team,
organiser, regulations or firsthand accounts. Label secondary evidence and fetch
limits honestly. A name such as "Hybrid" does not establish a hybrid powertrain;
a source saying engines were drawn by lot does not say whole cars were.

Keep real-car facts separate from exact simulator observations. Do not use a
summary to resolve an uncertain gearbox or identity by inference. Advice may
explain a consequence of an established mechanism, but avoid claims that every
unmatched downshift locks wheels or damages a gearbox. Actual damage claims and
simulator damage modelling need evidence. Simulator-general advice belongs with
the simulator, not in every car's summary.

Lead with the interesting point, then explain its significance. No mandatory
three-part template. Aim for a compact paragraph, normally around 200-300
characters; the schema owns the hard limit. Check actual card wrapping before
application. Shared class prose still needs a review of each member's scope.

## New contributions and generated proposals

The contribution research brief asks for an optional established
`/driver_summary` claim in `research-result.json`, with the paragraph as
`proposed_value`, source references, confidence and basis. Source locators should
list `/driver_summary` among the paths they support. Omit unsupported drafts.
The existing research validator checks the target type/length and references.

`prepare-review` carries that sourced draft into the proposed manifest, provenance,
preview and final review. Existing reviewed summaries are preserved when adding a
simulator contribution. The researcher supplies the prose; the deterministic
`generate_driver_summary` fallback cannot invent historical or class facts from
control enums. Without a researched paragraph, it only drafts known simulator
technique disagreements and otherwise leaves the field absent.

The summary edit/generation action still supports explicit maintainer revisions
and reruns the proposal dry run. Existing-car research amendments continue to use
that explicit summary review action. New text is always a proposal, never
permission to promote, overwrite reviewed prose or publish automatically.

## Audit and review

Maintainer-authorized batches may prepare candidates, including shared class
paragraphs. Keep candidates outside `data/v1` and retain originals, exact record
IDs, sources, dispositions and unresolved issues. Coordinator review is required:
passing schema and layout checks establishes neither factual accuracy nor
editorial quality. Apply only after explicit review approval. An approved audit
edits `driver_summary` in the records directly and keeps its evidence in a tracked
research file: the previous text, the applied text, inspected sources, basis and
open questions for every record. The September 2026 audit of all 337 records at
dataset 0.6.43 is `research/driver-summary-audit-2026-09.json`.
