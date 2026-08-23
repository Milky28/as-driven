# Guided simulator verification observations

The SimHub guided verification workflow produces staging evidence; it does not
edit a curated car record or approve a database release.

The contract is `schema/v1/verification-observation.schema.json`. Plugin 0.18.2
prefills the exact live telemetry name, class, game/client versions, timestamp,
and SimHub's reported maximum gear count. The tester confirms the gear count
and supplies the observations that require judgment.

Drafts are stored under:

```text
%LOCALAPPDATA%\SimHub\AsDriven\Verification\Drafts
```

They always use `review_status: draft`. Saving one does not change `data/v1`,
the research backlog, or a curation approval.

## Intended test sequence

1. Capture exact telemetry name, class, game version, client version, and time.
2. Record relevant assist state. A result is not comparable when automatic
   clutch or shifting state is unknown.
3. Ask whether the car pulls away from rest with the clutch released. The
   clutch may be used to engage first; the question is only whether moving
   off needs it. Demanding the gear without the clutch made testers grind a
   manual gearbox to destruction, which also ended the rest of the drive.
   The brake is held while the clutch is released, because a clutch let out
   gently against a free car can be slipped into a creep rather than a stall,
   and that creep reads as moving off without a clutch. Held against the
   brake the engine either stalls or it does not. Time spent stationary under
   throttle while braking is therefore never counted as a refusal to move.
4. Count accepted forward gears.
5. Test clutchless upshift and downshift acceptance.
6. Capture or confirm automatic cut and blip, including the observation method.
7. Record visible cockpit actuators and select the primary mechanism from
   hardware plus driver animation or reliable documentation. Direct gear inputs
   that merely advance a sequential gearbox are not evidence of H-pattern
   actuation.
8. Record wheel shape separately from integrated display, shift lights, and
   open-top construction.
9. Save as `draft`; a reviewer promotes or rejects it separately.

## SimHub workflow

1. Load the car and open the As Driven feature page.
2. Expand the visually separate **Contribute car data** workflow and click
   **Start verification from live car**.
3. Confirm the captured identity and exact game version. The left workflow rail
   reuses the last confirmed assist profile for that simulator; changing any
   assist value requires it to be confirmed again.
4. Click **Start in-sim guided drive**.
5. Follow the first maneuver immediately. Map the Next, Retry, Skip, and Cancel actions to
   convenient physical controls to avoid alt-tabbing.
6. Return to the form to review the telemetry suggestions and complete cockpit
   details. `Unknown` and `Not tested` are valid and preferable to a guess.
7. Click **Save draft observation**. A prominent success message is shown and
   the completed form collapses. The observer name is remembered locally for
   the next draft.
8. Use **Open drafts folder** to retrieve the JSON for review.

When an exact identity is unmatched, the plugin page shows **Contribute this
car**. The unmatched popup directs the tester to that page; capture and guided
start both happen there so a redundant contribution action mapping is not
required.

For AMS2, the form begins with the recommended test setup: automatic clutch
and automatic shifting disabled, and the separate throttle-blip assist marked
unavailable. These are proposed test settings, not assumed observations. The
tester must compare them with the simulator and check the green confirmation.
That confirmed profile is stored per simulator and reused on later cars.
When a recommended setting cannot be used, record its actual state and explain
the limitation; affected car behavior should remain unknown or not tested.

For ACC, SimHub reports the game as `AssettoCorsaCompetizione`; the client keeps
it separate as `acc` and captures both the internal car id and telemetry display
name. ACC's executables expose no useful file version, so the draft records the
exact Steam content build from `appmanifest_805550.acf`. A missing or inaccessible
manifest remains `unknown` and must be resolved during review rather than guessed.

The overlay starts directly with the move-off maneuver. Each test uses the same
cycle: perform the maneuver, wait for a captured result, then accept it or choose
Retry/Skip. The overlay uses a short summary and green capture mark so completion is immediately
visible; the longer falsifiable description is retained for form review.
Usable values populated from guided telemetry carry an `AUTO-DETECTED` badge.
An `unknown` or `not-tested` result is instead labeled `REVIEW NEEDED` when the
simulator can expose the needed telemetry. ACC does not expose engine torque
through SimHub, so its unresolved automatic-cut value remains honestly
`unknown` but is labeled `NOT EXPOSED` and is not contributor review work. A
legitimate `Not applicable` value based on the selected primary mechanism is
labeled `DERIVED`. Before that mechanism is chosen, direct H-pattern selection
is labeled `AFTER MECHANISM` rather than presented as a separate unresolved
claim. Detailed evidence text copied from the guided result retains an
`AUTO-FILLED` badge. Direct H-pattern
selection is never inferred merely from a non-adjacent gear telemetry
transition; it remains a cockpit/mechanism review, and sequential or paddle
actuation makes it explicitly not applicable.

A throttle-channel dip is not automatic-cut evidence. It may be traction
control, driver input, or a simulator's telemetry representation. Automatic cut
is detected only from a shift-local engine-torque collapse while throttle demand
stays high. Imports of older ACC drafts degrade any throttle-derived cut answer
to `unknown` because ACC exposes no engine-torque channel through SimHub.

Cockpit mechanism and wheel fields carry an orange `OPTIONAL · REVIEW` badge
until the tester supplies them. These fields improve a draft but never block
submission: a partial, falsifiable observation is preferable to a guess. If a
tester changes an unresolved guided result to a definite answer, the field is
marked `EVIDENCE REQUIRED` until new supporting detail is entered in the
corresponding method field or review notes. Evidence generated by the guided
drive itself does not satisfy this manual-override requirement.

Validate any exported draft from the repository root with:

```shell
python -m as_driven_db validate-observation path/to/observation.json
```

## Staging a record candidate from an observation

An approved observation is still not a curated record. To do the mechanical half
of the reviewer step, stage a candidate bundle from a draft:

```shell
python -m as_driven_db import-observation path/to/observation.json --output build/staged.json
```

The command validates the input against the observation schema (pass
`--skip-validate` to bypass), then writes a single bundle containing a staged
car record, a `sources.json` evidence-entry stub, and a `curation/` approval
stub. It maps only what the drive supports: simulator behavior plus the
authentic-control fields the observation establishes, leaving everything else
`unknown`. Move-off and clutchless results degrade to `unknown` unless the
observation confirms automatic clutch and shifting were both disabled, and it
never infers real-world identity — manufacturer, model, year, and real-world
notes are left as explicit `REVIEW-REQUIRED` placeholders, and any residual
review actions are printed as `REVIEW:` lines. The approval stub's
`approved_controls` are derived with the same mapping `validate` cross-checks,
so once the reviewer fills the identity, registers the source, and sets the
dataset version, promotion into `data/v1` validates cleanly. The bundle stays
outside `data/v1` and `curation` until that explicit reviewer step.

## Promoting a reviewed bundle

Staging does not curate anything. When the reviewer has resolved the real-world
identity and registered the supporting sources, promote the bundle with an
explicit review manifest:

```shell
python -m as_driven_db promote-observation curation/review-batch.json
```

Each entry names its bundle and supplies what a drive cannot establish:
`manufacturer`, `model`, `year`, `real_world_identity_notes`, at least one
registered `real_world_source_refs` entry, the `confidence` level, and the
`confidence_basis`, `identity_basis`, and `specification_basis` statements.
Optional keys cover an aero or configuration alias
(`additional_telemetry_names`), reviewer corrections to fields the drive could
not classify (`control_overrides`), and extra provenance (`additional_claims`).
The reviewed `archetype` classification may also be supplied so a promoted
record enters the same checked classification system as the rest of the dataset.
When a draft recorded `game_version: "unknown"`, a reviewer may supply a
structured `game_version_correction` containing the observed value, an exact
verified build, and the falsifiable basis tying that installed build to the
drive. The draft remains unchanged; the correction is preserved in the approval
and live-source note. It is refused when the draft already recorded a version.
Creating a mod-first record under a real-car id also requires `display_name`, so
the package author's prefix cannot leak into the simulator-independent name.

The command writes the curated record, its curation approval, the live-session
source, and the dataset index together, and sets `dataset_version` from the
manifest. It refuses to run when a required field is missing, when anything
still contains `REVIEW-REQUIRED`, when a cited real-world source is not
registered in `sources.json`, or when a curated record already exists. Nothing
is written unless every entry in the manifest passes those checks.

The approval's `approved_controls` are derived from the finished record with the
same mapping `validate` cross-checks, so the promoted pair validates. Run
`validate` and regenerate the coverage manifest afterwards.

## Automation boundary

The client automatically captures identity, versions, timestamp, and a
suggested gear count. During the guided drive it can detect accepted shifts,
vehicle clutch state, throttle input, an RPM/throttle blip, and a strong torque
interruption. These are reviewable suggestions, not automatic database facts;
ambiguous cut detection remains `unknown`. Cockpit hardware and primary
actuation remain human-reviewed because game input bindings accept both stick
and paddles for a sequential gearbox.

SimHub's clutch channel cannot be separated into pedal movement and any clutch
the car works itself, so the guided drive never rejects a maneuver merely
because that value changes. It raises a note only where the ambiguity could
change an answer: a test accepted as needing no clutch while clutch input was
present, which may be measuring the driver rather than the car. A rejected
attempt is unremarkable, because needing the clutch is what it found.

Move-off is accepted only after movement continues for at least 600 ms while
the engine remains running. A car that rolls slightly when first gear engages
and then stalls is recorded as requiring the standing-start clutch.

Observation files belong in local or ignored staging storage until reviewed.
Approved facts are copied into the appropriate simulator entry and cited by a
registered evidence source. Real-world fields still require independent
real-world evidence.

Multiple drafts for one simulator identity are reconciled claim by claim. A
later thorough draft may establish fields that an earlier draft left unknown,
but it does not silently replace previously supported claims or their evidence.
