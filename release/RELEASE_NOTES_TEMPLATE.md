# As Driven {{PLUGIN_VERSION}}

As Driven tells a sim racer which physical controls to fit and how to shift
authentically. This release includes SimHub client {{PLUGIN_VERSION}} and a
known-good copy of dataset {{DATASET_VERSION}} with {{RECORD_COUNT}} reviewed
car records.

## What you'll notice

- **A more readable public catalog.** The new Pit wall design uses a navy
  masthead, clearly alternating rows, larger driving instructions, and separate
  hardware and technique headings. Light and dark themes both have stronger
  row separation, including after filtering.
- **Clearer starts in nine H-pattern cars.** The real-car guidance now says
  **Clutch required** when pulling away instead of **Not established**. This
  affects the Giulia Sprint GTA, BMW 3.0 CSL IMSA Group 4, Ferrari 250 GTO,
  Ford GT40 Mk I, McLaren F1 GTR 1996, McLaren F1 LM, Porsche 964 Carrera 2 Cup,
  Shelby Cobra Daytona Coupe, and Ultima GTR.
- **Less clutter in car details.** Repeated summaries are reduced, and the
  website no longer labels identical simulator and real-car values as differences.
- **Clearer counts in SimHub.** The car browser shows reviewed cars separately
  from simulator views, so a car supported in two games is no longer counted as
  two distinct cars.

Also includes reliability improvements. There are no new car records in this
update. See the [exact affected cars and evidence](https://github.com/Milky28/as-driven/blob/v{{PLUGIN_VERSION}}/docs/releases/{{PLUGIN_VERSION}}-control-changes.md).

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
