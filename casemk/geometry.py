"""SolidPython geometry building for storage cases."""

from typing import List, Union

from solid import (
    cube,
    difference,
    linear_extrude,
    offset,
    rotate,
    scad_render_to_file,
    square,
    text,
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

    # Label text on top surface, in the label gap (reserved area)
    label_w, label_l = (0.0, 0.0) if config.label_size is None else config.label_size
    label_dir_x = config.label_dir == "X"
    text_depth = config.label_text_depth
    margin = 0.85  # use 85% of label area for text
    char_width_ratio = 0.6  # typical font: char width ≈ 0.6 * height

    label_texts = []
    for slot in slots:
        if not slot.label_text or slot.label_width is None:
            continue
        if label_dir_x:
            lx = wall + cavity_inset + slot.x + slot.width + config.divider_thickness
            ly = wall + cavity_inset + slot.y
            cx = lx + label_w / 2
            cy = ly + label_l / 2
        else:
            lx = wall + cavity_inset + slot.x + max(0, (slot.width - label_w) / 2)
            ly = wall + cavity_inset + slot.y + slot.length + config.divider_thickness
            cx = lx + label_w / 2
            cy = ly + label_l / 2

        # Scale text to fit within label area (label_size)
        # label_dir X: rotated 90°, text extents swap (size in X, n*0.6*size in Y)
        # label_dir Y: horizontal, text is n*0.6*size in X, size in Y
        n_chars = max(len(slot.label_text), 1)
        if label_dir_x:
            size_by_height = (label_l * margin) / (n_chars * char_width_ratio)
            size_by_width = label_w * margin
        else:
            size_by_height = label_l * margin
            size_by_width = (label_w * margin) / (n_chars * char_width_ratio)
        text_size = min(config.label_text_size, size_by_height, size_by_width)
        text_size = max(text_size, 2.5)  # minimum readable size

        txt = text(
            slot.label_text,
            size=text_size,
            halign="center",
            valign="center",
        )
        # Rotate so text reads correctly when viewing case from above
        # label_dir X: label to right of slot, rotate 90° so text runs along slot (vertical)
        # label_dir Y: label below slot, text runs horizontal (no rotation)
        txt_rotated = rotate([0, 0, 90 if label_dir_x else 0])(txt)
        txt_3d = linear_extrude(height=text_depth + 0.01)(txt_rotated)
        # Engrave into top surface (cut, not add)
        label_texts.append(translate([cx, cy, outer_z - text_depth])(txt_3d))

    if label_texts:
        tray = difference()(tray, union()(*label_texts))

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
