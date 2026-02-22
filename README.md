# casemk — Divided Storage Case Generator

Generate OpenSCAD models for 3D-printed divided storage cases from item dimensions. Supports both repeated (grid) and multiple item types, constrained to a configurable footprint (e.g., 350×300 mm).

## Installation

```bash
poetry install
```

Or with optional YAML support for config files:

```bash
poetry install --extras yaml
```

## Usage

Run with `poetry run python -m casemk` or `poetry run casemk` (or activate the venv with `poetry shell` first).

### Single item (grid layout)

Auto-fit as many slots as possible within the footprint:

```bash
poetry run python -m casemk --item 30x20x15 --max 350x300 -o case.scad
```

Exact number of slots:

```bash
poetry run python -m casemk --item 25x25x10 --count 12 -o case.scad
```

### Multiple item types

```bash
poetry run python -m casemk --items "30x20x15:4, 40x30x20:2" --max 350x300 -o case.scad
```

### Fixed case dimensions

Force the case to exact outer dimensions (slots fit within):

```bash
poetry run python -m casemk --item 25x25x10 --case-size 350x300 -o case.scad
```

### Stackable cases

Add lip and recess so cases stack (bottom of one fits into top of another):

```bash
poetry run python -m casemk --item 30x20x15 --count 12 --stackable -o case.scad
```

Format: `WxLxH:count` per item (count defaults to 1 if omitted).

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--max` | 350x300 | Max footprint (WxL) in mm |
| `--case-size` | — | Fixed outer case dimensions (WxL) in mm; overrides --max |
| `--clearance` | 1.5 | Clearance per dimension (mm) |
| `--wall` | 2.0 | Wall thickness (mm) |
| `--divider` | 1.5 | Divider thickness (mm) |
| `--base` | 2.0 | Base/floor height (mm) |
| `--corner-radius` | 0 | Corner radius in mm (0 = sharp) |
| `--stackable` | off | Add lip and recess for stacking |
| `--stack-lip` | 2.0 | Stack lip inward extent (mm) |
| `--stack-clearance` | 0.3 | Stack fit clearance (mm) |

## Output

Produces an OpenSCAD `.scad` file. Open it in [OpenSCAD](https://openscad.org/), adjust if needed, then export to STL for slicing and 3D printing.

## Python API

Run examples with `poetry run python examples/example_usage.py` after `poetry install`.

```python
from casemk.config import Config, parse_dimensions
from casemk.geometry import assemble_case, render_to_file
from casemk.layout import compute_grid_layout, compute_mixed_layout

config = Config(max_footprint=(350, 300))
layout = compute_grid_layout(parse_dimensions("30x20x15"), config, count=12)
assembly = assemble_case(layout, config)
render_to_file(assembly, "case.scad")
```

## Requirements

- [Poetry](https://python-poetry.org/)
- Python 3.8+
- [SolidPython](https://github.com/SolidCode/SolidPython) (generates OpenSCAD code)
