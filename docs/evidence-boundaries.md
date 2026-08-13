# Real, simulated, and effective controls

As Driven keeps three related answers separate so one simulator cannot
silently redefine the database's real-car facts.

## Layer 1: represented real car

`authentic_controls` describes the physical controls and operating technique of
the represented real-world car. Claims at this layer need manufacturer,
homologation, team documentation, period technical material, or clearly labeled
secondary research. A simulator observation alone cannot establish a real-car
claim.

When real-world evidence is incomplete, the authentic value remains `unknown`.
An in-game test may still fully establish the simulator layer.

## Layer 2: simulator representation

`simulators[].behavior` describes what an exact, versioned simulator identity
does. A verification observation records test setup, disabled assists, results,
cockpit hardware, and uncertainty. It is evidence for the simulator layer, not
automatic evidence for the represented real car.

`simulators[].overrides` records an explicit, sourced deviation from authentic
controls. An override points to the authentic path, supplies the effective
simulator value, and states the condition under which it applies.

## Layer 3: session-effective guidance

A client builds guidance for a selected simulator in this order:

1. Start with `authentic_controls`.
2. Apply applicable `simulators[].overrides`.
3. Use the simulator `behavior` summary for simulator-facing display fields.
4. Preserve `unknown`; do not fill it from a class peer or a similar car.

The compact `behavior` block is deliberately convenient for clients but is not
a replacement for the authentic record or its provenance.

## Migration audit

Early private-beta records sometimes promoted in-game observations directly
into authentic fields. They remain visible rather than being bulk-rewritten to
guesses. Run this report to find the migration queue:

```shell
python -m as_driven_db audit-boundaries --output build/evidence-boundaries.json
```

Each finding must be resolved by adding real-world evidence, moving a claim to
the simulator layer, or restoring the authentic value to `unknown`. This is a
review task, not an automatic conversion.

### Current state of the queue

The audit count is a burn-down metric, not a pass/fail gate. Guided verification
establishes the simulator layer quickly, so promoting a drive normally adds
findings here; that is expected and is not a reason to weaken the layers.

At dataset 0.3.19 the largest group is `/authentic_controls/steering/wheel_rim`,
where the rim category was read from the in-game cockpit model rather than from
real-world evidence. Those claims are treated as debt to be re-sourced over
time, not as an accepted shortcut. When a record's rim is later supported by
manufacturer or period photographic evidence, cite it and the finding clears.

Until then, do not treat a high audit count as permission to promote a real-car
claim from a simulator observation: an unsupported value still belongs at
`unknown` or in the simulator layer.
