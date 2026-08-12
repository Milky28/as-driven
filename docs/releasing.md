# Early-access release process

Plugin and database releases are separate artifacts. The plugin ZIP contains a
known-good database snapshot for first installation; the database ZIP updates
only curated data.

## Compatibility and versioning

- `AuthenticControls.Plugin` is the client version shown in SimHub.
- `AuthenticControls.Core` ships with the plugin and uses the same release
  version to keep installed binaries easy to audit.
- `data/v1/index.json` owns the independent dataset version.
- Schema v1 clients accept compatible schema-v1 dataset updates.

The first early-access release is plugin 0.15.0 with dataset 0.3.18. Do not
change the plugin version merely for a database-only release.

## Build release candidates

Run from the repository root on the Windows release machine with the supported
SimHub version installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-early-access.ps1
```

The command validates the database, runs Python and .NET tests, generates all
Dash Studio artifacts, exercises the plugin installer, database installer, and
plugin uninstaller against temporary fake installations, and writes the release
candidates under `dist/early-access`. It then extracts the final SimHub ZIP and
verifies its checksum, manifests, packaged hashes, required contents, and
installer from the same artifact a tester will receive.

The SimHub SDK assemblies are part of the local SimHub installation and are not
redistributed. For that reason, the plugin build is a maintainer-run Windows
release step. The database package is also built in public CI.

## Manual release-candidate checks

1. Confirm `git diff --check`, database validation, Python tests, and the full
   SimHub build pass from the intended source revision.
2. Check that plugin and core DLL versions match the release version.
3. Extract the SimHub ZIP into a new directory and run its installer with
   SimHub closed.
4. Start SimHub 9.11.22 and confirm the plugin author, version, dataset version,
   and record total.
5. Test idle preview and closing preview without a simulator running.
6. In AMS2 1.6.9.91, test one matched and one unmatched car.
7. Check Detailed, Compact, and Glance layouts at 100%, 125%, and 150% Windows
   scaling, including the longest car and technique strings.
8. Save a guided verification draft and confirm it remains local.
9. Install the database-only package and confirm plugin binaries, overlay
   positions, settings, and drafts remain unchanged.
10. Run the uninstaller and confirm user data and customized layouts remain.
11. Compare every artifact with its adjacent `.sha256` file.

## Publish

Create a GitHub prerelease using the plugin version as the tag, attach the
SimHub ZIP, database ZIP, both checksum files, and release metadata JSON, and
paste the relevant changelog section into the release notes. State the tested
SimHub and simulator versions and link to `EARLY_ACCESS.md` and `PRIVACY.md`.

Automatic update checking remains out of scope until the public repository and
release endpoint are stable. A future updater must use an explicit release
channel, verify downloaded content, remain opt-in, and never consume a moving
branch or silently replace curated data.
