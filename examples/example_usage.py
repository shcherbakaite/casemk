"""Example usage of casemk as a Python library."""

from pathlib import Path

from casemk.config import Config, parse_dimensions, parse_footprint
from casemk.geometry import assemble_case, render_to_file
from casemk.layout import compute_grid_layout, compute_mixed_layout

# Example 1: Single item, auto-fit grid
config = Config(
    max_footprint=(350, 300),
    clearance=1.5,
    wall_thickness=2.0,
    divider_thickness=1.5,
    base_height=2.0,
)
config.validate()

item_dims = parse_dimensions("30x20x15")
layout = compute_grid_layout(item_dims, config)
assembly = assemble_case(layout, config)
render_to_file(assembly, "example_grid_auto.scad")
print(f"Grid auto: {layout.cols}x{layout.rows} = {len(layout.slots)} slots")

# Example 2: Single item, exact count
layout2 = compute_grid_layout(item_dims, config, count=12)
assembly2 = assemble_case(layout2, config)
render_to_file(assembly2, "example_grid_12.scad")
print(f"Grid 12 slots: {layout2.cols}x{layout2.rows}")

# Example 3: Multiple item types
items = [
    {"width": 30, "length": 20, "height": 15, "count": 4},
    {"width": 40, "length": 30, "height": 20, "count": 2},
]
layout3 = compute_mixed_layout(items, config)
assembly3 = assemble_case(layout3, config)
render_to_file(assembly3, "example_mixed.scad")
print(f"Mixed: {len(layout3.slots)} slots")
