# As Driven early access

As Driven is ready for an early-access release, not a claim of
complete simulator or vehicle coverage. The release is intended for testers
who are comfortable reporting incorrect or missing data.

## Supported release target

- Windows with SimHub 9.11.22;
- Automobilista 2 executable version 1.6.9.91;
- As Driven SimHub client 0.16.0;
- As Driven dataset 0.3.54 and schema v1.

Newer SimHub or AMS2 versions may work, but have not been certified for this
release. The overlay always displays the exact game version associated with a
curated simulator observation. An exact telemetry-name match does not imply
that behavior was reverified after a game update.

## Included functionality

- exact, case-sensitive vehicle matching with no silent fuzzy matches;
- Detailed, Compact, and Glance pre-flight overlays;
- separate physical-control and shifting-technique guidance;
- car browsing and offline preview before starting the simulator;
- guided, versioned local verification drafts for missing or corrected cars;
- unmatched-identity diagnostics;
- independent, checksummed database updates with backup and rollback;
- a SimHub installer that preserves customized overlay positions by default.

The database currently contains 224 curated records. AMS2 coverage is useful but
incomplete, and unsupported cars are deliberately shown as unmatched instead of
receiving guessed controls. The generated coverage plan remains development
material and is not a promise that every listed identity is a distinct vehicle.

## Known early-access limitations

- Only AMS2 is supported by the SimHub client in this release.
- The plugin and PowerShell installers are not code-signed. Windows may show a
  warning for downloaded files or scripts.
- Updates are manual. There is no background network check or automatic
  download.
- Contribution drafts remain on the tester's PC. The development build does
  not submit them to GitHub.
- A maintainer must validate and approve every contribution before it enters a
  released dataset.
- Wheel artwork is category-based and may not reproduce a car's exact rim.
- Some curated values intentionally remain `unknown` when the evidence is
  insufficient.

## Install and update

1. Close SimHub.
2. Extract the SimHub release ZIP.
3. Run `simhub/install.ps1` from PowerShell.
4. Start SimHub, enable **As Driven**, and pin it to the left menu if
   desired.
5. Load one included As Driven overlay layout in Dash Studio and place
   it where desired.

Plugin and database versions advance independently. A database-only release can
be installed with `release/install-database.ps1`; it does not replace the plugin,
Dash Studio templates, overlay layouts, or settings. Restart SimHub or use
**Refresh database** after a manual database update.

The ZIP's adjacent `.sha256` file can be checked before installation:

```powershell
Get-FileHash .\as-driven-simhub-0.16.0-early-access.zip -Algorithm SHA256
```

Compare the displayed hash with the value in the downloaded `.sha256` file.

## Remove or roll back

Run `simhub/uninstall.ps1` with SimHub closed. The default removal keeps the
installed database, customized layouts, settings, diagnostics, and contribution
drafts so a later reinstall can reuse them. The script creates a timestamped
backup before removing plugin binaries and packaged Dash Studio templates.

Every plugin install also prints the path to a timestamped rollback backup.

## Reporting problems and contributing data

When reporting a client problem, include the plugin version, dataset version,
SimHub version, simulator version, and whether the issue occurs in live or
preview mode. Do not include private local paths or telemetry logs unless they
are needed and you have reviewed them.

For vehicle data, use **Contribute data** in the plugin. Review the generated
JSON draft before sharing it. See [CONTRIBUTING.md](CONTRIBUTING.md) for evidence
and approval requirements.
