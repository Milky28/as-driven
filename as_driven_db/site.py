"""Render the curated database as one self-contained page.

The dataset is the product, and until now the only way to read it was to install
a SimHub plugin or open the JSON. This builds a page anyone can open: every
curated car, what to fit, what to do, and - just as plainly - what is not
established yet.

The wording mirrors AsDriven.Core.PreflightLabels so the page and the in-sim
card say the same thing. The tone a value carries is the same question the card
asks: is this the driver's job. It has four answers, and `unknown` is not a quiet
`no`; the page gives it its own treatment so a gap in the evidence can never read
as a car that handles it.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

TONE_DRIVER = "you"
TONE_CAR = "car"
TONE_OPTIONAL = "optional"
TONE_UNKNOWN = "unknown"

TONE_TITLE = {
    TONE_DRIVER: "You do this",
    TONE_CAR: "The car does this",
    TONE_OPTIONAL: "Your choice",
    TONE_UNKNOWN: "Not established by the evidence",
}

ACTUATION = {
    "h-pattern": "H-pattern",
    "sequential-stick": "sequential",
    "sequential-paddles": "paddles",
    "automatic-lever": "automatic",
    "direct-selection": "direct select",
}

RIM = {
    "round": "Round rim",
    "d-shaped": "D-shaped rim",
    "gt-formula": "GT / Formula rim",
    "gt-style": "GT / Formula rim",
    "prototype": "GT / Formula rim",
    "formula": "GT / Formula rim",
    "yoke": "Yoke",
    "other": "Other rim",
}


def shifter(gears: Any, actuation: str) -> str:
    label = ACTUATION.get(actuation)
    if label is None:
        return "Shifter not recorded"
    return f"{gears}-speed {label}" if isinstance(gears, int) and gears > 0 else label


def gate(actuation: str, pattern: str, first_gear: str | None) -> str:
    if pattern == "dogleg-h":
        if first_gear == "down-left":
            return "Dogleg gate, 1st down and left"
        if first_gear == "down-right":
            return "Dogleg gate, 1st down and right"
        return "Dogleg gate, 1st outside the plane"
    if pattern == "standard-h":
        if first_gear == "up-right":
            return "Standard gate, 1st up and right"
        if first_gear == "down-left":
            return "Standard gate, 1st down and left"
        return "Standard gate, 1st up and left"
    if actuation == "sequential-paddles":
        return "Sequential, one gear at a time"
    if actuation == "sequential-stick":
        return "Fore and aft, one gear at a time"
    if pattern == "sequential":
        return "Sequential, one gear at a time"
    if pattern == "automatic-gate":
        return "Automatic gate"
    if pattern == "direct":
        return "Direct selection"
    return "Gate not recorded"


def launch(value: str) -> tuple[str, str]:
    return {
        "required": ("Clutch required", TONE_DRIVER),
        "not-required": ("No clutch needed", TONE_CAR),
        "anti-stall-available": ("Anti-stall fitted", TONE_CAR),
        "not-applicable": ("No clutch fitted", TONE_CAR),
    }.get(value, ("Not established", TONE_UNKNOWN))


def upshift(lift: str, cut: str, clutch: str) -> tuple[str, str]:
    if lift == "required":
        text = "Lift the throttle"
    elif lift == "partial":
        text = "Part lift"
    elif lift == "not-required":
        text = "Stay flat, car cuts" if cut == "yes" else "Stay flat"
    elif lift == "not-applicable":
        text = "Nothing to do"
    else:
        return "Not established", TONE_UNKNOWN
    if clutch == "required":
        return text, TONE_DRIVER
    return text, TONE_DRIVER if lift in {"required", "partial"} else TONE_CAR


def downshift(manual: str, automatic: str, clutch: str) -> tuple[str, str]:
    if manual == "required":
        return "Blip to rev-match", TONE_DRIVER
    if manual == "optional":
        return "Blip optional", TONE_OPTIONAL
    if manual == "not-required":
        text = "Car blips for you" if automatic == "yes" else "No blip needed"
        return text, TONE_DRIVER if clutch == "required" else TONE_CAR
    if manual == "not-applicable":
        return "Nothing to do", TONE_CAR
    return "Not established", TONE_UNKNOWN


def _car(record: dict[str, Any], archetypes: dict[str, str]) -> dict[str, Any]:
    identity = record["identity"]
    controls = record["authentic_controls"]
    transmission = controls["transmission"]
    rim = controls["steering"]["wheel_rim"]
    launch_text, launch_tone = launch(transmission["standing_start_clutch"])
    up_text, up_tone = upshift(
        transmission["upshift"]["throttle_lift"],
        transmission["upshift"]["automatic_cut"],
        transmission["upshift"]["clutch"],
    )
    down_text, down_tone = downshift(
        transmission["downshift"]["manual_blip"],
        transmission["downshift"]["automatic_blip"],
        transmission["downshift"]["clutch"],
    )
    simulators = record.get("simulators") or [{}]
    entry = simulators[0]
    block = record.get("archetype") or {}
    classification = block.get("classification")
    mechanism = archetypes.get(block.get("archetype_id", ""), "")

    open_fields = sorted(
        path.rsplit("/", 1)[-1].replace("_", " ")
        for path, value in _flatten(transmission).items()
        if value == "unknown"
    )
    return {
        "id": record["record_id"],
        "name": identity["display_name"],
        "car_class": identity.get("class", ""),
        "year": identity.get("year", {}).get("label", ""),
        "shifter": shifter(transmission["forward_gears"], transmission["shift_actuation"]),
        "gate": gate(
            transmission["shift_actuation"],
            transmission["shift_pattern"],
            transmission.get("first_gear_position"),
        ),
        "launch": [launch_text, launch_tone],
        "up": [up_text, up_tone],
        "down": [down_text, down_tone],
        "rim": RIM.get(rim.get("shape", ""), "Rim not recorded"),
        "summary": record.get("driver_summary", ""),
        "classification": classification,
        "mechanism": mechanism,
        "deviations": [
            {"field": item["path"].rsplit("/", 1)[-1].replace("_", " "), "why": item["basis"]}
            for item in block.get("deviations", [])
        ],
        "archetype_basis": block.get("basis", ""),
        "open_fields": open_fields,
        "simulator": entry.get("simulator", ""),
        "game_version": entry.get("verified_game_version", ""),
        "verified_at": entry.get("verified_at", ""),
        "actuation": transmission["shift_actuation"],
        "start": transmission["standing_start_clutch"],
        "blip": transmission["downshift"]["manual_blip"],
    }


def _flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in node.items():
        path = f"{prefix}/{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


def collect(root: Path) -> dict[str, Any]:
    data = root / "data" / "v1"
    index = json.loads((data / "index.json").read_text(encoding="utf-8"))
    archetypes: dict[str, str] = {}
    archetype_path = data / "archetypes.json"
    if archetype_path.exists():
        for entry in json.loads(archetype_path.read_text(encoding="utf-8"))["archetypes"]:
            archetypes[entry["archetype_id"]] = entry["label"]
    cars = [
        _car(json.loads((data / relative).read_text(encoding="utf-8")), archetypes)
        for relative in index["records"]
    ]
    cars.sort(key=lambda car: (car["name"].lower(), car["car_class"].lower()))
    return {
        "version": index["dataset_version"],
        "released_at": index["released_at"],
        "cars": cars,
    }


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _cell(value: list[str]) -> str:
    text, tone = value
    return (
        f'<td class="state"><span class="tone tone-{tone}" '
        f'title="{_e(TONE_TITLE[tone])}">{_e(text)}</span></td>'
    )


def _row(car: dict[str, Any]) -> str:
    detail = []
    if car["summary"]:
        detail.append(f'<p class="summary">{_e(car["summary"])}</p>')

    if car["mechanism"]:
        heading = "Mechanism" if car["classification"] == "matches" else "Based on"
        detail.append(
            f'<div class="block"><h4>{heading}</h4><p>{_e(car["mechanism"])}</p></div>'
        )
    if car["deviations"]:
        items = "".join(
            f'<li><span class="field">{_e(item["field"])}</span>{_e(item["why"])}</li>'
            for item in car["deviations"]
        )
        detail.append(f'<div class="block"><h4>Departs from it</h4><ul>{items}</ul></div>')
    if car["classification"] in {"undetermined", "no-archetype"} and car["archetype_basis"]:
        heading = (
            "Not yet classified" if car["classification"] == "undetermined" else "Its own mechanism"
        )
        detail.append(
            f'<div class="block"><h4>{heading}</h4><p>{_e(car["archetype_basis"])}</p></div>'
        )
    if car["open_fields"]:
        chips = "".join(f'<span class="chip">{_e(field)}</span>' for field in car["open_fields"])
        detail.append(
            '<div class="block"><h4>Not established</h4>'
            f'<div class="chips">{chips}</div></div>'
        )
    provenance = " · ".join(
        part
        for part in (
            car["simulator"].upper() if car["simulator"] else "",
            car["game_version"],
            f'verified {car["verified_at"]}' if car["verified_at"] else "",
        )
        if part
    )
    detail.append(f'<p class="provenance">{_e(provenance)}</p>')

    search = " ".join(
        [car["name"], car["car_class"], car["shifter"], car["gate"], car["year"]]
    ).lower()
    return (
        f'<tr class="car" data-search="{_e(search)}" data-actuation="{_e(car["actuation"])}" '
        f'data-start="{_e(car["start"])}" data-blip="{_e(car["blip"])}" tabindex="0" '
        f'aria-expanded="false">'
        f'<td class="car-name"><span class="name">{_e(car["name"])}</span>'
        f'<span class="meta">{_e(car["car_class"])}</span></td>'
        f'<td class="spec"><span class="shifter">{_e(car["shifter"])}</span>'
        f'<span class="meta">{_e(car["gate"])}</span></td>'
        f"{_cell(car['launch'])}{_cell(car['up'])}{_cell(car['down'])}"
        f'<td class="rim">{_e(car["rim"])}</td>'
        "</tr>"
        f'<tr class="detail" hidden><td colspan="6"><div class="detail-inner">'
        f'{"".join(detail)}</div></td></tr>'
    )


def render(payload: dict[str, Any]) -> str:
    cars = payload["cars"]
    clutch_start = sum(1 for car in cars if car["start"] == "required")
    you_blip = sum(1 for car in cars if car["blip"] == "required")
    open_any = sum(1 for car in cars if car["open_fields"])
    rows = "\n".join(_row(car) for car in cars)
    page = TEMPLATE.format(
        version=_e(payload["version"]),
        released=_e(payload["released_at"]),
        total=len(cars),
        clutch_start=clutch_start,
        you_blip=you_blip,
        open_any=open_any,
        rows=rows,
    )
    # The page owns no <head>, so it cannot declare a charset. Emitting numeric
    # references keeps a name like "Fórmula Inter MG15" or a separator correct
    # whatever encoding the host assumes.
    return page.encode("ascii", "xmlcharrefreplace").decode("ascii")


def build_site(root: Path) -> str:
    return render(collect(root))


TEMPLATE = """<title>As Driven Controls</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root {{
  --bg: #f4f5f7;
  --surface: #ffffff;
  --surface-2: #eceef2;
  --ink: #16181d;
  --muted: #5c626e;
  --faint: #878d9a;
  --line: #dfe2e8;
  --accent: #c2610a;
  --driver: #a8520a;
  --driver-bg: #fbeedd;
  --car: #2e6b5e;
  --car-bg: #e4efec;
  --optional: #7a5c1f;
  --optional-bg: #f5eddb;
  --focus: #1f5fa8;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #0f1115;
    --surface: #171a20;
    --surface-2: #1e222a;
    --ink: #e8eaee;
    --muted: #99a0ad;
    --faint: #737b88;
    --line: #272b33;
    --accent: #f0a03c;
    --driver: #f0a03c;
    --driver-bg: #33240f;
    --car: #5bb39b;
    --car-bg: #122b26;
    --optional: #c9a15e;
    --optional-bg: #2b2416;
    --focus: #6fa8e8;
  }}
}}
:root[data-theme="dark"] {{
  --bg: #0f1115;
  --surface: #171a20;
  --surface-2: #1e222a;
  --ink: #e8eaee;
  --muted: #99a0ad;
  --faint: #737b88;
  --line: #272b33;
  --accent: #f0a03c;
  --driver: #f0a03c;
  --driver-bg: #33240f;
  --car: #5bb39b;
  --car-bg: #122b26;
  --optional: #c9a15e;
  --optional-bg: #2b2416;
  --focus: #6fa8e8;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 40px 24px 80px; }}
header {{ display: flex; flex-direction: column; gap: 14px; margin-bottom: 32px; }}
h1 {{
  font-family: Archivo, ui-sans-serif, system-ui, sans-serif;
  font-weight: 700;
  font-size: clamp(30px, 5vw, 42px);
  letter-spacing: -0.02em;
  margin: 0;
  text-wrap: balance;
}}
.lede {{ margin: 0; max-width: 62ch; color: var(--muted); }}
.stats {{ display: flex; flex-wrap: wrap; gap: 10px 28px; padding-top: 6px; }}
.stat {{ display: flex; flex-direction: column; gap: 1px; }}
.stat b {{
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 21px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}}
.stat span {{
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 10.5px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
}}
.controls {{
  position: sticky; top: 0; z-index: 5;
  display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
  padding: 14px 0; margin-bottom: 6px;
  background: var(--bg); border-bottom: 1px solid var(--line);
}}
input[type="search"] {{
  flex: 1 1 240px; min-width: 200px;
  padding: 9px 12px;
  font: inherit; color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--line); border-radius: 3px;
}}
input[type="search"]::placeholder {{ color: var(--faint); }}
select {{
  padding: 9px 10px;
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 12.5px;
  color: var(--ink); background: var(--surface);
  border: 1px solid var(--line); border-radius: 3px;
}}
input:focus-visible, select:focus-visible, tr:focus-visible {{
  outline: 2px solid var(--focus); outline-offset: 1px;
}}
.count {{
  margin-left: auto;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px; color: var(--faint); font-variant-numeric: tabular-nums;
}}
.table-scroll {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; min-width: 880px; }}
/* Not sticky. The wide-content wrapper needs overflow-x, which makes it a
   scroll container, and a sticky header inside one anchors to the container
   rather than to the viewport - so it parks itself over the first row and
   stays there. The filter bar sits outside the wrapper and sticks properly. */
thead th {{
  padding: 9px 12px; text-align: left;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 10.5px; font-weight: 500;
  letter-spacing: 0.09em; text-transform: uppercase; color: var(--faint);
  background: var(--bg); border-bottom: 1px solid var(--line);
  white-space: nowrap;
}}
tr.car {{ border-bottom: 1px solid var(--line); cursor: pointer; }}
tr.car:hover {{ background: var(--surface); }}
tr.car td {{ padding: 11px 12px; vertical-align: top; }}
.name {{ display: block; font-weight: 600; }}
.shifter {{ display: block; font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 13px; }}
.meta {{ display: block; font-size: 12.5px; color: var(--faint); margin-top: 2px; }}
.rim {{ font-size: 13px; color: var(--muted); white-space: nowrap; }}
.state {{ white-space: nowrap; }}
.tone {{
  display: inline-block; padding: 3px 9px; border-radius: 2px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px; line-height: 1.45;
}}
.tone-you {{ background: var(--driver-bg); color: var(--driver); font-weight: 500; }}
.tone-car {{ background: var(--car-bg); color: var(--car); }}
.tone-optional {{ background: var(--optional-bg); color: var(--optional); }}
/* No fill. A gap in the evidence must never read as a state the car handles. */
.tone-unknown {{
  background: none; color: var(--faint);
  border: 1px dotted currentColor; padding: 2px 8px;
}}
tr.detail > td {{ padding: 0; border-bottom: 1px solid var(--line); background: var(--surface); }}
.detail-inner {{
  display: flex; flex-direction: column; gap: 16px;
  padding: 18px 14px 22px; max-width: 78ch;
}}
.summary {{ margin: 0; font-size: 14.5px; }}
.block {{ display: flex; flex-direction: column; gap: 5px; }}
.block h4 {{
  margin: 0;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 10.5px; font-weight: 500;
  letter-spacing: 0.09em; text-transform: uppercase; color: var(--faint);
}}
.block p {{ margin: 0; color: var(--muted); font-size: 14px; }}
.block ul {{ margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 7px; }}
.block li {{ font-size: 14px; color: var(--muted); }}
.field {{
  display: inline-block; margin-right: 8px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px; color: var(--accent);
}}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chip {{
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px; color: var(--faint);
  border: 1px dotted currentColor; border-radius: 2px; padding: 2px 8px;
}}
.provenance {{
  margin: 0;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11.5px; color: var(--faint);
}}
.empty {{ padding: 40px 12px; color: var(--muted); }}
.legend {{
  display: flex; flex-wrap: wrap; gap: 8px 18px;
  margin: 22px 0 0; padding-top: 18px; border-top: 1px solid var(--line);
  font-size: 13px; color: var(--muted);
}}
.legend .tone {{ margin-right: 7px; }}
footer {{ margin-top: 26px; font-size: 13px; color: var(--faint); max-width: 68ch; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
@media (max-width: 720px) {{
  .wrap {{ padding: 28px 14px 60px; }}
}}
</style>

<div class="wrap">
<header>
  <h1>As Driven</h1>
  <p class="lede">Which physical controls to fit, and how to shift, for an authentic
  drive. {total} cars, curated from manufacturer and homologation sources and
  verified in-sim. Where the evidence does not settle something, this says so
  rather than guessing.</p>
  <div class="stats">
    <div class="stat"><b>{total}</b><span>cars</span></div>
    <div class="stat"><b>{clutch_start}</b><span>need the clutch to pull away</span></div>
    <div class="stat"><b>{you_blip}</b><span>need you to blip</span></div>
    <div class="stat"><b>{open_any}</b><span>have something unestablished</span></div>
    <div class="stat"><b>{version}</b><span>dataset · {released}</span></div>
  </div>
</header>

<div class="controls">
  <input type="search" id="q" placeholder="Search a car, class or gearbox" aria-label="Search cars">
  <select id="f-actuation" aria-label="Filter by shifter">
    <option value="">Any shifter</option>
    <option value="h-pattern">H-pattern</option>
    <option value="sequential-stick">Sequential stick</option>
    <option value="sequential-paddles">Paddles</option>
  </select>
  <select id="f-start" aria-label="Filter by pulling away">
    <option value="">Pulling away: any</option>
    <option value="required">Clutch required</option>
    <option value="not-required">No clutch needed</option>
  </select>
  <select id="f-blip" aria-label="Filter by downshift blip">
    <option value="">Downshift: any</option>
    <option value="required">You blip</option>
    <option value="optional">Blip optional</option>
    <option value="not-required">No blip needed</option>
    <option value="unknown">Not established</option>
  </select>
  <span class="count" id="count"></span>
</div>

<div class="table-scroll">
<table>
  <thead><tr>
    <th scope="col">Car</th><th scope="col">Shifter</th>
    <th scope="col">Pulling away</th><th scope="col">Upshift</th>
    <th scope="col">Downshift</th><th scope="col">Wheel</th>
  </tr></thead>
  <tbody id="rows">
{rows}
  </tbody>
</table>
</div>
<p class="empty" id="empty" hidden>No car matches those filters.</p>

<div class="legend">
  <span><span class="tone tone-you">You do this</span></span>
  <span><span class="tone tone-car">The car does this</span></span>
  <span><span class="tone tone-optional">Your choice</span></span>
  <span><span class="tone tone-unknown">Not established</span></span>
</div>

<footer>Select a car for the mechanism it shares with others, where it departs
from that, and what a drive or a source would still have to settle. Simulator
behaviour that differs from the real car is recorded separately and never
overwrites it.</footer>
</div>

<script>
(function () {{
  var q = document.getElementById('q');
  var filters = ['actuation', 'start', 'blip'].map(function (name) {{
    return {{ name: name, node: document.getElementById('f-' + name) }};
  }});
  var rows = Array.prototype.slice.call(document.querySelectorAll('tr.car'));
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');

  function apply() {{
    var text = q.value.trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {{
      var ok = !text || row.dataset.search.indexOf(text) !== -1;
      filters.forEach(function (filter) {{
        var want = filter.node.value;
        if (ok && want && row.dataset[filter.name] !== want) {{ ok = false; }}
      }});
      row.hidden = !ok;
      var detail = row.nextElementSibling;
      if (!ok && detail) {{
        detail.hidden = true;
        row.setAttribute('aria-expanded', 'false');
      }}
      if (ok) {{ shown++; }}
    }});
    count.textContent = shown === rows.length
      ? rows.length + ' cars'
      : shown + ' of ' + rows.length + ' cars';
    empty.hidden = shown !== 0;
  }}

  function toggle(row) {{
    var detail = row.nextElementSibling;
    if (!detail) {{ return; }}
    var open = detail.hidden;
    detail.hidden = !open;
    row.setAttribute('aria-expanded', open ? 'true' : 'false');
  }}

  rows.forEach(function (row) {{
    row.addEventListener('click', function () {{ toggle(row); }});
    row.addEventListener('keydown', function (event) {{
      if (event.key === 'Enter' || event.key === ' ') {{
        event.preventDefault();
        toggle(row);
      }}
    }});
  }});
  q.addEventListener('input', apply);
  filters.forEach(function (filter) {{ filter.node.addEventListener('change', apply); }});
  apply();
}})();
</script>
"""
