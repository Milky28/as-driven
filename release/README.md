# Independent database releases

The database and SimHub plugin have separate release lifecycles.

Build a database-only ZIP and SHA-256 checksum with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-database.ps1
```

Build the complete release candidates (plugin and database as
separate checksummed ZIPs) with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-release.ps1
```

That command requires the supported SimHub SDK to be installed locally. It
runs the database and .NET checks, builds the SimHub package, tests database
installation and plugin removal in temporary directories, and writes release
metadata under `dist/release`. See `docs/releasing.md` for manual release
candidate checks and publishing steps.

The SimHub ZIP has three user-facing files at its root:

- `START HERE.txt` with the complete short installation guide;
- `Install As Driven.cmd`, which requests administrator approval and runs the
  tested installer;
- `Uninstall As Driven.cmd`, which preserves user data by default.

Public packages omit debug symbols and are scanned for local user paths. The
release-package test also verifies that every shipped file is checksummed and
that internal handoff documents are absent.

After manually checking the release candidate, preview a draft GitHub
release with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\publish-github-release.ps1
```

The preview verifies both ZIPs, their checksums, generated notes, metadata, and
temporary installations. It does not contact GitHub. Rerun with `-Approve` to
require a clean, synchronized `main` branch and create a draft release. The
script never publishes the draft.

The archive contains `data/`, `schema/`, the data-model and evidence-boundary
documentation, and license files. `release-manifest.json` identifies the
dataset version and hashes every packaged file. It contains no SimHub binaries,
layouts, or settings.

A plugin release may bundle a known-good database snapshot for a first install,
but that snapshot is not the plugin version. Compatible database packages can
be released more frequently and loaded without rebuilding the plugin. The
SimHub client already exposes its active dataset version and a database refresh
action.

Install the newest built database package without replacing plugin binaries,
Dash Studio templates, overlay layouts, or settings:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\install-database.ps1
```

Use `-PackagePath` to install a specific release ZIP and
`-SimHubInstallPath` for a non-default SimHub directory. `-BackupDirectory` is
available for managed deployments and automated testing. The installer verifies
the optional ZIP checksum, every manifest file hash, package format, schema
major, and dataset version before making changes. It refuses downgrades unless
`-AllowDowngrade` is supplied, swaps the database directory atomically, restores
the previous directory if post-install validation fails, and writes a rollback
backup under the user's temporary directory. If SimHub is running, use the
plugin's **Refresh database** action after installation.

## The update manifest

`publish-github-release.ps1` writes `as-driven-latest.json` beside the release
artifacts and attaches it, containing exactly three fields:

```json
{
  "dataset_version": "0.5.33",
  "plugin_version": "0.20.0",
  "release_url": "https://github.com/<owner>/<repo>/releases/tag/v0.20.0"
}
```

This is what the plugin's manual update check reads, and it is generated from the
versions the release is publishing rather than written by hand, because the check
finds its fields by name and a hand-written file gets one of them wrong exactly
once. The publisher reads it back with the same patterns
`AsDriven.Plugin.UpdateCheck.ReadField` uses and refuses to publish if any field
is missing or disagrees with the release.

**Serve it from a stable https URL.** The per-tag asset URL changes every release,
so a check pointed at one would read the same old versions forever. The plugin
refuses anything that is not https, and the endpoint is blank in a fresh install,
so nothing is contacted until somebody sets it.

The manifest carries three fields and nothing else on purpose. The check compares
two versions and shows a link; anything more would be a payload nobody reads and
a promise somebody has to keep.
