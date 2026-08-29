# As Driven

**Which physical controls should I use for this car, and how do I shift it?**

As Driven answers that before you leave the pits. Load a car in a supported
simulator and the overlay tells you what the real car had - the shape of its
wheel, whether it has a clutch pedal and when you actually need it, whether to
lift off the throttle when you upshift, whether to blip on the way down.

It is a database first and a SimHub plugin second. The data is open, versioned,
and simulator-independent; the plugin is one client that reads it.

## What it tells you

<table>
<tr>
<td align="center"><img src="docs/images/wheel-round.png" width="72" alt=""></td>
<td align="center"><img src="docs/images/wheel-gt-formula.png" width="72" alt=""></td>
<td align="center"><img src="docs/images/wheel-yoke.png" width="72" alt=""></td>
<td align="center"><img src="docs/images/shift-h-pattern.png" width="72" alt=""></td>
</tr>
<tr>
<td align="center"><b>Rim shape</b><br>round, D-shaped, GT, formula, yoke</td>
<td align="center"><b>Rim shape</b><br>and whether it is open-top</td>
<td align="center"><b>Rim shape</b><br>so you fit the right one first</td>
<td align="center"><b>Shift pattern</b><br>H-pattern, and how many gears</td>
</tr>
<tr>
<td align="center"><img src="docs/images/shift-dogleg-h.png" width="72" alt=""></td>
<td align="center"><img src="docs/images/shift-sequential-paddles.png" width="72" alt=""></td>
<td align="center"><img src="docs/images/control-clutch.png" width="72" alt=""></td>
<td align="center"><img src="docs/images/control-throttle.png" width="72" alt=""></td>
</tr>
<tr>
<td align="center"><b>Dogleg</b><br>first is down, not up</td>
<td align="center"><b>Sequential</b><br>paddles or a stick</td>
<td align="center"><b>Clutch</b><br>for starts, upshifts, downshifts</td>
<td align="center"><b>Throttle</b><br>lift on upshift, blip on downshift</td>
</tr>
</table>

> **Screenshots wanted.** The icons above are the plugin's own artwork, but the
> README does not yet show the overlay in a live session. If you run As Driven,
> a capture would be welcome - see
> [docs/development.md](docs/development.md#wanted-readme-screenshots).

## Install

1. Download the newest `As-Driven-for-SimHub-*.zip` from
   [Releases](https://github.com/Milky28/as-driven/releases).
2. Close SimHub and extract the ZIP.
3. Double-click **Install As Driven.cmd** and approve the Windows prompt.
4. Start SimHub, enable **As Driven** under Settings > Plugins.
5. Load an As Driven overlay in Dash Studio.

Updating is the same procedure: download the newest release and install it over
the old one. Your settings, layouts, and contribution drafts are preserved, and
every release carries the current car data with it.

Full details, checksum verification, rollback, and removal are in
[docs/install.md](docs/install.md).

The plugin works offline. It has no analytics, no account, and no background
update check. Its one network feature is a manual update check that is blank by
default, so no request is possible until you configure it. See
[PRIVACY.md](PRIVACY.md).

## What it covers

<!-- release-facts:start -->
Dataset 0.5.33 contains 279 reviewed car records.

| Simulator | Records | Also curated for AMS2 |
| --- | --- | --- |
| Automobilista 2 | 261 | not applicable |
| Assetto Corsa | 21 | 14 |
| Assetto Corsa Competizione | 18 | 18 |
| Assetto Corsa EVO | 7 | 3 |
| RaceRoom Racing Experience | 6 | 3 |
| rFactor 2 | 5 | 0 |
<!-- release-facts:end -->

Coverage is deepest in Automobilista 2, which is where the work started. The
other simulators carry reviewed entries rather than complete rosters.

Matching is exact and case-sensitive. A car the database has not reviewed is
reported as unmatched rather than given a guess, because a confident wrong
answer about a clutch is worse than no answer.

Tested against SimHub 9.11.22 and Automobilista 2 1.6.9.91 on Windows. Newer
versions generally work; they have not been verified.

## Why the data is trustworthy

Most car databases give you a value. This one also tells you where the value
came from and how sure it is, and it keeps three different questions apart:

| Layer | Question |
| --- | --- |
| `authentic_controls` | What did the **real car** have? |
| `simulators[].behavior` | What does **this simulator** actually do? |
| `simulators[].overrides` | Where the two differ, and the evidence for it |

Two rules follow from that, and they matter more than the record count:

- **`unknown` is not `no`.** A blank in a source means nobody established the
  answer. Converting that to "no clutch needed" invents a fact, so the database
  keeps it blank and the overlay says so.
- **Every material claim cites a source**, with a confidence level and a
  falsifiable basis. Simulator observations record the exact game version and
  the date they were checked, because a game update can silently change them.

Primary sources - manufacturer manuals, homologation documents, simulator
documentation - are preferred. Search snippets, unattributed reposts, and
AI-generated claims are not acceptable evidence.

## Scope

The database answers a narrow pre-session question. It covers the wheel rim,
shifter actuation and gear count, unusual patterns such as dogleg, clutch use,
throttle lift, shift cut, and blipping. Steering lock is optional reference
metadata, since most wheelbases apply it automatically.

General vehicle specifications, driver aids and electronics, and handbrake
construction are deliberately out of scope. It is not a car encyclopedia.

## Contributing

If a car is missing or looks wrong, the plugin can walk you through a guided
drive that produces a structured draft - **Contribute a simulator observation**
in the plugin's settings. Nothing is uploaded automatically; the draft stays on
your PC until you choose to attach it to a submission.

A maintainer reviews and approves every contribution before it enters a release.
See [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation

| For | Read |
| --- | --- |
| Installing, updating, removing | [docs/install.md](docs/install.md) |
| Contributing data | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Privacy and networking | [PRIVACY.md](PRIVACY.md) |
| Working on the project | [docs/development.md](docs/development.md) |
| Field semantics and identity rules | [docs/data-model.md](docs/data-model.md) |
| Version history | [CHANGELOG.md](CHANGELOG.md) |

## Licensing

Software is MIT licensed. The original database selection and arrangement is
CC BY 4.0; third-party sources retain their own rights. See
[LICENSE](LICENSE) and [DATA_LICENSE.md](DATA_LICENSE.md).
