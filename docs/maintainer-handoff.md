# Maintainer handoff

This is the detailed operational snapshot for maintainers. It supplements the
concise repository rules in `AGENTS.md`; read the relevant section when working
on the associated area.

## Repository history rewrite, 2026-08-29

The history was rewritten twice with `git filter-repo` and force-pushed the same
day, removing `output/pdf/homologation-form-renders/` (~95 MB of FIA
homologation page renders that nothing referenced) and
`docs/design/2026-08-11-icon-brand-concepts/` (5 MB of review-only boards). The
pack went from 198.6 MB to 4.96 MB with all commits intact.

- `main` holds the rewritten history and is the only branch; it was
  fast-forwarded off its stranded initial commit.
- Every commit from `232187a` forward has a new hash. Another clone of this
  repository must re-clone rather than pull.
- `../authentic-controls-db-prepurge-2026-08-29/` is the only complete
  pre-rewrite copy. Keep it.
- `main` is the default and only branch. The repository is public as of
  2026-08-29.

## Current operational state

- Client: 0.21.2 locally; 0.21.0 is the published release.
- Dataset: 0.5.46 with 282 curated records, and 0.5.37 is installed. The
  installed local plugin build includes the GPLaps theme and GTR2 identity
  resolver.
- Tested target: SimHub 9.11.22 and AMS2 1.6.9.91 on Windows.
- The ignored local contribution queue has 38 accepted cases with published
  feedback and six withdrawn, with nothing waiting on research or final review.
  Issues 46 through 48 are published curated-identity comparisons whose reviewed
  corrections produced dataset 0.5.33. Issue 1 for the Chevrolet Cruze Stock
  Car 2021 was restored from its original `new-identity` receipt after an
  exact-resubmission classification hid the already-stored draft, and is now
  published. Issues 31 through 33 are also published comparison cases; none
  needs further reconciliation.
- Use the maintainer workbench for contribution processing. Synchronization is
  serialized across browser tabs, and a same-issue retry with an unchanged
  attachment preserves the original classification. Issue 12 was restored as
  `new-identity` after exposing the former race and is now published.
- After a research brief creates its result template, the workbench provides an
  inline JSON editor through partial, blocked, final-review, and manifest-review
  states. Saving runs the normal import validation; revising a manifest-review
  result requires preparing the proposal again. Promoted records remain
  immutable and later corrections begin with a new research issue.
- The **Improve an existing car** issue form also enters the workbench through
  the shared `contribution` label. It resolves one curated record exactly and
  produces a source-backed, field-level research amendment; it never fabricates
  a guided-drive observation.

## Simulator coverage and disagreements

- Of 370 AMS2 identities observed on this PC, 355 are covered exactly and 15
  are closed by written decisions. No observed identity currently awaits guided
  verification. New content can still be absent because the inventory only
  contains cars loaded here. See `docs/ams2-coverage-plan.md`.
- Eight simulators are registered: 261 AMS2 entries, 21 AC, 18 ACC, 7 AC EVO,
  6 RaceRoom, 5 rFactor 2, 2 PMR and 2 GTR2 entries. `ac-rally` is reserved in
  the enums and not wired into the client. PMR's E46 and Nissan R390 GT1 drafts
  are curated. GTR2's HQ BMW M3 GTR and Chevrolet Corvette C5-R drives are also
  curated, using the exact `.CAR` identity resolved from the current
  telemetry-session header. A drive from an unregistered game is held rather
  than lost and released when that game is registered; see
  `docs/registering-a-simulator.md` and
  `docs/raceroom-downshift-measurement.md` for what telemetry can establish.
- Assetto Corsa EVO is the active second-simulator development track. Seven
  records now carry reviewed AC EVO entries; this is development coverage, not
  part of the tested target. `docs/ac-evo-coverage-plan.md` owns its drive order
  and open questions.
- Assetto Corsa Competizione is recognized as `acc`; 18 exact entries are
  reviewed, including the completed ranked-ten comparison batch. ACC drafts
  record the exact Steam content build because its executables expose no useful
  file version. This remains development coverage outside the tested target.
  `docs/acc-coverage-plan.md` owns its drive order and identity traps.
- Original Assetto Corsa development now covers 21 records: seven AC-only and
  14 shared with another simulator. Each source fingerprints the exact installed
  implementation; this remains development coverage outside the tested target.
- The AC BMW 3.0 CSL and Ford GT40 Mk I guided drives require a manual blip in
  those implementations. That result is stored as a simulator override while
  the authentic real-car manual-blip field remains unknown.
- The disagreement audit contains 37 findings across 23 cars: 13 supported
  departures, eight provisional departures and 16 open authentic baselines. The
  provisional set now also includes BMW M3 E46 GTR and Nissan R390 GT1 wheel
  geometry plus Chevrolet Corvette C5-R manual-blip, shift actuation, and shift
  pattern after their additional simulator drives. The exact 2005 Saleen S7-R
  wheel and downshift procedure remain open; early-car evidence cannot be
  inherited. Treat the remaining gaps as documented negative results, not an
  active batch to search again without a new exact-source lead.

## Review-only assets

Icon and brand-mark concepts under `docs/design/` are review-only and are not
wired into production assets.
