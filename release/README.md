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
action; an atomic database-only installer/updater is the next distribution
step.
