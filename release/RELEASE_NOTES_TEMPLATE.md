# As Driven {{PLUGIN_VERSION}}

As Driven tells a sim racer which physical controls to fit and how to shift
authentically. This release includes SimHub client {{PLUGIN_VERSION}} and a
known-good copy of dataset {{DATASET_VERSION}} with {{RECORD_COUNT}} reviewed
car records.

## What you'll notice

- **Nine more reviewed cars.** The Jaguar XJR-9, Mazda 787B, Toyota GT-One,
  Nissan R89C, Opel Calibra V6 DTM, Renault Laguna Super Touring, Porsche 944
  Turbo Cup, Alpine A110 Cup and Panoz Esperante GTR-1 bring the independently
  usable controls database to {{RECORD_COUNT}} reviewed records.
- **Four cars now say a control is not established.** The BMW M3 E46 GTR and
  TVR Tuscan T400R GT2 wheel rims, the Corvette C5-R downshift blip and the
  Sauber C9 gate each rested on a single guided drive that a later simulator
  read differently. A drive tells you what a simulator does, not what the real
  car did, so those answers are withdrawn until real-car evidence settles them.
  Each simulator's own reading is still shown.
- **A corrected Toyota GT-One cockpit rim.** A submitted drive had recorded the
  Automobilista 2 wheel as a control-panel rim; it is the open-top D-shape that
  the real car and Project Motor Racing both show.
- **Clearer evidence behind every answer.** Real-car facts and simulator
  observations no longer share a claim, so a confidence earned by watching a
  simulator cannot stand behind a statement about the real car.

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
