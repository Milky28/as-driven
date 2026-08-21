# Plugin distribution: the single-DLL question

SimHub users expect to install a plugin by dropping one `.dll` into the SimHub
folder. As Driven currently ships a 265-file package installed by a PowerShell
script. This note records what would have to change for a single-file drop-in to
work, what it would cost, and the one thing to test before committing to it.

Nothing here is decided. It is written down so the release work does not have to
rediscover it.

## What the package actually contains

Measured from `simhub/dist/AsDriven` at client 0.17.0, dataset 0.4.2:

| Part | Files | Size | Can it live inside the DLL? |
| --- | --- | --- | --- |
| `AsDriven.Plugin.dll`, `AsDriven.Core.dll` (+ `.pdb`) | 4 | 460 KB | It *is* the DLL |
| `DashTemplates/` | 15 | 641 KB | No - SimHub scans the folder |
| `OverlayLayouts/` | 2 | 3 KB | No - same |
| `PluginsData/AsDriven/Database/data/v1/` | 244 | 1,822 KB | Technically yes; see below |

The `.pdb` files are debug symbols and should not be in a public release
regardless of how it is packaged.

A literal one-file drop-in is therefore impossible as things stand, because the
Dash Studio templates *are* the product. Without them the plugin exposes
telemetry properties and draws no pre-flight card, which is the thing anyone
installs it for.

## What a single-DLL distribution would need

### 1. Merge the core assembly - easy

`AsDriven.Core.dll` is a separate assembly only because the reader and guidance
logic are deliberately SimHub-independent. ILRepack at package time, or
compiling the core sources into the plugin assembly, both work.

Keep the split in source either way. The separation is what lets a non-SimHub
client use the same reader, and `CLAUDE.md` aligns the two version numbers so a
build is easy to audit; merging is a packaging step, not a source change.

### 2. Extract templates and layouts on first run - the real work

Ship `DashTemplates/` and `OverlayLayouts/` as embedded resources and have the
plugin write them into SimHub's folders when they are missing.

**It must never overwrite a customized layout.** `simhub/install.ps1` preserves
existing `As Driven*.olayout` files by default, and self-extraction has to match
that behaviour exactly or the drop-in path quietly destroys work the installer
protects.

### 3. The database - the part that is a design decision, not packaging

Embedding is cheap in bytes: 1,822 KB of JSON deflates to 183 KB, a ten-to-one
saving, so the whole dataset costs less than a fifth of a megabyte in the
assembly.

The cost is not size. `release/build-database.ps1` exists so a dataset update
ships without a new plugin, and `CLAUDE.md` states plugin and dataset versions
are independent. Embedding the database welds them together: every corrected
record would need a new DLL, and the database-only release stops meaning
anything.

**The way out is already half-built.** `AsDriven.ResolveDatabasePath` resolves in
order:

1. the `AS_DRIVEN_DATA` environment variable, if set;
2. `<SimHub>/PluginsData/AsDriven/Database/data/v1`.

Adding a third fallback to an embedded **seed** dataset keeps both properties: a
dropped-in DLL works on its own from day one, and an installed database still
wins because it is found first. The seed is a floor, not the source of truth.

That also gives the seed an honest meaning in the UI - the settings page can say
which of the three the current data came from, so "why is my dataset old" has a
visible answer.

## The thing to test first

**Can the plugin write to `C:\Program Files (x86)\SimHub\DashTemplates` at
runtime?**

A user copying a DLL into Program Files gets a UAC prompt and proceeds. A plugin
writing files while SimHub runs unelevated is a different question, and if the
answer is no, the single DLL degrades to "properties work, no cards" - worse than
an honest two-step install, because it fails silently and looks like a broken
plugin.

Test before building anything else here. It decides whether the rest is worth
doing, and it is a short experiment: a plugin build that tries to create one file
in that folder on load and logs the result.

If it fails, the fallbacks are worth knowing in advance: write to
`%LOCALAPPDATA%` and ask SimHub to load templates from there if it supports it;
or ship the DLL plus a templates folder as a two-file install, which is still
much closer to the convention than 265 files.

## What to verify about SimHub itself

This note is confident about what *this* package needs and much less so about
SimHub's own conventions. Before designing to them, look at how two or three
widely used SimHub plugins actually distribute dash templates - whether the
single-DLL convention extends to plugins that ship dashboards at all, or whether
those are conventionally distributed separately for the user to import. Matching
what users already expect is most of the value of doing this.

## Proposed shape, if it all works

- **`AsDriven.dll`** - merged core, embedded templates, layouts and seed
  database, self-extracting on first run and never overwriting a customized
  layout. The drop-in path.
- **`simhub/install.ps1` stays** for the timestamped rollback backup, layout
  preservation, and controlled dataset updates. It is the supported path for
  anyone who wants those, and it is what `EARLY_ACCESS.md` documents.
- **`release/build-database.ps1` is unaffected**, which is the point of the seed
  fallback rather than a plain embed.
