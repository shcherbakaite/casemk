"""SolidPython geometry building for storage cases."""

from typing import List, Union

from solid import (
    cube,
    difference,
    linear_extrude,
    offset,
    scad_render_to_file,
    square,
    translate,
    union,
)

from .config import Config
from .layout import GridLayoutResult, MixedLayoutResult, SlotRect


def build_base_tray(
    slots: List[SlotRect],
    total_width: float,
    total_length: float,
    config: Config,
):
    """Build the solid base tray (floor + perimeter walls) with slot cavities subtracted."""
    wall = config.wall_thickness
    base_h = config.base_height
    max_height = max(s.height for s in slots)

    if config.case_size is not None:
        outer_x, outer_y = config.case_size
    outer_z = base_h + max_height
    r = config.corner_radius

    if config.case_size is not None:
        pass  # outer_x, outer_y already set
    else:
        corner_inset = (r + 1.0) if r > 0 else 0
        corner_padding = 2 * corner_inset
        outer_x = total_width + 2 * wall + corner_padding
        outer_y = total_length + 2 * wall + corner_padding

    if r > 0:
        # Round only outer corners in XY plane: 2D offset + linear_extrude
        base_2d = square([outer_x - 2 * r, outer_y - 2 * r])
        rounded_2d = offset(r=r)(base_2d)
        outer_box = linear_extrude(height=outer_z)(rounded_2d)
    else:
        outer_box = cube([outer_x, outer_y, outer_z])

    # Subtract each slot cavity (use uniform depth so all slots are clearly visible)
    # Inset by corner_radius + safety margin so cavities don't cut into rounded corners
    cavity_inset = (r + 1.0) if r > 0 else 0
    cavities = []
    for slot in slots:
        cavity = translate([wall + cavity_inset + slot.x, wall + cavity_inset + slot.y, base_h])(
            cube([slot.width, slot.length, max_height + 0.01])  # +epsilon for clean cut
        )
        cavities.append(cavity)

    if cavities:
        tray = difference()(outer_box, union()(*cavities))
    else:
        tray = outer_box

    if config.stackable:
        lip_inner = config.stack_lip_inner
        lip_height = config.stack_lip_height
        clearance = config.stack_clearance

        # Top lip: extends INWARD from top (original design)
        if r > 0:
            outer_2d = offset(r=r)(square([outer_x - 2 * r, outer_y - 2 * r]))
        else:
            outer_2d = square([outer_x, outer_y])
        inner_2d = offset(r=-lip_inner)(outer_2d)
        lip_ring = difference()(outer_2d, inner_2d)

        lip_3d = translate([0, 0, outer_z])(linear_extrude(height=lip_height)(lip_ring))
        tray = union()(tray, lip_3d)

        # Bottom foot: extends DOWN with shape matching lip opening (negative of lip)
        # Foot fits into the lip opening and sits on the ledge
        foot_2d = offset(r=-(lip_inner + clearance))(outer_2d)
        foot_3d = translate([0, 0, -lip_height])(linear_extrude(height=lip_height)(foot_2d))
        tray = union()(tray, foot_3d)

    return tray


def assemble_case(
    layout_result: Union[GridLayoutResult, MixedLayoutResult],
    config: Config,
):
    """Assemble the complete case: base tray with slot cavities (dividers are implicit)."""
    slots = layout_result.slots
    total_width = layout_result.total_width
    total_length = layout_result.total_length

    case = build_base_tray(slots, total_width, total_length, config)
    return case


def render_to_file(assembly, filepath: str) -> None:
    """Render the assembly to an OpenSCAD .scad file."""
    scad_render_to_file(assembly, filepath)
