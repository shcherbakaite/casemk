"""Command-line interface for casemk."""

import argparse
import sys
from pathlib import Path

from .config import Config, parse_dimensions, parse_footprint
from .geometry import assemble_case, render_to_file
from .layout import compute_grid_layout, compute_mixed_layout


def parse_items_arg(s: str) -> list[dict]:
    """Parse '30x20x15:4, 40x30x20:2(70123-SD-1)' into list of item dicts.
    (LABEL) suffix reserves label space and inserts the text on each bin."""
    items = []
    for part in s.split(","):
        part = part.strip()
        label_text = None
        if ":" in part:
            dims_str, count_str = part.rsplit(":", 1)
            count_str = count_str.strip()
            if "(" in count_str:
                count_part, rest = count_str.split("(", 1)
                count = int(count_part.strip())
                label_text = rest.rstrip(")").strip() or None  # e.g. "70123-SD-1"
            else:
                count = int(count_str)
        else:
            dims_str = part
            count = 1
        w, l, h = parse_dimensions(dims_str.strip())
        items.append({"width": w, "length": l, "height": h, "count": count, "label": label_text})
    return items


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate divided storage case OpenSCAD models for 3D printing"
    )
    parser.add_argument(
        "--item",
        metavar="WxLxH",
        help="Single item dimensions (e.g. 30x20x15). Use with --count for exact slot count.",
    )
    parser.add_argument(
        "--count",
        type=int,
        metavar="N",
        help="Number of slots (single item mode). If omitted, maximize within footprint.",
    )
    parser.add_argument(
        "--items",
        metavar="SPEC",
        help='Multiple items: "30x20x15:4, 40x30x20:2" (dims:count per item)',
    )
    parser.add_argument(
        "--max",
        metavar="WxL",
        default="350x300",
        help="Max footprint in mm (default: 350x300)",
    )
    parser.add_argument(
        "--case-size",
        metavar="WxL",
        help="Fixed outer case dimensions in mm (overrides --max)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default="case.scad",
        help="Output .scad file (default: case.scad)",
    )
    parser.add_argument(
        "--clearance",
        type=float,
        default=1.5,
        help="Clearance per dimension in mm (default: 1.5)",
    )
    parser.add_argument(
        "--wall",
        type=float,
        default=2.0,
        help="Wall thickness in mm (default: 2.0)",
    )
    parser.add_argument(
        "--divider",
        type=float,
        default=1.5,
        help="Divider thickness in mm (default: 1.5)",
    )
    parser.add_argument(
        "--base",
        type=float,
        default=2.0,
        help="Base/floor height in mm (default: 2.0)",
    )
    parser.add_argument(
        "--corner-radius",
        type=float,
        default=0.0,
        metavar="R",
        help="Corner radius in mm, 0 = sharp (default: 0)",
    )
    parser.add_argument(
        "--stackable",
        action="store_true",
        help="Add lip and recess for stacking cases",
    )
    parser.add_argument(
        "--stack-lip",
        type=float,
        default=2.0,
        metavar="MM",
        help="Stack lip inner extent in mm (default: 2.0)",
    )
    parser.add_argument(
        "--stack-clearance",
        type=float,
        default=0.3,
        metavar="MM",
        help="Stack fit clearance in mm (default: 0.3)",
    )
    parser.add_argument(
        "--label-size",
        metavar="WxL",
        help="Label area size in mm for bins with (Label) in spec (e.g. 10x30)",
    )
    parser.add_argument(
        "--label-dir",
        choices=["X", "Y"],
        default="X",
        help="Label orientation: X = to the right (default), Y = below",
    )
    parser.add_argument(
        "--label-text-size",
        type=float,
        default=4.0,
        metavar="MM",
        help="Label text font size in mm (default: 4.0)",
    )
    parser.add_argument(
        "--label-text-depth",
        type=float,
        default=0.5,
        metavar="MM",
        help="Label engrave depth into top surface in mm (default: 0.5)",
    )

    args = parser.parse_args()

    if args.item and args.items:
        parser.error("Use either --item or --items, not both")
    if not args.item and not args.items:
        parser.error("Specify --item or --items")

    try:
        case_size = parse_footprint(args.case_size) if args.case_size else None
        label_size = parse_footprint(args.label_size) if args.label_size else None
        config = Config(
            max_footprint=parse_footprint(args.max),
            case_size=case_size,
            clearance=args.clearance,
            corner_radius=args.corner_radius,
            wall_thickness=args.wall,
            divider_thickness=args.divider,
            base_height=args.base,
            stackable=args.stackable,
            stack_lip_inner=args.stack_lip,
            stack_clearance=args.stack_clearance,
            label_size=label_size,
            label_dir=args.label_dir,
            label_text_size=args.label_text_size,
            label_text_depth=args.label_text_depth,
        )
        config.validate()
    except ValueError as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.item:
            item_dims = parse_dimensions(args.item)
            layout_result = compute_grid_layout(
                item_dims, config, count=args.count
            )
        else:
            items = parse_items_arg(args.items)
            if any(it.get("label") is not None for it in items) and config.label_size is None:
                parser.error("--label-size required when using (Label) in items spec")
            layout_result = compute_mixed_layout(items, config)
    except ValueError as e:
        print(f"Layout error: {e}", file=sys.stderr)
        sys.exit(1)

    assembly = assemble_case(layout_result, config)
    output_path = Path(args.output)
    if output_path.suffix.lower() != ".scad":
        output_path = output_path.with_suffix(".scad")
    render_to_file(assembly, str(output_path))
    print(f"Wrote {output_path} ({len(layout_result.slots)} slots)")
