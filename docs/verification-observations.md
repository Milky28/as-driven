# Guided simulator verification observations

The guided verification workflow produces staging evidence; it does not edit a
curated car record or approve a database release.

The contract is `schema/v1/verification-observation.schema.json`. A future
SimHub guided mode can populate the fields that telemetry can establish and ask
the tester only for observations that require judgment.

## Intended test sequence

1. Capture exact telemetry name, class, game version, client version, and time.
2. Record relevant assist state. A result is not comparable when automatic
   clutch or shifting state is unknown.
3. Ask whether the car moves from rest without physical clutch input.
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

## Automation boundary

The client may automatically capture identity, versions, timestamp, gear count,
and telemetry traces. It should present suggested cut/blip results with the
measurement basis and let the tester confirm them. Cockpit hardware and primary
actuation remain human-reviewed because game input bindings accept both stick
and paddles for a sequential gearbox.

Observation files belong in local or ignored staging storage until reviewed.
Approved facts are copied into the appropriate simulator entry and cited by a
registered evidence source. Real-world fields still require independent
real-world evidence.
