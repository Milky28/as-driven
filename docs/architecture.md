# Architecture principles

1. **The database is the product.** Consumers adapt to its public releases; no
   UI framework or telemetry SDK leaks into the JSON model.
2. **Real, simulated, and session-effective behavior are separate layers.** A
   game limitation or series rule never rewrites the authentic car record.
3. **Evidence is queryable.** Provenance attaches to paths, not a vague record
   footer.
4. **Imports fail closed.** Layout changes create candidates or errors, never
   silent edits to curated data.
5. **Identifiers are typed aliases.** Display names are useful fallbacks, not
   assumed stable keys.
6. **Version everything that changes meaning.** Schema, dataset, importer, and
   verified game versions evolve independently.

For v1, files are preferable to a database server: they diff cleanly, work
offline, are easy to review on GitHub, and can be consumed by any language.
SQLite or an API can later be generated as release artifacts without replacing
the canonical JSON.

