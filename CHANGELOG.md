# Changelog

Plugin and dataset versions count different things, but ship together in one
release. Dataset history is also recorded in `data/v1/index.json` and the
project documentation.

## 0.21.0 - 2026-08-29

- Add a manual update check, off until an endpoint is set. The endpoint is blank
  by default so no request is possible, must be https, and the check compares two
  version strings without downloading anything.
- Add packaged popup themes selectable by car era, including GPLaps Classic, and
  give popup behavior the full page width so the theme rack wraps instead of
  stacking one choice per row.
- Correct the running-shift clutch on 72 H-pattern records. A guided drive
  records what the simulator accepts, which is not the real car's authentic
  technique: a synchromesh gearbox is shifted with the clutch, a dog box is not,
  and an unestablished gearbox settles nothing.
- Ship dataset 0.5.34 with 279 curated records.
- Drop the early-access framing. What survives is a plain statement of the
  versions actually tested.

## 0.20.2 - 2026-08-27

- Add the native As Driven settings page with live preflight, offline car
  browsing, contribution capture, and advanced diagnostics.
- Add the guided-drive workflow and explicit GitHub handoff for simulator
  observations while keeping every upload under the user's control.
- Add category artwork for round, D-shaped, GT or Formula, and open-top wheel
  configurations alongside the established shifter and technique guidance.
- Expand exact reviewed development coverage across AMS2, Assetto Corsa,
  Assetto Corsa Competizione, Assetto Corsa EVO, RaceRoom, and rFactor 2 while
  retaining AMS2 as the tested client target.
- Preserve customized overlay positions during upgrades and keep settings,
  drafts, diagnostics, and the database during default removal.
- Ship a privacy-scanned, checksummed SimHub ZIP with root-level guided install
  and uninstall launchers plus an independently updateable database package.

## 0.15.0 early access - 2026-08-12

- Establish the first documented early-access compatibility boundary: Windows,
  SimHub 9.11.22, AMS2 1.6.9.91, and schema v1.
- Provide exact-match live guidance, offline car preview, three overlay sizes,
  unmatched-car diagnostics, and guided local contribution drafts.
- Separate plugin and database release artifacts, each with SHA-256 checksums.
- Add a safe uninstaller that preserves user data and customized layouts by
  default.
- Package dataset 0.3.18 with 85 curated records.
- Document offline behavior, local data storage, known limitations, release
  validation, contribution review, and rollback.

## Dataset history

Moved verbatim from the README, where a paragraph per dataset version had
grown longer than the description of the project. Ordered oldest first, as
it was written. Dataset versions are independent of the plugin versions
above.

The 0.3.6 review resolves the five verified historical sequential-stick cars
with no automatic blip to `manual_blip = required`, making the driver-supplied
rev-matching technique explicit.
The 0.3.7 review adds Aston Martin DBR9, Chevrolet Corvette C5-R, Saleen S7-R
GT1, and Milano GT55 from exact AMS2 1.6.9.91 identities and live control
tests. Each uses a six-speed sequential stick, standing-start clutch,
automatic upshift cut, manual downshift blipping, and a round no-display rim.
The 0.3.8 review adds Milano GT36, Porsche 996 GT3 RSR, Spyker C8 Spyder
GT2-R, and TVR Tuscan T400R GT2. The Porsche directly verified automatic
downshift blipping; the other three require driver blipping.
The 0.3.9 review adds Audi R8 LMP1, Courage C60 Hybrid, and Dallara SP1. The
Dallara's paddle classification is supported by visible paddles and replay
animation while retaining its visible cockpit lever as an explicit caveat.
The 0.3.10 review adds the Lola B05/40 V8 and Turbo. Both directly verified
clutch-free move-off, six paddle gears, automatic cut and blip, and D-shaped
display rims; the move-off mechanism remains unknown.
Dataset 0.3.11 adds orthogonal simulator wheel observations for display,
shift-light, and open-top construction without changing the five cars' shape
categories. It also introduces schema-enforced approvals, automatic backlog
reconciliation, and the staged guided-verification contract. The SimHub client
version remains independent.
Dataset 0.3.12 promotes four separately reviewed guided-verification drafts:
Alpine A110 GT4 Evo, Aston Martin Vantage GT3 Evo, Formula Vee Gen2, and
Chevrolet Corvette C3.R Convertible.
Dataset 0.3.13 promotes Audi R8 LMS GT3 Evo II, Lamborghini Huracan GT3 EVO2,
Chevrolet Cruze Stock Car 2024, and Toyota Corolla Stock Car 2024. Guided
telemetry directly established most controls; each automatic-cut claim is
separately disclosed at medium confidence because the tester manually observed
a brief throttle-graph interruption that the detector did not classify.
Dataset 0.3.14 promotes Audi V8 quattro DTM, Lamborghini Veneno Roadster, Audi
R8 LMS GT3, Chevrolet Corvette C8 Z06 (+Z07 Upgrade), and Super Trophy Trucks.
The Audi DTM draft also demonstrates reviewed correction of a false move-off
caused by a slight roll before stalling. Super Trophy Trucks preserves its
automatic construction separately from its visible sequential manual-override
lever, and all unresolved automatic-cut behavior remains `unknown`.
Dataset 0.3.15 promotes Maserati GT2 Stradale, the road-going Aston Martin
Valkyrie, and the exact High Downforce identities for Renault R25, R26, and
R28. The two road cars retain medium-confidence manually confirmed automatic
cut claims; the Renault guided tests captured shift-local automatic cut and
blip traces directly. Untested Renault aero identities are not silently added.
Dataset 0.3.16 promotes ten exact guided identities: Ligier JS2 R,
Lamborghini Miura SV and Revuelto, Audi R8 V10 GT, Dodge Viper ACR, BMW M3
E46 GTR, Maserati GranSport Trofeo, and three configuration-specific Stock USA
records. Stock USA mappings remain fictionalized and configuration-scoped;
the Audi record uses the later seven-speed S tronic generation rather than the
unrelated 2010 six-speed R tronic car.
Dataset 0.3.17 revalidates the fifteen remaining spreadsheet-era records in
AMS2 1.6.9.91 and corrects their exact identities and simulator observations.
Dataset 0.3.18 promotes the final nine reviewed entries from that audit,
including exact high-downforce and tyre-specific identities. The separate AMS2
coverage manifest now classifies the larger current roster for later research
and verification; it is not silently included in the curated dataset.
Dataset 0.3.19 promotes the first modern-prototype verification batch: BMW M
Hybrid V8, Porsche 963, Chevrolet Corvette GTP, MetalMoro AJR Chevrolet, and
MetalMoro AJR Gen2 Chevrolet. The two LMDh cars use the category's spec
seven-speed paddle transmission with automatic cut and blip, while the 1988
IMSA GTP Corvette is the batch's only manual-technique car: a five-speed
H-pattern requiring the clutch to pull away, a throttle lift to upshift, and a
manual blip to downshift. The two MetalMoro prototypes are reviewed
independently of one another rather than inherited across the generation.
Dataset 0.3.20 promotes the seven remaining aero-inheritance-ready identities
as explicit Low Downforce aliases of already verified base records. No control
value changes and no record is added; each alias is disclosed as an untested
aero configuration in its record notes and curation approval.
Dataset 0.3.21 closes the remaining review-only queue. Four unqualified Formula
identities and one whitespace-only Stock USA identity become explicit aliases of
their curated records, and six identities are closed as written decisions in
`research/ams2-identity-decisions.json`: five retired pre-rename observations
that are deliberately not aliased because they are not selectable in the
certified build, and the BMW M3 Safety Car as outside product scope. Guided
verification is now the only remaining category of open work.
Dataset 0.3.22 promotes modern-prototype batch 02: Nissan R89C, Porsche 962C,
and MetalMoro MRX Duratec P4. The two Group C cars are manual-technique cars,
each a five-speed H-pattern needing the clutch to pull away, a throttle lift to
upshift, and a manual blip to downshift. The MRX uses a sequential stick with an
automatic cut but no automatic blip. Nissan's own heritage record supplies the
R89C five-speed VGC transmission and Lola-built chassis, while Metalmoro states
the MRX fixes no transmission, so its sequential six-speed is recorded at medium
confidence as the configuration modeled in AMS2. Verifying these bases makes the
R89C and 962C Low Downforce identities inheritance-ready.
Dataset 0.3.23 promotes those two as explicit Low Downforce aliases, again without
driving and without changing any control value.
Dataset 0.3.24 promotes the first contemporary GT batch: seven paddle-shift GT3
cars whose controls proved identical, and the Ginetta G55 GT3, which AMS2 classes
as GT Open and which uses a sequential lever and needs the clutch to pull away.
Its throttle lift and manual blip stay unknown because a lever paired with
automatic cut and blip has no precedent among curated cars.
Dataset 0.3.26 promotes the GT4 batch, which is deliberately not uniform. BMW M4
GT4, McLaren 570S GT4, and Porsche 718 Cayman GT4 Clubsport MR carry road-derived
dual-clutch gearboxes, which is why two of them have seven gears where most GT4
cars have six, while the Mercedes-AMG GT4 and both Ginetta G55 variants use
conventional racing sequentials. The Cayman carries the first simulator override
in the dataset: its real PDK has no clutch pedal, so the record says the
standing-start clutch is not required while a sourced override records that AMS2
requires clutch input to move off.
Dataset 0.3.27 completes the GT family with two late-1990s Le Mans GT1 cars, two
modern GTE cars, and the Puma GTE, which despite its name is a 1970s Brazilian
road car on Volkswagen running gear with four H-pattern gears and no automation.
Dataset 0.3.28 promotes the touring and stock batch, whose three period European
cars carry the first dogleg gates recorded from a guided drive rather than from a
specification: the BMW M1 Procar, the Mercedes-Benz 190E 2.5-16 Evolution II and
the BMW M3 Sport Evolution. Super V8 is Reiza's fictionalised Australian
Supercars car, which retains a manual stick shift on a six-speed sequential
transaxle.
Dataset 0.3.29 promotes the club and road batch, finishing every category except
open-wheel. Eight are ordinary synchromesh H-pattern cars with no automation. The
tenth is the batch's finding: `Ginetta G40` is the GT5 Challenge car on a
six-speed Quaife sequential, not the five-speed synchromesh H-pattern of
`Ginetta G40 Cup`, so a shared nameplate again proved to be no basis for shared
controls. This release also settles what `manual_blip` asserts: mechanical
necessity, so `required` is reserved for gearboxes that cannot engage without a
blip and synchromesh cars are `optional`. Three earlier records were corrected to
match.
Dataset 0.3.30 opens the open-wheel queue with the 1967 to 1979 era: six
five-speed H-pattern cars with no automation. Brabham BT26A and Lotus 49C are the
first `dogbox` records established from evidence rather than observed behavior,
because both use racing Hewlands engaged by dog rings rather than synchronisers,
which makes their downshift blip required. The four Reiza cars carry no
real-world chassis, so their gearbox construction stays `unknown`.
Dataset 0.3.31 adds the 1983 to 1986 turbo era and establishes how simulator aero
configurations reach a driver. AMS2 selects the downforce variant from the
circuit rather than from the player, so one car reports different telemetry
identities at different tracks; each record now carries every observed aero
identity, or a driver would be reported unmatched purely for choosing a
different track. Lotus Renault 98T carries the first gear-count override: its
real gearbox is a six-speed and AMS2 models five.
