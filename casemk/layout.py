"""Layout algorithms for divided storage cases."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .config import Config


@dataclass
class SlotRect:
    """A single slot/cell in the layout."""

    x: float
    y: float
    width: float
    length: float
    height: float
    label_width: Optional[float] = None  # extra space for label to the right
    label_length: Optional[float] = None
    label_text: Optional[str] = None  # text to engrave in label area


@dataclass
class GridLayoutResult:
    """Result of grid layout computation."""

    cols: int
    rows: int
    cell_width: float
    cell_length: float
    cell_height: float
    slots: List[SlotRect]
    total_width: float
    total_length: float


@dataclass
class MixedLayoutResult:
    """Result of mixed layout computation."""

    slots: List[SlotRect]
    total_width: float
    total_length: float


def compute_grid_layout(
    item_dims: Tuple[float, float, float],
    config: Config,
    count: Optional[int] = None,
) -> GridLayoutResult:
    """
    Compute grid layout for repeated item type.

    Args:
        item_dims: (width, length, height) of item
        config: Configuration with max_footprint, clearance, etc.
        count: Optional max number of slots; if None, maximize within constraint

    Returns:
        GridLayoutResult with cols, rows, cell dimensions, and slot list

    Raises:
        ValueError: If item is larger than footprint
    """
    width, length, height = item_dims
    cell_w = width + config.clearance
    cell_l = length + config.clearance
    cell_h = height + config.clearance

    inner_x = config.max_x - 2 * config.wall_thickness
    inner_y = config.max_y - 2 * config.wall_thickness
    # Reduce available area for rounded corners (each corner loses r + safety margin)
    r = config.corner_radius
    if r > 0:
        corner_inset = r + 1.0  # +1mm safety to avoid cutting into rounded corners
        inner_x = max(0, inner_x - 2 * corner_inset)
        inner_y = max(0, inner_y - 2 * corner_inset)

    if cell_w > inner_x or cell_l > inner_y:
        raise ValueError(
            f"Item dimensions {width}x{length}x{height}mm (with clearance) "
            f"exceed max footprint {config.max_x}x{config.max_y}mm"
        )

    # Try both orientations: W×L and L×W
    def try_layout(cw: float, cl: float) -> Tuple[int, int]:
        cols = max(1, int((inner_x + config.divider_thickness) / (cw + config.divider_thickness)))
        rows = max(1, int((inner_y + config.divider_thickness) / (cl + config.divider_thickness)))
        return cols, rows

    cols_a, rows_a = try_layout(cell_w, cell_l)
    cols_b, rows_b = try_layout(cell_l, cell_w)

    cells_a = cols_a * rows_a
    cells_b = cols_b * rows_b

    if cells_a >= cells_b:
        cols, rows = cols_a, rows_a
        cell_width, cell_length = cell_w, cell_l
    else:
        cols, rows = cols_b, rows_b
        cell_width, cell_length = cell_l, cell_w

    total_cells = cols * rows
    if count is not None:
        total_cells = min(total_cells, count)
        # Adjust rows if we have a partial last row
        rows = (total_cells + cols - 1) // cols

    # Build slot list (may have partial last row)
    slots: List[SlotRect] = []
    actual_cols = 0
    for row in range(rows):
        cols_this_row = cols if (row + 1) * cols <= total_cells else total_cells - row * cols
        actual_cols = max(actual_cols, cols_this_row)
        for col in range(cols_this_row):
            x = col * (cell_width + config.divider_thickness)
            y = row * (cell_length + config.divider_thickness)
            slots.append(
                SlotRect(x=x, y=y, width=cell_width, length=cell_length, height=cell_h)
            )

    # Compute total dimensions from actual slot extent
    if slots:
        max_slot_x = max(s.x + s.width for s in slots)
        max_slot_y = max(s.y + s.length for s in slots)
        total_width = max_slot_x
        total_length = max_slot_y
    else:
        total_width = cell_width
        total_length = cell_length

    return GridLayoutResult(
        cols=actual_cols,
        rows=rows,
        cell_width=cell_width,
        cell_length=cell_length,
        cell_height=cell_h,
        slots=slots,
        total_width=total_width,
        total_length=total_length,
    )


def compute_mixed_layout(
    items: List[dict],
    config: Config,
) -> MixedLayoutResult:
    """
    Compute layout for multiple item types using first-fit row packing.

    Each item dict has: width, length, height, count (optional, default 1),
    label (optional): if True, reserve space for label next to bin (requires config.label_size).

    Returns:
        MixedLayoutResult with slot list and total dimensions
    """
    label_w, label_l = (0.0, 0.0) if config.label_size is None else config.label_size
    label_dir_x = config.label_dir == "X"  # X = right, Y = below

    # Flatten to list of (w, l, h, label_text) with count
    expanded: List[Tuple[float, float, float, Optional[str]]] = []
    for item in items:
        w = item["width"]
        l = item["length"]
        h = item["height"]
        cnt = item.get("count", 1)
        label_text = item.get("label")  # None or str
        cell_w = w + config.clearance
        cell_l = l + config.clearance
        cell_h = h + config.clearance
        for _ in range(cnt):
            expanded.append((cell_w, cell_l, cell_h, label_text))

    # Sort by area descending (largest first)
    expanded.sort(key=lambda x: x[0] * x[1], reverse=True)

    inner_x = config.max_x - 2 * config.wall_thickness
    inner_y = config.max_y - 2 * config.wall_thickness
    r = config.corner_radius
    if r > 0:
        corner_inset = r + 1.0  # +1mm safety to avoid cutting into rounded corners
        inner_x = max(0, inner_x - 2 * corner_inset)
        inner_y = max(0, inner_y - 2 * corner_inset)

    # Row-based packing: place slots left-to-right, top-to-bottom
    slots: List[SlotRect] = []
    row_y = 0.0
    row_height = 0.0
    row_x = 0.0
    max_x_used = 0.0
    max_y_used = 0.0

    for cw, cl, ch, label_text in expanded:
        has_label = label_text is not None
        slot_label_w = label_w if has_label else None
        slot_label_l = label_l if has_label else None
        if has_label and label_dir_x:
            # Label to the right (X)
            x_advance = cw + config.divider_thickness + label_w + config.divider_thickness
            effective_cl = max(cl, label_l)
        elif has_label and not label_dir_x:
            # Label below (Y)
            x_advance = max(cw, label_w) + config.divider_thickness
            effective_cl = cl + config.divider_thickness + label_l
        else:
            x_advance = cw + config.divider_thickness
            effective_cl = cl

        x_extent = x_advance - config.divider_thickness
        if x_extent > inner_x or effective_cl > inner_y:
            raise ValueError(
                f"Item {cw}x{cl}mm (with clearance) exceeds max footprint "
                f"{config.max_x}x{config.max_y}mm"
            )

        # Try to place in current row
        if row_x + x_advance <= inner_x + config.divider_thickness and effective_cl <= inner_y - row_y:
            # Fits in current row
            slots.append(
                SlotRect(
                    x=row_x, y=row_y, width=cw, length=cl, height=ch,
                    label_width=slot_label_w, label_length=slot_label_l,
                    label_text=label_text,
                )
            )
            row_x += x_advance
            row_height = max(row_height, effective_cl)
            slot_right = row_x - config.divider_thickness
            if has_label and label_dir_x:
                slot_right -= config.divider_thickness  # label area, no divider after it
            max_x_used = max(max_x_used, slot_right)
        else:
            # New row
            row_y += row_height + config.divider_thickness
            row_height = effective_cl
            row_x = 0.0
            if row_y + effective_cl > inner_y:
                raise ValueError(
                    f"Items do not fit in footprint {config.max_x}x{config.max_y}mm"
                )
            slots.append(
                SlotRect(
                    x=0.0, y=row_y, width=cw, length=cl, height=ch,
                    label_width=slot_label_w, label_length=slot_label_l,
                    label_text=label_text,
                )
            )
            row_x = x_advance
            slot_right = x_advance - config.divider_thickness
            if has_label and label_dir_x:
                slot_right -= config.divider_thickness
            max_x_used = max(max_x_used, slot_right)
        max_y_used = max(max_y_used, row_y + row_height)

    total_width = max_x_used
    total_length = max_y_used

    return MixedLayoutResult(
        slots=slots,
        total_width=total_width,
        total_length=total_length,
    )
