# Website and release ideas - September 6, 2026

Original proposal reviewed at `d40c05a`. Pit wall was selected by the maintainer
and implemented for the 0.21.4 candidate, along with today's release summary,
browser deployment gate, and the car/view count clarification. Dataset 0.5.50
versions the existing reviewed corrections. The remaining override cleanup is
deferred for explicit record review. The sections below preserve the proposal.

## Recommended direction: pit wall

Give the catalog the clarity of a motorsport timing sheet: a dark navy masthead,
a narrow livery stripe, a strong table header, and clearly alternating rows.
Keep the existing As Driven name and control vocabulary. The motorsport character
comes from typography, alignment and restrained colour, with no imagery behind
the actual guidance.

Two alternatives are worth comparing: **heritage paddock**, with ivory surfaces,
deep green and a brass accent; and **minimal technical**, which keeps a neutral
slate header and the existing amber accent. Pit wall is the best fit across both
historic and modern cars. These are alternative art directions, not a proposal
to ship three more user-selectable themes.

## Readability changes worth shipping today

1. **Separate car rows.** Current `tr.car` has a border but no resting background;
   every row shares the page grey. Use white and pale blue-grey rows in light
   mode, with more distinct charcoal/navy surfaces in dark mode. Preserve a
   separate hover treatment and a selected-row marker. Apply alternating classes
   to the *visible car rows* after filtering, ignoring hidden detail rows. Plain
   `nth-child(even)` will not work reliably with the current car/detail pairs.
2. **Make the column headings easier to track.** Group Wheel/Shifter under FIT
   and the three technique columns under DRIVE, with one divider between them.
   Use a dark header and readable labels rather than the current 10.5px faint
   uppercase headings. Keep all six current columns and accurate labels.
3. **Use larger ordinary text for instructions.** Aim for 14–15px guidance and
   13–14px secondary text; reserve monospace for compact technical values and
   version metadata. Give the car name approximately 24% of the table, and
   retain Claude's wrapping fix. Test long qualifications before finalising
   widths. Avoid fixed row heights or truncating essential instructions.
4. **Make the active context unmistakable.** Keep Real-car baseline / Driving in
   [simulator] immediately above the table. Keep simulator selection and search
   prominent in the full page; the six-row design sample only illustrates table
   presentation, not replacement filtering or data architecture.
5. **Retain meaning independent of colour.** Driver actions stay amber, automatic
   actions green, optional guidance outlined, unknown guidance dotted and
   explicitly labelled. Livery colours belong in the masthead, not in those
   semantic badges. Mobile cards should preserve the same labels and separation.

The current secondary text token `#535c6a` on `#f0f2f5` measures about 6.03:1;
this is primarily a hierarchy and row-separation problem, not evidence that all
existing text fails contrast. Proposed secondary text `#4a5c6d` on striped
`#e8eef4` measures 5.90:1. Proposed driver, automatic and optional text pairings
measure at least 5.79:1 in the light sample. These are token calculations, not a
complete accessibility certification. Validate all states against the
[W3C text-contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
which requires 4.5:1 for ordinary text. Row stripes themselves are not text and
do not need that ratio.

## Other worthwhile release work

| Priority | Improvement | Why it matters |
| --- | --- | --- |
| Today | Publish a short “Your driving guidance changed” summary | Claude's nine standing-start corrections matter more to existing drivers than a generic maintenance note. Use the existing release-control-changes tool against the published dataset, retaining source links and exact car identities. |
| Today | Gate Pages on the browser checks | Pages now runs the Python suite, but the Playwright job runs separately in `validate.yml`. Include the browser checks in the Pages build dependency so a failed interaction test cannot still deploy. Add theme/filter/expanded-row coverage to that suite. |
| Next | Distinguish dataset identity from catalog view count | The SimHub screenshot says “331 curated cars” while the dataset holds 285 records. The website already distinguishes cars from simulator views. Make the client wording equally explicit so users do not think cars are missing. |
| Next | Review redundant simulator overrides | `AGENTS.md` records 48 existing overrides that restate their baselines. Triage them with a report and explicit review, preserving deliberate retractions/history. Remove misleading difference labels only after their records are reviewed. |

Do not reopen work Claude already completed: summary padding, wheel-text
overflow, coverage-inventory shrinkage, and accounting for uncited sources.
Also defer steering-DOR collection and bulk car additions; they do not solve
this release's readability problem.

## Release boundary and acceptance

The current tree contains data changes since the published 0.21.3 release while
the dataset still identifies itself as 0.5.49. Give today's curated changes a new
dataset version through the normal release process so manual update checks can
distinguish them. Review the resulting driver-facing change summary before
packaging.

For the website work, check light/dark/system appearance, row striping after
search and filters, hover/focus/expanded states, simulator deep links, long
names and qualifications, mobile reflow and enlarged text. Keep the public
dataset and its evidence unchanged by styling. The interactive proposal was
checked separately from production; it is not a completed site implementation.
