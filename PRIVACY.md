# Privacy

As Driven has no telemetry upload, analytics, advertising, account,
background update check, or other network feature.

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
