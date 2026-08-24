# Simulator-observation intake

The public contribution unit is one **simulator observation**, not one car
record. A guided drive establishes what one exact simulator implementation did
under recorded test conditions. It does not establish which real car that
implementation depicts, whether the real car behaves the same way, or whether a
new database record should exist.

Contributors submit one draft per GitHub issue through the **Submit a simulator
observation** form. The form accepts the JSON written by the SimHub plugin and
asks separately for optional real-car identity knowledge and sources. `I don't
know` is acceptable. Identity remains a maintainer review decision.

Nothing is uploaded automatically. After saving, the plugin can reveal the
exact file and open the contribution form only after an explicit click. The
contributor attaches the file in their browser.

## Public contents and attribution

A full public draft can contain:

- the chosen observer name or handle and exact observation timestamp;
- simulator, game, client, and dataset versions;
- exact telemetry names, internal identifiers, test results, and notes; and
- for Assetto Corsa, the driven package's content id, author, declared version,
  and fingerprint.

The implementation block identifies only the package driven for that
observation, not the contributor's complete installed library. It is nevertheless
public information once attached to a public issue and, when promoted, may remain
part of the released provenance.

The plugin may create an explicitly named redacted copy that replaces the
observer with `Anonymous` and removes the implementation block. That copy is a
research lead. In a mod-capable simulator it normally cannot support an
implementation-level promotion because the reviewed package is no longer
attributable. Private delivery does not by itself remove this boundary: any
implementation evidence selected for public release still needs publication
consent.

Contributors license their original factual observations and written notes for
incorporation under CC BY 4.0. A link to a manufacturer manual, regulation, or
other source does not relicense that source. Do not upload game files,
manufacturer documents, telemetry logs, or copied source text.

## Intake classifications

Validation and deduplication happen before identity research. An exact payload
hash answers only whether the same file was submitted twice. It never treats two
independent drives as duplicates.

| Classification | Meaning | Review action |
| --- | --- | --- |
| Exact resubmission | The submitted bytes match an already received draft. | Link the existing receipt and close the duplicate. |
| Corroboration | An independent drive of the same exact implementation is compatible with the reviewed result. | Retain it as additional simulator evidence. It does not strengthen the real-car baseline. |
| Contradiction | The same exact implementation and game version produced an incompatible established result. | Prioritise clarification or a repeat drive; never majority-vote the answer. |
| Changed implementation | The package identity is similar but its fingerprint or declared version differs. | Review it as a versioned implementation rather than silently inheriting old behaviour. |
| Additional implementation | Another package claims to depict an already-curated real car. | Resolve real-car identity first, then compare behaviour. |
| Correction | The contributor says an existing reviewed simulator view is wrong. | Preserve the old evidence and use the explicit correction promotion path. |
| New identity | No exact curated simulator identity matches. | Research the real car before creating or selecting a record. |

## Maintainer state

Each issue moves through a small, visible state machine:

```text
received -> schema-valid -> identity-research -> approved -> released
                         \-> needs-clarification
                         \-> declined
```

Suggested labels mirror these states. A maintainer—not the contributor—creates
the curation manifest and changes `data/v1`. The raw issue attachment remains
staging evidence and never enters the curated database automatically.

The local intake command validates the strict schema, records a SHA-256 receipt,
and compares the observation with previously received files and exact curated
simulator identities. It must not execute content from a draft, unpack arbitrary
archives, perform fuzzy identity matching, or promote a record.

Maintainers normally use `python -m as_driven_db review-submissions sync`
instead of downloading and running intake by hand. Synchronization is read-only
with respect to GitHub: it fetches open issues and their JSON attachments, then
runs the same intake and import functions into ignored local review cases. See
`docs/maintainer-review-workflow.md`.
