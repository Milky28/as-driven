"""Built-in simulator names shared by Python tooling and the public catalog.

Vehicle identities are still matched exactly. The aliases below apply only to
telemetry clients' game names. Schemas and the independent C# client retain
explicit contracts, with compatibility checked by regression tests.
"""

# id: (product name, filter label, accepted compact game names)
_REGISTRY = {
    'ams2': ('Automobilista 2', 'AMS2', ('automobilista2', 'ams2')),
    'ac': ('Assetto Corsa', 'AC', ('assettocorsa', 'ac')),
    'acc': ('Assetto Corsa Competizione', 'ACC', ('assettocorsacompetizione', 'acc')),
    'ac-evo': ('Assetto Corsa EVO', 'AC EVO', ('assettocorsaevo', 'acevo')),
    'ac-rally': ('Assetto Corsa Rally', 'AC Rally', ()),
    'raceroom': ('RaceRoom Racing Experience', 'RaceRoom', ('rrre', 'rrre64', 'raceroom', 'raceroomracingexperience', 'r3e')),
    'rfactor2': ('rFactor 2', 'rF2', ('rfactor2', 'rf2')),
    'pmr': ('Project Motor Racing', 'PMR', ('projectmotorracing', 'pmr')),
    'gtr2': ('GTR 2', 'GTR2', ('simbingtr2', 'gtr2', 'gtr2fiagtracinggame')),
    'iracing': ('iRacing', 'iRacing', ('iracing',)),
}

SIMULATORS = set(_REGISTRY) | {"other"}
# Preserve reserved ids in the schema/source vocabulary; an empty aliases tuple
# does not recognize a live game until its client integration is ready.
OBSERVING_SIMULATORS = tuple(sorted(_REGISTRY))
SIMULATOR_NAMES = {key: value[0] for key, value in _REGISTRY.items()}
SIMULATOR_LABELS = {**SIMULATOR_NAMES, "ams2": "AMS2"}
SIMULATOR_FILTER_LABELS = {key: value[1] for key, value in _REGISTRY.items()}
SIMULATOR_GAME_NAMES = {key: value[2] for key, value in _REGISTRY.items() if value[2]}


def simulator_label(simulator: str) -> str:
    return SIMULATOR_LABELS.get(simulator, simulator.upper())


def canonical_simulator(game_name: str) -> str | None:
    """Resolve a whole game name, never a prefix or a vehicle identity."""
    compact = "".join(c for c in (game_name or "") if c.isalnum()).lower()
    for simulator, spellings in SIMULATOR_GAME_NAMES.items():
        if compact in spellings:
            return simulator
    return None
