# As Driven {{PLUGIN_VERSION}}

As Driven tells a sim racer which physical controls to fit and how to shift
authentically. This release includes SimHub client {{PLUGIN_VERSION}} and a
known-good copy of dataset {{DATASET_VERSION}} with {{RECORD_COUNT}} reviewed
car records.

## Install

1. Download `{{PLUGIN_PACKAGE}}` below.
2. Extract the ZIP.
3. Close SimHub.
4. Double-click `Install As Driven.cmd` and approve the Windows prompt.
5. Start SimHub and enable As Driven under Settings > Plugins.

The installer backs up an existing installation and preserves customized
overlay positions by default. See `START HERE.txt` inside the ZIP for the full
short guide.

## Tested against

- SimHub {{SIMHUB_VERSION}}
- Automobilista 2 {{AMS2_VERSION}}
- Windows

Newer versions generally work but have not been verified. The other simulators
in the dataset carry reviewed entries rather than complete rosters.

## What Windows will warn you about

Expect two warnings, and neither means something is wrong. The administrator
prompt names an unknown publisher, because a signing certificate is a paid
annual subscription for a free project. Windows may also block the downloaded
ZIP: right-click it, open Properties, tick Unblock, and extract it again.

A `.sha256` file is attached beside each ZIP. Comparing it is worth more than a
signature would be, because it tells you the bytes are the published ones.

## The database package

`{{DATABASE_PACKAGE}}` is the curated dataset on its own, for clients that are
not SimHub. You do not need it to install or update the plugin: the ZIP above
already carries this dataset.

Read the [install guide](https://github.com/Milky28/as-driven/blob/main/docs/install.md)
and the [privacy policy](https://github.com/Milky28/as-driven/blob/main/PRIVACY.md),
and use the [problem-report form](https://github.com/Milky28/as-driven/issues/new/choose)
if something is wrong.
