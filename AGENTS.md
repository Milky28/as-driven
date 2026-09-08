# As Driven project guidance

## Purpose and scope

Answer: which physical controls should I use, and how should I shift this car?
The versioned JSON database is the source of truth; SimHub is one read-only
client. Cover rim category, shifter actuation/pattern/gears, clutch technique,
lift/cut/blipping, and optional steering DOR. General car specifications,
driver aids, and unrelated electronics are out of scope.
Steering DOR remains for compatibility; do not start new research for it or
populate the real-car field from simulator settings.

## Evidence and review

- Preserve `unknown`; absence of evidence is not `no`.
- Every material claim needs sources, confidence, and a falsifiable basis.
- Keep real-car facts separate from simulator observations. Observations need
  an exact verified game version and check date.
- Match simulator identities exactly. Never silently fuzzy-match or treat
  chassis manufacturer as the vehicle marque.
- Keep candidates outside `data/v1` until explicit review approval. Use the
  existing promotion tools to write records, approvals, sources, and index.
- Established mechanisms may settle technique; technique cannot establish a
  mechanism. Follow `docs/data-model.md` for the actual derivation rules.
- Registered sources must be cited or declare `establishes: nothing` with notes
  explaining what was examined and why it settled nothing.
- Overrides describe simulator differences or observations over an unknown
  baseline. Do not add overrides agreeing with the authentic value.
- `driver_summary` is optional. Do not invent one to complete a record; follow
  `docs/driver-summaries.md` and write manual summaries with the maintainer.
- Preserve the checked-in coverage inventory when local inputs are absent.
  Refreshing it must not silently discard previously observed identities.

The schemas own field types, required fields, ranges, and vocabularies.
`as_driven_db/validate.py` owns cross-record and evidence relationships. Tests
exercise those rules and client behavior; avoid duplicating schema constraints
or turning punctuation, JSON whitespace, colors, or fixed layout dimensions
into correctness gates. Use `python -m as_driven_db format-records` after manual
car JSON edits; import and promotion tools already format their output.

## Working discipline

- Use a separate Git worktree on a task-specific `codex/` branch for code,
  documentation, and other tracked implementation changes; integrate deliberately.
  Never edit, stage, stash, or commit another worker's uncommitted changes.
- Routine contribution research and proposal preparation use the main checkout
  and its ignored `build/review-cases` queue, shared with the workbench. Do not
  create a worktree just to research a case. Preparation leaves curated files
  unchanged; promotion still requires explicit approval. See the maintainer
  workflow for commands targeting this queue from another directory.
- Complete the requested behavior and necessary consequences. Report unrelated
  cleanup separately. A small correction should not become a repository audit.
- Prefer small, direct modifications. Retain standard SimHub `IPlugin`,
  `IDataPlugin`, `IWPFSettings`, and `PluginManager` integration and the existing
  .NET Framework target. Do not add layers or dependencies speculatively, or
  redistribute installed SimHub SDK assemblies.
- Keep the database independently usable. Update schema, documentation,
  validation, and meaningful tests together when changing a data contract.
- Never commit generated build/dist/bin/obj directories, caches, or local drafts.
- Builds must not install into SimHub. Installation, publishing, and contributor
  messages require the user's authorization for those actions. Drafts stay local.

## Verification

After data, schema, importer, research-manifest, or Python tooling changes:

```powershell
python -m as_driven_db validate
python -m unittest discover -s tests -v
```

After C#, SimHub adapter, XAML, dashboard, asset, or build-script changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

Run `git diff --check` before committing. Re-run checks after relevant changes
or failures; a passing unchanged result does not need to be repeated.

## Where to look

- Current dataset: `data/v1/index.json`; public counts: generated README block.
- Published update: `as-driven-latest.json`; client version: assembly metadata.
- Data changes: `CONTRIBUTING.md`, `docs/data-model.md`, `docs/evidence-boundaries.md`.
- Contributions: `docs/maintainer-review-workflow.md`. Prefer the assistant-led
  path using the existing CLI; the workbench remains available for the same cases.
- Build and releases: `docs/development.md`, `docs/releasing.md`, `release/README.md`.
- Installation and privacy: `docs/install.md`, `PRIVACY.md`.
- Contribution state, coverage, disagreements, or release history:
  `docs/maintainer-handoff.md`. Read it for those tasks, not routine changes.
- Closed research: `docs/gearbox-construction-research.md`. Reopen only with new
  evidence. `research/auto-blip-premeasurement.json` tracks remaining drive checks;
  clear those when naturally driven, not by scheduling a new batch.
