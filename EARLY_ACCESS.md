# As Driven early access

As Driven is an open authentic-controls layer with a SimHub reference client.
This early-access release is one certified client target, not a claim that every
simulator or vehicle represented by the independent dataset is supported here.
It is intended for testers who are comfortable reporting incorrect or missing
data.

## Supported release target

- Windows with SimHub 9.11.22;
- Automobilista 2 executable version 1.6.9.91;
- As Driven SimHub client 0.20.2;
- As Driven dataset 0.5.17 and schema v1.

Newer SimHub or AMS2 versions may work, but have not been certified for this
release. The overlay always displays the exact game version associated with a
curated simulator observation. An exact telemetry-name match does not imply
that behavior was reverified after a game update.

## Included functionality

- exact, case-sensitive vehicle matching with no silent fuzzy matches;
- Detailed and Compact pre-flight overlays;
- separate physical-control and shifting-technique guidance;
- car browsing and offline preview before starting the simulator;
- guided, versioned local verification drafts for missing or corrected cars;
- unmatched-identity diagnostics;
- independent, checksummed database updates with backup and rollback;
- a SimHub installer that preserves customized overlay positions by default.

The database currently contains 271 curated car records. Of those, 256 carry AMS2 entries; 4 are currently AC EVO-only and 7 original-AC
records are AC-only. 3 AMS2 records also carry reviewed Assetto Corsa EVO
development entries, 14 AMS2 records also carry reviewed original Assetto Corsa
entries, and 18 AMS2 records also carry reviewed Assetto Corsa Competizione entries.
This release is
certified only for the AMS2 target above. Unsupported cars and simulators are
deliberately shown as unmatched instead of receiving guessed controls. The
generated coverage plans remain development material and are not promises that
every listed identity is a distinct vehicle.

## Known early-access limitations

- Only the AMS2 target above is certified for this SimHub client release. Other
  simulator entries in the dataset remain development coverage.
- The plugin and PowerShell installers are not code-signed. Windows may show a
  warning for downloaded files or scripts.
- Updates are manual. There is no background network check or automatic
  download.
- Contribution drafts remain on the tester's PC until the tester explicitly
  opens the public observation form and attaches one. The client never uploads
  a draft itself.
- A maintainer must validate and approve every contribution before it enters a
  released dataset.
- Wheel artwork is category-based and may not reproduce a car's exact rim.
- Some curated values intentionally remain `unknown` when the evidence is
  insufficient.

## Install and update

1. Download and extract the newest `As-Driven-for-SimHub-*.zip` release.
2. Close SimHub.
3. Double-click **Install As Driven.cmd** and approve the Windows administrator
   prompt.
4. Start SimHub, enable **As Driven**, and pin it to the left menu if
   desired.
5. Load one included As Driven overlay layout in Dash Studio and place
   it where desired.

`START HERE.txt` inside the ZIP contains the same short instructions. Advanced
users can run `simhub/install.ps1` directly from PowerShell. If Windows blocks
the downloaded scripts, right-click the ZIP, open Properties, select Unblock,
and extract it again.

Plugin and database versions advance independently. A database-only release can
be installed with `release/install-database.ps1`; it does not replace the plugin,
Dash Studio templates, overlay layouts, or settings. Restart SimHub or use
**Refresh database** after a manual database update.

The ZIP's adjacent `.sha256` file can be checked before installation:

```powershell
Get-FileHash .\as-driven-simhub-0.20.2-early-access.zip -Algorithm SHA256
```

Compare the displayed hash with the value in the downloaded `.sha256` file.

## Remove or roll back

Close SimHub and double-click **Uninstall As Driven.cmd**. Advanced users can
run `simhub/uninstall.ps1` directly. The default removal keeps the installed
database, customized layouts, settings, diagnostics, and contribution drafts
so a later reinstall can reuse them. The script creates a timestamped backup
before removing plugin binaries and packaged Dash Studio templates.

Every plugin install also prints the path to a timestamped rollback backup.

## Reporting problems and contributing data

When reporting a client problem, include the plugin version, dataset version,
SimHub version, simulator version, and whether the issue occurs in live or
preview mode. Do not include private local paths or telemetry logs unless they
are needed and you have reviewed them.

For vehicle data, use **Contribute a simulator observation** in the plugin.
Review the generated JSON before sharing it. The saved-draft actions can select
the exact file, create an explicitly weaker redacted research copy, or
open the GitHub submission form. See [CONTRIBUTING.md](CONTRIBUTING.md) for
evidence and approval requirements.
