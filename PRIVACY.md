# Privacy

As Driven has no telemetry upload, analytics, advertising, account, or
background update check or download.

The System tab has a **Check for updates** button, and the address it contacts
ships with the client so there is nothing to configure. A request is made
**only** when you press that button: there is no timer, nothing at startup, and
nothing after an install.

The address is stored in the plugin's settings file as `UpdateCheckUrl` and can
be pointed elsewhere there. Leaving it empty means unconfigured rather than
disabled, and the client falls back to its own address; the check still contacts
nothing until you press the button, which is the guarantee that matters.

What the request sends is what any HTTPS fetch sends - your IP address, the time,
and a `AsDriven` user agent. It carries no identifier, no car, no drive, and no
version of yours; the comparison happens on your machine after the reply
arrives. The endpoint must be https, because a plaintext one could be rewritten
in transit into an announcement of an update that does not exist.

The check reads two version strings plus the release page, package address, and
SHA-256 checksum. It never downloads or installs the package. If a newer release
exists and the manifest provides a valid HTTPS package address and checksum, a
separate **Download and install** button appears.

Pressing **Download and install** first shows a confirmation. If you confirm, the
plugin makes a second HTTPS request to download the full SimHub release ZIP. That
request exposes the same ordinary connection information (your IP address, time,
and the `AsDriven` user agent) to GitHub and its HTTPS download hosts. It carries
no identifier, telemetry, car, drive, or installed version. The ZIP is written
under the Windows temporary directory, limited to 512 MiB, and is not run unless
its locally calculated SHA-256 exactly matches the manifest.

After verification, a local helper waits for you to close SimHub. It validates
the archive paths and package format, asks Windows for administrator approval,
runs the same rollback-capable installer shipped in the public ZIP, and restarts
SimHub after a successful install. Declining the confirmation or the Windows
approval installs nothing. The helper attempts to remove its downloaded and
extracted temporary files after success or failure; an interrupted Windows
session may leave its uniquely named `AsDrivenUpdate-*` temporary directory for
manual removal.

The SimHub client reads the current simulator identity and limited telemetry
needed to match a car, display control guidance, and run an optional guided
verification. It stores the following information locally:

- plugin preferences under SimHub's normal plugin settings storage;
- deduplicated unmatched simulator identities under
  `%LOCALAPPDATA%\SimHub\AsDriven\Diagnostics`;
- user-requested verification drafts under
  `%LOCALAPPDATA%\SimHub\AsDriven\Verification\Drafts`.

Verification drafts may contain the observer name entered in the form, exact
simulator and vehicle identity, game and SimHub versions, test observations,
notes, and timestamps. They are never added to the curated database or sent
elsewhere automatically.

The plugin can open a public contribution form only after the user explicitly
asks it to. It does not attach or transmit the draft; the user chooses the file
in their browser. A public attachment can expose the chosen observer name or
handle, exact timestamp, simulator and vehicle identifiers, versions, tests,
notes, and the Assetto Corsa implementation details described below. The plugin
can also create an explicitly marked redacted copy with anonymous
attribution and no implementation block. That copy may be useful as a research
lead but normally cannot support a mod implementation claim.

Capturing a verification draft in Assetto Corsa additionally reads files from
that game's installation, and only then. It reads the driven car's `data.acd` -
or its unpacked `data` directory - to record a digest of it, and `ui/ui_car.json`
for the author and declared version the package states. This is how a draft
records which installed copy of a car was driven, which matters in a game where
several packages may share a name. The digest is recorded; the files are not
copied, and no installation path is written into the draft. To locate the game,
the plugin reads Steam's own library list, or the `AS_DRIVEN_AC_CONTENT`
environment variable when it is set. Nothing here contacts the network, and a
game the plugin cannot find simply produces a draft without this block.

The database contains public evidence URLs. The plugin does not open or contact
those sources during normal operation.

To remove local drafts or diagnostics, close SimHub and delete the corresponding
subdirectory. The default uninstaller preserves this data so it is not lost
accidentally.
