# Contributing

Contributions should make a claim easier to verify, not merely add more fields.

The scope is hardware selection and authentic control technique. Do not add
general performance specifications, electronics, or other available source
fields without an approved user-facing control use case. Steering DOR may be
contributed as optional reference metadata, but its absence is not an error.

## Source hierarchy

Use the strongest available evidence:

1. manufacturer, team, sanctioning body, homologation, or workshop material;
2. official simulator documentation, release notes, or vehicle manuals;
3. direct in-game observation with game version and reproducible steps;
4. established community research with a named author and stable URL;
5. inference, clearly labeled and used only when better evidence is absent.

AI output, a search-result snippet, or another database without traceable
sources is not evidence. A source may support real-car hardware, simulator
behavior, or both; do not silently extend it to the other domain.

## Provenance rules

- Add stable metadata to `data/v1/sources.json` and reference its `source_id`.
- Name an AMS2 live-observation source
  `ams2.local-live-<car>-controls.<game-version>`, matching the record slug and
  the tested build. The validator enforces this so a car's drive evidence is
  predictable from its name; other publishers keep their own prefixes.
- Use JSON Pointer paths in `provenance.claims`. Group paths only when the same
  evidence and confidence apply.
- State the basis: what the source directly says or what was observed.
- Use `inferred` confidence only with a written inference and competing
  explanations considered.
- Archive URLs are encouraged where permitted, but do not archive content that
  forbids it.
- Paraphrase. Do not paste lengthy source text or proprietary tables.
- A missing value remains `unknown`; absence must be supported or be produced
  by a documented source-specific rule.

## Confidence levels

- `verified`: checked against a primary source or reproducible game behavior by
  a reviewer.
- `high`: directly supported by a strong source but not independently checked.
- `medium`: credible secondary/community source or limited observation.
- `low`: plausible inference kept visible for follow-up.
- `unknown`: no evidence sufficient for a claim.

Confidence measures evidence, not contributor certainty.

## Pull request checklist

- Keep record IDs stable and lowercase (`simulator.slug`).
- Put real-world facts in `authentic_controls` and game behavior in
  `simulators[].behavior`.
- Represent a difference with an override; do not rewrite authentic history to
  match a game limitation.
- Include `verified_game_version`, `verified_at`, and source references.
- Update `data/v1/index.json` for added or removed records.
- Run `python -m as_driven_db validate` and the unit tests.
- Explain licensing or reuse terms for any proposed bulk import.
