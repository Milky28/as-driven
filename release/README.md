# Independent database releases

The database and SimHub plugin have separate release lifecycles.

Build a database-only ZIP and SHA-256 checksum with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-database.ps1
```

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
