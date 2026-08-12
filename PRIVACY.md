# Privacy

Authentic Controls has no telemetry upload, analytics, advertising, account,
background update check, or other network feature.

The SimHub client reads the current simulator identity and limited telemetry
needed to match a car, display control guidance, and run an optional guided
verification. It stores the following information locally:

- plugin preferences under SimHub's normal plugin settings storage;
- deduplicated unmatched simulator identities under
  `%LOCALAPPDATA%\SimHub\AuthenticControls\Diagnostics`;
- user-requested verification drafts under
  `%LOCALAPPDATA%\SimHub\AuthenticControls\Verification\Drafts`.

Verification drafts may contain the observer name entered in the form, exact
simulator and vehicle identity, game and SimHub versions, test observations,
notes, and timestamps. They are never added to the curated database or sent
elsewhere automatically.

The database contains public evidence URLs. The plugin does not open or contact
those sources during normal operation.

To remove local drafts or diagnostics, close SimHub and delete the corresponding
subdirectory. The default uninstaller preserves this data so it is not lost
accidentally.
