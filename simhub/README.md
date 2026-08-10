# SimHub proof of concept

This directory contains a read-only SimHub adapter for the independent JSON
database. The plugin never rewrites curated data and does not contain overlay
UI. Its job is to turn the current SimHub game/car identity into stable
properties that a Dash Studio popup can consume.

## Components

```text
AuthenticControls.Core          JSON reader, exact matcher, guidance formatter
AuthenticControls.Plugin        Minimal SimHub IDataPlugin adapter
AuthenticControls.Diagnostics   Lookup without launching SimHub
AuthenticControls.Core.Tests    Dependency-free .NET regression runner
build.ps1                       Build, test, and create a SimHub-ready package
```

The core library supports schema version `1.0.0`, rejects index paths outside
the data directory, fails on conflicting exact identities, and performs no
fuzzy matching. AMS2 game names are normalized to the database's `ams2` key,
but car identifiers remain exact and case-sensitive.

## Build and test

The build uses the SDK assemblies included with the locally installed SimHub.
It does not download packages or copy anything into SimHub.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\simhub\build.ps1
```

A successful build runs the .NET lookup assertions and creates:

```text
simhub/dist/AuthenticControls/
  AuthenticControls.Plugin.dll
  AuthenticControls.Core.dll
  PluginsData/AuthenticControls/Database/data/v1/...
```

The package mirrors SimHub's folder layout. Installing it is a separate,
explicit step: close SimHub, copy the package contents into the SimHub install
directory, restart SimHub, and enable **Authentic Controls** under
Settings > Plugins. The build script itself never performs that installation.

## Diagnostic lookup

After building, test a telemetry identity without starting SimHub:

```powershell
.\simhub\AuthenticControls.Diagnostics\bin\Release\AuthenticControls.Diagnostics.exe .\data\v1 Automobilista2 "Dallara F301"
```

An exact match exits with code 0. An unknown car exits with code 1 and prints
`MatchStatus=unmatched` plus the raw game/car values.

## Published SimHub properties

The plugin class is named `AuthenticControls`, so its attached properties are
available under that prefix:

```text
AuthenticControls.HasMatch
AuthenticControls.MatchStatus
AuthenticControls.RawGameName
AuthenticControls.RawCarIdentifier
AuthenticControls.DatabasePath
AuthenticControls.DatasetVersion
AuthenticControls.RecordId
AuthenticControls.DisplayName
AuthenticControls.CarClass
AuthenticControls.ShiftType
AuthenticControls.ShiftActuation
AuthenticControls.GearCount
AuthenticControls.UpshiftGuidance
AuthenticControls.DownshiftGuidance
AuthenticControls.StandingStartClutch
AuthenticControls.AutoBlip
AuthenticControls.ShiftCut
AuthenticControls.WheelRimShape
AuthenticControls.WheelRimSourceLabel
AuthenticControls.HasSteeringDOR
AuthenticControls.SteeringDOR
AuthenticControls.VerifiedGameVersion
AuthenticControls.Confidence
AuthenticControls.SourceSummary
AuthenticControls.MatchKind
AuthenticControls.GuidanceSummary
AuthenticControls.PopupRevision
```

`PopupRevision` increments once when a new matched car is observed. Repeated
telemetry frames do not change it. Moving to an unknown car immediately clears
the previous record and does not increment the revision.

The plugin also registers `AuthenticControls.RefreshDatabase`. The database is
normally loaded from:

```text
<SimHub>/PluginsData/AuthenticControls/Database/data/v1
```

For local development, the `AUTHENTIC_CONTROLS_DATA` environment variable can
override that path.

## Current boundary

This is a property and diagnostics milestone, not the finished user experience.
It has been compiled against the installed SimHub 9.11.22 SDK and tested
outside the running SimHub process. Version 0.1.0 has also been installed
locally with dataset 0.2.0, and the installed file hashes and database lookup
were verified. The next step is a live SimHub/AMS2 check, followed by the Dash
Studio popup.
