# Project audit and redesign concepts

Audit date: September 4, 2026 (Pacific). Suggestions only; no production code or curated data changed.

## Assessment

The strongest part of As Driven is its evidence discipline: exact identities, explicit unknowns, real-car and simulator separation, reviewer approvals, and an independently usable JSON dataset. Preserve those choices. The next investment should improve the reliability and clarity of the existing experience before adding large amounts of coverage or more themes.

This was a targeted architecture, tooling, release, and UX audit, not a re-verification of every automotive claim or an exhaustive security assessment.

## Inspection and validation

- Inspected both open websites: the public GitHub Pages catalog and the local preview at port 8768. They have different behavior despite using the same dataset version.
- Preserved existing uncommitted changes to `as_driven_db/site.py` and `tests/test_site.py`, plus the existing social-concepts directory.
- Opened SimHub and visually inspected the installed As Driven Garage page. It displayed plugin 0.21.2, dataset 0.5.37, and SimHub 9.12.4. The repository's tested SimHub target remains 9.11.22; opening a settings page does not establish compatibility with all features of a newer host.
- Native automation reported an elevated-window limitation. Other settings pages were reviewed through their current source and checked-in screenshots; the popup and guided overlay were reviewed through their generator and recorded screenshots. No simulator drive was performed, and live overlay positioning was not verified.
- `python -m as_driven_db validate`: passed.
- `python -m unittest discover -s tests -v`: 294 tests passed.
- Non-installing `simhub/build.ps1`: passed, including settings smoke checks and 11,487 .NET assertions. Build emitted MSB3270 architecture warnings for the AnyCPU/WPF reference combination. This is a warning to resolve deliberately, not evidence of an observed runtime crash.
- Local logs are in ignored `build/audit-python-tests.log` and `build/audit-simhub-build.log`.

## Prioritized findings

### 1. Selected simulator detail can disappear under active filters

**Confirmed in the local browser.** With no global simulator selected, Paddles and Clutch required filters active, the Mercedes-AMG GT3 real-car row is visible. Open it and click its AMS2 tab. This sets the global simulator filter; AMS2's reviewed clutch-free launch fails the existing clutch-required filter, hiding the very car the user just selected. The URL still names that car.

Relevant code: `as_driven_db/site.py:2423` (`apply`) and `:2507` (simulator tab handlers). Keep the selected detail independently visible, or clear only conflicting filters with a visible explanation. Do not silently discard every filter. Add a browser regression test that asserts visible content and focus after the click.

### 2. Promotion is validation-safe but not resilient to write failure

**Confirmed by code inspection.** `as_driven_db/promote_observation.py:1516` writes car/approval files, then sources, then index. `as_driven_db/promote.py:224` also writes records before the index. A disk-full condition or failed later write can leave a partially updated tree, although all input validation passed. No such failure was induced in the user's data.

Stage every output first, preserve originals, and use a small transaction journal with rollback/recovery for interrupted batches. A rename per file is useful but does not by itself make a multi-file transaction atomic. Test a failure on the second write and before index replacement using temporary fixture repositories.

### 3. Pages can deploy without the test workflow succeeding

**Confirmed from workflows.** `.github/workflows/pages.yml` validates the data and builds the page independently of `.github/workflows/validate.yml`, which runs the Python suite. A renderer or interaction regression can therefore deploy despite failing tests elsewhere.

Run the relevant tests in the Pages build, or use a shared workflow with an explicit test dependency. Add a small browser suite for simulator selection, conflicting filters, keyboard tabs, deep links, empty states, and mobile reflow. Current site tests are valuable semantic/markup checks, but assertions that JavaScript strings occur in generated HTML do not execute that behavior (`tests/test_site.py:402`).

### 4. Release checks do not exercise the .NET client in CI

The checked-in validation workflow builds the database package, not the SimHub client. Add a Windows Core build/test job if its dependencies can run independently; retain the SDK-backed adapter smoke test as a release gate on a machine with SimHub installed. Do not redistribute SDK binaries just to make CI convenient. Resolve the observed processor-architecture warnings against the supported host architecture.

### 5. Search status needs assistive-technology announcements

`as_driven_db/site.py:2329` and `:2344` render the changing result count and empty message without a status role/live region. Announce a concise settled result count using `role="status"` and appropriate atomic text, avoiding an announcement for every intermediate keystroke. The copy-result status already uses a live region and is a useful precedent.

W3C explicitly discusses result-count and no-results messages in [Understanding Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html). This was a targeted markup finding, not a complete WCAG conformance audit.

## Website recommendations

1. Put simulator selection and car search first. Move most aggregate statistics and Benchmark behind a clearly named Compare simulators or Research entry. Keep a compact dataset badge.
2. Explicitly label the table context: Real-car baseline or Driving in AMS2. The published site's simulator filter limits coverage while rows remain real-car advice; the local working changes correctly move toward simulator-specific advice. Make that distinction visible before the first row, not only in footer prose.
3. Give expanded guidance one hierarchy: Fit hardware, Drive, Simulator differences, Evidence. The local page repeats related information in Drive it, differences, Compare driving setup, and Understand this record. Keep the evidence, but collapse secondary comparisons by default.
4. Add active-filter chips, Clear filters, and a useful empty state. Preserve the selected car during simulator changes. Give a direct Get SimHub plugin link prominent placement.
5. Use a wider car-name column and quieter badges. Long names plus three stacked badges currently make some table rows unusually tall. Explore a list/detail layout for focused lookup, while retaining a dense table for comparison.
6. Continue mobile cards already present in the local CSS. Verify on narrow screens and at increased text size before adopting the mockup. Mobile was not interactively tested in this audit.

## Settings, info popup, and guided drive

**Garage:** put size, duration, and theme beside a persistent preview. Keep Save changes and dirty-state feedback visible without scrolling past the theme grid (`AsDrivenSettingsControl.cs:906`, `:1146`). Keep the full theme gallery available in a secondary picker. The existing themes are a differentiator; more themes are lower priority than easier comparison.

**Empty Garage:** replace repeated Not available tiles with a short Choose a preview car action. Offer a clearly labeled sample preview without pretending it is live telemetry. The current page accurately labels waiting states, but spends most of the initial screen repeating them.

**Car browser:** retain the existing separation between selecting a catalog entry and showing an overlay. Give long car names two lines and a separate simulator label; avoid depending on horizontal scrolling in the list. Add a direct source/details link and a small recent/favorites list stored locally.

**Contribute data:** retain the existing four stages, local drafts, explicit assist confirmation, review, and manual sharing. Reduce the introductory paragraphs into one instruction per stage. Add a button-binding readiness summary before starting the drive. Say which action is still unbound rather than letting the user discover it in the cockpit. Preserve the distinction between simulator driving assists and systems built into the real car.

**System:** lead with installed plugin, installed dataset, and last manually checked available versions. Put the explanation about offline operation below that summary. Preserve the existing user-triggered update check and deliberate installation; do not add background network activity.

**Info popup:** keep FIT and USE/DRIVE. Make the action more prominent than its label: Use clutch, Lift + clutch, Clutch / blip optional. The recorded Touring theme uses red headings over blue panels; validate those pairings and other themes at actual overlay size. Move long explanatory text to a secondary detail view or keep only a short note in compact mode. Keep exact identity match distinct from confidence in individual claims.

**Guided overlay:** the current title is larger than the instruction (`simhub/dash/generate.py:1168`), and footer controls are only 10-11 units at native size (`:1153`, `:1159`). Make the imperative the largest text: Lift, then shift up. Keep Leave the clutch untouched visible. Show Captured / awaiting acceptance separately from Accepted. Negative test outcomes can still be valid captures; preserve that existing behavior. Display actual mapped button hints when available, with an explicit unbound state otherwise. Keep text labels in addition to color and test legibility against bright track scenery at real size.

## Useful additions within scope

- A local My hardware profile: owned rim categories, H-pattern/sequential shifter, clutch pedal. Compare it with a selected setup without rewriting the authentic record or claiming hardware was automatically detected.
- Per-field evidence freshness: recorded simulator build/check date versus the detected current build. Say Not reverified on this build; do not automatically declare the old evidence false.
- A release-to-release control-change summary: which cars changed wheel, shifter, clutch or blip guidance, with evidence links. Prioritize changes affecting the user's recent cars.
- Prioritize unresolved controls that change hardware or technique, using the existing coverage and identity decisions. Do not silently queue mods or retired identities as missing official content.

## Concepts and implementation notes

- [Website concept](01-website.png): simulator-first lookup, list/detail desktop layout, stacked mobile advice.
- [Settings concept](02-settings.png): preview beside appearance controls, visible save bar, focused contribution setup.
- [Overlay concepts](03-overlays.png): detailed and compact preflight plus a larger guided-drive imperative.
- [Exact prompts](prompts.md): built-in imagegen generation and correction prompts.

These are raster design sketches, not working UIs or final data specifications. Retain the existing As Driven mark and approved controls icons rather than adopting the generated logos. Use one search field in the website implementation; the sketch redundantly adds Filter results. Use a momentary Show preview button rather than the checkbox drawn in the settings sketch. The compact overlay's hardware belongs in its own FIT row, not alongside technique rows. The generated progress dots do not match the text step count; use the actual step state or omit the dots. Populate all evidence dates, gear-gate geometry, and instructions from the curated record. Keep the state demonstration strip outside the shipped driving overlay.

Recommended order: fix the disappearing detail, gate deployment on tests, make promotion recoverable, then simplify the Garage and guided overlay. Add hardware profiles and personalized change summaries after those foundations.
