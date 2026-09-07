# Release process

Plugin and database releases are separate artifacts. The plugin ZIP contains a
known-good database snapshot for first installation; the database ZIP updates
only curated data.

## Compatibility and versioning

- `AsDriven.Plugin` is the client version shown in SimHub.
- `AsDriven.Core` ships with the plugin and uses the same release
  version to keep installed binaries easy to audit.
- `data/v1/index.json` owns the independent dataset version.
- Schema v1 clients accept compatible schema-v1 dataset updates.

The first release is plugin 0.15.0 with dataset 0.3.18. Do not
change the plugin version merely for a database-only release.

## Build release candidates

Run from the repository root on the Windows release machine with the supported
SimHub version installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\build-release.ps1
```

The command validates the database, runs Python and .NET tests, generates all
Dash Studio artifacts, exercises the plugin installer, database installer, and
plugin uninstaller against temporary fake installations, and writes the release
candidates under `dist/release`. It then extracts the final SimHub ZIP and
verifies its checksum, manifests, packaged hashes, required contents, and
installer from the same artifact a tester will receive. Release packages omit
debug symbols and fail verification if a local user path or internal handoff
document is present.

The SimHub SDK assemblies are part of the local SimHub installation and are not
redistributed. For that reason, the plugin build is a maintainer-run Windows
release step. Public CI restores Newtonsoft.Json only to build and run the
SDK-independent core tests; the full adapter build and native-settings smoke
test remain a maintainer-run release gate. The database package is also built
in public CI.

## Manual release-candidate checks

1. Confirm `git diff --check`, database validation, Python tests, and the full
   SimHub build pass from the intended source revision.
2. Check that plugin and core DLL versions match the release version.
3. Extract the SimHub ZIP into a new directory and double-click
   `Install As Driven.cmd` with SimHub closed.
4. Start SimHub 9.11.22 and confirm the plugin author, version, dataset version,
   and record total.
5. Test idle preview and closing preview without a simulator running.
6. In AMS2 1.6.9.91, test one matched and one unmatched car.
7. Check the Detailed and Compact layouts at 100%, 125%, and 150% Windows
   scaling, including the longest car and technique strings.
8. Save a guided verification draft and confirm it remains local.
9. Install the database-only package and confirm plugin binaries, overlay
   positions, settings, and drafts remain unchanged.
10. Run the uninstaller and confirm user data and customized layouts remain.
11. Compare every artifact with its adjacent `.sha256` file.

## Control-guidance release summary

Before publishing a dataset change, compare the prepared tree with an extracted
copy of the previous database release. The command only reports controls that
matter to a driver's hardware or technique, and carries forward links to the
current record's registered evidence:

```powershell
python -m as_driven_db release-control-changes C:\releases\as-driven-0.5.45 --output build\control-changes.json
python -m as_driven_db release-control-changes C:\releases\as-driven-0.5.45 --markdown --output build\control-changes.md
```

Review the Markdown report with the release notes. New and retired records are
listed in its JSON summary; they are not mislabeled as a changed control. Pass
`--priority-record` once per locally recent record id when preparing a
driver-specific report; those changes are listed first and visibly labeled.

## Publish

First preview the checked release without changing GitHub:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\publish-github-release.ps1
```

Then create a draft release from a clean, synchronized `main` branch:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\release\publish-github-release.ps1 -Approve
```

The script rechecks the SimHub ZIP, database ZIP, adjacent checksums, metadata,
generated release notes, and temporary installations. It creates a GitHub draft
and release tag targeting the current commit, uploads all release artifacts,
and stops. Review the draft and manual checks before publishing it on GitHub.

Keep the root `as-driven-latest.json` on the last published release while a new
candidate is a draft. After publishing, copy the verified manifest from that
release into the root and commit it so the manual update check announces the
available download. A local candidate's dataset version can be ahead of the
public update manifest; the regression check validates the manifest against its
own release's changelog entry.

Nothing prompts you to do that copy, and 0.21.5 was published with the root
still announcing 0.21.4, so every installation that checked was told it was
current. Confirm the promotion once the release is no longer a draft:

```powershell
python -m as_driven_db check-update-manifest
```

It lists the repository's releases and fails when the root manifest is behind
the published latest, or when it announces a version that is not published at
all. A draft is not published, so the check stays quiet while a candidate is
still being prepared. Pass `--releases` a saved listing to run it offline.

Automatic update checking is out of scope by design, not for want of an
endpoint. The endpoint exists and is stable: `main` is public, and
`https://raw.githubusercontent.com/Milky28/as-driven/main/as-driven-latest.json`
serves the manifest from a stable path. The check stays manual anyway, because a
dataset that changed under a driver mid-session would rewrite the guidance they
had already verified. That is why installing is deliberate.

The check reads two version strings and downloads nothing. Any future updater
would still have to use an explicit release channel, verify downloaded content,
remain opt-in, and never consume a moving branch or silently replace curated
data.
