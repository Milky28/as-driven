# Installing, updating, and removing As Driven

As Driven installs into an existing SimHub installation on Windows. Installing
and updating are the same procedure, and each release carries both the plugin
and the current car data.

Version numbers are deliberately absent here. The README states which versions
are current and tested; this document describes the procedure, which does not
change between releases.

## Install

1. Download the newest `As-Driven-for-SimHub-*.zip` from
   [GitHub Releases](https://github.com/Milky28/as-driven/releases).
2. Close SimHub.
3. Extract the ZIP.
4. Double-click **Install As Driven.cmd** and approve the Windows administrator
   prompt.
5. Start SimHub and enable **As Driven** under Settings > Plugins.
6. Open Dash Studio and load the included As Driven overlay layout.

`START HERE.txt` inside the ZIP repeats these steps. If you prefer PowerShell,
`simhub/install.ps1` is the same installer and takes an optional
`-SimHubInstallPath`.

If installation fails, the administrator window stays open with the actual
error until you press Enter. It also prints the location of an
`AsDriven-install-error-*.txt` file in its temporary folder. Include that file
when reporting a problem. The opening reminder to close SimHub appears on every
run; it does not mean SimHub was detected. If administrator approval is declined,
the launcher reports that it could not start the installer.

### The two warnings Windows shows

Neither means something is wrong, and both are expected.

**The administrator prompt names an unknown publisher.** As Driven is not
code-signed; a signing certificate is a paid annual subscription, and this is a
free project. Windows says the same about every unsigned installer.

**Windows may block the downloaded ZIP.** Right-click it, open Properties, tick
**Unblock**, and extract it again.

Verifying the checksum below is a better guarantee than a signature would be: it
tells you the bytes are the ones the project published.

The installer creates a timestamped rollback backup and prints its path. It
preserves customized `As Driven*.olayout` files by default, so overlay
positions you have adjusted survive a reinstall.

### Verify the download first (optional)

Every release ZIP has an adjacent `.sha256` file.

```powershell
Get-FileHash .\As-Driven-for-SimHub-<version>.zip -Algorithm SHA256
```

Compare the printed hash with the value in the `.sha256` file. The plugin and
the PowerShell scripts are not code-signed, so this check is the meaningful one.

## Update

Updating is always something you start. The plugin has no background update
check or download; see [Checking for updates](#checking-for-updates) below.

There is one procedure, and it is the same one you used to install: download the
newest release, close SimHub, and run **Install As Driven.cmd** over the existing
installation.

The installer backs up what it replaces. Your settings, diagnostics, contribution
drafts, and customized overlay layouts are preserved.

Most releases exist because the car data changed rather than the client, so
every release carries the current dataset with it. You do not have to work out
whether a given release is a data update or a client update - installing it
gives you both.

### Checking for updates

The plugin can tell you when a newer dataset or plugin exists. It contacts
nothing until you press the button, and checking does not download the package.

1. Open the plugin's **System** tab in SimHub.
2. Press **Check for updates**.

There is nothing to configure. The address ships with the client; advanced users
can point it elsewhere by editing `UpdateCheckUrl` in the plugin's settings file.
Leaving that value empty means unconfigured, not disabled, and the shipped
address is used.

The check reads version and verified-package metadata and compares the versions
with what you have installed. If something newer exists, **Download and
install** appears. Pressing it shows a separate confirmation; only after you
confirm does the plugin download the full release ZIP and verify its SHA-256.

Once the verified package is ready, close SimHub. A local helper validates the
archive, asks for the normal Windows administrator approval, runs the same
rollback-capable installer used for a manual installation, and restarts SimHub
when the install succeeds. Declining either confirmation installs nothing. You
can still ignore the button and use the release page and manual procedure above.

A check that fails for any reason reports the failure rather than claiming you
are up to date. See
[PRIVACY.md](../PRIVACY.md) for exactly what the request does and does not send.

The check, download, and install remain separate deliberate acts. The dataset is
never replaced mid-session: installation waits until you close SimHub.

## Remove or roll back

Close SimHub and double-click **Uninstall As Driven.cmd**, or run
`simhub/uninstall.ps1` from PowerShell.

The default removal keeps the installed database, customized layouts, settings,
diagnostics, and contribution drafts, so a later reinstall can reuse them. It
creates a timestamped backup before removing plugin binaries and packaged Dash
Studio templates.

Pass `-RemovePackagedLayouts` to back up and remove the packaged overlay layouts
as well.

Every install also prints the path to its rollback backup, which is the fastest
way back to the previous version.

## Reporting a problem

Open an issue with:

- the plugin version and dataset version (both shown in the plugin's settings);
- your SimHub version;
- the simulator and its exact version;
- whether the problem happens in a live session or in offline preview.

Please do not paste local paths or telemetry logs unless they are needed, and
review them before sharing.

If a car is missing or its guidance looks wrong, the more useful route is
**Contribute a simulator observation** in the plugin, which walks you through a
guided drive and produces a structured draft. Review the generated JSON before
sharing it. See [CONTRIBUTING.md](../CONTRIBUTING.md) for what makes a claim
acceptable evidence.
