# Automatic-cut evidence audit

**Decision date:** 2026-08-23  
**Dataset release:** 0.4.18

## Decision rule

A no-lift upshift establishes that the simulator accepted the shift without the
driver lifting. It does not by itself establish how engine torque was removed.
A dip in the reported throttle channel is also not diagnostic: it may represent
driver input, traction-control intervention, a simulator's filtered throttle
signal, or an actual shift cut.

As Driven therefore records `automatic_cut: yes` from live telemetry only when
engine torque collapses around the gear change while the driver's throttle input
remains sustained, or when an independent technical source explicitly describes
the cut. If the simulator does not expose a suitable torque channel and no such
source exists, the value is `unknown`, never an assumed `no`.

## Findings

Twelve older AMS2 reviews used a brief throttle-graph interruption as their only
automatic-cut evidence. None had a torque trace or an independent source that
settled the mechanism. Their authentic automatic-cut field and AMS2 `shift_cut`
field were retracted to `unknown`:

- Aston Martin Valkyrie
- Audi R8 LMS GT3
- Audi R8 LMS GT3 Evo II
- Chevrolet Corvette C8 Z06 (+Z07 Upgrade)
- Chevrolet Cruze Stock Car 2024
- Lamborghini Huracán GT3 EVO2
- Lamborghini Veneno Roadster
- Maserati GT2 Stradale
- Renault R25
- Renault R26
- Renault R28
- Toyota Corolla Stock Car 2024

The Audi R8 LMS GT3 Evo II's fingerprinted RSS implementation in Assetto Corsa
is separate evidence. Its guided drive detected a torque collapse under sustained
throttle, so that implementation keeps `automatic_cut: yes` as a simulator
override while the real-car baseline and AMS2 value remain unknown.

## Consequence for future drives

The guided detector no longer treats throttle movement as automatic-cut
evidence. ACC currently exposes no engine-torque property through this SimHub
path, so ACC cut fields remain unknown unless independent evidence establishes
them. This is an evidence limitation, not a claim that those cars lack shift-cut
systems.
